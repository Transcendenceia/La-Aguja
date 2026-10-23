"""Reject a saved generation whose early-boot drivers cannot load."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
import updates as u


class BootPair(unittest.TestCase):
    def tree(self, root, releases):
        (root / 'boot').mkdir()
        for release in releases:
            (root / 'boot' / ('vmlinuz-' + release)).write_bytes(b'synthetic-kernel')
            (root / 'boot' / ('initrd.img-' + release)).write_bytes(b'synthetic-initrd')

    def test_newer_kernel_wins_even_when_old_kernel_was_copied_last(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.tree(root, ['6.12.9-amd64', '6.12.113-amd64'])
            os.utime(root / 'boot/vmlinuz-6.12.9-amd64', (2000000000, 2000000000))
            with patch.object(u, 'run', return_value=SimpleNamespace(stdout=b'usr/lib/modules/6.12.113-amd64/kernel/usb.ko\n')):
                kernel, initrd = u.boot_pair(root)
            self.assertEqual(kernel.name, 'vmlinuz-6.12.113-amd64')
            self.assertEqual(initrd.name, 'initrd.img-6.12.113-amd64')

    def test_mismatched_or_absent_modules_prevent_activation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.tree(root, ['6.12.113-amd64'])
            for listing in (b'usr/lib/modules/6.12.111-amd64/kernel/usb.ko\n', b'init\n'):
                with self.subTest(listing=listing), patch.object(u, 'run', return_value=SimpleNamespace(stdout=listing)):
                    with self.assertRaisesRegex(ValueError, 'no coinciden'):
                        u.boot_pair(root)

    def test_missing_matching_initrd_does_not_fall_back_to_old_kernel(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.tree(root, ['6.12.111-amd64', '6.12.113-amd64'])
            (root / 'boot/initrd.img-6.12.113-amd64').unlink()
            with self.assertRaisesRegex(ValueError, 'Falta el initramfs'):
                u.boot_pair(root)


if __name__ == '__main__':
    unittest.main()
