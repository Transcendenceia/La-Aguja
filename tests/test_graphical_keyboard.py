"""Console and graphical sessions must use the owner's same layout/variant."""
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'runtime'))
import gui_session


class GraphicalKeyboardTests(unittest.TestCase):
    def test_selected_keyboard_and_variant_are_independent_of_language(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory)/'keyboard'
            for layout, variant in [('es', ''), ('latam', 'nodeadkeys'), ('us', 'intl')]:
                config.write_text(f'# owner selection\nXKBLAYOUT="{layout}"\nXKBVARIANT="{variant}"\n')
                with patch.dict(os.environ, {'LANG': 'de_DE.UTF-8'}), patch('gui_session.subprocess.run') as run:
                    gui_session.apply_keyboard(config)
                args = run.call_args.args[0]
                self.assertEqual(args[args.index('-layout')+1], layout)
                self.assertEqual(args[args.index('-variant')+1], variant)
                self.assertEqual(args[args.index('-option')+1], '')

    def test_invalid_selection_is_never_executed_as_shell_or_keyboard_args(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory)/'keyboard'
            for text in ['XKBLAYOUT="$(touch /tmp/keyboard-injection)"',
                         'XKBLAYOUT="es"\nXKBVARIANT="intl"',
                         'XKBLAYOUT="es,us"']:
                config.write_text(text)
                with patch('gui_session.subprocess.run') as run:
                    with self.assertRaises(ValueError):
                        gui_session.apply_keyboard(config)
                    run.assert_not_called()

    def test_regular_session_applies_keyboard_before_opening_browser(self):
        order = []
        process = SimpleNamespace(terminate=lambda: None, wait=lambda **_: 0)
        with patch('gui_session.read_request', return_value={'action': 'browser', 'url': None}), \
             patch('gui_session.subprocess.Popen', return_value=process), \
             patch('gui_session.wait_window_manager'), \
             patch('gui_session.apply_keyboard', side_effect=lambda: order.append('keyboard')), \
             patch('gui_session.direct', side_effect=lambda *args: order.append('browser') or 0), \
             patch('gui_session.shutil.which', return_value=None), patch.dict(os.environ):
            self.assertEqual(gui_session.session(Path('/tmp/synthetic')), 0)
        self.assertEqual(order, ['keyboard', 'browser'])

    def test_shared_preference_refreshes_all_local_xorg_sessions(self):
        with tempfile.TemporaryDirectory() as directory:
            for pid, name, args in [
                ('123', 'Xorg', ['/usr/bin/Xorg', ':20', '-auth', '/tmp/normal/Xauthority']),
                ('124', 'Xorg', ['/usr/bin/Xorg', ':21', '-auth', '/run/oauth/Xauthority']),
                ('125', 'other', ['/usr/bin/other', ':22']),
                ('126', 'Xorg', []),
            ]:
                process = Path(directory)/pid
                process.mkdir()
                (process/'comm').write_text(name+'\n')
                (process/'cmdline').write_bytes('\0'.join(args).encode())
            with patch('gui_session.apply_keyboard') as apply:
                gui_session.apply_active_keyboards(directory)
            self.assertEqual(apply.call_count, 2)
            environments = [call.kwargs['environment'] for call in apply.call_args_list]
            self.assertEqual({env['DISPLAY'] for env in environments}, {':20', ':21'})
            self.assertEqual({env['XAUTHORITY'] for env in environments},
                             {'/tmp/normal/Xauthority', '/run/oauth/Xauthority'})


if __name__ == '__main__':
    unittest.main()
