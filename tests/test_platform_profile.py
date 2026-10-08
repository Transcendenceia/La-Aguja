import asyncio
import copy
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'runtime'))
import profile
spec = importlib.util.spec_from_file_location('platform_helper', ROOT / 'scripts/platform-profile.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def capsule():
    return {'schema': 1, 'hostname': 'aguja-test',
            'network': {'wifi': {'ssid': 'Test;$#', 'password': 'synthetic!pass', 'security': 'wpa-psk', 'country': 'ES', 'hidden': True},
                        'ethernet': {'method': 'manual', 'address': '192.0.2.44', 'prefix': 24, 'gateway': '192.0.2.1', 'dns': ['192.0.2.53']}},
            'ssh': {'password': 'synthetic-ssh', 'public_key': '', 'port': 2222},
            'providers': {'antigravity': {'mode': 'api', 'api_key': 'synthetic-gemini-key'}}, 'remote': {'enabled': False}}


class ProfileTests(unittest.TestCase):
    def test_plain_round_trip_and_literal_values(self):
        c = capsule()
        result = profile.open_capsule(profile.seal(c, {'mode': 'plain'}))
        self.assertEqual(result, profile.validate(c))
        self.assertEqual(profile.configuration(result, {})['wifi_password'], c['network']['wifi']['password'])
        keyfile = profile.ethernet_keyfile(result['network']['ethernet'])
        self.assertIn('address1=192.0.2.44/24,192.0.2.1', keyfile)
        self.assertIn('dns=192.0.2.53;', keyfile)

    def test_encrypted_roundtrip_wrong_passphrase_tamper_and_no_plain_secrets(self):
        try:
            import cryptography
        except ImportError:
            self.skipTest('cryptography missing')
        c = capsule()
        sealed = profile.seal(c, {'mode': 'encrypted', 'passphrase': 'synthetic-profile-pass'})
        self.assertNotIn(b'synthetic!pass', sealed)
        self.assertNotIn(b'synthetic-gemini-key', sealed)
        self.assertIsNone(profile.open_capsule(sealed))
        self.assertEqual(profile.open_capsule(sealed, 'synthetic-profile-pass'), profile.validate(c))
        with self.assertRaises(Exception):
            profile.open_capsule(sealed, 'different-passphrase')
        tampered = json.loads(sealed)
        raw = bytearray(profile.unb64(tampered['data'])); raw[0] ^= 1
        tampered['data'] = profile.b64(raw)
        with self.assertRaises(Exception):
            profile.open_capsule(json.dumps(tampered).encode(), 'synthetic-profile-pass')

    def test_reject_unknown_invalid_network_ssh_and_missing_oauth(self):
        cases = []
        for key, value in [('schema', 2), ('hostname', 'bad;hostname'), ('unexpected', True)]:
            c = capsule(); c[key] = value; cases.append(c)
        c = capsule(); c['network']['ethernet']['address'] = 'bad'; cases.append(c)
        c = capsule(); c['ssh']['port'] = True; cases.append(c)
        c = capsule(); c['ssh']['password'] = 'hidden\nvalue'; cases.append(c)
        c = capsule(); c['providers']['antigravity'] = {'mode': 'import', 'import_paths': []}; cases.append(c)
        for c in cases:
            with self.assertRaises((ValueError, TypeError)):
                profile.validate(c)

    def test_apis_written_privately_and_antigravity_actual_enable_setting(self):
        c = capsule()
        c['providers'] |= {'codex': {'mode': 'api', 'api_key': 'synthetic-openai'},
                           'claude': {'mode': 'api', 'api_key': 'synthetic-anthropic', 'model': 'synthetic-model'},
                           'opencode': {'mode': 'api', 'api_key': 'synthetic-zen'}}
        with tempfile.TemporaryDirectory() as folder:
            home, state = Path(folder) / 'home', Path(folder) / 'state'
            result = profile.apply(c, home, state)
            self.assertEqual(result['antigravity']['GEMINI_API_KEY'], 'synthetic-gemini-key')
            self.assertEqual(json.loads((home / '.gemini/antigravity-cli/settings.json').read_text())['modelProvider'], 'gemini')
            self.assertEqual(profile.provider_environment('claude', home)['ANTHROPIC_MODEL'], 'synthetic-model')
            for path in home.rglob('*'):
                if path.is_file():
                    self.assertEqual(path.stat().st_mode & 0o777, 0o700 if path.parent.name == 'bin' else 0o600)
            metadata = (state / 'status.json').read_text()
            self.assertNotIn('synthetic', metadata)

    def test_selective_import_drops_hooks_paths_and_rejects_symlinks(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            auth = home / '.codex/auth.json'; auth.parent.mkdir(); auth.write_text('{"tokens":{"access_token":"synthetic"}}')
            settings = home / '.codex/config.toml'; settings.write_text('model="test"\n[mcp_servers.unsafe]\ncommand="do-not-copy"\n')
            discovery = profile.discover('codex', home)
            self.assertTrue(discovery['portable'])
            c = capsule(); c['providers'] = {'codex': {'mode': 'import', 'import_paths': discovery['import_paths']}}
            out = profile.materialize_imports(c, home)
            self.assertNotIn('import_paths', out['providers']['codex'])
            self.assertNotIn(b'mcp_servers', profile.unb64(out['providers']['codex']['files']['.codex/config.toml']))
            auth.unlink(); auth.symlink_to(settings)
            with self.assertRaises(ValueError):
                profile.materialize_imports(c, home)
            self.assertFalse(profile.discover('antigravity', home)['portable'])

    def antigravity_files(self, home, data=None):
        data = data or {'token': {'access_token': 'synthetic-access', 'token_type': 'Bearer',
                                  'refresh_token': 'synthetic-refresh', 'expiry': '2020-01-01T00:00:00Z'},
                       'auth_method': 'consumer', 'id_token': 'synthetic-id'}
        auth = home / '.gemini/antigravity-cli/antigravity-oauth-token'
        auth.parent.mkdir(parents=True, exist_ok=True)
        auth.write_text(json.dumps(data)); auth.chmod(0o600)
        settings = auth.parent / 'settings.json'
        settings.write_text(json.dumps({'model': 'synthetic-model', 'modelProvider': 'gemini',
                                       'trustedWorkspaces': ['/never-export'], 'hooks': {'command': 'never-export'},
                                       'mcpServers': {'unsafe': 'never-export'}})); settings.chmod(0o600)
        return auth, settings, data

    def test_antigravity_native_oauth_private_roundtrip_and_no_api_switch(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder) / 'source'
            auth, settings, native = self.antigravity_files(home)
            discovery = profile.discover('antigravity', home)
            self.assertTrue(discovery['portable'])
            self.assertNotIn('synthetic', json.dumps(discovery))
            c = capsule(); c['providers'] = {'antigravity': {'mode': 'import', 'import_paths': discovery['import_paths']}}
            out = profile.materialize_imports(c, home)
            self.assertNotIn('import_paths', out['providers']['antigravity'])
            imported = out['providers']['antigravity']['files']
            self.assertEqual(json.loads(profile.unb64(imported[str(auth.relative_to(home))])), native)
            self.assertEqual(json.loads(profile.unb64(imported[str(settings.relative_to(home))])),
                             {'model': 'synthetic-model'})
            sealed = profile.seal(out, {'mode': 'encrypted', 'passphrase': 'synthetic-protection'})
            self.assertNotIn(b'synthetic-access', sealed)
            self.assertIsNone(profile.open_capsule(sealed))
            unlocked = profile.open_capsule(sealed, 'synthetic-protection')
            target = Path(folder) / 'target'
            self.assertEqual(profile.apply(unlocked, target, Path(folder) / 'state'), {})
            self.assertEqual(json.loads((target / auth.relative_to(home)).read_text()), native)
            self.assertNotIn('modelProvider', json.loads((target / settings.relative_to(home)).read_text()))
            for filename in imported:
                self.assertEqual((target / filename).stat().st_mode & 0o777, 0o600)
            self.assertEqual(profile.provider_environment('antigravity', target), {})
            # A token-only import resets an earlier API setting too.
            imported.pop(str(settings.relative_to(home)))
            (target / settings.relative_to(home)).write_text('{"modelProvider":"gemini"}')
            profile.apply(out, target, Path(folder) / 'state')
            self.assertEqual(json.loads((target / settings.relative_to(home)).read_text()), {})

    def test_antigravity_oauth_invalid_schema_errors_and_discovery_never_expose_values(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            auth, settings, valid = self.antigravity_files(home)
            cases = [[], {'token': 'synthetic-private-marker'}, {**valid, 'hooks': 'synthetic-private-marker'}]
            for field, value in [('access_token', None), ('refresh_token', ''), ('expiry', 'synthetic-private-marker'),
                                 ('expiry', '2026-13-01T00:00:00Z'), ('token_type', []), ('extra', 'synthetic-private-marker')]:
                data = copy.deepcopy(valid); data['token'][field] = value; cases.append(data)
            data = copy.deepcopy(valid); data['id_token'] = False; cases.append(data)
            cases += ['malformed-json']
            for data in cases:
                raw = b'{"synthetic-private-marker":' if isinstance(data, str) else json.dumps(data).encode()
                auth.write_bytes(raw)
                discovery = profile.discover('antigravity', home)
                self.assertFalse(discovery['portable'])
                self.assertEqual(discovery['import_paths'], [])
                self.assertNotIn('synthetic-private-marker', json.dumps(discovery))
                c = capsule(); c['providers'] = {'antigravity': {'mode': 'import', 'files': {
                    str(auth.relative_to(home)): profile.b64(raw)}}}
                with self.assertRaises(ValueError) as error:
                    profile.validate(c)
                self.assertNotIn('synthetic-private-marker', str(error.exception))
            auth.write_text(json.dumps(valid))
            settings.write_text('{"model":"synthetic-model", "modelProvider":"gemini", "mcpServers":{}}')
            self.assertTrue(profile.discover('antigravity', home)['portable'])
            settings.write_text('{"model": false}')
            self.assertEqual(profile.discover('antigravity', home)['import_paths'], [str(auth)])

    def test_antigravity_oauth_rejects_insecure_permissions_owner_and_symlink_parents(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder) / 'source'
            auth, settings, _ = self.antigravity_files(home)
            selected = profile.discover('antigravity', home)['import_paths']
            c = capsule(); c['providers'] = {'antigravity': {'mode': 'import', 'import_paths': selected}}
            for mode in (0o644, 0o660, 0o700, 0o200):
                auth.chmod(mode)
                self.assertFalse(profile.discover('antigravity', home)['portable'])
                with self.assertRaises(ValueError): profile.materialize_imports(c, home)
            auth.chmod(0o600)
            with patch.object(profile.os, 'getuid', return_value=os.getuid() + 1):
                self.assertFalse(profile.discover('antigravity', home)['portable'])
                with self.assertRaises(ValueError): profile.materialize_imports(c, home)
            saved = auth.parent / 'saved-token'; auth.rename(saved); auth.symlink_to(saved)
            self.assertFalse(profile.discover('antigravity', home)['portable'])
            with self.assertRaises(ValueError): profile.materialize_imports(c, home)
            auth.unlink(); saved.rename(auth)
            native_dir = auth.parent; relocated = home / 'relocated'
            native_dir.rename(relocated); native_dir.symlink_to(relocated, target_is_directory=True)
            self.assertFalse(profile.discover('antigravity', home)['portable'])
            with self.assertRaises(ValueError): profile.materialize_imports(c, home)

    def test_antigravity_apply_rejects_destination_symlink_before_auth_writes(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder) / 'source'
            auth, _, _ = self.antigravity_files(home)
            c = capsule(); c['providers'] = {'antigravity': {'mode': 'import', 'import_paths': [str(auth)]}}
            out = profile.materialize_imports(c, home)
            target, external = Path(folder) / 'target', Path(folder) / 'external'
            target.mkdir(); external.mkdir(); (target / '.gemini').symlink_to(external, target_is_directory=True)
            with self.assertRaises(ValueError): profile.apply(out, target, Path(folder) / 'state')
            self.assertEqual(list(external.iterdir()), [])

    def test_remote_no_owner_token_and_expired_device_does_not_break_profile(self):
        c = capsule()
        c['remote'] = {'enabled': True, 'relay_url': 'https://aguja.example.com', 'device_id': 'd' * 22,
                       'device_token': 't' * 32, 'e2e_key': profile.b64(bytes(32)),
                       'expires_at': '2020-01-01T00:00:00Z'}
        self.assertEqual(profile.validate(c)['remote'], {'enabled': False})
        c['remote']['owner_token'] = 'never-on-usb'
        self.assertEqual(profile.validate(c)['remote'], {'enabled': False})

    def test_protected_boot_locks_factory_access_before_unlock(self):
        import boot, config
        with patch.object(boot, 'run') as run, patch.object(boot, 'secure_write') as write:
            mode = boot.configure_owner_access(config.DEFAULTS, Path('/synthetic/home'), locked=True)
            self.assertEqual(mode, 'locked')
            write.assert_called_once_with(Path('/synthetic/home/.ssh/authorized_keys'), '')
            run.assert_called_once_with('passwd', '-l', 'aguja', stdout=subprocess.DEVNULL)
        with patch.object(boot, 'run') as run, patch.object(boot, 'secure_write'):
            self.assertEqual(boot.configure_owner_access(config.DEFAULTS, Path('/synthetic/home')), 'default')
            self.assertEqual(run.call_args.args, ('chpasswd',))
            self.assertEqual(run.call_args.kwargs['input'], 'aguja:aguja\n')

    def test_plain_runtime_updates_persist_capsule_and_encrypted_stays_sealed(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'profile.json'
            path.write_bytes(profile.seal(capsule(), {'mode': 'plain'}))
            self.assertTrue(profile.update_plain_settings(path, {'ssh_password': 'changed-ssh', 'wifi_hidden': 'no'}))
            result = profile.open_capsule(path.read_bytes())
            self.assertEqual(result['ssh']['password'], 'changed-ssh')
            self.assertFalse(result['network']['wifi']['hidden'])
            original = profile.seal(capsule(), {'mode': 'encrypted', 'passphrase': 'synthetic-protection'})
            path.write_bytes(original)
            self.assertFalse(profile.update_plain_settings(path, {'ssh_password': 'do-not-persist'}))
            self.assertEqual(path.read_bytes(), original)


class ImagePreparationTests(unittest.TestCase):
    def test_tailscale_requires_image_capability_before_credentials_export(self):
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder) / 'factory.img', Path(folder) / 'private.img'
            source.write_bytes(b'synthetic-fixture')
            c = capsule(); c['tailscale'] = {'enabled': True, 'auth_key': 'synthetic-headscale-key'}
            request = {'image_path': str(source), 'output_path': str(output), 'image_sha256': 'a' * 64, 'capsule': c}
            def marker_command(args, **kwargs):
                Path(args[-1]).write_text('{"features":["platform-profile-v1"]}')
            with patch.object(helper.shutil, 'which', return_value='/synthetic/mcopy'), \
                 patch.object(helper, 'sha256', return_value='a' * 64), \
                 patch.object(helper, 'config_partition', return_value=(0, 0)), \
                 patch.object(helper.subprocess, 'run', side_effect=marker_command), \
                 patch.object(helper, 'materialize_imports') as materialize:
                result = helper.prepare(request)
                self.assertFalse(result['ok'])
                self.assertIn('Tailscale/Headscale', result['error'])
                self.assertFalse(output.exists())
                materialize.assert_not_called()

    def test_locale_requires_image_capability_before_any_credentials_export(self):
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder) / 'factory.img', Path(folder) / 'private.img'
            source.write_bytes(b'synthetic-fixture')
            c = capsule(); c['locale'] = dict(profile.DEFAULT_LOCALE)
            request = {'image_path': str(source), 'output_path': str(output), 'image_sha256': 'a' * 64, 'capsule': c}
            def marker_command(args, **kwargs):
                Path(args[-1]).write_text('{"version":"0.4.1","features":["platform-profile-v1","antigravity-oauth-file-v1"]}')
            with patch.object(helper.shutil, 'which', return_value='/synthetic/mcopy'), \
                 patch.object(helper, 'sha256', return_value='a' * 64), \
                 patch.object(helper, 'config_partition', return_value=(0, 0)), \
                 patch.object(helper.subprocess, 'run', side_effect=marker_command), \
                 patch.object(helper, 'materialize_imports') as materialize:
                result = helper.prepare(request)
                self.assertFalse(result['ok'])
                self.assertIn('0.4.3', result['error'])
                self.assertFalse(output.exists())
                materialize.assert_not_called()

    def test_chinese_requires_new_catalog_before_credentials_export_before_any_credentials_export(self):
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder) / 'factory.img', Path(folder) / 'private.img'
            source.write_bytes(b'synthetic-fixture')
            c = capsule(); c['locale'] = {'language':'zh_CN.UTF-8','keyboard':'cn','variant':''}
            request = {'image_path': str(source), 'output_path': str(output), 'image_sha256': 'a' * 64, 'capsule': c}
            def marker_command(args, **kwargs):
                Path(args[-1]).write_text('{"version":"0.6.1","features":["platform-profile-v1","antigravity-oauth-file-v1","locale-profile-v1"]}')
            with patch.object(helper.shutil, 'which', return_value='/synthetic/mcopy'), \
                 patch.object(helper, 'sha256', return_value='a' * 64), \
                 patch.object(helper, 'config_partition', return_value=(0, 0)), \
                 patch.object(helper.subprocess, 'run', side_effect=marker_command), \
                 patch.object(helper, 'materialize_imports') as materialize:
                result = helper.prepare(request)
                self.assertFalse(result['ok'])
                self.assertIn('0.7.0', result['error'])
                self.assertFalse(output.exists())
                materialize.assert_not_called()

    def test_antigravity_requires_image_capability_before_export_and_safe_error(self):
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder) / 'factory.img', Path(folder) / 'private.img'
            source.write_bytes(b'synthetic-fixture')
            c = capsule(); c['providers'] = {'antigravity': {'mode': 'import', 'import_paths': [
                '/synthetic-home/.gemini/antigravity-cli/antigravity-oauth-token']}}
            request = {'image_path': str(source), 'output_path': str(output), 'image_sha256': 'a' * 64, 'capsule': c}
            def marker_command(args, **kwargs):
                Path(args[-1]).write_text('{"features":["platform-profile-v1"]}')
            with patch.object(helper.shutil, 'which', return_value='/synthetic/mcopy'), \
                 patch.object(helper, 'sha256', return_value='a' * 64), \
                 patch.object(helper, 'config_partition', return_value=(0, 0)), \
                 patch.object(helper.subprocess, 'run', side_effect=marker_command), \
                 patch.object(helper, 'materialize_imports') as materialize:
                result = helper.prepare(request)
                self.assertFalse(result['ok'])
                self.assertIn('0.4.1', result['error'])
                self.assertNotIn('synthetic-home', json.dumps(result))
                self.assertFalse(output.exists())
                materialize.assert_not_called()

    @unittest.skipUnless(shutil.which('sgdisk') and shutil.which('mkfs.vfat') and shutil.which('mcopy'), 'GPT/FAT tools missing')
    def test_synthetic_image_prepare_original_unchanged_reject_existing_and_corrupt(self):
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder) / 'factory.img', Path(folder) / 'private.img'
            with open(source, 'wb') as stream: stream.truncate(96 * 1024 * 1024)
            subprocess.run(['sgdisk', '--clear', '--new=4:2048:+64M', '--typecode=4:0700', '--change-name=4:AGUJA_CFG', str(source)], check=True, capture_output=True)
            fat = Path(folder) / 'cfg.fat'
            with open(fat, 'wb') as stream: stream.truncate(64 * 1024 * 1024)
            subprocess.run(['mkfs.vfat', '-F', '32', '-n', 'AGUJA_CFG', str(fat)], check=True, capture_output=True)
            with open(source, 'r+b') as target, open(fat, 'rb') as stream:
                target.seek(2048 * 512); shutil.copyfileobj(stream, target)
            marker = Path(folder) / 'release.json'
            marker.write_text('{"version":"0.4.0","features":["platform-profile-v1"]}')
            subprocess.run(['mcopy', '-i', str(source) + '@@1048576', str(marker), '::/release.json'], check=True, capture_output=True)
            baseline = helper.sha256(source)
            request = {'op': 'prepare', 'image_path': str(source), 'output_path': str(output), 'image_sha256': baseline,
                       'capsule': capsule(), 'protection': {'mode': 'plain'}}
            result = helper.prepare(request)
            self.assertEqual(baseline, helper.sha256(source))
            self.assertTrue(result['profile_verified'])
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            readback = Path(folder) / 'readback'
            subprocess.run(['mcopy', '-i', str(output) + '@@1048576', '::/aguja-profile.json', str(readback)], check=True, capture_output=True)
            self.assertEqual(profile.open_capsule(readback.read_bytes())['hostname'], 'aguja-test')
            with self.assertRaises(ValueError): helper.prepare(request)
            request['output_path'] = str(Path(folder) / 'bad.img'); request['image_sha256'] = '0' * 64
            with self.assertRaises(ValueError): helper.prepare(request)
            self.assertFalse(Path(request['output_path']).exists())


