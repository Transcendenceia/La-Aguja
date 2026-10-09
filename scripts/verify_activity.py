"""End-to-end checks against an isolated running LA AGUJA Rescue Disk VM."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import time


def verify(remote, env, workdir, screenshot=None, target_root='/data/workspace'):
    report = {}
    def run(command, **kwargs):
        return subprocess.run(remote + [command], env=env, capture_output=True, timeout=30, **kwargs)
    def snapshot():
        p = run('aguja activity --json')
        if p.returncode:
            raise ValueError('Activity snapshot unavailable')
        return json.loads(p.stdout)
    if run('systemctl is-active --quiet aguja-activity').returncode:
        raise ValueError('Activity service is not active')
    report['activity_service'] = True
    p = run('python3 -', input=b'import os,sys\nos.write(1,b"raw\\x00out\\xff")\nos.write(2,b"raw\\x00err\\xfe")\nsys.exit(17)\n')
    if p.returncode != 17 or p.stdout != b'raw\x00out\xff' or p.stderr != b'raw\x00err\xfe':
        raise ValueError('SSH stdin/binary streams/exit code changed')
    report['stdin_binary_streams_exit'] = True
    sentinel = 'SYNTHETIC_TOKEN_DO_NOT_PUBLISH_736421'
    # The command-detail contract retains ordinary argv. Register the synthetic
    # value as a known credential rather than assume all token-like words in
    # arbitrary command arguments can be detected. This also proves live reload.
    fixture = '/home/aguja/.config/aguja/provider-env.json'
    setup = "from pathlib import Path;import json,os;os.umask(0o077);p=Path(" + repr(fixture) + ");assert not p.exists();p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps({'AGUJA_TEST_TOKEN':" + repr(sentinel) + "}))\n"
    created = run('python3 -', input=setup.encode())
    if created.returncode:
        raise ValueError('Synthetic credential fixture requires an isolated factory guest')
    try:
        time.sleep(1.3)
        p = run("printf '%s\\n' " + sentinel)
        if p.stdout.strip() != sentinel.encode():
            raise ValueError('Remote confidential output changed')
        time.sleep(.7)
        data = snapshot()
        if sentinel in json.dumps(data):
            raise ValueError('Synthetic credential reached local activity')
        if not any('printf' in c.get('command','') and '[oculto]' in c.get('command','') for c in data.get('commands',[])):
            raise ValueError('Known secret was not masked while preserving command argv')
    finally:
        cleanup = "from pathlib import Path;import json;p=Path(" + repr(fixture) + ");assert json.loads(p.read_text())=={'AGUJA_TEST_TOKEN':" + repr(sentinel) + "};p.unlink()\n"
        if run('python3 -', input=cleanup.encode()).returncode:
            raise ValueError('Synthetic credential fixture cleanup failed')
    report['sensitive_contents_hidden'] = True
    p = run('uname -s')
    if p.stdout.strip() != b'Linux':
        raise ValueError('SSH diagnostic changed')
    time.sleep(.7)
    mirror_deadline=time.monotonic()+10
    while time.monotonic()<mirror_deadline:
        data=snapshot();events=data['events']
        if any(e.get('kind') == 'output' and e.get('text') == 'Linux' for e in events):break
        time.sleep(.5)
    else:
        (workdir/'missing-diagnostic-snapshot.json').write_text(json.dumps(data))
        raise ValueError('Noninteractive diagnostic not mirrored')
    report['command_output_mirror'] = True

    # Preserve both modern SFTP-backed SCP and legacy SCP, plus rsync framing.
    ssh_index = remote.index('ssh')
    auth_prefix = remote[:ssh_index]
    host = remote[-1]
    options = remote[ssh_index + 1:-1]
    scp_options = list(options)
    for i, value in enumerate(scp_options):
        if value == '-p':
            scp_options[i] = '-P'
    source = workdir / 'transfer-source.bin'
    source.write_bytes(bytes(range(256)) * 64)
    source.chmod(0o600)
    for label, extra in [('sftp', []), ('legacy_scp', ['-O'])]:
        target = target_root + '/check-' + label + '.bin'
        destination = workdir / ('transfer-' + label + '.bin')
        for endpoints in ([str(source), host + ':' + target], [host + ':' + target, str(destination)]):
            p = subprocess.run(auth_prefix + ['scp'] + extra + scp_options + endpoints,
                               env=env, capture_output=True, timeout=30)
            if p.returncode:
                raise ValueError(label + ' transfer failed')
        if destination.read_bytes() != source.read_bytes():
            raise ValueError(label + ' transfer contents changed')
        report[label + '_exact'] = True
    p = subprocess.run(['rsync', '-a', '-e', shlex.join(remote[:-1]), str(source),
                        host + ':' + target_root + '/check-rsync.bin'], env=env, capture_output=True, timeout=30)
    if p.returncode:
        raise ValueError('rsync transfer failed')
    expected_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    p = run('sha256sum ' + shlex.quote(target_root + '/check-rsync.bin'))
    if p.stdout.decode().split()[0] != expected_hash:
        raise ValueError('rsync transfer contents changed')
    report['rsync_exact'] = True

    # A real interactive SSH login exercises Zsh command_start and exit hooks.
    interactive = remote[:-1] + ['-tt', remote[-1]]
    p = subprocess.Popen(interactive, env=dict(env,TERM='xterm'), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        import select
        def wait_prompt():
            deadline=time.monotonic()+30;output=b''
            while time.monotonic()<deadline:
                if select.select([p.stdout],[],[],.5)[0]:
                    part=os.read(p.stdout.fileno(),65536)
                    if not part:raise ValueError('Interactive terminal closed before prompt')
                    output+=part
                    if b'\x1b[?2004h' in output:return
            raise ValueError('Interactive terminal did not become ready')
        wait_prompt()
        def confirmed_command(command,exit_code):
            p.stdin.write(command.encode()+b'\n');p.stdin.flush()
            deadline=time.monotonic()+45
            while time.monotonic()<deadline:
                data=snapshot()
                ids={session['id'] for session in data.get('sessions',[]) if session.get('mode')=='interactive'}
                if any(c.get('session') in ids and c.get('command')==command and c.get('exit')==exit_code for c in data.get('commands',[])):
                    wait_prompt();return data
                time.sleep(.5)
            (workdir/'missing-interactive-snapshot.json').write_text(json.dumps(data))
            raise ValueError('Interactive command did not complete: '+command)
        confirmed_command('uname -s',0)
        live=confirmed_command('false',1)
        p.stdin.write(b'sleep 30\n');p.stdin.flush()
        events = live['events']
        interactive_ids = {s['id'] for s in live.get('sessions', []) if s.get('mode') == 'interactive'}
        if not interactive_ids:
            raise ValueError('Interactive session missing from monitor')
        events = [e for e in events if e.get('session') in interactive_ids]
        if not any(e.get('kind') == 'command_start' and 'uname -s' in e.get('text', '') for e in events):
            raise ValueError('Interactive Zsh command hook did not run')
        if not any(e.get('kind') == 'command_end' and 'código 1' in e.get('text', '') for e in events):
            raise ValueError('Interactive command exit status not preserved')
        report['interactive_hooks_exit_status'] = True
        report['interactive_output_mirror'] = any(e.get('kind') == 'output' and e.get('text') == 'Linux' for e in events)
        if not report['interactive_output_mirror']:
            raise ValueError('Interactive diagnostic output missing from its own session')
        sleeper = subprocess.Popen(remote + ['sudo -n sleep 20'], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            descendant_deadline=time.monotonic()+10
            while time.monotonic()<descendant_deadline:
                live=snapshot()
                if len(live.get('sessions',[]))>=2 and any('sleep' in process.get('command','') for process in live.get('processes',[])):break
                time.sleep(.5)
            if len(live.get('sessions', [])) < 2 or not any('sleep' in x.get('command', '') for x in live.get('processes', [])):
                raise ValueError('Concurrent sessions/process descendants not tracked')
            report['concurrent_sessions_root_descendants'] = True
            if screenshot:
                screenshot('ssh-activity.png')
                time.sleep(.8)
                screenshot('ssh-activity-next-frame.png')
            # KDGETMODE only reads the VT mode: 1 proves the graphical renderer
            # is active on the real guest console, not merely a PNG preview.
            query = b'import os,fcntl,array,json\nf=os.open("/dev/tty1",os.O_RDONLY); a=array.array("i",[0]); fcntl.ioctl(f,0x4B3B,a); print(json.dumps({"graphics":a[0]==1})); os.close(f)\n'
            q = run('sudo -n python3 -', input=query)
            report['physical_vm_framebuffer'] = json.loads(q.stdout)['graphics']
            if screenshot and not report['physical_vm_framebuffer']:
                raise ValueError('VM console did not enter graphical framebuffer mode')
        finally:
            sleeper.wait(timeout=25)
        p.stdin.write(b'\x03exit 0\n'); p.stdin.flush()
        p.communicate(timeout=15)
        if p.returncode:
            raise ValueError('Interactive SSH did not exit cleanly')
    finally:
        if p.poll() is None:
            p.terminate()
            p.wait(timeout=10)
    report['lifecycle_alerts'] = any(e.get('kind') == 'session_start' for e in snapshot()['events']) and any(e.get('kind') == 'session_end' for e in snapshot()['events'])
    return report
