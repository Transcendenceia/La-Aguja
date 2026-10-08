import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("config", Path(__file__).resolve().parents[1] / "runtime/config.py")
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)


class ConfigTests(unittest.TestCase):
    def parse(self, value):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "aguja.conf"
            p.write_text(value)
            return config.load(p)

    def test_shell_text_stays_literal(self):
        c = self.parse('[aguja]\nwifi_ssid=Rescate #1\nwifi_password=$(touch /tmp/pwned)%$#;xx\nssh_password=a:b#;$%\n')
        self.assertEqual(c['wifi_ssid'], 'Rescate #1')
        self.assertEqual(c['wifi_password'], '$(touch /tmp/pwned)%$#;xx')
        self.assertIn('\\;', config.wifi_keyfile(c))

    def test_crlf_bom(self):
        self.assertEqual(self.parse('\ufeff[aguja]\r\nhostname=aguja-pc\r\n')['hostname'], 'aguja-pc')

    def test_reject_port_and_unknown(self):
        for value in ('ssh_port=0', 'ssh_port=65536', 'ssh_port=22;id', 'unknown=1'):
            with self.assertRaises(ValueError):
                self.parse('[aguja]\n' + value)

    def test_reject_multiline_secret(self):
        with self.assertRaises(ValueError):
            self.parse('[aguja]\nssh_password=abc\n def')

    def test_reject_weak_wifi(self):
        with self.assertRaises(ValueError):
            self.parse('[aguja]\nwifi_ssid=test\nwifi_password=short')

    def test_open_wifi(self):
        c = self.parse('[aguja]\nwifi_ssid=test\nwifi_security=open')
        self.assertNotIn('psk=', config.wifi_keyfile(c))

    def test_duplicate_keys_rejected(self):
        with self.assertRaises(Exception):
            self.parse('[aguja]\nssh_port=22\nssh_port=23')


if __name__ == '__main__':
    unittest.main()
