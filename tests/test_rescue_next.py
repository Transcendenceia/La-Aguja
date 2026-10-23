"""Regression checks for boot gating, credential locations and menu accessibility."""
import contextlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
import profile_vault as vault
import storage
import hardware
import display
import cockpit
import updates
import update_tasks


class Gate(unittest.TestCase):
    def test_graphical_question_uses_native_plymouth_without_agent_race(self):
        with patch.object(vault.subprocess,'run',return_value=subprocess.CompletedProcess([],0)), patch.object(vault,'command',return_value=subprocess.CompletedProcess([],0,stdout=b'synthetic-pass\n')) as command:
            self.assertEqual(vault.ask('fixed public prompt'),'synthetic-pass')
            command.assert_called_once_with(['plymouth','ask-for-password','--prompt=fixed public prompt'])

    def test_factory_and_automatic_skip_prompt(self):
        with tempfile.TemporaryDirectory() as folder:
            cfg = Path(folder)
            with patch.object(vault, 'CFG', cfg), patch.object(vault, 'VAULT', cfg/'vault'), patch.object(vault, 'private_root', return_value=None), patch.object(vault, 'ask') as ask:
                c, path, password, protection = vault.gate()
                self.assertIsNone(c)
                self.assertEqual(protection, 'none')
                ask.assert_not_called()

    def test_legacy_unlock_before_return_wrong_password_retries(self):
        import profile
        from test_platform_profile import capsule
        with tempfile.TemporaryDirectory() as folder:
            cfg = Path(folder)
            secret = 'synthetic-boot-secret'
            (cfg/'aguja-profile.json').write_bytes(profile.seal(capsule(), {'mode':'encrypted','passphrase':secret}))
            with patch.object(vault,'CFG',cfg), patch.object(vault,'VAULT',cfg/'vault'), patch.object(vault,'private_root',return_value=None), patch.object(vault,'ask',side_effect=['wrong', secret]):
                c, path, password, protection = vault.gate()
                self.assertEqual(protection, 'legacy-aes')
                self.assertEqual(password, secret)
                self.assertEqual(c['hostname'], 'aguja-test')

    def test_conversion_removes_inner_password_without_changing_the_original(self):
        import profile
        from test_platform_profile import capsule
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'aguja-profile.json'
            raw=profile.seal(capsule(),{'mode':'encrypted','passphrase':'synthetic-previous-pass'})
            path.write_bytes(raw)
            with patch.object(vault.getpass,'getpass',return_value='synthetic-previous-pass'):
                payload=vault.migration_payload([path])
            self.assertEqual(path.read_bytes(),raw)
            self.assertEqual(profile.open_capsule(payload[path.name])['hostname'],'aguja-test')
            self.assertEqual(json.loads(payload[path.name])['protection'],'plain')

    def test_cancelled_gate_cannot_continue(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'vault';path.write_bytes(b'LUKS')
            with patch.object(vault,'VAULT',path), patch.object(vault,'private_root',return_value=None), patch.object(vault,'ask',return_value=''):
                with self.assertRaises(ValueError):vault.gate()

    def test_open_vault_secret_only_in_stdin_and_cleanup_on_mount_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            cfg=Path(folder);image=cfg/'vault';image.write_bytes(b'LUKS')
            def fail(argv, **kwargs):
                self.assertNotIn('synthetic-secret', ' '.join(argv))
                if argv[0]=='mount':raise subprocess.CalledProcessError(1,argv)
            with patch.object(vault,'VAULT',image), patch.object(vault,'PRIVATE',cfg/'private'), patch.object(vault,'private_root',return_value=None), patch.object(vault,'command',side_effect=fail) as command:
                with self.assertRaises(subprocess.CalledProcessError):vault.open_vault('synthetic-secret')
                self.assertEqual(command.call_args_list[0].kwargs['input'],b'synthetic-secret')
                self.assertEqual(command.call_args_list[-1].args[0],['cryptsetup','close','aguja-profile'])

    def test_symlink_vault_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'link';path.symlink_to('/etc/passwd')
            with self.assertRaises(ValueError):vault.regular(path)

    def test_path_watcher_does_not_order_basic_target_after_boot(self):
        root=Path(__file__).resolve().parents[1]
        self.assertNotIn('After=aguja-boot.service',(root/'runtime/aguja-tailnet-save.path').read_text())

    def test_access_services_require_boot_gate_and_no_unlock_menu(self):
        root=Path(__file__).resolve().parents[1]
        install=(root/'scripts/install-runtime.sh').read_text()
        self.assertIn('Requires=aguja-boot.service',install)
        self.assertIn('chroot "$ROOT" passwd -l aguja',install)
        self.assertNotIn('unlock',cockpit.MENU_ACTIONS)
        unit=(root/'runtime/aguja-boot.service').read_text()
        self.assertIn('plymouth-quit.service',unit)
        self.assertIn('plymouth-quit-wait.service',unit)


class StorageAndInventory(unittest.TestCase):
    def test_no_vault_means_ram_not_unencrypted_usb_credentials(self):
        with patch.object(vault,'private_root',return_value=None):
            self.assertEqual(storage.configuration(),Path('/run/aguja-storage/storage/rclone.conf'))
            self.assertFalse(storage.status()['persistent'])
        with patch.object(vault,'private_root',return_value=Path('/config/private')):
            self.assertEqual(storage.configuration(),Path('/config/private/storage/rclone.conf'))

    def test_plan_is_observation_not_automatic_backup_or_partition(self):
        state={'storage':[],'available_bytes':1234}
        options=hardware.backup_options(state)
        self.assertFalse(options['automatic_action'])
        self.assertEqual(options['hardware'],state)
        self.assertEqual(len(options['options_in_preference_order']),7)
        self.assertIn('explicit',options['options_in_preference_order'][-1]['condition'])


class Menu(unittest.TestCase):
    def test_every_option_is_visible_and_clickable_at_all_supported_sizes(self):
        for width,height in [(640,480),(800,600),(1024,768),(1280,720),(1920,1080)]:
            for selected in range(len(cockpit.MENU)):
                boxes=display.menu_boxes(width,height,selected)
                self.assertIn(selected,[index for index,_ in boxes])
                for index,(x,y,r,b) in boxes:
                    self.assertTrue(0<=x<r<width)
                    self.assertTrue(0<=y<b<height)
                    control=type('Control',(),{'view':'help','menu_selected':selected})()
                    self.assertEqual(display.pointer_action(control,{}, {'action':'click','x':(x+r)/2,'y':(y+b)/2},width,height),cockpit.MENU_ACTIONS[index])

    def test_small_terminal_keeps_selection_visible(self):
        for capacity in (1,3,8,20):
            for selected in range(len(cockpit.MENU)):
                self.assertIn(selected,list(cockpit.menu_window(selected,capacity)))


class Release(unittest.TestCase):
    def test_new_rescue_is_first_and_reviewed_version_is_passed(self):
        inventory={'release':{'available':True,'current':'1.0.0','latest':'1.1.0'},'packages':[{'name':'curl','current':'1','latest':'2'}]}
        rows=update_tasks.rows(inventory)
        self.assertEqual(rows[0]['kind'],'release')
        with patch.object(updates,'release_update',return_value={'ok':True}) as upgrade:
            result=update_tasks.apply(rows,{'release:rescue':'persistent'})
            self.assertTrue(result['ok'])
            upgrade.assert_called_once_with(expected_version='1.1.0')

    def test_release_catalog_change_is_not_silently_accepted(self):
        with patch.object(updates,'lock',return_value=contextlib.nullcontext()), patch.object(updates.sources,'catalog',return_value=[{'version':'1.2.0'}]), patch.object(Path,'read_text',return_value='{}'), patch.object(updates,'capacity') as capacity:
            with self.assertRaisesRegex(ValueError,'catálogo cambió'):updates.release_update(expected_version='1.1.0')
            capacity.assert_not_called()
