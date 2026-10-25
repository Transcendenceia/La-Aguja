"""Regress the real GTK delete-event handler without requiring a display server."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock


class BusyWindowTests(unittest.TestCase):
    def test_close_is_consumed_and_progress_remains_visible_while_busy(self):
        source=ast.parse((Path(__file__).resolve().parents[1]/'runtime/desk.py').read_text())
        desk=next(node for node in source.body if isinstance(node,ast.ClassDef) and node.name=='Desk')
        method=next(node for node in desk.body if isinstance(node,ast.FunctionDef) and node.name=='close')
        gtk=SimpleNamespace(main_quit=Mock())
        namespace={'tr':lambda value:value,'Gtk':gtk}
        exec(compile(ast.Module(body=[method],type_ignores=[]),'desk.close','exec'),namespace)
        for action in (None,'persist-poweroff','persist-reboot','poweroff','reboot'):
            with self.subTest(action=action):
                window=SimpleNamespace(persist_active=True,status=SimpleNamespace(set_text=Mock()))
                if action:window.power_choice=SimpleNamespace(get_active_id=lambda:action)
                self.assertIs(namespace['close'](window),True)
                window.status.set_text.assert_called_once()
                self.assertIn('Saving' if action is None or action.startswith('persist-') else 'Finishing',window.status.set_text.call_args.args[0])
        gtk.main_quit.assert_not_called()
