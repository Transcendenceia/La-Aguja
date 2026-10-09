#!/usr/bin/python3
"""Volatile, bounded SSH activity mirror. Never writes transcripts to DATA.

Only the monitor's sanitized view goes here; remote SSH bytes are untouched.
Unknown, unlabelled secrets cannot be reliably recognized: this is not a DLP tool.
"""
import argparse
import base64
import collections
import configparser
import json
import os
from pathlib import Path
import pwd
import re
import socket
import shlex
from urllib.parse import urlsplit, urlunsplit
import struct
import time

DIRECTORY = Path('/run/aguja-activity')
SOCKET = DIRECTORY / 'events.sock'
SNAPSHOT = DIRECTORY / 'snapshot.json'
MAX_PACKET = 131072
MAX_TEXT = 2048
MAX_COMMAND_TEXT = 16384
MAX_EVENTS = 2048
MAX_SESSIONS = 24
MAX_PROCESSES = 96
MAX_COMMANDS = 100
END_GRACE = 0.12
EMPTY = {'sessions': [], 'events': [], 'processes': [], 'available': False}
# Strip CSI, OSC (including hyperlinks), DCS, and remaining controls. The UI must
# additionally use text nodes/plain curses strings, never interpolate into markup.
ESCAPE = re.compile(r'\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07\x1b]*(?:\x07|\x1b\\)|[PX^_][\s\S]*?\x1b\\|.)')
SENSITIVE = re.compile(r'(?i)(oauth|authorize|code_challenge|redirect_uri|password|passwd|passphrase|secret|token|credential|authorization|api[_-]?key|e2e[_-]?key|sshpass|chpasswd|show-secrets|private.key|bitlocker|recovery.?key|\bpsk\b|\.ssh/|\.env\b|vaultwarden|/proc/[^ ]*/environ|/etc/shadow)')
OPAQUE = re.compile(r'(?<![\w])[A-Za-z0-9_+/=-]{32,}(?![\w])')
SAFE_OUTPUT = {'ls', 'df', 'du', 'free', 'uname', 'uptime', 'lscpu', 'lsblk', 'vmstat', 'iostat', 'whoami', 'id', 'pwd', 'date', 'sleep', 'true', 'false'}


def probe_context(command):
    """Recognize only generated PATH/cd/read-only Git checks outside a repo.

    No shell evaluation; ordinary `git ...` commands remain visible failures.
    This describes the caller's probe, never changes its exit code or output.
    """
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=';&|')
        lexer.whitespace_split = True
        fragments, fragment = [], []
        for word in lexer:
            if word in (';', '&&', '||'):
                if fragment:
                    fragments.append(fragment)
                fragment = []
            elif word in ('|', '&'):
                return None
            else:
                fragment.append(word)
        if fragment:
            fragments.append(fragment)
        directory, verb, generated = None, None, False
        for words in fragments:
            while words and re.fullmatch(r'(PATH|GIT_OPTIONAL_LOCKS|LC_ALL|LANG)=.*', words[0]):
                generated = True
                words = words[1:]
            if not words:
                continue
            if words[0] == 'cd' and len(words) == 2 and not re.search(r'[$`]', words[1]):
                directory = Path(words[1]).expanduser()
            elif Path(words[0]).name == 'git' and '--no-index' not in words:
                verb = next((w for w in words[1:] if w in ('status', 'diff', 'rev-parse', 'ls-files', 'symbolic-ref', 'log', 'show', 'for-each-ref', 'describe', 'ls-tree', 'cat-file', 'merge-base', 'branch', 'config')), None)
                if verb is None:
                    return None
                global_options = words[1:words.index(verb)]
                if any(w.startswith(('--git-dir', '--work-tree')) for w in global_options):
                    return None
                if '-C' in global_options:
                    index = words.index('-C')
                    if index+1 >= len(words) or directory is None:
                        return None
                    candidate = Path(words[index+1])
                    directory = candidate if candidate.is_absolute() else directory / candidate
                if verb == 'branch' and not any(w in ('--show-current','--list','-a','-r','--all','--remotes') for w in words):
                    return None
                if verb == 'config' and not any(w in ('--get','--get-all','--get-regexp','--list','-l') for w in words):
                    return None
            else:
                return None
        if not (generated and directory and directory.is_absolute() and directory.is_dir() and verb):
            return None
        if any((parent / '.git').exists() for parent in [directory, *directory.parents]):
            return None
        return {'kind': 'git_workspace', 'verb': verb, 'reason': 'La carpeta consultada no es un repositorio Git'}
    except (ValueError, OSError):
        return None


