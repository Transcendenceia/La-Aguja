"""Never execute a real power command on the test host."""
import io
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
import power as p

class PowerTests(unittest.TestCase):
    def baseline(self):
        self.enterContext(patch.object(os,'geteuid',return_value=0))
        self.enterContext(patch.object(Path,'read_text',return_value='boot=live'))
        self.enterContext(patch.object(os,'readlink',side_effect=['private','host']))
        self.enterContext(patch.object(p.persistence,'emit'))

    def test_success_orders_save_flush_power(self):
        self.baseline();events=[]
        with patch.object(p.persistence,'save',side_effect=lambda _:events.append('save') or 0),patch.object(os,'sync',side_effect=lambda:events.append('sync')),patch.object(p.subprocess,'run',side_effect=lambda *a,**k:events.append(a[0])):
            self.assertEqual(p.worker('persist-reboot','synthetic-password'),0)
        self.assertEqual(events,['save','sync',['systemctl','reboot']])

    def test_save_error_or_nonzero_never_powers(self):
        for fail in (ValueError('synthetic'),1):
            with self.subTest(fail=type(fail).__name__):
                with patch.object(os,'geteuid',return_value=0),patch.object(Path,'read_text',return_value='boot=live'),patch.object(os,'readlink',side_effect=['private','host']),patch.object(p.persistence,'save',side_effect=fail if isinstance(fail,Exception) else None,return_value=fail),patch.object(p.subprocess,'run') as run,patch.object(os,'sync') as sync:
                    with self.assertRaises(ValueError):p.worker('persist-poweroff','synthetic-password')
                    run.assert_not_called();sync.assert_not_called()

    def test_no_power_from_installed_system(self):
        with patch.object(os,'geteuid',return_value=0),patch.object(Path,'read_text',return_value='boot=installed'),patch.object(p.subprocess,'run') as run:
            with self.assertRaises(ValueError):p.worker('reboot')
            run.assert_not_called()

    def test_reject_shared_namespace_before_save(self):
        with patch.object(os,'geteuid',return_value=0),patch.object(Path,'read_text',return_value='boot=live'),patch.object(os,'readlink',return_value='host'),patch.object(p.persistence,'save') as save:
            with self.assertRaises(ValueError):p.worker('persist-reboot','synthetic-password')
            save.assert_not_called()

    def test_plain_power_does_not_snapshot(self):
        self.baseline()
        with patch.object(p.persistence,'save') as save,patch.object(os,'sync'),patch.object(p.subprocess,'run') as run:
            p.worker('poweroff');save.assert_not_called();self.assertEqual(run.call_args.args[0],['systemctl','poweroff'])

    def test_cancel_selection_or_confirmation_never_starts_child(self):
        import cockpit
        for answers in ([None],['persist-reboot',False]):
            with patch.object(cockpit,'option_dialog',side_effect=answers),patch.object(p.subprocess,'Popen') as start:
                self.assertEqual(p.console(),0);start.assert_not_called()

    def test_progress_and_command_never_include_password(self):
        self.assertIn('4.0 MiB',p.progress_text({'stage':'copy','completed':4194304,'unit':'bytes'}))
        self.assertIn('unshare',p.command('persist-reboot'))
        with self.assertRaises(ValueError):p.command('halt; sh')

if __name__=='__main__':unittest.main()
