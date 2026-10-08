import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
import config
import network
import cockpit


class AccessAndPersistenceTests(unittest.TestCase):
    def test_stock_and_legacy_blank_have_working_default_but_key_only_stays_key_only(self):
        self.assertEqual(config.ssh_access(config.DEFAULTS), ('aguja', 'default'))
        self.assertEqual(config.ssh_access(config.DEFAULTS | {'ssh_password': ''}), ('aguja', 'default'))
        self.assertEqual(config.ssh_access(config.DEFAULTS | {'ssh_password': '', 'ssh_public_key': 'configured'}), (None, 'key'))
        self.assertEqual(config.ssh_access(config.DEFAULTS | {'ssh_password': 'synthetic-custom'}), ('synthetic-custom', 'custom'))

    def test_atomic_wifi_update_preserves_custom_access_and_comments(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'aguja.conf'
            target.write_text('# My notes\n[aguja]\nssh_password = synthetic-custom\nhostname = rescue-me\n')
            result = config.update(target, {'wifi_ssid': 'Test:# Network', 'wifi_password': 'synthetic%$#secret', 'wifi_hidden': 'yes'})
            self.assertEqual(result['ssh_password'], 'synthetic-custom')
            self.assertEqual(result['hostname'], 'rescue-me')
            self.assertTrue(target.read_text().startswith('# My notes\n'))
            self.assertIn('hidden=true', config.wifi_keyfile(result))
            self.assertEqual(result, config.load(target))

    def test_invalid_update_does_not_replace_live_configuration(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'aguja.conf'
            target.write_text('[aguja]\nssh_password = synthetic-custom\n')
            baseline = target.read_bytes()
            with self.assertRaises(ValueError):
                config.update(target, {'wifi_ssid': 'test', 'wifi_password': 'short'})
            self.assertEqual(target.read_bytes(), baseline)
            self.assertEqual(list(Path(folder).iterdir()), [target])


class NetworkWelcomeTests(unittest.TestCase):
    def state_with(self, addresses):
        def fake_output(*args, **kwargs):
            if args[:3] == ('ip', '-j', 'address'):
                return json.dumps(addresses)
            if args[0] == 'nmcli':
                return 'wlan0:wifi:connected\nenp0s1:ethernet:unavailable'
            if args[0] == 'systemctl':
                return 'active\nactive'
            if args[0] == 'busctl':
                return json.dumps({'type': 's', 'data': ['aguja-2.local']})
            return ''
        with patch.object(network, 'output', side_effect=fake_output), patch.object(network, 'session', return_value={'ssh_port': '2222', 'ssh_auth_mode': 'custom'}):
            return network.state()

    def test_loopback_is_not_network_and_live_ip_appears_later(self):
        loopback = {'ifname': 'lo', 'addr_info': [{'scope': 'host', 'local': '127.0.0.1', 'family': 'inet'}]}
        self.assertFalse(self.state_with([loopback])['connected'])
        wifi = {'ifname': 'wlan0', 'addr_info': [{'scope': 'global', 'local': '192.0.2.22', 'family': 'inet'}]}
        connected = self.state_with([loopback, wifi])
        self.assertTrue(connected['connected'])
        self.assertEqual(connected['addresses'][0]['ip'], '192.0.2.22')
        self.assertEqual(connected['mdns'], 'aguja-2.local')
        self.assertEqual(cockpit.ssh_command(connected['mdns'], connected['ssh_port']), 'ssh -p 2222 aguja@aguja-2.local')
        self.assertNotIn('password', connected)
        with patch('i18n.ui_language', return_value='es'):
            self.assertNotIn('aguja', cockpit.auth_label('custom').split('personalizada')[1])

    def test_nmcli_escaping_and_non_wifi_devices(self):
        self.assertEqual(network.fields(r'Test\:name:75:WPA2'), ['Test:name', '75', 'WPA2'])
        self.assertEqual(network.fields(r'back\\slash:75:WPA3'), ['back\\slash', '75', 'WPA3'])

    def test_countdown_opens_wifi_and_live_connection_cancels_it(self):
        class Screen:
            def timeout(self, value): pass
            def getch(self): return ord('1')
        with patch.object(cockpit.curses, 'curs_set'), patch.object(cockpit.curses, 'has_colors', return_value=False), patch.object(cockpit, 'draw'), patch.object(network, 'state', return_value={'connected': False}):
            self.assertEqual(cockpit.choose(Screen(), auto_setup=True, delay=0), 'wifi')
        with patch.object(cockpit.curses, 'curs_set'), patch.object(cockpit.curses, 'has_colors', return_value=False), patch.object(cockpit, 'draw'), patch.object(network, 'state', return_value={'connected': True}):
            self.assertEqual(cockpit.choose(Screen(), auto_setup=True, delay=0), 'shell')


if __name__ == '__main__':
    unittest.main()
