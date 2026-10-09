"""Local VT wheel bridge. Root reads input; only wheel deltas leave the helper.

No grab, keyboard events, coordinates, buttons or input logs are forwarded.
Disabled unless the caller's own VT is visible and in text mode. X/GUI devices
keep their native handling. Parent exit/closed pipe stops this bounded helper.
"""
import array
import fcntl
import os
from pathlib import Path
import re
import select
import struct
import sys
import time

EVENT = struct.Struct('llHHi')


def wheel_delta(data):
    return sum(value for _, _, kind, code, value in EVENT.iter_unpack(data)
               if kind == 2 and code == 8)  # EV_REL / REL_WHEEL only.


def wheel_devices(root=Path('/sys/class/input')):
    result = []
    for event in root.glob('event*'):
        if not re.fullmatch(r'event[0-9]+', event.name):
            continue
        try:
            bits = int((event/'device/capabilities/rel').read_text().strip().split()[-1], 16)
        except (OSError, ValueError, IndexError):
            continue
        if bits & (1 << 8):
            result.append('/dev/input/' + event.name)
    return result


def text_visible(vt):
    try:
        if Path('/sys/class/tty/tty0/active').read_text().strip() != Path(vt).name:
            return False
        fd = os.open(vt, os.O_RDONLY | os.O_NOCTTY)
        try:
            mode = array.array('i', [0])
            fcntl.ioctl(fd, 0x4B3B, mode)
            return mode[0] == 0  # KD_TEXT only.
        finally:
            os.close(fd)
    except OSError:
        return False


def identity(pid):
    try:
        process = Path('/proc')/str(pid)
        return process.stat().st_uid, (process/'stat').read_text().rsplit(')', 1)[1].split()[19]
    except (OSError, IndexError):
        return None


def main(pid, vt):
    if os.geteuid() != 0 or not re.fullmatch(r'/dev/tty[1-9][0-9]*', vt):
        return 1
    owner = identity(pid)
    if owner is None or owner[0] != int(os.environ.get('SUDO_UID', '-1')):
        return 1
    import browser
    try:
        if browser.original_vt(pid) != int(vt[8:]):
            return 1
    except ValueError:
        return 1
    devices = {}
    scanned = 0
    try:
        while identity(pid) == owner:
            if time.monotonic() >= scanned:
                for path in wheel_devices():
                    if path not in devices.values():
                        try:
                            devices[os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC)] = path
                        except OSError:
                            pass
                scanned = time.monotonic() + 1
            ready, _, _ = select.select([0] + list(devices), [], [], .3)
            for fd in ready:
                if fd == 0:
                    if not os.read(0, 1):
                        return 0
                    continue  # Lifecycle pipe only; input is never forwarded.
                try:
                    data = os.read(fd, EVENT.size * 64)
                    if not data:
                        raise OSError('Device removed')
                    delta = wheel_delta(data)
                except OSError:
                    os.close(fd)
                    devices.pop(fd)
                    continue
                if delta and text_visible(vt):
                    print(max(-16, min(16, delta)), flush=True)
    except (BrokenPipeError, KeyboardInterrupt):
        return 0
    finally:
        for fd in devices:
            os.close(fd)
    return 0


if __name__ == '__main__':
    if len(sys.argv) != 3 or not sys.argv[1].isdigit():
        raise SystemExit(1)
    raise SystemExit(main(int(sys.argv[1]), sys.argv[2]))
