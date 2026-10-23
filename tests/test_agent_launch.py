import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
import auth_pty,harness,updates


class NativeAgents(unittest.TestCase):
    def test_codex_embedded_launch_keeps_both_permission_modes(self):
        for mode in ('safe','unsafe'):
            _,args,_=harness.invocation('codex',mode)
            self.assertIn('--no-daemon',args)
            if mode=='unsafe':self.assertIn('--dangerously-bypass-approvals-and-sandbox',args)
            else:self.assertEqual(args[args.index('--sandbox')+1],'workspace-write')

    def test_explicit_remote_codex_is_not_given_an_incompatible_embedded_flag(self):
        _,args,_=harness.invocation('codex','unsafe',['--remote','unix:///synthetic/socket'])
        self.assertNotIn('--no-daemon',args)

    def test_google_login_method_is_selected_once_for_explicit_login_only(self):
        output=b'Select login method:\n\x1b[32m> 1. Google OAuth\x1b[0m\n  2. Use a Google Cloud project'
        for name,login in [('codex',True),('antigravity',False),('claude',True)]:
            self.assertIsNone(auth_pty.NativeLoginChoice(name,login).feed(output))
        choice=auth_pty.NativeLoginChoice('antigravity',True)
        self.assertIsNone(choice.feed(output[:15]));self.assertEqual(choice.feed(output[15:]),b'\r')
        self.assertIsNone(choice.feed(output))

    def test_nondefault_or_unrecognized_method_is_not_selected(self):
        choice=auth_pty.NativeLoginChoice('antigravity',True)
        self.assertIsNone(choice.feed(b'Select login method:\n  1. Google OAuth\n> 2. Use a Google Cloud project'))
        choice.feed(b'x'*20000);self.assertLessEqual(len(choice.buffer),8192)

    def metadata_archive(self,version):
        raw=json.dumps({'name':'@openai/codex','version':version}).encode();archive=io.BytesIO()
        with tarfile.open(fileobj=archive,mode='w:gz') as tar:
            info=tarfile.TarInfo('package/package.json');info.size=len(raw);tar.addfile(info,io.BytesIO(raw))
        return archive.getvalue()

    def test_mismatched_metadata_never_replaces_an_installed_manifest(self):
        self.check_metadata('0.160.0',False)

    def test_matching_metadata_is_installed_without_a_node_runtime(self):
        self.check_metadata('0.162.1',True)

    def check_metadata(self,version,valid):
        archive=self.metadata_archive(version)
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);cache=root/'cache';cache.mkdir();target=root/'opt/aguja/agents/codex/package.json'
            target.parent.mkdir(parents=True);target.write_bytes(b'previous')
            descriptor={'version':'0.162.1','url':'https://registry.npmjs.org/@openai/codex/-/codex-0.162.1.tgz','algorithm':'sha512','digest':hashlib.sha512(archive).hexdigest()}
            def fetch(url,destination,*args,**kwargs):destination.write_bytes(archive)
            with patch.object(updates.sources,'fetch',side_effect=fetch):
                if valid:
                    updates.install_codex_metadata(root,descriptor,cache)
                    self.assertEqual(json.loads(target.read_text())['version'],'0.162.1')
                    self.assertEqual(target.stat().st_mode&0o777,0o644)
                else:
                    with self.assertRaises(ValueError):updates.install_codex_metadata(root,descriptor,cache)
                    self.assertEqual(target.read_bytes(),b'previous')
            self.assertFalse(list(cache.iterdir()))


if __name__=='__main__':unittest.main()
