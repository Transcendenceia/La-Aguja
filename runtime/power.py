"""Power actions, with fail-closed encrypted persistence before shutdown."""
import argparse
import getpass
import json
import os
from pathlib import Path
import subprocess
import sys

import persistence
from desk_i18n import tr

ACTIONS = ('poweroff', 'reboot', 'persist-poweroff', 'persist-reboot')
LABELS = ('Power off', 'Restart', 'Persist and power off', 'Persist and restart')
STAGES = {'scan':'Scanning the live', 'encrypt':'Preparing encrypted storage',
          'copy':'Copying live files', 'initramfs':'Preparing the next boot',
          'compress':'Compressing the snapshot', 'sync':'Synchronizing the USB',
          'compact':'Compacting encrypted storage', 'verify':'Verifying saved bytes',
          'activate':'Activating the next boot', 'done':'Changes saved and verified',
          'power':'Finishing and powering off / restarting', 'failed':'Changes were not saved'}


def progress_text(event):
    label = tr(STAGES.get(event.get('stage'), 'Working…'))
    done, total = event.get('completed'), event.get('total')
    if isinstance(done, (int,float)):
        if event.get('unit') == 'bytes':
            label += f' · {done/1024**2:.1f} MiB' + (f' / {total/1024**2:.1f} MiB' if total else '')
        elif event.get('unit') == 'percent': label += f' · {done:.0f}%'
        elif event.get('unit') == 'files': label += f' · {done:.0f} ' + tr('files')
    return label


def worker(action, password=None):
    if action not in ACTIONS: raise ValueError('Invalid power action')
    if os.geteuid() != 0 or 'boot=live' not in Path('/proc/cmdline').read_text().split():
        raise ValueError('Power actions require the LA AGUJA live system.')
    if action.startswith('persist-'):
        if os.readlink('/proc/self/ns/mnt') == os.readlink('/proc/1/ns/mnt'):
            raise ValueError('Persistence requires a private mount namespace.')
        # save returns only after verification, activation AND mount cleanup.
        if persistence.save(password) != 0:
            raise ValueError('Persistence failed; power action cancelled.')
    os.sync()
    persistence.emit('power')
    subprocess.run(['systemctl', action.removeprefix('persist-')], check=True, timeout=30)
    return 0


def command(action):
    if action not in ACTIONS: raise ValueError('Invalid power action')
    prefix = ['sudo', '-n']
    if action.startswith('persist-'):
        prefix += ['unshare', '--mount', '--propagation', 'private']
    return prefix + ['/usr/bin/python3', '/usr/lib/aguja/power.py', 'worker', action]


def console(action=None):
    import cockpit
    if action is None:
        action = cockpit.option_dialog(tr('Power off computer'),
                 [(tr(label), key) for key, label in zip(ACTIONS,LABELS)])
    if action is None: return 0
    # Explicit final choice, safe default, Escape/EOF never approve.
    if cockpit.option_dialog(tr(dict(zip(ACTIONS,LABELS))[action]),
            [(tr('Cancel'), False), (tr('Continue'), True)],
            tr('Unsaved RAM changes will be lost.') if not action.startswith('persist-')
            else tr('Save and verify the encrypted snapshot before the power action.')) is not True:
        return 0
    secret = None
    try:
        if action.startswith('persist-'):
            secret = getpass.getpass(tr('Snapshot password') + ': ')
            if len(secret) < 8 or secret != getpass.getpass(tr('Repeat password') + ': '):
                raise ValueError('Use at least 8 characters and repeat the same password.')
        with subprocess.Popen(command(action), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL, text=True) as process:
            process.stdin.write(json.dumps({'password':secret}));process.stdin.close();secret=None
            for line in process.stdout:
                event=json.loads(line)
                print(progress_text(event), flush=True)
            code=process.wait()
        if code: print(tr('Power action cancelled. The computer stays on.'), flush=True)
        return code
    except (EOFError,KeyboardInterrupt,ValueError,OSError):
        print(tr('Power action cancelled. The computer stays on.'), flush=True)
        return 1


def main(argv=None):
    parser=argparse.ArgumentParser(prog='aguja power')
    parser.add_argument('mode',nargs='?',default='menu',choices=('menu','worker',*ACTIONS))
    parser.add_argument('action',nargs='?',choices=ACTIONS)
    args=parser.parse_args(argv)
    if args.mode != 'worker':return console(None if args.mode=='menu' else args.mode)
    try:
        request=json.loads(sys.stdin.buffer.read(8192))
        return worker(args.action, request.get('password'))
    except (OSError,ValueError,subprocess.SubprocessError):
        persistence.emit('failed');return 1


if __name__=='__main__':raise SystemExit(main())
