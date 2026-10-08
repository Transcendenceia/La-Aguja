import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'runtime'))
import tailscale_service as ts
from subprocess import CompletedProcess, TimeoutExpired


class TailscaleServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.patches = [patch.object(ts, name, self.folder / filename) for name, filename in
                        [('PLATFORM_DIR', '.'), ('CONFIG_FILE', 'tailscale.json'),
                         ('KEY_FILE', 'tailscale.key'), ('STATUS_FILE', 'status.json'),
                         ('RUN_DIR', 'daemon'), ('SOCKET_PATH', 'daemon/socket')]]
        for item in self.patches:
            item.start()
        self.addCleanup(self.temp.cleanup)
        for item in self.patches:
            self.addCleanup(item.stop)
        self.config = {'enabled': True, 'login_server': 'https://headscale.example.test',
                       'hostname': 'aguja-rescue', 'ssh': False, 'accept_routes': False}
        self.key = 'headscale-synthetic-private-key-1234'

    def prepare(self):
        ts.secure_write(ts.CONFIG_FILE, json.dumps(self.config))
        ts.secure_write(ts.KEY_FILE, self.key)

    def status(self, state='Running', online=True):
        return {'BackendState': state, 'Self': {'HostName': 'aguja-rescue', 'Online': online,
                                               'TailscaleIPs': ['100.70.0.45']}}

    def result(self, value='', rc=0, stderr=''):
        return CompletedProcess([], rc, value, stderr)

    def test_unlock_tailnet_restart_is_nonblocking_and_failure_not_unlock_failure(self):
        import boot
        with patch.object(boot.subprocess, 'run', return_value=self.result(rc=1)) as run:
            self.assertFalse(boot.restart_tailnet())
            self.assertIn('--no-block', run.call_args.args[0])
            self.assertFalse(run.call_args.kwargs['check'])
        with patch.object(boot.subprocess, 'run', side_effect=TimeoutExpired(['synthetic'], 1)):
            self.assertFalse(boot.restart_tailnet())

    def test_bad_server_or_types_rejected_without_secret_output(self):
        for config in (dict(self.config, login_server='https://secret:credential@example.test'),
                       dict(self.config, login_server='http://localhost'),
                       dict(self.config, ssh='true'), dict(self.config, hostname='bad_host')):
            with self.assertRaises(ValueError):
                ts.validate_config(config)

    def test_no_config_has_no_side_effects(self):
        with patch.object(ts.subprocess, 'run') as run:
            self.assertEqual(ts.main(), 0)
            run.assert_not_called()

    def test_disabled_erases_key_and_stops_only_managed_daemon(self):
        self.prepare()
        ts.secure_write(ts.CONFIG_FILE, json.dumps({'enabled': False}))
        with patch.object(ts.subprocess, 'run', return_value=self.result()) as run:
            self.assertEqual(ts.main(), 0)
            self.assertEqual(run.call_args.args[0], ['systemctl', 'stop', ts.DAEMON_UNIT])
        self.assertFalse(ts.KEY_FILE.exists())
        self.assertFalse(json.loads(ts.STATUS_FILE.read_text())['connected'])

    def test_private_write_does_not_follow_symlink(self):
        victim = self.folder / 'victim'
        victim.write_text('original')
        ts.KEY_FILE.symlink_to(victim)
        with self.assertRaises(ValueError):
            ts.secure_write(ts.KEY_FILE, 'replacement')
        self.assertEqual(victim.read_text(), 'original')

    def test_private_config_rejects_public_permissions(self):
        self.prepare()
        ts.CONFIG_FILE.chmod(0o644)
        with patch.object(ts.subprocess, 'run') as run:
            self.assertEqual(ts.main(), 1)
            run.assert_not_called()
        self.assertNotIn(self.key, ts.STATUS_FILE.read_text())

    def test_success_has_file_key_explicit_flags_and_no_secret_config(self):
        self.prepare()
        config = dict(self.config, auth_key=self.key)
        ts.secure_write(ts.CONFIG_FILE, json.dumps(config))
        observations = [self.status('NeedsLogin', False), self.status()]
        def run(command, **kwargs):
            self.assertNotIn(self.key, ' '.join(command))
            if 'up' in command:
                self.assertIn('--auth-key=file:' + str(ts.KEY_FILE), command)
                self.assertIn('--ssh=false', command)
                self.assertIn('--accept-routes=false', command)
                self.assertIn('--accept-dns=false', command)
                self.assertIn('--login-server=https://headscale.example.test', command)
                self.assertEqual(ts.KEY_FILE.read_text(), self.key)
                return self.result()
            return self.result(json.dumps(observations.pop(0)))
        with patch.object(ts, 'wait_for_network', return_value=True), \
             patch.object(ts, 'ensure_binaries', return_value=('tailscale', 'tailscaled')), \
             patch.object(ts, 'ensure_tailscaled', return_value=True), \
             patch.object(ts.subprocess, 'run', side_effect=run):
            self.assertEqual(ts.main(), 0)
        state = json.loads(ts.STATUS_FILE.read_text())
        self.assertTrue(state['connected'])
        self.assertFalse(state['ssh_verified'])
        self.assertEqual(state['identity_storage'], 'volatile')
        self.assertFalse(ts.KEY_FILE.exists())
        self.assertNotIn(self.key, ts.CONFIG_FILE.read_text() + ts.STATUS_FILE.read_text())
        self.assertEqual(ts.STATUS_FILE.stat().st_mode & 0o777, 0o644)

    def test_stale_ip_is_not_connected(self):
        for status in (self.status('NeedsLogin'), self.status('Stopped'), self.status(online=False)):
            with patch.object(ts.subprocess, 'run', return_value=self.result(json.dumps(status))):
                state = ts.retrieve_status('tailscale')
                self.assertEqual(state['ipv4'], '100.70.0.45')
                self.assertFalse(state['connected'])

    def test_no_network_retains_key_for_retry(self):
        self.prepare()
        with patch.object(ts, 'ensure_binaries', return_value=('tailscale', 'tailscaled')), \
             patch.object(ts, 'wait_for_network', return_value=False), \
             patch.object(ts, 'ensure_tailscaled') as daemon:
            self.assertEqual(ts.main(), 1)
            daemon.assert_not_called()
        self.assertEqual(ts.KEY_FILE.read_text(), self.key)

    def test_failed_up_cannot_leak_headscale_key_or_consume_retry_key(self):
        self.prepare()
        output = io.StringIO()
        with patch.object(ts.subprocess, 'run', return_value=self.result(rc=1, stderr=self.key)), \
             contextlib.redirect_stdout(output):
            success, error = ts.connect_tailscale('tailscale', self.config)
        self.assertFalse(success)
        self.assertNotIn(self.key, output.getvalue() + error)
        self.assertTrue(ts.KEY_FILE.exists())

    def test_timeout_retains_key(self):
        self.prepare()
        with patch.object(ts.subprocess, 'run', side_effect=TimeoutExpired(['synthetic'], 1)):
            success, error = ts.connect_tailscale('tailscale', self.config)
        self.assertFalse(success)
        self.assertTrue(ts.KEY_FILE.exists())

    def test_running_node_does_not_reuse_consumed_key(self):
        self.prepare()
        ts.KEY_FILE.unlink()
        with patch.object(ts, 'ensure_binaries', return_value=('tailscale', 'tailscaled')), \
             patch.object(ts, 'wait_for_network', return_value=True), \
             patch.object(ts, 'ensure_tailscaled', return_value=True), \
             patch.object(ts.subprocess, 'run', return_value=self.result(json.dumps(self.status()))) as run:
            self.assertEqual(ts.main(), 0)
            self.assertEqual(len(run.call_args_list), 1)
            self.assertNotIn('up', run.call_args.args[0])

    def test_missing_bundle_never_installs_at_boot(self):
        self.prepare()
        with patch.object(ts, 'ensure_binaries', return_value=(None, None)), \
             patch.object(ts.subprocess, 'run') as run:
            self.assertEqual(ts.main(), 1)
            run.assert_not_called()
        self.assertTrue(ts.KEY_FILE.exists())

    def test_route_supports_ipv6_only_network(self):
        with patch.object(ts.subprocess, 'run', side_effect=[self.result(), self.result('default via fd00::1')]) as run:
            self.assertTrue(ts.wait_for_network(1))
            self.assertEqual(run.call_args.args[0][1], '-6')

    def test_unknown_or_malformed_status_fails_closed(self):
        for value in ('invalid', '[]', '{"Self":null}', '{"BackendState":"Running","Self":{"Online":true,"TailscaleIPs":["invalid"]}}'):
            with patch.object(ts.subprocess, 'run', return_value=self.result(value)):
                self.assertFalse(ts.retrieve_status('tailscale')['connected'])


if __name__ == '__main__':
    unittest.main()