def task_label(command):
    try:
        words = shlex.split(command)
        if words[:2] == ['aguja', 'run'] and len(words) >= 6 and words[2] == '--label' and words[4] == '--':
            return redact(words[3], secret_values())[:100]
    except ValueError:
        pass
    return None


def safe_task_output(command):
    try:
        words = shlex.split(command)
        return bool(task_label(command)) and safe_output(shlex.join(words[5:]))
    except ValueError:
        return False


def result_state(code, probe=None):
    if probe and code in (128, 129):
        return 'probe', 'Sondeo Git · carpeta sin repositorio (código ' + str(code) + ')'
    if code == 0:
        return 'ok', 'Completado'
    if isinstance(code, int) and code < 0:
        import signal
        try:
            name = signal.Signals(-code).name
        except ValueError:
            name = str(-code)
        return 'cancelled', 'Interrumpido · ' + name
    if code is None:
        return 'disconnected', 'Conexión finalizada · resultado no recibido'
    return 'error', 'Finalizado · código ' + plain(code, 10)


def safe_output(command):
    # No pipelines, expansions, shell constructs or interpreter scripts. This
    # intentionally hides useful unknown output rather than guess its privacy.
    if not command or re.search(r'[\n\r;&|<>`$(){}]', command) or SENSITIVE.search(command):
        return False
    try:
        words = shlex.split(command)
        return bool(words) and Path(words[0]).name in SAFE_OUTPUT
    except ValueError:
        return False


DISPLAY_COMMANDS = SAFE_OUTPUT | {'smartctl', 'findmnt', 'lspci', 'lsusb', 'dmidecode', 'ip', 'ss', 'ps', 'top', 'htop', 'systemctl', 'journalctl', 'ethtool', 'rfkill', 'blkid', 'fdisk', 'parted', 'sensors', 'nvidia-smi', 'hostnamectl'}
URL = re.compile(r'https?://[^\s\"\'<>]+')


def safe_url(match):
    try:
        parsed = urlsplit(match.group(0))
        host = parsed.netloc.split('@')[-1]
        # Values of every query field and fragment are hidden, not only those
        # whose field names happen to mention credentials.
        return urlunsplit((parsed.scheme, host, parsed.path, '[consulta oculta]' if parsed.query else '', '[fragmento oculto]' if parsed.fragment else ''))
    except ValueError:
        return '[URL oculta]'


SECRET_NAME = r'(?:password|passwd|passphrase|secret|token|credential|authorization|api[_-]?key|e2e[_-]?key|private[_-]?key|psk)'
QUOTED_VALUE = r'''(?:"(?:\\.|[^"\\])*"|'[^']*'|[^\s;&|'"<>]+)'''
SECRET_OPTION = re.compile(r'(?i)((?<![\w])--?[\w-]*'+SECRET_NAME+r'[\w-]*(?:\s*=\s*|\s+))'+QUOTED_VALUE)
SECRET_ASSIGN = re.compile(r'''(?i)((?<![\w])['"]?[\w-]*'''+SECRET_NAME+r'''[\w-]*['"]?\s*[:=]\s*)'''+QUOTED_VALUE)
BEARER = re.compile(r'(?i)(\bBearer\s+)[A-Za-z0-9._~+/-]+=*')
AUTH_HEADER = re.compile(r'''(?i)(\bAuthorization\s*:\s*)(?:Bearer\s+|Basic\s+)?[^\s'";]+''')
JWT = re.compile(r'\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b')


