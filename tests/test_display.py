"""Geometry, filtering, animation, VT safety and raster integration checks."""
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
import display
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class GeometryTests(unittest.TestCase):
    def test_responsive_rectangles_stay_inside_screen(self):
        for w,h in ((320,240),(640,480),(800,600),(1280,720),(1920,1080),(3840,2160)):
            geo = display.layout(w,h)
            for name in ('stream','sidebar','body'):
                box = geo[name]
                if box:
                    x0,y0,x1,y1 = box
                    self.assertTrue(0<=x0<x1<w)
                    self.assertTrue(0<=y0<y1<h)

    def test_untrusted_output_cannot_inject_terminal_or_bidi_controls(self):
        self.assertEqual(display.clean('\x1b[31mred\x1b[0m\x1b]0;fake title\x07\x00\u202esecret'),'red  secret')

    def test_process_tree_survives_exit_race_and_cycles(self):
        procs = [{'pid':2,'ppid':1,'command':'shell'}, {'pid':3,'ppid':2,'command':'worker'},
                 {'pid':4,'ppid':5,'command':'cycle A'}, {'pid':5,'ppid':4,'command':'cycle B'}]
        rows=display.process_rows(procs)
        self.assertEqual(len(rows),4)
        self.assertIn('↳ 3',rows[1][0])

    def test_activity_protocol_names_and_ended_session_count(self):
        rows=display.event_rows([{'time':0,'kind':'command_start','text':'lsblk'},
                                 {'time':0,'kind':'session_start','text':'SSH connected'}])
        self.assertEqual(rows[0][1:],('$ lsblk','command'))
        self.assertEqual(rows[1][2],'connect')
        self.assertEqual(len(display.active_sessions({'sessions':[{'status':'active'},{'status':'ended'}]})),1)

    def test_animation_changes_expression_for_idle_busy_and_arrival(self):
        self.assertNotEqual(display.expression_at(0),display.expression_at(1.2))
        self.assertNotEqual(display.expression_at(1,True),display.expression_at(6,True))
        self.assertEqual(display.expression_at(.2,connected=True),'surprise')


