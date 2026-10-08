"""Public runtime contracts: retired credentials inert, DNS failures still diagnosed."""
import contextlib
import importlib.machinery
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'runtime'))
loader = importlib.machinery.SourceFileLoader('public_cli', str(ROOT / 'runtime/aguja'))
spec = importlib.util.spec_from_loader(loader.name, loader)
cli = importlib.util.module_from_spec(spec)
loader.exec_module(cli)


class PublicRuntimeTests(unittest.TestCase):
    def test_retired_runtime_is_not_shipped(self):
        for filename in ('runtime/remote.py', 'runtime/tunnel.py', 'runtime/access.py',
                         'runtime/aguja-tunnel.service', 'connector/aguja_mcp.py'):
            self.assertFalse((ROOT / filename).exists(), filename)

    def test_dns_failure_is_reported_and_optional_agents_do_not_fail_health(self):
        for dns, expected in ((True, 0), (False, 1)):
            output = io.StringIO()
            with patch.object(cli.os, 'geteuid', return_value=0), \
                 patch.object(cli, 'load', return_value={'ssh_password': 'aguja', 'ssh_public_key': ''}), \
                 patch.object(cli.shutil, 'which', side_effect=lambda name: None if name in ('claude', 'agy') else '/usr/bin/'+name), \
                 patch.object(cli.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)), \
                 patch.object(cli.network, 'state', return_value={'connected': True}), \
                 patch('network_health.resolves', return_value=dns), contextlib.redirect_stdout(output):
                self.assertEqual(cli.doctor(['--json']), expected)
            result = json.loads(output.getvalue())
            self.assertEqual(result['dns_ok'], dns)
            self.assertNotIn('legacy_remote', result)
            self.assertFalse(result['tools']['claude'])

    def test_missing_optional_provider_does_not_launch_or_authorize_it(self):
        with patch.object(cli.shutil, 'which', return_value=None), \
             patch.object(cli.os, 'execvp') as launch, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.launch('claude', []), 127)
            launch.assert_not_called()
