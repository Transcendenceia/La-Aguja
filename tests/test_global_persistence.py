"""Persistence boundaries and native progress, without touching a host device."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
import persistence as p


class GlobalPersistence(unittest.TestCase):
    def test_public_cli_elevates_only_its_own_arguments(self):
        with patch.object(os, 'geteuid', return_value=1000), patch.object(p.subprocess, 'call', return_value=0) as execute:
            self.assertEqual(p.main(['status','--json']),0)
        self.assertEqual(execute.call_args.args[0][-2:],['status','--json'])
        self.assertNotIn('persist',execute.call_args.args[0])
    def test_invalid_password_never_mutates_or_mounts(self):
        for secret in ('', 'short', 'abcdefgh\0', None):
            with patch.object(p, 'command') as execute:
                with self.assertRaises(ValueError):
                    p.save(secret)
                execute.assert_not_called()

    def test_nonlive_system_cannot_be_captured(self):
        with patch.object(Path, 'read_text', return_value='boot=installed'), patch.object(p, 'command') as execute:
            with self.assertRaises(ValueError):
                p.save('synthetic-test-key')
            execute.assert_not_called()

    def test_cd_status_reports_unavailable_without_writing(self):
        with patch.object(p.u, 'verify_persistent_target', side_effect=ValueError('CD')), patch.object(p, 'command') as execute:
            result = p.status()
            self.assertFalse(result['available'])
            execute.assert_not_called()

    def test_runtime_and_other_disks_are_not_included_but_personal_files_are(self):
        for path in ('data/workspace/private', 'config/private/profile', 'mnt/disk/work', 'run/token', 'proc/1/environ', 'var/cache/aguja-session-updates/download'):
            self.assertTrue(p.excluded(path), path)
        for path in ('etc/custom.conf', 'home/aguja/.codex/auth.json', 'root/work', 'opt/tool', 'var/lib/database'):
            self.assertFalse(p.excluded(path), path)

    def test_native_progress_contains_measurements_not_raw_names(self):
        events = []
        with patch.object(p, 'emit', side_effect=lambda stage, **values: events.append((stage, values))):
            p.measured([sys.executable, '-c', 'print("SECRET-NAME");print("12");print("100")'], 'compress')
        self.assertEqual([v['completed'] for _, v in events], [12, 100])
        self.assertNotIn('SECRET', json.dumps(events))

    def test_failed_native_copy_is_not_reported_as_success(self):
        with patch.object(p, 'emit'):
            with self.assertRaises(ValueError):
                p.measured([sys.executable, '-c', 'raise SystemExit(23)'], 'copy')

    def test_runtime_restore_copies_data_not_sockets_or_symlink_targets(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'source'
            source.mkdir()
            (source / 'config.json').write_text('synthetic')
            (source / 'daemon.pid').write_text('1')
            (source / 'elsewhere').symlink_to('/etc/passwd')
            with patch.object(os, 'chown'):
                p.copy_regular_tree(source, root / 'copy')
            self.assertEqual([f.name for f in (root / 'copy').iterdir()], ['config.json'])

    def test_pending_release_cannot_escape_owned_staging(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run / 'pending-release.json').write_text('{}')
            with patch.object(p.u, 'RUN', run), patch.object(p.u, 'metadata', return_value={'folder': '/etc'}):
                with self.assertRaises(ValueError):
                    p.pending_release()

    def test_password_is_stdin_only_for_crypto_commands(self):
        from types import SimpleNamespace
        with patch.object(p.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout=b'')) as execute:
            p.command(['cryptsetup', 'open', '--key-file', '-', '/synthetic/file', 'synthetic-map'], b'SYNTHETIC-PASSWORD')
        self.assertNotIn('SYNTHETIC-PASSWORD', repr(execute.call_args.args))
        self.assertEqual(execute.call_args.kwargs['input'], b'SYNTHETIC-PASSWORD')


if __name__ == '__main__':
    unittest.main()