class LocaleTests(unittest.TestCase):
    def test_optional_legacy_and_selected_locale_plain_cipher_roundtrips(self):
        legacy = capsule()
        self.assertNotIn('locale', profile.validate(legacy))
        self.assertNotIn('locale', profile.open_capsule(profile.seal(legacy, {'mode': 'plain'})))
        for language in profile.LANGUAGES:
            c = capsule(); c['locale'] = {'language': language, 'keyboard': 'latam', 'variant': 'nodeadkeys'}
            for protection in ({'mode': 'plain'}, {'mode': 'encrypted', 'passphrase': 'synthetic-locale-pass'}):
                with self.subTest(language=language, mode=protection['mode']):
                    sealed = profile.seal(c, protection)
                    opened = profile.open_capsule(sealed, protection.get('passphrase'))
                    self.assertEqual(opened['locale'], c['locale'])

    def test_reject_unsupported_untyped_and_shell_injection_locale_values(self):
        selections = [None, [], {}, {'language': 'es_ES.UTF-8', 'keyboard': 'es'},
                      dict(profile.DEFAULT_LOCALE, timezone='Europe/Madrid')]
        for key, values in {
            'language': [True, [], 'es_ES', 'es_ES.UTF-8\nLC_ALL=C', '$(touch /tmp/locale-injection)'],
            'keyboard': [True, [], 'es,us', 'es";touch /tmp/keyboard-injection;#'],
            'variant': [True, [], 'intl', 'nodeadkeys\n'],
        }.items():
            selections.extend(dict(profile.DEFAULT_LOCALE, **{key: value}) for value in values)
        selections.extend({'language': 'en_US.UTF-8', 'keyboard': key, 'variant': 'nodeadkeys'}
                          for key in ('us', 'gb', 'fr', 'br', 'de', 'it'))
        for selection in selections:
            with self.subTest(selection=selection), self.assertRaises(ValueError):
                profile.validate(dict(capsule(), locale=selection))

    def test_apply_live_locale_keyboard_regenerates_cache_and_locked_resets_defaults(self):
        from unittest.mock import Mock
        c = capsule(); c['locale'] = {'language': 'es_CO.UTF-8', 'keyboard': 'latam', 'variant': 'nodeadkeys'}
        sealed = profile.seal(c, {'mode': 'encrypted', 'passphrase': 'synthetic-locale-pass'})
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); keyboard_target = root / 'etc/console-setup/keyboard'
            keyboard_target.parent.mkdir(parents=True)
            (root / 'etc/default').mkdir()
            (root / 'etc/default/keyboard').symlink_to('../console-setup/keyboard')
            runner = Mock()
            # The same boot path handles a locked capsule, owner unlock and reboot.
            for password, expected in ((None, profile.DEFAULT_LOCALE), ('synthetic-locale-pass', c['locale']),
                                       (None, profile.DEFAULT_LOCALE)):
                opened = profile.open_capsule(sealed, password)
                selection = profile.apply_locale(opened, root, runner)
                self.assertEqual(selection, expected)
                self.assertEqual(profile.locale_environment(root / 'etc/default/locale'),
                                 {'LANG': expected['language'], 'LC_ALL': expected['language']})
                config = keyboard_target.read_text()
                self.assertIn('XKBLAYOUT="' + expected['keyboard'] + '"', config)
                self.assertIn('XKBVARIANT="' + expected['variant'] + '"', config)
                self.assertIn('XKBMODEL="pc105"', config)
                self.assertEqual(keyboard_target.stat().st_mode & 0o777, 0o644)
                self.assertTrue((root / 'etc/default/keyboard').is_symlink())
            self.assertEqual(runner.call_count, 3)
            self.assertEqual(runner.call_args.args[0], ['setupcon', '--keyboard-only', '--save', '--force'])
            self.assertTrue(runner.call_args.kwargs['check'])

    def test_language_reader_ignores_arbitrary_config_not_shell_evaluated(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / 'locale'
            for value in ('LANG=$(touch /tmp/locale-injection)\n', 'LANG="fr_FR.UTF-8"\n',
                          'LANG=unsupported\nLC_ALL=en_US.UTF-8\n'):
                config.write_text(value)
                self.assertEqual(profile.locale_environment(config), {})
            config.write_text('LANG=fr_FR.UTF-8\nPATH=not-an-environment-import\n')
            self.assertEqual(profile.locale_environment(config), {'LANG': 'fr_FR.UTF-8', 'LC_ALL': 'fr_FR.UTF-8'})

    def test_shell_refresh_after_unlock_overrides_stale_language_without_eval(self):
        with tempfile.TemporaryDirectory() as folder:
            config, marker = Path(folder) / 'locale', Path(folder) / 'must-not-exist'
            config.write_text('LANG=$(touch ' + str(marker) + ')\nLANG=es_CO.UTF-8\n')
            helper = Path(folder) / 'i18n.py'
            helper.write_text((ROOT / 'runtime/i18n.py').read_text().replace('/etc/default/locale', str(config)))
            shutil.copyfile(ROOT / 'runtime/locale-catalog.json', Path(folder) / 'locale-catalog.json')
            script = (ROOT / 'runtime/locale.sh').read_text().replace('/usr/lib/aguja/i18n.py', str(helper))
            command = script + '\nprintf "%s/%s" "$LANG" "$LC_ALL"\n'
            result = subprocess.run(['bash', '-c', command], capture_output=True, text=True, check=True,
                                    env=dict(os.environ, LANG='en_US.UTF-8', LC_ALL='C'))
            self.assertEqual(result.stdout, 'es_CO.UTF-8/es_CO.UTF-8')
            self.assertFalse(marker.exists())


