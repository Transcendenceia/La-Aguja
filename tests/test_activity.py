import base64
import importlib.util
import json
import fcntl
import pty
import select
import signal
import struct
import termios
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
import activity
import ssh_session


class RedactionTests(unittest.TestCase):
    def test_labels_known_values_multiline_and_terminal_injection(self):
        for text in ('curl -H Authorization:Bearer SAMPLE', 'password = sample', 'TOKEN=sample'):
            self.assertIn('oculto', activity.redact(text, command=True))
        self.assertNotIn('synthetic-secret', activity.redact('value: synthetic-secret', {'synthetic-secret'}))
        self.assertEqual(activity.plain('\x1b[2Jhi\x1b]0;fake\x07\x00'), 'hi')
        self.assertNotIn('123456-', activity.redact('-'.join(['123456'] * 8)))

    def test_full_arguments_and_shell_structure_visible_without_url_credentials(self):
        self.assertEqual(activity.redact('echo ordinary-command-argument', command=True), 'echo ordinary-command-argument')
        value=activity.redact('curl https://user:pass@example.org/?a=b', command=True)
        self.assertIn('curl https://example.org/',value)
        self.assertNotIn('user:pass',value)
        self.assertEqual(activity.redact('sudo -n smartctl -a /dev/nvme0n1', command=True), 'sudo -n smartctl -a /dev/nvme0n1')
        self.assertEqual(activity.redact('lsblk -o NAME,SIZE', command=True), 'lsblk -o NAME,SIZE')
        text = activity.redact('url https://user:pass@example.org/a?unknown=unlabelled#private')
        self.assertNotIn('user:pass', text)
        self.assertNotIn('unlabelled', text)
        self.assertNotIn('#private', text)
        self.assertIn('example.org/a', text)
        self.assertFalse(activity.safe_output('sudo -n smartctl -a /dev/nvme0n1'))

    def test_scripts_pipelines_paths_and_hashes_preserve_trace(self):
        for command in ('python3 -c "print(123)"','echo okay\ncat /etc/shadow',
                        'sudo -n sh -c \'printf "HELLO\\n"; uname -a\'',
                        'git -C /data/workspace/long-project-directory-with-more-than-32-characters diff --stat | head -30',
                        'sha256sum '+('a'*64)+'.img'):
            self.assertEqual(activity.redact(command,command=True),command)

    def test_only_secret_values_masked_inside_arguments_and_script(self):
        command='curl --request POST --token "fake test secret" -H "Authorization: Bearer test-credential" --output /tmp/result; TOKEN=another-private-value python3 -c "print(123)"'
        result=activity.redact(command,command=True)
        for secret in ('fake test secret','test-credential','another-private-value'):self.assertNotIn(secret,result)
        for visible in ('curl','--request POST','--token','Authorization:','--output /tmp/result','python3 -c "print(123)"'):self.assertIn(visible,result)
        self.assertEqual(activity.redact('aguja doctor --json',{'known-custom-password'},command=True),'aguja doctor --json')

    def test_long_trace_is_explicitly_bounded_not_silently_lost(self):
        command='echo '+('normal argument '*2000)
        value=activity.redact(command,command=True)
        self.assertIn('comando truncado',value)
        self.assertGreater(len(value),activity.MAX_COMMAND_TEXT)

    def test_snapshot_mirror_does_not_recursively_capture_its_own_history(self):
        snapshot={'events':[{'text':'ordinary previous output'}],'commands':[{'command':'uname -s'}], 'privacy':'Comandos y argumentos visibles; credenciales ocultas. No se registra stdin.', 'available':True}
        visible=activity.OutputFilter().feed((json.dumps(snapshot)+'\n').encode())
        self.assertEqual(visible,['Consulta de actividad entregada · 1 tareas · 1 eventos'])
        self.assertEqual(ssh_session.protocol('aguja activity --json'),'observer')
        self.assertIsNone(ssh_session.protocol('aguja doctor --json'))

    def test_large_diagnostic_is_complete_and_split_secret_masked_before_pagination(self):
        text='diagnostic-data '*2500+' boundary-secret '+('z'*7000)
        expected=text.replace('boundary-secret','[oculto]')
        filter=activity.OutputFilter({'boundary-secret'})
        self.assertEqual(filter.feed(text[:35010].encode()),[])
        lines=filter.feed((text[35010:]+'\n').encode())
        self.assertEqual(''.join(lines),expected)
        self.assertTrue(all(len(line)<=activity.MAX_TEXT for line in lines))

    def test_split_secret_and_pem_never_reach_visible_line(self):
        filter = activity.OutputFilter({'test-custom-pass'})
        self.assertEqual(filter.feed(b'hello test-custom-'), [])
        self.assertEqual(filter.feed(b'pass\n'), ['hello [oculto]'])
        self.assertEqual(filter.feed(b'TO'), [])
        self.assertEqual(filter.feed(b'KEN=abc\n'), ['TOKEN=[oculto]'])
        self.assertEqual(filter.feed(b'-----BEGIN PRIVATE KEY-----\n'), ['[bloque de clave/certificado oculto]'])
        self.assertEqual(filter.feed(b'very-private-unknown-text\n-----END PRIVATE KEY-----\n'), [])
        self.assertEqual(filter.feed(b'ok\n'), ['ok'])

    def test_new_pairing_tokens_redacted_even_in_existing_filter(self):
        secrets = set()
        filter = activity.OutputFilter(secrets)
        grant, key = 'T' * 43, 'K' * 43
        access = {'url': 'https://aguja.test/v1/agent/devices/' + 'd' * 22,
                  'token': 'aguja1.' + grant + '.' + key}
        with patch.object(Path, 'read_text', return_value=json.dumps(access)):
            secrets.update(activity.secret_values())
        self.assertIn(grant, secrets)
        self.assertIn(key, secrets)
        self.assertEqual(filter.feed(('values '+grant+' '+key+'\n').encode()),
                         ['values [oculto] [oculto]'])

    def test_overflow_never_releases_tail_of_secret(self):
        filter = activity.OutputFilter()
        self.assertEqual(filter.feed(b'x' * 1048577), [])
        self.assertEqual(filter.feed(b'secret-tail\n'), ['[línea supera 1 MiB: límite de memoria del panel; salida íntegra en consola]'])
        self.assertEqual(filter.feed(b'partial'), [])
        self.assertEqual(filter.feed(b'', final=True), ['partial'])

    def test_only_predictable_diagnostics_have_output(self):
        for text in ('df -h', 'lsblk -o NAME,SIZE', 'uname -a', 'free -m'):
            self.assertTrue(activity.safe_output(text), text)
        for text in ('cat x', 'echo unlabelled', 'python3 -', 'bash -s', 'ls; cat x',
                     'ls $(cat /secret)', 'env', 'curl http://example.org',
                     'nmcli connection show', 'ls\ncat x', 'printf hello', ''):
            self.assertFalse(activity.safe_output(text), text)


