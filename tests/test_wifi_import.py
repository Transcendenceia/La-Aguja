import importlib.util
import io
import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('wifi_helper', Path(__file__).resolve().parents[1] / 'desktop/wifi-helper.py')
wifi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wifi)

class WifiImportTests(unittest.TestCase):
    def invoke(self, security='wpa-psk', password='SYNTHETIC:password with spaces ', rows=None):
        fields={'802-11-wireless-security.key-mgmt':security, '802-11-wireless.ssid':'Synthetic: Wi-Fi', '802-11-wireless-security.psk':password, '802-11-wireless.hidden':'yes'}
        def nm(args, **kwargs):
            self.assertEqual(args[:3], ['/usr/bin/nmcli', '--escape', 'no'])
            self.assertEqual(kwargs['env']['LC_ALL'], 'C')
            self.assertEqual(kwargs['timeout'], 20)
            if 'UUID,TYPE' in args:
                return rows if rows is not None else '00000000-1111-2222-3333-444444444444:802-11-wireless\n00000000-1111-2222-3333-555555555555:tun\n'
            if '802-11-wireless-security.psk' in args:
                self.assertIn('--show-secrets', args)
            return fields[args[args.index('-g')+1]]+'\n'
        output=io.StringIO()
        with patch.object(wifi.os,'geteuid',return_value=0), patch.object(wifi.sys,'argv',['helper.py']), patch.object(wifi.subprocess,'check_output',side_effect=nm), patch.object(wifi.sys,'stdout',output):
            wifi.main()
        return json.loads(output.getvalue())

    def test_personal_wifi_preserves_literal_values_and_ignores_other_active_connections(self):
        for security in ('wpa-psk','sae'):
            d=self.invoke(security)
            self.assertEqual(d['password'],'SYNTHETIC:password with spaces ')
            self.assertEqual(d['security'],security)
            self.assertTrue(d['hidden'])

    def test_open_and_unsupported_security(self):
        self.assertEqual(self.invoke('')['password'],'')
        for security in ('wpa-eap','ieee8021x','owe','none'):
            with self.assertRaisesRegex(ValueError,'Enterprise'):
                self.invoke(security)

    def test_missing_secrets_and_ambiguous_connections_do_not_succeed(self):
        for password in ('','--','<hidden>'):
            with self.assertRaisesRegex(ValueError,'llavero'):
                self.invoke(password=password)
        with self.assertRaisesRegex(ValueError,'única red'):
            self.invoke(rows='')
        with self.assertRaisesRegex(ValueError,'única red'):
            self.invoke(rows='00000000-1111-2222-3333-444444444444:wifi\n00000000-1111-2222-3333-555555555555:wifi\n')
