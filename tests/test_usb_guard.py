import importlib.util
import io
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location("flash", Path(__file__).resolve().parents[1] / "scripts/flash-usb.py")
flash = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flash)


class UsbGuardTests(unittest.TestCase):
    def disk(self, **values):
        return dict(path="/dev/sda", type="disk", serial="TEST-USB", tran="usb", rm=True,
                    size=16_000_000_000, mountpoints=[None], children=[], **values)

    def invoke(self, d, serial="TEST-USB"):
        with patch.object(flash.subprocess, "check_output", return_value=json.dumps({"blockdevices": [d]}).encode()):
            return flash.identify("/dev/sda", serial)

    def test_matching_removable_usb(self):
        self.assertEqual(self.invoke(self.disk())["serial"], "TEST-USB")

    def test_requests_real_tree_from_lsblk(self):
        response = json.dumps({"blockdevices": [self.disk()]}).encode()
        with patch.object(flash.subprocess, "check_output", return_value=response) as tool:
            flash.identify("/dev/sda", "TEST-USB")
            self.assertIn("--tree", tool.call_args.args[0])

    def test_wrong_serial(self):
        with self.assertRaises(ValueError):
            self.invoke(self.disk(), "ANOTHER-USB")

    def test_internal_disk_refused(self):
        d = self.disk()
        d.update(tran="nvme", rm=False)
        with self.assertRaises(ValueError):
            self.invoke(d)

    def test_mounted_descendant_refused(self):
        d = self.disk()
        d["children"] = [{"mountpoints": ["/media/usb"]}]
        with self.assertRaises(ValueError):
            self.invoke(d)

    def test_short_read_refused(self):
        import io
        with self.assertRaises(ValueError):
            flash.hash_stream(io.BytesIO(b"partial"), 100)

    def test_e2fsck_repaired_is_success_but_reboot_and_error_bits_stop(self):
        for code in (0, 1, 2, 3, 4, 8, 16, 32, 128, -9):
            with self.subTest(code=code), patch.object(flash.subprocess, 'run',
                    return_value=subprocess.CompletedProcess(['e2fsck'], code)) as command:
                if code in (0, 1):
                    self.assertEqual(flash.check_data_filesystem('/dev/sda5'), code)
                else:
                    with self.assertRaises(ValueError):
                        flash.check_data_filesystem('/dev/sda5')
                self.assertFalse(command.call_args.kwargs['check'])

    def test_backup_wrong_hash_short_extra_or_decompress_failure_refused_and_cleaned(self):
        data = b'synthetic-backup'
        for recovered, code in ((b'wrong-data-here', 0), (data[:-1], 0), (data + b'extra', 0), (data, 1)):
            proc = Mock(stdout=io.BytesIO(recovered))
            proc.wait.return_value = code
            proc.poll.return_value = None
            with self.subTest(recovered=recovered, code=code), \
                 patch.object(flash.subprocess, 'Popen', return_value=proc):
                with self.assertRaises(ValueError):
                    flash.verify_backup('/synthetic/backup', len(data), hashlib.sha256(data).hexdigest())
                self.assertTrue(proc.stdout.closed)
                proc.kill.assert_called_once()

    def simulate_writer(self, *, fsck=0, recovered=None, change_identity=False, change_image=False, readback=None, backup=True):
        """Real temporary image/report files; all block reads/tools are fake."""
        from contextlib import ExitStack, redirect_stdout
        original, image_data = b'synthetic-usb-before' * 8, b'synthetic-factory-image'
        commands = []
        with tempfile.TemporaryDirectory() as folder, ExitStack() as stack:
            image, backup_dir = Path(folder) / 'source.img', Path(folder) / 'backups'
            image.write_bytes(image_data)
            # Do not rely on a private directory to protect a full disk backup.
            backup_dir.mkdir(mode=0o755)
            disk = self.disk(); disk['size'] = len(original)
            identities = [disk] * 4
            if change_identity:
                identities[1] = dict(disk, size=len(original) + 1)
            stack.enter_context(patch.object(flash, 'identify', side_effect=identities))
            stack.enter_context(patch.object(flash.os, 'geteuid', return_value=0))
            argv = ['flash-usb.py', str(image), '/dev/sda', '--serial', 'TEST-USB',
                    '--sha256', hashlib.sha256(image_data).hexdigest(), '--report-dir', str(backup_dir),
                    '--confirm', 'FLASH:TEST-USB']
            if backup:
                argv += ['--backup-dir', str(backup_dir)]
            stack.enter_context(patch.object(sys, 'argv', argv))
            stack.enter_context(patch.object(flash.subprocess, 'check_output', side_effect=lambda args, **kw:
                '/dev/hostdisk1\n' if args[0] == 'findmnt' else 'First sector: 2048 (at 1024.0 KiB)\n'))
            device_reads = iter(([original] if backup else []) + [image_data if readback is None else readback])
            def device_open(path, *args, **kwargs):
                if path == '/dev/sda':
                    return io.BytesIO(next(device_reads))
                raise AssertionError('Unexpected direct filesystem open')
            stack.enter_context(patch.object(flash, 'open', side_effect=device_open, create=True))
            class Input(io.BytesIO):
                def close(self):
                    pass
            def popen(args, **kwargs):
                if '-dc' in args:
                    proc = Mock(stdout=io.BytesIO(original if recovered is None else recovered))
                    proc.wait.return_value = 0; proc.poll.return_value = 0
                    return proc
                proc = Mock(stdin=Input())
                def finish():
                    kwargs['stdout'].write(proc.stdin.getvalue())
                    if change_image:
                        image.write_bytes(b'changed-during-backup')
                    return 0
                proc.wait.side_effect = finish; proc.poll.return_value = 0
                return proc
            stack.enter_context(patch.object(flash.subprocess, 'Popen', side_effect=popen))
            def command(args, **kwargs):
                commands.append(args)
                return subprocess.CompletedProcess(args, fsck if args[0] == 'e2fsck' else 0)
            stack.enter_context(patch.object(flash.subprocess, 'run', side_effect=command))
            error = None
            with redirect_stdout(io.StringIO()):
                try:
                    flash.main()
                except ValueError as caught:
                    error = str(caught)
            reports = list(backup_dir.glob('flash-*.json'))
            report = json.loads(reports[0].read_text()) if reports else {}
            backups = list(backup_dir.glob('usb-*.img.zst'))
            self.assertEqual(len(backups), 1 if backup else 0)
            if backup:
                self.assertEqual(backups[0].stat().st_mode & 0o777, 0o600)
                self.assertEqual(backups[0].read_bytes(), original)
            return error, commands, report

    def test_direct_writer_does_not_read_or_copy_old_content_and_still_verifies(self):
        error, commands, report = self.simulate_writer(backup=False)
        self.assertIsNone(error)
        self.assertFalse(report['backup_requested'])
        self.assertFalse(report['backup_verified'])
        self.assertNotIn('backup', report)
        self.assertTrue(report['image_readback_verified'])
        self.assertTrue(report['data_expanded'])
        self.assertEqual(report['stage'], 'complete')

    def test_direct_writer_bad_readback_never_changes_partitions(self):
        error, commands, report = self.simulate_writer(backup=False, readback=b'not-the-image-at-all' * 4)
        self.assertIsNotNone(error)
        self.assertEqual([args[0] for args in commands], ['dd', 'blockdev'])
        self.assertFalse(report.get('image_readback_verified'))

    def test_writer_repaired_filesystem_completes_with_verified_private_backup(self):
        error, commands, report = self.simulate_writer(fsck=1)
        self.assertIsNone(error)
        self.assertTrue(report['backup_verified'])
        self.assertTrue(report['image_readback_verified'])
        self.assertTrue(report['data_expanded'])
        self.assertEqual(report['e2fsck_exit_code'], 1)
        self.assertEqual(report['stage'], 'complete')
        self.assertIn('resize2fs', [args[0] for args in commands])

    def test_writer_backup_identity_or_source_change_never_reaches_dd(self):
        for options in ({'recovered': b'corrupted-backup'}, {'change_identity': True}, {'change_image': True}):
            with self.subTest(options=options):
                error, commands, report = self.simulate_writer(**options)
                self.assertIsNotNone(error)
                self.assertEqual(commands, [])
                self.assertFalse(report.get('image_readback_verified'))

    def test_writer_readback_failure_stops_partition_changes(self):
        error, commands, report = self.simulate_writer(readback=b'wrong-image-on-usb' * 8)
        self.assertIsNotNone(error)
        self.assertEqual([args[0] for args in commands], ['dd', 'blockdev'])
        self.assertTrue(report['backup_verified'])
        self.assertFalse(report.get('image_readback_verified'))

    def test_writer_fsck_error_preserves_recovery_report_and_never_resizes(self):
        error, commands, report = self.simulate_writer(fsck=4)
        self.assertIsNotNone(error)
        self.assertTrue(report['backup_verified'])
        self.assertTrue(report['image_readback_verified'])
        self.assertEqual(report['stage'], 'data_check_failed')
        self.assertEqual(report['e2fsck_exit_code'], 4)
        self.assertNotIn('resize2fs', [args[0] for args in commands])
        self.assertFalse(report.get('data_expanded'))


if __name__ == '__main__':
    unittest.main()