def command_view(value):
    """Keep argv, quoting and shell structure; conceal credential values only.

    Unlabelled arbitrary strings are not detectable secrets. Known config/native
    credentials and explicit credential options/assignments are always masked.
    """
    for pattern in (AUTH_HEADER, BEARER, SECRET_OPTION, SECRET_ASSIGN):
        value = pattern.sub(lambda m: m.group(1)+'[oculto]', value)
    value = JWT.sub('[token oculto]', value)
    return URL.sub(safe_url, value)


RECOVERY = re.compile(r'\b\d{6}(?:-\d{6}){7}\b')


def plain(value, limit=MAX_TEXT):
    value = ESCAPE.sub('', str(value))
    value = ''.join(c for c in value if c in '\n\t' or (32 <= ord(c) < 127) or (ord(c) >= 160 and not 0x200b <= ord(c) <= 0x206f))
    return value[:limit]


SECRET_FILES = ('/etc/aguja/aguja.conf', '/config/aguja.conf',
                '/home/aguja/.config/aguja/provider-env.json', '/run/aguja-platform/remote.json',
                '/config/aguja-profile.json', '/config/aguja-remote.json', '/config/aguja-agent-access.json',
                '/home/aguja/.codex/auth.json', '/home/aguja/.gemini/antigravity-cli/antigravity-oauth-token',
                '/home/aguja/.claude/.credentials.json', '/home/aguja/.local/share/opencode/auth.json')


def secret_stamp():
    """Cheap change detection, including atomic credential replacement after boot."""
    result = []
    for filename in SECRET_FILES:
        try:
            info = Path(filename).stat()
            result.append((info.st_ino, info.st_mtime_ns, info.st_size))
        except OSError:
            result.append(None)
    return tuple(result)


def secret_values():
    """Read only known config credentials, never display or persist them."""
    found = set()
    for name in SECRET_FILES[:2]:
        try:
            c = configparser.ConfigParser(interpolation=None)
            c.read(name)
            for section in c.sections():
                for key, value in c.items(section):
                    if SENSITIVE.search(key) and len(value) >= 4 and value != 'aguja':
                        found.add(value)
        except (OSError, configparser.Error):
            pass
    for filename in SECRET_FILES[2:]:
        try:
            value = json.loads(Path(filename).read_text())
            def collect(item):
                if isinstance(item, dict):
                    for key, item_value in item.items():
                        if SENSITIVE.search(key) and isinstance(item_value, str) and len(item_value) >= 4 and item_value != 'aguja':
                            found.add(item_value)
                            # A delegated token packs two secrets; redact either
                            # component too, should a command use it separately.
                            if item_value.startswith('aguja1.'):
                                found.update(item_value.split('.')[1:])
                        elif isinstance(item_value, (dict, list)):
                            collect(item_value)
                elif isinstance(item, list):
                    for child in item:
                        collect(child)
            collect(value)
        except (OSError, ValueError):
            pass
    return found


def redact(value, secrets=(), command=False):
    value = plain(value, 65536 if command else max(12000,len(str(value))))
    if '-----BEGIN ' in value or '-----END ' in value:
        return '[bloque de clave/certificado oculto]'
    for secret in sorted(secrets, key=len, reverse=True):
        if secret:
            value = value.replace(secret, '[oculto]')
    value = RECOVERY.sub('[clave de recuperación oculta]', value)
    if command:
        value = command_view(value)
        return value[:MAX_COMMAND_TEXT] + ('\n[comando truncado: límite 16384 caracteres]' if len(value)>MAX_COMMAND_TEXT else '')
    value = command_view(value)
    # Mask common unlabelled provider credentials, not hashes/long ordinary text.
    value = re.sub(r'\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9_]{20,}|KF_API_[A-Za-z0-9-]+)\b', '[credencial oculta]', value)
    return value


