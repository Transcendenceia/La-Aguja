#!/usr/bin/python3
"""Prove stock-image autologin, ready SSH and automatic setup with no network adapter."""
import argparse
import json
from pathlib import Path
import re
import shlex
import socket
import subprocess
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    parser.add_argument('--workdir', type=Path, required=True)
    parser.add_argument('--timeout', type=int, default=360)
    parser.add_argument('--accelerator', choices=['tcg', 'kvm'], default='tcg')
    args = parser.parse_args()
    args.workdir.mkdir(mode=0o700, parents=True, exist_ok=True)
    image = args.workdir / 'offline.img'
    subprocess.run(['cp', '--sparse=always', str(args.image.resolve()), str(image)], check=True)
    serial_path = (args.workdir / 'serial.sock').resolve()
    qmp_path = (args.workdir / 'qmp.sock').resolve()
    command = ['qemu-system-x86_64', '-machine', 'q35', '-accel', args.accelerator, '-cpu', 'host' if args.accelerator == 'kvm' else 'max',
               '-smp', '2', '-m', '2048', '-display', 'none', '-monitor', 'none',
               '-serial', f'unix:{serial_path},server=on,wait=off',
               '-drive', f'if=none,id=stick,file={image},format=raw', '-device', 'qemu-xhci',
               '-device', 'usb-storage,drive=stick,removable=true', '-boot', 'order=c',
               '-nic', 'none', '-vga', 'std', '-qmp', f'unix:{qmp_path},server=on,wait=off']
    serial = qmp = stream = None
    transcript = ''
    with (args.workdir / 'qemu.log').open('w') as log:
        process = subprocess.Popen(command, stdout=log, stderr=log)
        start = time.monotonic()
        def receive():
            nonlocal transcript
            try:
                chunk = serial.recv(65536)
                transcript += chunk.decode(errors='replace')
            except socket.timeout:
                pass
            (args.workdir / 'serial.log').write_text(transcript)
        def qmp_command(name, arguments=None):
            stream.write((json.dumps({'execute': name, **({'arguments': arguments} if arguments else {})}) + '\n').encode())
            stream.flush()
            while True:
                result = json.loads(stream.readline())
                if 'return' in result:
                    return result['return']
                if 'error' in result:
                    raise ValueError('QMP command failed')
        def capture(name):
            qmp_command('screendump', {'filename': str((args.workdir / name).resolve()), 'format': 'png'})
        try:
            while not serial_path.exists():
                if process.poll() is not None or time.monotonic() - start > 15:
                    raise ValueError('QEMU did not start')
                time.sleep(0.1)
            serial = socket.socket(socket.AF_UNIX)
            serial.settimeout(1)
            serial.connect(str(serial_path))
            qmp = socket.socket(socket.AF_UNIX)
            qmp.settimeout(5)
            qmp.connect(str(qmp_path))
            stream = qmp.makefile('rwb')
            json.loads(stream.readline())
            qmp_command('qmp_capabilities')
            while 'AGUJA_READY:' not in transcript:
                if process.poll() is not None or time.monotonic() - start > args.timeout:
                    raise ValueError('Offline boot failed; inspect private serial log')
                receive()
            # Serial welcome is non-modal; the hardware-facing tty1 owns the setup UI.
            deadline = time.monotonic() + 20
            while 'aguja@' not in transcript and time.monotonic() < deadline:
                receive()
            time.sleep(2)
            capture('offline-welcome.png')
            time.sleep(14)
            capture('offline-wifi-wizard.png')
            check = "systemctl is-active --quiet ssh && systemctl is-active --quiet avahi-daemon && pgrep -x nmtui-connect >/dev/null && test -z \"$(hostname -I)\" && printf '\\nOFFLINE_WIZARD_OK\\n'"
            serial.sendall(('sudo -n sh -c ' + shlex.quote(check) + '\n').encode())
            deadline = time.monotonic() + 20
            while not re.search(r'(?m)^OFFLINE_WIZARD_OK\r?$', transcript) and time.monotonic() < deadline:
                receive()
            if not re.search(r'(?m)^OFFLINE_WIZARD_OK\r?$', transcript):
                raise ValueError('Offline onboarding check failed; inspect private serial log')
            report = {'firmware': 'bios', 'network_adapter': False, 'stock_configuration': True,
                      'autologin': True, 'no_network_ip': True, 'ssh_service_ready': True,
                      'mdns_service_ready': True, 'wifi_setup_automatically_opened': True}
            (args.workdir / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
            print(json.dumps(report), flush=True)
            serial.sendall(b'sudo -n poweroff\n')
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=10)
        finally:
            if stream:
                stream.close()
            if qmp:
                qmp.close()
            if serial:
                serial.close()
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)


if __name__ == '__main__':
    main()