class PixelSafetyTests(unittest.TestCase):
    def setUp(self):
        self.v=display.VarInfo()
        self.f=display.FixInfo()
        self.v.xres=self.v.xres_virtual=640
        self.v.yres=self.v.yres_virtual=480
        self.v.bits_per_pixel=32
        for field,offset in ((self.v.red,16),(self.v.green,8),(self.v.blue,0)):
            field.length=8
            field.offset=offset
        self.f.visual=2
        self.f.line_length=640*4
        self.f.smem_len=640*480*4

    def test_valid_bgrx_and_pitch_padding(self):
        self.assertEqual(display.pixel_format(self.v,self.f),'BGRX')
        self.f.line_length += 16
        self.f.smem_len=self.f.line_length*480
        self.assertEqual(display.pixel_format(self.v,self.f),'BGRX')

    def test_alpha_channel_remains_opaque(self):
        self.v.transp.length=8
        self.v.transp.offset=24
        self.assertEqual(display.pixel_format(self.v,self.f),'BGRA')
        if HAS_PIL:
            self.assertEqual(Image.new('RGB',(1,1),(255,0,0)).convert('RGBA').tobytes('raw','BGRA'), b'\x00\x00\xff\xff')

    def test_reject_non_truecolour_bad_pitch_and_memory(self):
        for mutate in (lambda: setattr(self.f,'visual',3),lambda: setattr(self.f,'line_length',1),
                       lambda: setattr(self.f,'smem_len',10),lambda: setattr(self.v,'xoffset',100),
                       lambda: setattr(self.v,'bits_per_pixel',16),lambda: setattr(self.v.red,'length',5)):
            self.setUp()
            mutate()
            with self.assertRaises(ValueError):
                display.pixel_format(self.v,self.f)

    def test_remote_pty_never_maps_framebuffer(self):
        with patch.object(display.os,'ttyname',return_value='/dev/pts/0'),patch.object(display.os,'open') as opened:
            with self.assertRaises(OSError):
                display.Framebuffer()
            opened.assert_not_called()

    @unittest.skipUnless(HAS_PIL,'Pillow optional on build host')
    def test_present_respects_offsets_and_does_not_overwrite_pitch_padding(self):
        fb=display.Framebuffer.__new__(display.Framebuffer)
        fb.width,fb.height=2,2
        fb.var=self.v
        fb.var.xoffset=1
        fb.var.yoffset=1
        fb.fix=self.f
        fb.fix.line_length=20
        fb.raw_mode='BGRX'
        fb.fd=123
        pixels=bytearray(b'\xaa'*100)
        def write(fd,data,offset):
            self.assertEqual(fd,123)
            pixels[offset:offset+len(data)]=data
            return len(data)
        with patch.object(display.os,'pwrite',side_effect=write) as writer:
            fb.present(Image.new('RGB',(2,2),(255,0,0)))
        self.assertEqual(writer.call_count,2)
        self.assertEqual(pixels[24:32],b'\x00\x00\xff\x00'*2)
        self.assertEqual(pixels[44:52],b'\x00\x00\xff\x00'*2)
        self.assertEqual(pixels[32:44],b'\xaa'*12)
        self.assertEqual(pixels[:24],b'\xaa'*24)

    def test_short_writes_do_not_drop_pixels_or_repeat_offsets(self):
        fb=display.Framebuffer.__new__(display.Framebuffer)
        fb.fd=123
        received=bytearray()
        def write(fd,data,offset):
            self.assertEqual(offset,10+len(received))
            received.extend(data[:2])
            return min(2,len(data))
        with patch.object(display.os,'pwrite',side_effect=write):
            fb._write_pixels(b'abcdefg',10)
        self.assertEqual(received,b'abcdefg')

    def test_zero_length_write_fails_to_allow_text_fallback(self):
        fb=display.Framebuffer.__new__(display.Framebuffer)
        fb.fd=123
        with patch.object(display.os,'pwrite',return_value=0):
            with self.assertRaises(OSError):
                fb._write_pixels(b'pixels',0)


@unittest.skipUnless(HAS_PIL,'Pillow optional on build host')
class RasterTests(unittest.TestCase):
    def setUp(self):
        self.current={'addresses':[{'ip':'192.0.2.1'}], 'ssh_port':22, 'ssh_active':True,
                      'mdns':'aguja.local','ssh_auth_mode':'default'}
        self.activity={'sessions':[{'user':'aguja','peer':'192.0.2.20','command':'lsblk'}],
                       'events':[{'time':0,'kind':'command_start','text':'lsblk'},
                                 {'time':1,'kind':'output','text':'x'*400+'\nresult'}],
                       'processes':[{'pid':10,'ppid':1,'command':'lsblk','state':'R'}]}

    def test_all_views_and_dimensions_render_without_device_access(self):
        with patch.object(display.os,'open',side_effect=AssertionError('Unexpected device access')):
            for dims in ((320,240),(640,480),(1280,720),(1920,1080)):
                for view in ('activity','processes','help'):
                    image=display.render(*dims,self.current,self.activity,view=view,paused=True,scroll=2)
                    self.assertEqual(image.size,dims)
                    self.assertEqual(image.mode,'RGB')
                    self.assertGreater(len(image.getcolors(1_000_000)),20)

    def test_mascot_moves_and_animates_on_both_narrow_and_wide_screens(self):
        for dims in ((640,480),(1280,720)):
            first=display.render(*dims,self.current,self.activity,tick=0)
            next_frame=display.render(*dims,self.current,self.activity,tick=4)
            self.assertTrue(first.tobytes()!=next_frame.tobytes(),'Mascot frame did not change')

    def test_empty_network_and_missing_observer_still_render(self):
        image=display.render(1280,720,{}, {'available':False},countdown=12)
        self.assertEqual(image.size,(1280,720))


if __name__=='__main__':
    unittest.main()