class OutputFilter:
    """Reassemble chunk-split lines before sanitizing; never publish stdin.

    Redact complete lines before splitting them into bounded visible events. PEM blocks remain muted
    even when their headers, contents and trailers arrive in separate chunks.
    """
    def __init__(self, secrets=()):
        self.secrets = secrets
        self.pending = b''
        self.overflow = False
        self.pem = False

    def feed(self, chunk, final=False):
        results = []
        for part in chunk.splitlines(keepends=True):
            self.pending += part
            if len(self.pending) > 1048576:
                self.pending = b''
                self.overflow = True
            if part.endswith((b'\n', b'\r')):
                if self.overflow:
                    results.append('[línea supera 1 MiB: límite de memoria del panel; salida íntegra en consola]')
                else:
                    results += self._line(self.pending)
                self.pending = b''
                self.overflow = False
        if final and (self.pending or self.overflow):
            if self.overflow:
                results.append('[línea supera 1 MiB: límite de memoria del panel; salida íntegra en consola]')
            else:
                results += self._line(self.pending)
            self.pending = b''
            self.overflow = False
        return results

    def _line(self, line):
        value = line.decode('utf-8', 'replace').rstrip('\r\n')
        if '-----BEGIN ' in value:
            self.pem = True
            return ['[bloque de clave/certificado oculto]']
        if self.pem:
            if '-----END ' in value:
                self.pem = False
            return []
        text = redact(value, self.secrets)
        return [text[i:i+MAX_TEXT] for i in range(0,len(text),MAX_TEXT)] if text.strip() else []


def emit(kind, text='', **fields):
    """Fire-and-forget; monitoring can never be required for SSH to work."""
    try:
        sensitive = kind in ('session_start', 'command_start') and not safe_output(text)
        packet = dict(fields, kind=kind, text=redact(text, secret_values(), command=kind in ('session_start', 'command_start')),
                      session=fields.get('session') or os.environ.get('AGUJA_SESSION_ID', ''))
        packet['sensitive'] = fields.get('sensitive', False) or sensitive
        if kind == 'command_start' and not fields.get('label'):
            packet['label'] = task_label(text)
        raw = json.dumps(packet, ensure_ascii=True).encode()
        if len(raw) > MAX_PACKET:
            return
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as client:
            needs_ack = kind not in ('output', 'input_activity')
            client.settimeout(1.0 if needs_ack else 0.005)
            client.bind('')  # Linux abstract autobind, never filesystem traces.
            client.sendto(raw, str(SOCKET))
            if needs_ack:
                client.recv(16)
    except (OSError, ValueError):
        pass


def snapshot():
    try:
        if SNAPSHOT.stat().st_size > 8000000:
            return dict(EMPTY)
        data = json.loads(SNAPSHOT.read_text())
        if not isinstance(data, dict) or time.time() - data.get('updated', 0) > 5:
            return dict(EMPTY)
        return data
    except (OSError, ValueError, TypeError):
        return dict(EMPTY)


def read_processes(root='/proc'):
    result = {}
    for path in Path(root).glob('[0-9]*'):
        try:
            # comm may contain parentheses/spaces. Fields after final ')' start
            # at state (field 3), not at comm's first whitespace.
            stat = (path / 'stat').read_text()
            tail = stat[stat.rfind(')') + 2:].split()
            result[int(path.name)] = {'pid': int(path.name), 'ppid': int(tail[1]),
                'state': tail[0], 'start_ticks': int(tail[19]),
                'ticks': int(tail[11]) + int(tail[12]),
                'command': (path / 'cmdline').read_bytes().replace(b'\0', b' ').decode('utf-8', 'replace').strip() or '[proceso del núcleo]'}
        except (OSError, ValueError, IndexError):
            pass
    return result


