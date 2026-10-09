import fcntl
import hashlib
import os
from pathlib import Path
import pty
import select
import socket
import struct
import subprocess
import sys
import tempfile
import termios
import time
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
import auth
import browser


class BrowserProtocolTests(unittest.TestCase):
    def test_chunked_binary_protocol_and_size_limit(self):
        data=bytes(range(256))*20
        wire=browser.frame(1,data)+browser.frame(2,b'12345678')
        buffer=bytearray();result=[]
        for index in range(0,len(wire),13):
            buffer.extend(wire[index:index+13]);result.extend(browser.frames(buffer))
        self.assertEqual(result,[(1,data),(2,b'12345678')]);self.assertFalse(buffer)
        with self.assertRaises(ValueError):browser.frames(bytearray(browser.HEADER.pack(0,browser.MAX_FRAME+1)))

    def test_same_native_pty_input_output_resize_and_permissions(self):
        with tempfile.TemporaryDirectory() as d:
            directory=Path(d);relay=browser.Relay(directory);master,slave=pty.openpty()
            old=termios.tcgetattr(slave);raw=termios.tcgetattr(slave);raw[3]&=~(termios.ICANON|termios.ECHO)
            termios.tcsetattr(slave,termios.TCSANOW,raw)
            client=socket.socket(socket.AF_UNIX);client.connect(str(relay.path));client.settimeout(1)
            try:
                self.assertEqual(relay.path.stat().st_mode&0o777,0o600)
                code=b'SYNTHETIC-CODE-'+b'Z'*1024
                dimensions=struct.pack('4H',32,110,0,0)
                client.sendall(browser.frame(1,code)+browser.frame(2,dimensions));relay.poll(master)
                received=os.read(slave,2048)
                self.assertEqual(hashlib.sha256(received).digest(),hashlib.sha256(code).digest())
                self.assertEqual(fcntl.ioctl(master,termios.TIOCGWINSZ,bytes(8)),dimensions)
                payload=b'\x00\xffNative CLI output\n';relay.output(payload);relay.poll(master)
                buffer=bytearray(client.recv(4096));self.assertIn((0,payload),browser.frames(buffer))
            finally:
                relay.close();client.close();termios.tcsetattr(slave,termios.TCSANOW,old)
                os.close(master);os.close(slave)
            self.assertFalse((directory/'console.sock').exists())

    def test_native_localhost_callback_preserved_but_invalid_target_rejected(self):
        url='https://auth.openai.com/oauth/authorize?client_id=fixture&response_type=code&state=SYNTHETIC&redirect_uri=http%3A%2F%2F127.0.0.1%3A8123%2Fcallback'
        self.assertEqual(auth.provider(url),'Codex')
        detector=auth.LinkDetector();detector.feed(url.encode(),now=1)
        self.assertEqual(detector.poll(now=2),url)
        for bad in ('0.0.0.0%3A8123','user%40localhost%3A8123','localhost','localhost%3A99999'):
            self.assertIsNone(auth.provider(url.replace('127.0.0.1%3A8123',bad)))

    def test_graphical_launch_only_local_normal_user(self):
        with patch.dict(os.environ,{'SSH_CONNECTION':'synthetic','AGUJA_LOCAL_CONSOLE':'1'}):
            self.assertFalse(browser.local_console())

    def test_browser_url_is_private_sandbox_intact_and_profile_removed(self):
        from types import SimpleNamespace
        url='https://auth.openai.com/oauth/authorize?client_id=fixture&state=SYNTHETIC&response_type=code'
        record={'url':url,'pid':os.getpid(),'start_ticks':auth.process_stamp(os.getpid())}
        class Selection:
            def close(self):pass
        calls=[];profile_paths=[]
        def spawn(argv,**_):
            calls.append(argv)
            if argv[0]=='chromium':
                self.assertNotIn(url,' '.join(argv))
                self.assertFalse(any(a in ('--no-sandbox','--disable-setuid-sandbox') for a in argv))
                page=Path(next(a for a in argv if a.startswith('--app=')).split('file://',1)[1])
                self.assertIn(url,page.read_text());self.assertEqual(page.stat().st_mode&0o777,0o600)
                profile_paths.append(page.parent)
            return SimpleNamespace(poll=lambda:0)
        with tempfile.TemporaryDirectory() as d,patch.object(auth,'read_record',return_value=record),\
             patch.object(browser,'SelectionOwners',Selection),patch.object(subprocess,'Popen',side_effect=spawn):
            # No clipboard process nor DOM interrogation is created. The code
            # remains in the provider page until the user explicitly pastes.
            self.assertEqual(browser.user_session(Path(d)),0)
        self.assertEqual([c[0] for c in calls],['openbox','xterm','chromium'])
        self.assertIn('-sb', calls[1])
        self.assertEqual(calls[1][calls[1].index('-sl')+1], '10000')
        self.assertFalse(any(p.exists() for p in profile_paths))

    def test_clipboard_owner_signal_never_auto_injects_code(self):
        selection=browser.SelectionOwners.__new__(browser.SelectionOwners)
        selection.owners=(0,)
        with patch.object(selection,'sample',side_effect=[(42,),(42,),(0,),(43,)]):
            self.assertTrue(selection.changed());self.assertFalse(selection.changed())
            self.assertFalse(selection.changed());self.assertTrue(selection.changed())

    def test_privileged_helper_rejects_arbitrary_directory_before_spawn(self):
        with tempfile.TemporaryDirectory() as d,patch.object(os,'getuid',return_value=0),\
             patch.dict(os.environ,{'SUDO_UID':str(os.getuid())}),patch.object(subprocess,'Popen') as spawn:
            self.assertEqual(browser.privileged_launch(Path(d)),1)
            spawn.assert_not_called()
        with patch.object(os,'getuid',return_value=0):self.assertFalse(browser.available())
        with patch.dict(os.environ,{},clear=True),patch.object(os,'ttyname',return_value='/dev/ttyS0'):
            self.assertFalse(browser.local_console())


class NativeRelayTests(unittest.TestCase):
    def test_immediate_input_exit_code_and_no_output_opening_outside_login(self):
        runtime=Path(__file__).resolve().parents[1]/'runtime'
        with tempfile.TemporaryDirectory() as d:
            source='import sys; print("https://auth.openai.com/codex/device",flush=True); line=sys.stdin.readline(); print("UNCHANGED:"+line.strip(),flush=True); sys.exit(7)'
            script='import sys,pathlib; sys.path.insert(0,'+repr(str(runtime))+'); import auth,auth_pty; auth.BASE=pathlib.Path('+repr(d)+'); raise SystemExit(auth_pty.run([sys.executable,"-c",'+repr(source)+'],"claude"))'
            master,slave=pty.openpty()
            process=subprocess.Popen([sys.executable,'-c',script],stdin=slave,stdout=slave,stderr=slave)
            os.close(slave);os.write(master,b'SYNTHETIC-EARLY-INPUT\n');output=bytearray();deadline=time.monotonic()+5
            while time.monotonic()<deadline:
                if select.select([master],[],[],.1)[0]:
                    try:data=os.read(master,65536)
                    except OSError:break
                    if not data:break
                    output.extend(data)
                if process.poll() is not None:break
            process.wait(timeout=2);os.close(master)
            self.assertEqual(process.returncode,7,output.decode(errors='replace'))
            self.assertIn(b'UNCHANGED:SYNTHETIC-EARLY-INPUT',output)
            self.assertNotIn(b'abriendo navegador',output)
            self.assertFalse(list(Path(d).glob('*/session-*')))


if __name__=='__main__':unittest.main()
