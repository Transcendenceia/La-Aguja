import importlib.machinery
import importlib.util
import io
import contextlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'runtime'))
import network_health as health


class NetworkHealthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = patch.object(health, 'STATUS', Path(self.temp.name) / 'status.json')
        self.state.start()
        self.addCleanup(self.state.stop)

    def test_working_dns_never_changes_network(self):
        with patch.object(health, 'resolves', return_value=True), patch.object(health, 'command') as command:
            self.assertTrue(health.check(True)['dns_ok'])
            command.assert_not_called()

    def test_recovers_only_after_gateway_answers_and_verifies_system_resolver(self):
        with patch.object(health, 'resolves', side_effect=[False, True]), \
             patch.object(health, 'tailnet_dns', return_value=False), \
             patch.object(health, 'candidates', return_value=[('eth0', '192.0.2.1')]), \
             patch.object(health, 'gateway_resolves', return_value=True), \
             patch.object(health, 'command', return_value=subprocess.CompletedProcess([], 0)) as command:
            self.assertEqual(health.check(True)['state'], 'recovered')
            self.assertEqual(command.call_args.args[0], ['nmcli', 'device', 'modify', 'eth0',
                             'ipv4.ignore-auto-dns', 'yes', 'ipv4.dns', '192.0.2.1'])

    def test_unreachable_gateway_and_magicdns_never_change_network(self):
        for magic in (True, False):
            with patch.object(health, 'resolves', return_value=False), \
                 patch.object(health, 'tailnet_dns', return_value=magic), \
                 patch.object(health, 'candidates', return_value=[('eth0', '192.0.2.1')]), \
                 patch.object(health, 'gateway_resolves', return_value=False), \
                 patch.object(health, 'command') as command:
                self.assertFalse(health.check(True)['dns_ok'])
                command.assert_not_called()

    def test_failed_recovery_rolls_back(self):
        with patch.object(health, 'resolves', return_value=False), \
             patch.object(health, 'tailnet_dns', return_value=False), \
             patch.object(health, 'candidates', return_value=[('eth0', '192.0.2.1')]), \
             patch.object(health, 'gateway_resolves', return_value=True), \
             patch.object(health, 'command', return_value=subprocess.CompletedProcess([], 0)) as command:
            self.assertFalse(health.check(True)['dns_ok'])
            self.assertEqual(command.call_args.args[0], ['nmcli', 'device', 'reapply', 'eth0'])

    def test_networkmanager_delayed_resolver_update_is_not_reverted(self):
        with patch.object(health, 'resolves', side_effect=[False, False, True]), \
             patch.object(health, 'tailnet_dns', return_value=False), \
             patch.object(health, 'candidates', return_value=[('eth0', '192.0.2.1')]), \
             patch.object(health, 'gateway_resolves', return_value=True), \
             patch.object(health.time, 'sleep'), \
             patch.object(health, 'command', return_value=subprocess.CompletedProcess([], 0)) as command:
            self.assertEqual(health.check(True)['state'], 'recovered')
            self.assertEqual(command.call_count, 1)

    def test_manual_dns_static_and_vpn_are_not_candidates(self):
        def result(value):
            return subprocess.CompletedProcess([], 0, value, '')
        routes = json.dumps([{'dev': 'eth0', 'gateway': '192.0.2.1'}])
        for kind, settings in [('ethernet', 'manual\n\nno\n'), ('ethernet', 'auto\n192.0.2.53\nno\n'),
                               ('ethernet', 'auto\n\nyes\n'), ('tun', 'auto\n\nno\n')]:
            with patch.object(health, 'command', side_effect=[result(routes), result(kind), result('uuid'), result(settings)]):
                self.assertEqual(health.candidates(), [])
        with patch.object(health, 'command', side_effect=[result(routes), result('ethernet'), result('uuid'), result('auto\n\nno\n')]):
            self.assertEqual(health.candidates(), [('eth0', '192.0.2.1')])

    def test_timeout_becomes_failure_without_printing_raw_errors(self):
        with patch.object(health.subprocess, 'run', side_effect=subprocess.TimeoutExpired('getent', 3)):
            self.assertFalse(health.resolves())


if __name__ == '__main__':
    unittest.main()
