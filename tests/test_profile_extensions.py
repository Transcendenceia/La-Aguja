import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
import profile_extensions as ext
import profile as profile

class ExtendedProfileTests(unittest.TestCase):
    def test_wifi_priorities_and_literal_keyfiles(self):
        rows=[dict(ssid='A #$; ñ',password='SYNTHETIC-ONLY',security='wpa-psk',country='ES',hidden=False),dict(ssid='B',password='',security='open',country='ES',hidden=True)]
        ext.validate({'wifi_profiles':rows})
        files=ext.wifi_keyfiles(rows)
        self.assertIn('autoconnect-priority=100',files['aguja-wifi.nmconnection'])
        self.assertIn('autoconnect-priority=99',files['aguja-wifi-2.nmconnection'])
        self.assertNotIn('[wifi-security]',files['aguja-wifi-2.nmconnection'])
        self.assertIn('hidden=true',files['aguja-wifi-2.nmconnection'])

    def test_storage_write_no_network_and_private_files(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'rclone.conf'
            rows=[dict(name='nas',type='smb',fields=dict(host='192.0.2.1',user='fixture',**{'pass':'SYNTHETIC-ONLY'}))]
            with patch('subprocess.run') as run:
                run.return_value.stdout=b'OBSCURED-FIXTURE\n'
                ext.storage_apply(rows,target)
                self.assertEqual(run.call_args.args[0],['rclone','obscure','-'])
                self.assertEqual(run.call_args.kwargs['input'],b'SYNTHETIC-ONLY')
            self.assertEqual(target.stat().st_mode&0o777,0o600)
            self.assertNotIn('SYNTHETIC-ONLY',target.read_text())

    def test_custom_environment_literals_and_provider_precedence(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)/'.config/aguja';root.mkdir(parents=True)
            (root/'custom-env.json').write_text(json.dumps({'CUSTOM':'$(not-run) $HOME','OPENAI_API_KEY':'CUSTOM-FIXTURE'}))
            (root/'provider-env.json').write_text(json.dumps({'codex':{'OPENAI_API_KEY':'PROVIDER-FIXTURE'}}))
            result=profile.provider_environment('codex',folder)
            self.assertEqual(result['CUSTOM'],'$(not-run) $HOME')
            self.assertEqual(result['OPENAI_API_KEY'],'PROVIDER-FIXTURE')

    def test_invalid_extensions(self):
        for value in ({'environment':{'BAD NAME':'value'}},{'tailscale':{'accept_dns':'yes'}},{'storage':[{'name':'bad','type':'sftp','fields':{'ssh':'command'}}]}):
            with self.assertRaises(ValueError):ext.validate(value)