class MonitorTests(unittest.TestCase):
    sid = 'a' * 24
    processes = {
        10: {'pid': 10, 'ppid': 1, 'start_ticks': 100, 'ticks': 0, 'state': 'S', 'command': '/usr/bin/python3 /usr/lib/aguja/ssh_session.py'},
        11: {'pid': 11, 'ppid': 10, 'start_ticks': 101, 'ticks': 0, 'state': 'S', 'command': '/bin/zsh'},
        12: {'pid': 12, 'ppid': 11, 'start_ticks': 102, 'ticks': 0, 'state': 'R', 'command': 'df -h'},
        20: {'pid': 20, 'ppid': 1, 'start_ticks': 103, 'ticks': 0, 'state': 'S', 'command': 'unrelated'},
    }

    def setUp(self):
        self.monitor = activity.Monitor({'synthetic-secret'})
        self.uid = os.getuid()

    def event(self, kind, text='', pid=10, **extra):
        self.monitor.event(dict(session=self.sid, kind=kind, text=text, **extra), pid, self.uid, self.processes)

    def output(self, text):
        self.event('output', chunk=base64.b64encode(text).decode())

    def start(self, **extra):
        self.event('session_start', 'interactive', sensitive=True, peer='192.0.2.1:222', **extra)

    def test_lifecycle_descendants_credentials_and_pid_reuse(self):
        self.start()
        self.event('command_start', 'df -h', pid=12, sensitive=False)
        self.monitor.scan(self.processes, 1)
        self.assertEqual({p['pid'] for p in self.monitor.processes}, {10, 11, 12})
        self.event('command_start', 'forged', pid=20)
        self.assertEqual(self.monitor.sessions[self.sid]['command'], 'df -h')
        self.output(b'Filesystem details\n')
        self.assertEqual(self.monitor.events[-1]['text'], 'Filesystem details')
        self.event('session_end', exit=7)
        self.assertEqual(self.monitor.sessions[self.sid]['exit'], 7)
        self.assertEqual(self.monitor.sessions[self.sid]['status'], 'ended')
        before = len(self.monitor.events)
        self.output(b'late output\n')
        self.assertEqual(len(self.monitor.events), before)
        self.monitor = activity.Monitor()
        self.start()
        changed = {pid: dict(p) for pid, p in self.processes.items()}
        changed[10]['start_ticks'] = 999
        self.monitor.scan(changed, 2)
        self.assertEqual(self.monitor.sessions[self.sid]['status'], 'ended')

    def test_tunnel_and_local_transports_record_full_commands(self):
        for transport,wrapper in [('tunnel','tunnel.py'),('local','console_session.py')]:
            m=activity.Monitor({'synthetic-secret'})
            procs={10:dict(self.processes[10],command='python3 /usr/lib/aguja/'+wrapper)}
            command='sudo -n sh -c "uname -a; printf hello"'
            m.event({'session':self.sid,'kind':'session_start','text':command,'transport':transport,'mode':'exec'},10,self.uid,procs)
            self.assertEqual(m.sessions[self.sid]['transport'],transport)
            self.assertEqual(next(iter(m.commands.values()))['command'],command)
            m.event({'session':self.sid,'kind':'session_end','exit':0},10,self.uid,procs)
            self.assertEqual(next(iter(m.commands.values()))['exit'],0)

    def test_arbitrary_commands_visible_known_values_hidden_and_idle_echo_not_logged(self):
        self.start()
        self.event('command_start', 'set -e; aguja doctor --json | cat', pid=12)
        self.output(b'healthy: true\nTOKEN=abc\n')
        self.assertEqual(self.monitor.events[-1]['text'], 'TOKEN=[oculto]')
        self.assertTrue(any(e['text']=='healthy: true' for e in self.monitor.events))
        self.event('command_end', '0', pid=12)
        self.event('input_activity')
        self.output(b'next command echoed by TTY\n')
        self.assertNotIn('next command',str(list(self.monitor.events)))
        self.event('command_start','python3 custom-diagnostic.py',pid=12)
        self.output(b'custom diagnostic complete\n')
        self.assertEqual(self.monitor.events[-1]['text'],'custom diagnostic complete')

    def test_command_end_can_overtake_final_pty_output_without_losing_it(self):
        self.start()
        self.event('command_start', 'uname -s', pid=12, sensitive=False)
        with patch.object(activity.time, 'monotonic', return_value=10):
            self.event('command_end', '1', pid=12)
        with patch.object(activity.time, 'monotonic', return_value=10.02):
            self.output(b'Linux\n')
        self.assertEqual(self.monitor.events[-1]['text'], 'Linux')
        self.assertTrue(any('código 1' in event['text'] for event in self.monitor.events))
        self.monitor.scan(self.processes, 10.2)
        with patch.object(activity.time, 'monotonic', return_value=10.3):
            self.output(b'late prompt or output\n')
        self.assertNotIn('late prompt', str(list(self.monitor.events)))
        self.event('command_start', 'uname -s', pid=12, sensitive=False)
        with patch.object(activity.time, 'monotonic', return_value=20):
            self.event('command_end', '0', pid=12)
        with patch.object(activity.time, 'monotonic', return_value=20.02):
            self.output(b'final partial safe line')
        self.monitor.scan(self.processes, 20.2)
        self.assertEqual(self.monitor.events[-1]['text'], 'final partial safe line')

    def test_end_grace_never_admits_typed_input_or_sensitive_tail(self):
        self.start()
        self.event('command_start', 'uname -s', pid=12, sensitive=False)
        with patch.object(activity.time, 'monotonic', return_value=10):
            self.event('command_end', '0', pid=12)
        self.event('input_activity')
        with patch.object(activity.time, 'monotonic', return_value=10.01):
            self.output(b'unlabelled typed credential\n')
        self.assertNotIn('unlabelled', str(list(self.monitor.events)))
        self.event('command_start', 'cat credentials', pid=12, sensitive=True)
        with patch.object(activity.time, 'monotonic', return_value=20):
            self.event('command_end', '0', pid=12)
            self.output(b'TOKEN=synthetic-private-tail\n')
        self.assertNotIn('synthetic-private-tail', str(list(self.monitor.events)))

    def test_bounded_events_and_unavailable_snapshot(self):
        self.start()
        for _ in range(activity.MAX_EVENTS + 20):
            self.event('command_start', 'df -h', pid=12, sensitive=False)
        self.assertEqual(len(self.monitor.events), activity.MAX_EVENTS)
        with patch.object(activity, 'SNAPSHOT', Path('/nonexistent/aguja-test-snapshot')):
            self.assertFalse(activity.snapshot()['available'])

    def test_proc_parser_parentheses_and_descendant_cycles(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / '123'
            p.mkdir()
            # Fields 3..22; parent=10, utime=7, stime=3, start=200.
            tail = ['S', '10'] + ['0'] * 18
            tail[11], tail[12], tail[19] = '7', '3', '200'
            (p / 'stat').write_text('123 (name (with) spaces) ' + ' '.join(tail))
            (p / 'cmdline').write_bytes(b'df\0-h\0')
            result = activity.read_processes(directory)
            self.assertEqual(result[123]['ppid'], 10)
            self.assertEqual(result[123]['ticks'], 10)
            self.assertEqual(result[123]['start_ticks'], 200)
        self.assertTrue(activity.descends(12, 10, self.processes))
        self.assertFalse(activity.descends(20, 10, self.processes))
        self.assertFalse(activity.descends(1, 10, {1: {'ppid': 2}, 2: {'ppid': 1}}))


class WrapperTests(unittest.TestCase):
    def test_protocol_dispatch_and_shell_semantics(self):
        cases = {'internal-sftp': 'sftp', '/usr/lib/openssh/sftp-server': 'sftp',
                 'scp -t /tmp/file': 'scp', 'scp -pf /tmp/file': 'scp',
                 'rsync --server -logDtpre.iLsfxCIvu . /tmp': 'rsync',
                 'rsync --version': None, 'uname -a': None, '': None}
        for command, expected in cases.items():
            self.assertEqual(ssh_session.protocol(command), expected)
        self.assertEqual(ssh_session.command_argv('', '/bin/zsh', None), ['/bin/zsh', '-l'])
        self.assertEqual(ssh_session.command_argv('internal-sftp', '/bin/zsh', 'sftp'), ['/usr/lib/openssh/sftp-server'])

    def wrapper(self, command, stdin=b''):
        env = dict(os.environ, SSH_ORIGINAL_COMMAND=command, SSH_CONNECTION='192.0.2.1 222 192.0.2.2 22')
        return subprocess.run([sys.executable, str(Path(ssh_session.__file__))], input=stdin,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=8)

    def test_stdin_script_streams_and_exit_are_exact(self):
        result = self.wrapper('python3 -', b'import sys\nsys.stdout.buffer.write(bytes(range(256)))\nsys.stderr.write("stderr test")\nsys.exit(17)\n')
        self.assertEqual(result.stdout, bytes(range(256)))
        self.assertEqual(result.stderr, b'stderr test')
        self.assertEqual(result.returncode, 17)

    def test_shell_signal_preserves_signal_status(self):
        result = self.wrapper('kill -TERM $$')
        self.assertEqual(result.returncode, -15)

    def test_pty_stdin_window_and_line_discipline_are_preserved(self):
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 24, 80, 0, 0))
        command = "python3 -c 'import os; print(\"TTY\",os.isatty(0), flush=True); print(os.get_terminal_size(),flush=True); print(\"READY\",flush=True); print(\"ANSWER\",input(),flush=True)'"
        env = dict(os.environ, SSH_ORIGINAL_COMMAND=command)
        child = subprocess.Popen([sys.executable, ssh_session.__file__], stdin=slave, stdout=slave, stderr=slave,
                                 start_new_session=True, env=env)
        os.close(slave)
        output = b''
        sent = False
        deadline = time.monotonic() + 6
        try:
            while time.monotonic() < deadline:
                ready, _, _ = select.select([master], [], [], 0.2)
                if ready:
                    try:
                        data = os.read(master, 4096)
                    except OSError:
                        break
                    output += data
                    if b'READY' in output and not sent:
                        os.write(master, b'typed input\n')
                        sent = True
                if child.poll() is not None and not ready:
                    break
            self.assertEqual(child.wait(timeout=2), 0)
            self.assertIn(b'TTY True\r\n', output)
            self.assertIn(b'columns=80, lines=24', output)
            self.assertIn(b'ANSWER typed input\r\n', output)
            self.assertNotIn(b'\r\r\n', output)
        finally:
            if child.poll() is None:
                child.kill()
                child.wait()
            os.close(master)

    def test_pty_preserves_input_queued_before_wrapper_initializes(self):
        master, slave = pty.openpty()
        # Queue a line BEFORE the wrapper exists, exactly like `ssh -tt` with
        # piped input arriving while Python/ForceCommand is still starting.
        os.write(master, b'prequeued command\n')
        command = "python3 -c 'import sys; print(\"GOT:\"+sys.stdin.readline().rstrip(),flush=True)'"
        env = dict(os.environ, SSH_ORIGINAL_COMMAND=command)
        child = subprocess.Popen([sys.executable, ssh_session.__file__], stdin=slave, stdout=slave, stderr=slave,
                                 start_new_session=True, env=env)
        os.close(slave)
        output = b''
        deadline = time.monotonic() + 5
        try:
            while time.monotonic() < deadline:
                ready, _, _ = select.select([master], [], [], 0.1)
                if ready:
                    try:
                        output += os.read(master, 4096)
                    except OSError:
                        break
                if child.poll() is not None and not ready:
                    break
            self.assertEqual(child.wait(timeout=1), 0)
            self.assertIn(b'GOT:prequeued command\r\n', output)
        finally:
            if child.poll() is None:
                child.kill()
                child.wait()
            os.close(master)

    def test_monitor_absence_does_not_break_remote_execution(self):
        result = self.wrapper('printf hello')
        self.assertEqual((result.stdout, result.stderr, result.returncode), (b'hello', b'', 0))


if __name__ == '__main__':
    unittest.main()