def descends(pid, ancestor, processes):
    seen = set()
    while pid in processes and pid not in seen:
        if pid == ancestor:
            return True
        seen.add(pid)
        pid = processes[pid]['ppid']
    return False


class Monitor:
    def __init__(self, secrets=()):
        self.secrets = set(secrets)
        self.sessions = collections.OrderedDict()
        self.events = collections.deque(maxlen=MAX_EVENTS)
        self.processes = []
        self.samples = {}
        self.last_scan = 0
        self.suppressed = {}
        self.filters = {}
        self.ending = {}
        self.commands = collections.OrderedDict()
        self.command_number = 0

    def restore_history(self, data, processes=None):
        """Keep sanitized trace; only reconnect sessions with the same live PID."""
        processes=processes or {}
        for session in data.get('sessions',[])[:MAX_SESSIONS]:
            if not isinstance(session,dict):continue
            process=processes.get(session.get('pid'))
            if not process or process.get('start_ticks')!=session.get('start_ticks'):continue
            if not any(name in process.get('command','').split() for name in ('/usr/lib/aguja/ssh_session.py','/usr/lib/aguja/tunnel.py','/usr/lib/aguja/console_session.py')):continue
            try:uid=Path('/proc/'+str(session['pid'])).stat().st_uid
            except OSError:continue
            sid=session.get('id')
            if not isinstance(sid,str) or not re.fullmatch(r'[a-f0-9]{24}',sid):continue
            self.sessions[sid]=dict(session,uid=uid)
            self.suppressed[sid]=True
            self.filters[sid]=OutputFilter(self.secrets)
        for row in data.get('commands', [])[-MAX_COMMANDS:]:
            if not isinstance(row,dict) or not isinstance(row.get('id'),str):continue
            row=dict(row)
            row['command']=redact(row.get('command',''),self.secrets,command=True)
            row['title']=redact(row.get('title',''),self.secrets)[:100]
            if row.get('status')=='running' and row.get('session') not in self.sessions:
                row.update(status='disconnected',exit=None,result=result_state(None)[1])
            self.commands[row['id']]=row
            try:self.command_number=max(self.command_number,int(row['id'].rsplit(':',1)[1]))
            except (ValueError,IndexError):pass
        for row in data.get('events', [])[-MAX_EVENTS:]:
            if isinstance(row,dict):
                self.events.append(dict(row,text=redact(row.get('text',''),self.secrets,command=row.get('kind')=='command_start')))

    def begin_command(self, sid, text, label=None):
        s = self.sessions[sid]
        previous = self.commands.get(s.get('command_id'))
        if label and previous and previous['status'] == 'running' and previous.get('labelled'):
            previous.update(title=redact(label, self.secrets)[:100], command=text,
                            output_private=False)
            return
        self.finish_command(sid, None)
        self.command_number += 1
        key = sid + ':' + str(self.command_number)
        self.commands[key] = {'id': key, 'session': sid, 'title': redact(label, self.secrets)[:100] if label else text.split('\n')[0][:100],
                              'command': text, 'started': time.time(), 'status': 'running',
                              'transport': s.get('transport','ssh'),
                              'technical': bool(s.get('probe')), 'output_private': False, 'labelled': bool(label),
                              'user': s.get('user','aguja'), 'peer': s.get('peer',''), 'executor': s.get('transport','ssh')}
        if s.get('probe'):
            self.commands[key]['title'] = 'Comprobar repositorio Git'
        s['command_id'] = key
        s['command_started'] = time.time()
        while len(self.commands) > MAX_COMMANDS:
            ended = next((k for k, c in self.commands.items() if c['status'] != 'running'), None)
            if ended is None:
                break
            del self.commands[ended]

    def finish_command(self, sid, code):
        s = self.sessions[sid]
        c = self.commands.get(s.get('command_id'))
        if c and c['status'] == 'running':
            c.update(ended=time.time(), exit=code)
            c['status'], c['result'] = result_state(code, s.get('probe'))
            c['duration'] = round(max(0, c['ended'] - c['started']), 2)

    def event(self, packet, pid, uid, processes):
        """Kernel SCM_CREDENTIALS identity; never trust a supplied root pid/uid."""
        sid = packet.get('session', '')
        kind = packet.get('kind')
        if not isinstance(sid, str) or not re.fullmatch(r'[a-f0-9]{24}', sid):
            return
        if kind == 'session_start':
            process = processes.get(pid)
            if not process or not any(name in process['command'].split() for name in ('/usr/lib/aguja/ssh_session.py', '/usr/lib/aguja/tunnel.py', '/usr/lib/aguja/console_session.py', 'ssh_session.py', 'tunnel.py', 'console_session.py')):
                return
            if sid in self.sessions or sum(s['status'] == 'active' for s in self.sessions.values()) >= MAX_SESSIONS:
                return
            if len(self.sessions) >= MAX_SESSIONS:
                ended = next((key for key, s in self.sessions.items() if s['status'] != 'active'), None)
                if ended:
                    del self.sessions[ended]
                    self.filters.pop(ended, None)
                    self.suppressed.pop(ended, None)
                    self.ending.pop(ended, None)
            self.sessions[sid] = {'id': sid, 'user': plain(pwd.getpwuid(uid).pw_name, 40),
                'peer': plain(packet.get('peer', ''), 100), 'started': time.time(),
                'command': redact(packet.get('text', ''), self.secrets, command=True),
                'status': 'active', 'pid': pid, 'start_ticks': process['start_ticks'], 'uid': uid,
                'mode': plain(packet.get('mode', ''), 40), 'transport': packet.get('transport') if packet.get('transport') in ('tunnel','local') else 'ssh'}
            probe = packet.get('probe')
            if isinstance(probe, dict) and probe.get('kind') == 'git_workspace':
                self.sessions[sid]['probe'] = {'kind': 'git_workspace'}
            self.suppressed[sid] = packet.get('mode') == 'interactive'
            self.filters[sid] = OutputFilter(self.secrets)
            if packet.get('mode') != 'interactive':
                self.begin_command(sid, self.sessions[sid]['command'], packet.get('label'))
            text = {'tunnel':'Túnel conectado · ','local':'Consola iniciada · '}.get(self.sessions[sid]['transport'],'Conexión SSH · ') + self.sessions[sid]['peer']
        else:
            s = self.sessions.get(sid)
            if not s or s['status'] != 'active' or uid != s['uid']:
                return
            root = processes.get(s['pid'])
            if not root or root['start_ticks'] != s['start_ticks'] or not descends(pid, s['pid'], processes):
                return
            if kind not in ('session_end', 'command_start', 'command_end', 'output', 'input_activity'):
                return
            if kind == 'input_activity':
                # No bytes, length, timing transcript or content of stdin.
                # Mute PTY echo while a human types; hook re-enables only
                # after the shell has accepted a safe command.
                command = self.commands.get(s.get('command_id'), {})
                if command.get('status') != 'running':
                    self.suppressed[sid] = True
                    self.filters[sid] = OutputFilter(self.secrets)
                    self.ending.pop(sid, None)
                return
            if kind == 'session_end':
                if not self.suppressed.get(sid):
                    for line in self.filters[sid].feed(b'', final=True):
                        self.events.append({'time': time.time(), 'kind': 'output', 'session': sid, 'text': line, 'command_id': s.get('command_id'), 'technical': bool(s.get('probe'))})
                if pid != s['pid']:
                    return
                s.update(status='ended', ended=time.time(), exit=packet.get('exit'))
                self.finish_command(sid, packet.get('exit'))
                self.filters.pop(sid, None)
                self.suppressed.pop(sid, None)
                self.ending.pop(sid, None)
                state, reason = result_state(packet.get('exit'), s.get('probe'))
                text = {'tunnel':'Túnel finalizado · ','local':'Consola finalizada · '}.get(s['transport'],'SSH finalizado · ') + reason
            elif kind == 'command_start':
                self.ending.pop(sid, None)
                raw = packet.get('text', '')
                sensitive = False
                self.filters[sid] = OutputFilter(self.secrets)
                self.suppressed[sid] = sensitive
                text = redact(raw, self.secrets, command=True)
                s['command'] = text
                self.begin_command(sid, text, packet.get('label'))
            elif kind == 'command_end':
                # The shell hook and PTY relay are separate senders. The end
                # hook can overtake final stdout still queued in the PTY.
                # A bounded drain grace admits only the preceding SAFE output;
                # any keyboard input mutes immediately before it can echo.
                if not self.suppressed.get(sid):
                    self.ending[sid] = time.monotonic() + END_GRACE
                else:
                    self.filters[sid] = OutputFilter(self.secrets)
                text = 'Comando terminado · código ' + plain(packet.get('text', ''), 10)
                try:
                    code = int(packet.get('text', ''))
                except (ValueError, TypeError):
                    code = None
                self.finish_command(sid, code)
            else:
                self.expire(time.monotonic())
                if pid != s['pid'] or self.suppressed.get(sid):
                    return
                try:
                    chunk = base64.b64decode(packet.get('chunk', ''), validate=True)
                except (ValueError, TypeError):
                    return
                if len(chunk) > 4096:
                    return
                for line in self.filters[sid].feed(chunk):
                    self.events.append({'time': time.time(), 'kind': kind, 'session': sid, 'text': line,
                                        'command_id': s.get('command_id'), 'technical': bool(s.get('probe'))})
                return
        self.events.append({'time': time.time(), 'kind': kind, 'session': sid, 'text': text[:MAX_TEXT],
                            'command_id': self.sessions[sid].get('command_id'), 'technical': bool(self.sessions[sid].get('probe'))})

    def expire(self, now):
        for sid, deadline in list(self.ending.items()):
            if now < deadline:
                continue
            if not self.suppressed.get(sid) and sid in self.filters:
                for line in self.filters[sid].feed(b'', final=True):
                    self.events.append({'time': time.time(), 'kind': 'output', 'session': sid, 'text': line,
                                        'command_id': self.sessions[sid].get('command_id'), 'technical': bool(self.sessions[sid].get('probe'))})
            self.suppressed[sid] = True
            self.filters[sid] = OutputFilter(self.secrets)
            self.ending.pop(sid, None)

    def scan(self, processes, now=None):
        now = time.monotonic() if now is None else now
        self.expire(now)
        view = []
        for sid, session in self.sessions.items():
            if session['status'] != 'active':
                continue
            root = processes.get(session['pid'])
            if not root or root['start_ticks'] != session['start_ticks']:
                session.update(status='ended', ended=time.time())
                self.finish_command(sid, None)
                self.filters.pop(sid, None)
                self.suppressed.pop(sid, None)
                self.ending.pop(sid, None)
                self.events.append({'time': time.time(), 'kind': 'session_end', 'session': sid, 'text': 'Conexión finalizada',
                                    'technical': bool(session.get('probe'))})
                continue
            for pid, process in processes.items():
                if not descends(pid, session['pid'], processes):
                    continue
                key = (pid, process['start_ticks'])
                previous = self.samples.get(key)
                cpu = 0.0
                if previous and now > previous[0]:
                    cpu = max(0.0, (process['ticks'] - previous[1]) / os.sysconf('SC_CLK_TCK') / (now - previous[0]) * 100)
                self.samples[key] = (now, process['ticks'])
                view.append({'session': sid, 'pid': pid, 'ppid': process['ppid'], 'state': process['state'], 'technical': bool(session.get('probe')),
                    'command': redact(process['command'], self.secrets, command=True), 'cpu': round(cpu, 1)})
                if len(view) >= MAX_PROCESSES:
                    break
        keys = {(p['pid'], p['start_ticks']) for p in processes.values()}
        self.samples = {key: value for key, value in self.samples.items() if key in keys}
        self.processes = view[:MAX_PROCESSES]

    def data(self):
        return {'sessions': [{k: v for k, v in s.items() if k != 'uid'} for s in self.sessions.values() if s['status'] == 'active'],
                'recent_sessions': [{k: v for k, v in s.items() if k != 'uid'} for s in self.sessions.values() if s['status'] != 'active'],
                'events': list(self.events), 'commands': list(self.commands.values()), 'processes': self.processes, 'available': True, 'updated': time.time(),
                'privacy': 'Comandos y argumentos visibles; credenciales ocultas. No se registra stdin.'}


