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
import agent_context
import activity
import recovery_keys
import recovery_state
import secret_inventory

KEY = '  SYNTHETIC LUKS Unicode ñ exact key  '
ENTRY = {'type': 'luks', 'label': 'Other computer', 'identifier': '', 'key': KEY}


class RecoveryIntegration(unittest.TestCase):
    def fixture(self, directory):
        source = Path(directory) / 'capsule.json'
        source.write_text(json.dumps({'format': recovery_keys.FORMAT, 'schema': 1, 'protection': 'plain', 'keys': [ENTRY]}))
        return source, Path(directory) / 'ram'

    def test_cache_is_private_exact_and_status_does_not_expose_keys(self):
        with tempfile.TemporaryDirectory() as folder:
            source, root = self.fixture(folder)
            state = recovery_state.unlock(source=source, root=root)
            self.assertTrue(state['loaded'])
            self.assertEqual(state['count'], 1)
            self.assertNotIn(KEY, json.dumps(state))
            self.assertEqual(recovery_state.cached(source, root), [ENTRY])
            self.assertEqual(root.stat().st_mode & 0o777, 0o700)
            self.assertEqual((root / 'keys.json').stat().st_mode & 0o777, 0o600)

    def test_changed_source_and_tampered_cache_do_not_reuse_old_keys(self):
        with tempfile.TemporaryDirectory() as folder:
            source, root = self.fixture(folder)
            recovery_state.unlock(source=source, root=root)
            original = source.read_bytes()
            source.write_text(original.decode().replace('Other computer', 'New computer'))
            self.assertFalse(recovery_state.status(source, root)['loaded'])
            with self.assertRaises(ValueError):
                recovery_state.cached(source, root)
            source.write_bytes(original)
            (root / 'keys.json').write_text('{}')
            with self.assertRaises(ValueError):
                recovery_state.cached(source, root)

    def test_symlinks_and_world_readable_caches_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            source, root = self.fixture(folder)
            unsafe = Path(folder) / 'link'
            unsafe.symlink_to(source)
            with self.assertRaises(ValueError):
                recovery_state.unlock(source=unsafe, root=root)
            recovery_state.unlock(source=source, root=root)
            (root / 'keys.json').chmod(0o644)
            with self.assertRaises(ValueError):
                recovery_state.cached(source, root)

    def test_no_capsule_is_absence_not_a_factory_credential(self):
        with tempfile.TemporaryDirectory() as folder:
            state = recovery_state.status(Path(folder) / 'missing', Path(folder) / 'ram')
            self.assertFalse(state['present'])
            self.assertFalse(state['loaded'])
            self.assertNotIn('keys', state)

    def test_inventory_checks_locations_without_reading_credential_bodies(self):
        with tempfile.TemporaryDirectory() as folder:
            secret = Path(folder) / 'api.json'
            secret.write_text(KEY)
            with patch.object(secret_inventory, 'SOURCES', {'api': str(secret)}), patch.object(recovery_state, 'status', return_value={'present': False}), patch.object(Path, 'read_text', side_effect=AssertionError('credential body read')):
                value = secret_inventory.inventory()
            self.assertTrue(value['sources'][0]['present'])
            self.assertFalse(value['values_displayed'])
            self.assertNotIn(KEY, json.dumps(value))

    def test_activity_redacts_exact_luks_keys_from_known_private_cache(self):
        def read(path, *args, **kwargs):
            if str(path) == '/run/aguja-recovery/keys.json':
                return json.dumps({'schema': 1, 'keys': [ENTRY]})
            raise FileNotFoundError()
        with patch.object(Path, 'read_text', read):
            secrets = activity.secret_values()
        self.assertIn(KEY, secrets)
        self.assertNotIn(KEY, activity.redact('diagnostic ' + KEY, secrets))

    def test_owner_context_survives_updates_and_managed_pointer_is_not_duplicated(self):
        with tempfile.TemporaryDirectory() as folder:
            workspace = Path(folder) / 'workspace'
            workspace.mkdir()
            canonical = Path(folder) / 'canonical.md'
            canonical.write_text('Current live context')
            owner = workspace / 'AGENTS.md'
            owner.write_text('Owner instructions: preserve my workflow.\n')
            owner.chmod(0o600)
            agent_context.ensure(workspace, canonical)
            agent_context.ensure(workspace, canonical)
            self.assertTrue(owner.read_text().startswith('Owner instructions: preserve my workflow.\n'))
            self.assertEqual(owner.read_text().count(agent_context.BEGIN), 1)
            self.assertIn('/usr/share/aguja/SECRETS.md', owner.read_text())
            self.assertEqual(owner.stat().st_mode & 0o777, 0o600)
            self.assertIn('Current live context', (workspace / 'CLAUDE.md').read_text())

    def test_context_does_not_follow_an_owner_symlink(self):
        with tempfile.TemporaryDirectory() as folder:
            workspace = Path(folder) / 'workspace'
            workspace.mkdir()
            outside = Path(folder) / 'outside.md'
            outside.write_text('Leave me unchanged')
            (workspace / 'AGENTS.md').symlink_to(outside)
            agent_context.ensure(workspace, outside)
            self.assertEqual(outside.read_text(), 'Leave me unchanged')


if __name__ == '__main__':
    unittest.main()
