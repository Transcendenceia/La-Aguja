import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
import auth
import auth_pty
import activity

# Synthetic templates only. No authorization request or credentials in fixtures.
CLAUDE='https://claude.ai/oauth/authorize?client_id=aguja-fixture&response_type=code&state='+('S'*48)+'&code_challenge='+('C'*43)+'&redirect_uri=https%3A%2F%2Fclaude.ai%2Foauth%2Fcode'
GOOGLE='https://accounts.google.com/o/oauth2/v2/auth?client_id=aguja-fixture&response_type=code&state='+('G'*48)+'&code_challenge='+('P'*43)+'&scope=openid%20email'


class ProviderTests(unittest.TestCase):
    def test_exact_https_authorization_links_and_device_page(self):
        self.assertEqual(auth.provider(CLAUDE),'Claude Code')
        self.assertEqual(auth.provider(CLAUDE.replace('claude.ai/oauth','claude.com/cai/oauth')+'&code=true'),'Claude Code')
        self.assertIsNone(auth.provider(GOOGLE+'&code=true'))
        self.assertEqual(auth.provider(GOOGLE),'Antigravity')
        self.assertEqual(auth.provider(GOOGLE+'&redirect_uri=http%3A%2F%2Flocalhost%3A8123%2Fcallback'),'Antigravity')
        self.assertEqual(auth.provider('https://auth.openai.com/codex/device'),'Codex')
        for url in [CLAUDE.replace('https:','http:'),CLAUDE.replace('claude.ai/','claude.ai.evil.test/'),
                    CLAUDE.replace('claude.ai/','claude.ai@evil.test/'),CLAUDE.replace('/oauth/authorize','/docs'),
                    CLAUDE+'&access_token=private',CLAUDE+'&code=private',CLAUDE+'#private',CLAUDE+'\x1b',
                    'https://localhost/authorize','https://claude.ai/oauth/authorize',CLAUDE.replace('code_challenge='+('C'*43),'code_challenge=short')]:
            self.assertIsNone(auth.provider(url))
    def test_output_redaction_does_not_include_authorization_queries(self):
        text=activity.redact('aguja-auth-open '+CLAUDE,command=True)
        self.assertNotIn('state=',text);self.assertNotIn('S'*48,text)
        self.assertFalse(activity.safe_output('aguja login claude'))


class DetectorTests(unittest.TestCase):
    def test_split_stream_waits_for_complete_stable_url(self):
        d=auth.LinkDetector()
        split=CLAUDE.index('code_challenge=')+20
        d.feed(CLAUDE[:split].encode(),now=1)
        self.assertIsNone(d.poll(now=2))
        d.feed((CLAUDE[split:]+'\nPaste your code here: ').encode(),now=3)
        self.assertIsNone(d.poll(now=3.2))
        self.assertEqual(d.poll(now=3.5),CLAUDE)
        self.assertIsNone(d.poll(now=4))
    def test_osc_links_and_hard_wrapped_long_urls(self):
        for output in [('\x1b]8;;'+GOOGLE+'\x1b\\Click\x1b]8;;\x1b\\'),
                       '\x1b[32m'+GOOGLE[:95]+'\r\n'+GOOGLE[95:190]+'\r\n'+GOOGLE[190:]+'\x1b[0m\n\nPaste code: ']:
            d=auth.LinkDetector();d.feed(output.encode(),now=1)
            self.assertEqual(d.poll(now=2),GOOGLE)
    def test_memory_bounded_and_non_auth_urls_ignored(self):
        d=auth.LinkDetector();d.feed(b'x'*50000+b'https://claude.ai/docs\n',now=1)
        self.assertLessEqual(len(d.buffer),16384);self.assertIsNone(d.poll(now=2))


class VolatileHandoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name);self.patch=patch.object(auth,'BASE',self.base);self.patch.start()
    def tearDown(self):self.patch.stop();self.tmp.cleanup()
    def test_owner_only_native_code_not_stored_and_cleanup(self):
        s=auth.Session();self.assertTrue(s.offer(CLAUDE))
        p=s.directory/'request.json'
        self.assertEqual(p.stat().st_mode&0o777,0o600)
        self.assertEqual(s.directory.stat().st_mode&0o777,0o700)
        self.assertEqual(auth.current()['url'],CLAUDE)
        s.close();self.assertIsNone(auth.current());self.assertFalse(p.exists())
    def test_expiry_pid_reuse_permissions_and_symlinks_fail_closed(self):
        s=auth.Session();s.offer(CLAUDE);p=s.directory/'request.json';record=json.loads(p.read_text())
        for change in [{'expires':time.monotonic()-1},{'start_ticks':'not-the-process'},{'pid':999999999}]:
            p.write_text(json.dumps(dict(record,**change)));self.assertIsNone(auth.read_record(p))
        p.write_text(json.dumps(record));p.chmod(0o644);self.assertIsNone(auth.read_record(p));p.chmod(0o600)
        target=s.directory/'alias.json';target.symlink_to(p);self.assertIsNone(auth.read_record(target));target.unlink()
        s.close()
    def test_browser_hook_cannot_target_other_directory_or_pid(self):
        s=auth.Session();env={'AGUJA_AUTH_DIR':str(s.directory),'AGUJA_AUTH_PID':str(s.pid),'AGUJA_AUTH_STAMP':s.stamp}
        with patch.dict(os.environ,env):self.assertEqual(auth.capture_browser([GOOGLE]),0)
        with patch.dict(os.environ,dict(env,AGUJA_AUTH_DIR='/tmp')):self.assertEqual(auth.capture_browser([GOOGLE]),1)
        with patch.dict(os.environ,dict(env,AGUJA_AUTH_STAMP='wrong')):self.assertEqual(auth.capture_browser([GOOGLE]),1)
        s.close()
    def test_no_authorization_url_in_public_activity_data(self):
        s=auth.Session();s.offer(CLAUDE)
        public=json.dumps(activity.Monitor().data())
        self.assertNotIn(CLAUDE,public);self.assertNotIn('code_challenge',public)
        s.close()


class RelayContractTests(unittest.TestCase):
    def test_boot_permissions_survive_restrictive_service_umask(self):
        import importlib.util, subprocess
        spec=importlib.util.spec_from_file_location('boot_under_test',Path(__file__).resolve().parents[1]/'runtime/boot.py')
        boot=importlib.util.module_from_spec(spec);spec.loader.exec_module(boot)
        from types import SimpleNamespace
        def install_without_chown(*args):
            filtered=list(args[:4])+[args[-1]]
            return subprocess.run(filtered,check=True)
        with tempfile.TemporaryDirectory() as d:
            parent=Path(d)/'auth';mask=os.umask(0o077)
            try:
                with patch.object(boot,'run',side_effect=install_without_chown), patch('pwd.getpwnam',return_value=SimpleNamespace(pw_uid=os.getuid())):
                    boot.prepare_auth_runtime(parent)
            finally:os.umask(mask)
            self.assertEqual(parent.stat().st_mode&0o777,0o755)
            self.assertEqual((parent/str(os.getuid())).stat().st_mode&0o777,0o700)
    def test_noninteractive_and_machine_output_are_never_wrapped(self):
        with patch.object(os,'isatty',return_value=False):self.assertFalse(auth_pty.interactive(['claude']))
        with patch.object(os,'isatty',return_value=True):
            self.assertTrue(auth_pty.interactive(['claude','--dangerously-skip-permissions']))
            for argv in [['claude','-p','hi'],['agy','--print','hi'],['agy','--output-format=json'],['codex','exec','hi']]:
                self.assertFalse(auth_pty.interactive(argv))


class BrowserHelpTests(unittest.TestCase):
    def test_view_has_browser_steps_no_qr_or_private_url(self):
        record={'url':CLAUDE,'provider':'Claude Code','expires':time.monotonic()+600}
        text=' '.join(auth.terminal_lines(record,80,24))
        self.assertIn('Ctrl+]',text);self.assertIn('Ctrl+Shift+V',text)
        self.assertNotIn('QR',text);self.assertNotIn(CLAUDE,text)


if __name__=='__main__':unittest.main()