def serve():
    DIRECTORY.mkdir(mode=0o755, parents=True, exist_ok=True)
    SOCKET.unlink(missing_ok=True)
    monitor = Monitor(secret_values())
    try:
        info=SNAPSHOT.lstat()
        if info.st_uid==0 and not info.st_mode & 0o022 and not SNAPSHOT.is_symlink() and info.st_size<=8000000:
            monitor.restore_history(json.loads(SNAPSHOT.read_text()),read_processes())
    except (OSError,ValueError,TypeError,KeyError):pass
    credentials_stamp = secret_stamp()
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
        server.bind(str(SOCKET))
        os.chown(SOCKET, 0, pwd.getpwnam('aguja').pw_gid)
        os.chmod(SOCKET, 0o660)
        server.settimeout(0.2)
        last_scan = 0
        processes = {}
        while True:
            try:
                raw, ancillary, flags, address = server.recvmsg(MAX_PACKET, socket.CMSG_SPACE(struct.calcsize('3i')))
                credentials = next((struct.unpack('3i', value[:12]) for level, kind, value in ancillary
                    if level == socket.SOL_SOCKET and kind == socket.SCM_CREDENTIALS), None)
                if credentials and not flags & socket.MSG_TRUNC:
                    updated_stamp = secret_stamp()
                    if updated_stamp != credentials_stamp:
                        # Filters share this set, so an already-open SSH session
                        # cannot expose access credentials created after boot.
                        monitor.secrets.update(secret_values())
                        credentials_stamp = updated_stamp
                    packet = json.loads(raw)
                    if isinstance(packet, dict):
                        # Hooks may be short-lived, so snapshot parents while
                        # the caller is still alive (client briefly waits).
                        if packet.get('kind') != 'output':
                            processes = read_processes()
                        monitor.event(packet, credentials[0], credentials[1], processes)
                        if address and packet.get('kind') not in ('output', 'input_activity'):
                            server.sendto(b'ack', address)
            except (OSError, ValueError, TypeError, KeyError, OverflowError):
                pass
            if time.monotonic() - last_scan > 0.5:
                last_scan = time.monotonic()
                processes = read_processes()
                monitor.scan(processes)
                temp = SNAPSHOT.with_suffix('.tmp')
                fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
                os.fchmod(fd, 0o644)
                with os.fdopen(fd, 'w') as target:
                    json.dump(monitor.data(), target, ensure_ascii=False)
                os.replace(temp, SNAPSHOT)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['serve', 'emit'])
    parser.add_argument('kind', nargs='?', default='command_start')
    # Text arrives via a pipe, NOT argv: otherwise the observer itself would
    # briefly expose sensitive shell text in /proc and process views.
    parser.add_argument('--sensitive', action='store_true')
    args = parser.parse_args()
    if args.action == 'serve':
        serve()
    else:
        import sys
        text = sys.stdin.read(12000)
        emit(args.kind, text, sensitive=args.sensitive or '\n' in text.rstrip('\n') or bool(SENSITIVE.search(text)))


if __name__ == '__main__':
    main()
