"""Regression: CD/no-DATA boots must not crash the entire GTK application."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'runtime'))
from file_open import workspace_directory


class DesktopWorkspaceTests(unittest.TestCase):
    def test_denied_data_parent_uses_owner_workspace(self):
        # Python 3.13 Path.exists/is_dir can raise EACCES on a private parent.
        original = Path.is_dir
        with tempfile.TemporaryDirectory() as home:
            workspace = Path(home)/'workspace'
            workspace.mkdir()
            def is_dir(path):
                if path == Path('/data/workspace'):
                    raise PermissionError(13, 'Permission denied', str(path))
                return original(path)
            with patch.object(Path, 'home', return_value=Path(home)), patch.object(Path, 'is_dir', is_dir):
                self.assertEqual(workspace_directory(), workspace)

    def test_missing_or_unreadable_data_uses_home_without_changing_permissions(self):
        with tempfile.TemporaryDirectory() as home:
            before = Path(home).stat().st_mode
            with patch.object(Path, 'home', return_value=Path(home)), patch('file_open.os.access', side_effect=lambda p, mode: p == Path(home)):
                self.assertEqual(workspace_directory(), Path(home))
            self.assertEqual(Path(home).stat().st_mode, before)

    def test_accessible_data_remains_preferred(self):
        with patch.object(Path, 'is_dir', return_value=True), patch('file_open.os.access', return_value=True):
            self.assertEqual(workspace_directory(), Path('/data/workspace'))


if __name__ == '__main__':
    unittest.main()
