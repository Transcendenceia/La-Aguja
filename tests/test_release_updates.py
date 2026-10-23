"""Real multipart assembly and ISO/squashfs extraction, without host/USB writes."""
import contextlib,hashlib,json,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
import updates as u
@unittest.skipUnless(shutil.which('mksquashfs') and shutil.which('xorriso'),'native live archive tools required')
class ReleaseUpdates(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.p=Path(self.temp.name);self.data=self.p/'data';self.cfg=self.p/'cfg';self.root=self.data/'updates';self.cfg.mkdir();self.root.mkdir(parents=True);self.pin=self.p/'pin.json';self.pin.write_text('{}')
  self.patches=[patch.object(u,'DATA',self.data),patch.object(u,'CFG',self.cfg),patch.object(u,'ROOT',self.root),patch.object(u,'STATE',self.root/'state.json'),patch.object(u,'PIN',self.pin),patch.object(u,'lock',contextlib.nullcontext),patch.object(u,'capacity',lambda n:None),patch.object(u.Path,'read_text',autospec=True,side_effect=self.read_text)]
  for p in self.patches:p.start()
  root=self.p/'fixture-root';share=root/'usr/share/aguja';share.mkdir(parents=True);(share/'VERSION').write_text('1.0.1\n');(share/'update-protocol.json').write_text(json.dumps({'schema':1,'profile_schema':1,'config_partition':4,'data_partition':5}))
  tree=self.p/'iso/live';tree.mkdir(parents=True)
  subprocess.run(['mksquashfs',str(root),str(tree/'filesystem.squashfs'),'-noappend','-processors','1','-mem','16M','-no-progress'],check=True,capture_output=True)
  for n in ('vmlinuz','initrd.img'):(tree/n).write_bytes(b'SYNTHETIC-BOOT-NOT-A-HARDWARE-CLAIM')
  image=self.p/'fixture.iso';subprocess.run(['xorriso','-as','mkisofs','-o',str(image),str(tree.parent)],check=True,capture_output=True)
  with image.open('ab') as f:f.write(b'\0'*max(0,1048576-image.stat().st_size))
  raw=image.read_bytes();self.pieces=[raw[:len(raw)//2],raw[len(raw)//2:]]
  self.release={'version':'1.0.1','bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'parts':[{'url':'https://github.com/Fixture/La-Aguja/releases/download/v1.0.1/part'+str(i),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}for i,b in enumerate(self.pieces)]}
 def tearDown(self):
  for p in self.patches:p.stop()
  self.temp.cleanup()
 def fetch(self,url,target,*args,**kwargs):target.write_bytes(self.pieces[int(url[-1])])
 def test_verified_release_extracts_and_activates_only_completed_live_files(self):
  with patch.object(u.sources,'catalog',return_value=[self.release]),patch.object(u.sources,'fetch',self.fetch),patch.object(u.subprocess,'check_output',return_value='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'):
   result=u.release_update()
  self.assertTrue(result['ok']);self.assertTrue(result['reboot_required']);self.assertEqual(u.state()['active'],result['generation']);self.assertIn(result['generation'],(self.cfg/'aguja-update.cfg').read_text())
  folder=self.root/result['generation'];self.assertFalse((folder/'download.img').exists());self.assertFalse(list(folder.glob('part-*')));self.assertEqual(json.loads((folder/'manifest.json').read_text())['version'],'1.0.1')
 def read_text(self,path,*args,**kwargs):
  if str(path)=='/usr/share/aguja/VERSION':return '1.0.0'
  if str(path)=='/run/aguja-data-device':return '/dev/fixture5'
  # Sources read only public VERSION/pin; use open to avoid recursive mock.
  with path.open('r',encoding=kwargs.get('encoding','utf-8')) as f:return f.read()
 def test_corrupt_full_image_never_changes_boot_selection(self):
  bad={**self.release,'sha256':'0'*64}
  with patch.object(u.sources,'catalog',return_value=[bad]),patch.object(u.sources,'fetch',self.fetch):
   with self.assertRaises(ValueError):u.release_update()
  self.assertFalse((self.cfg/'aguja-update.cfg').exists());self.assertIsNone(u.state()['active'])
 def test_stage_only_verifies_image_without_changing_boot_selection(self):
  with patch.object(u.sources,'catalog',return_value=[self.release]),patch.object(u.sources,'fetch',self.fetch),patch.object(u,'activate') as activate:
   result=u.release_update(expected_version='1.0.1',stage_only=True)
  self.assertTrue(result['staged']);self.assertFalse(result['reboot_required']);activate.assert_not_called()
  self.assertFalse((self.cfg/'aguja-update.cfg').exists());self.assertIsNone(u.state()['active'])
  live=u.generation_live(result['generation']);self.assertTrue((live/'filesystem.squashfs').is_file())
if __name__=='__main__':unittest.main()
