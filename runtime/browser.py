"""Local OAuth browser and a private bridge to the *existing* CLI PTY.

No clipboard content is read. A changed X selection owner only focuses the
console; the user explicitly pastes there. No passwords/codes are logged or
exchanged here. The normal-user Chromium sandbox is never disabled.
"""
import ctypes
import fcntl
import json
import os
from pathlib import Path
import pwd
import select
import shutil
import signal
import socket
import stat
import struct
import subprocess
import sys
import tempfile
import termios
import time
import tty

import auth

MAX_FRAME=65536
HEADER=struct.Struct('!BI')


def frame(kind,data):
    if len(data)>MAX_FRAME:raise ValueError('Oversized console frame')
    return HEADER.pack(kind,len(data))+data


def frames(buffer):
    rows=[]
    while len(buffer)>=HEADER.size:
        kind,size=HEADER.unpack(buffer[:HEADER.size])
        if size>MAX_FRAME:raise ValueError('Oversized console frame')
        if len(buffer)<HEADER.size+size:break
        rows.append((kind,bytes(buffer[HEADER.size:HEADER.size+size])))
        del buffer[:HEADER.size+size]
    return rows


def local_console():
    if os.environ.get('SSH_CONNECTION') or os.environ.get('SSH_TTY'):return False
    try:
        name=os.ttyname(0)
        return name.startswith('/dev/tty') and name[8:].isdigit() or os.environ.get('AGUJA_LOCAL_CONSOLE')=='1'
    except OSError:return False


def available():
    return os.getuid()!=0 and local_console() and all(shutil.which(x) for x in
        ('chromium','Xorg','xterm','openbox','xdotool','xauth','sudo'))


class Relay:
    """Single same-UID client, bounded RAM-only output, no protocol logging."""
    def __init__(self,directory):
        self.path=directory/'console.sock'
        self.server=socket.socket(socket.AF_UNIX);self.server.bind(str(self.path))
        self.path.chmod(0o600);self.server.listen(1);self.server.setblocking(False)
        self.client=None;self.rx=bytearray();self.tx=bytearray();self.history=bytearray()
    def disconnect(self):
        if self.client:self.client.close()
        self.client=None;self.rx.clear();self.tx.clear()
    def output(self,data):
        self.history.extend(data);self.history=self.history[-MAX_FRAME:]
        if self.client:
            self.tx.extend(frame(0,data))
            if len(self.tx)>1024*1024:self.disconnect()
    def poll(self,master):
        try:
            client,_=self.server.accept()
            uid=struct.unpack('3i',client.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))[1]
            if uid!=os.getuid() or self.client:client.close()
            else:
                self.client=client;client.setblocking(False)
                self.tx.extend(frame(0,bytes(self.history)))
        except BlockingIOError:pass
        if not self.client:return
        try:
            try:
                data=self.client.recv(MAX_FRAME)
                if not data:self.disconnect();return
                self.rx.extend(data)
            except BlockingIOError:pass
            for kind,data in frames(self.rx):
                if kind==1:
                    from auth_pty import write_all
                    write_all(master,data)
                elif kind==2 and len(data)==8:fcntl.ioctl(master,termios.TIOCSWINSZ,data)
                else:raise ValueError('Invalid console frame')
            if self.tx:
                try:del self.tx[:self.client.send(self.tx)]
                except BlockingIOError:pass
        except (OSError,ValueError):self.disconnect()
    def close(self):
        self.disconnect();self.server.close();self.path.unlink(missing_ok=True)


def launch(directory):
    (directory/'browser-stop').unlink(missing_ok=True)
    return subprocess.Popen(['sudo','-n','/usr/local/bin/aguja-browser-launch',str(directory)],
                            stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)


def terminal(directory):
    """xterm input belongs to the same native CLI, not a new login process."""
    connection=socket.socket(socket.AF_UNIX);connection.connect(str(directory/'console.sock'))
    attributes=termios.tcgetattr(0);buffer=bytearray()
    def resize(*_):
        connection.sendall(frame(2,fcntl.ioctl(0,termios.TIOCGWINSZ,bytes(8))))
    previous=signal.signal(signal.SIGWINCH,resize)
    try:
        resize();tty.setraw(0,when=termios.TCSANOW)
        while True:
            ready,_,_=select.select([0,connection],[],[],.2)
            for item in ready:
                data=os.read(0,4096) if item==0 else connection.recv(MAX_FRAME)
                if not data:return 0
                if item==0:connection.sendall(frame(1,data))
                else:
                    buffer.extend(data)
                    for kind,payload in frames(buffer):
                        if kind!=0:raise ValueError('Invalid console output')
                        from auth_pty import write_all
                        write_all(1,payload)
    finally:
        (directory/'browser-stop').touch(mode=0o600)
        termios.tcsetattr(0,termios.TCSANOW,attributes)
        signal.signal(signal.SIGWINCH,previous);connection.close()


class SelectionOwners:
    """Observe ownership only; never call XConvertSelection/read clipboard."""
    def __init__(self):
        self.x=ctypes.CDLL('libX11.so.6')
        self.x.XOpenDisplay.argtypes=[ctypes.c_char_p];self.x.XOpenDisplay.restype=ctypes.c_void_p
        self.x.XInternAtom.argtypes=[ctypes.c_void_p,ctypes.c_char_p,ctypes.c_int];self.x.XInternAtom.restype=ctypes.c_ulong
        self.x.XGetSelectionOwner.argtypes=[ctypes.c_void_p,ctypes.c_ulong];self.x.XGetSelectionOwner.restype=ctypes.c_ulong
        self.x.XCloseDisplay.argtypes=[ctypes.c_void_p]
        self.display=self.x.XOpenDisplay(None)
        if not self.display:raise OSError('No X display')
        # PRIMARY changes when text is merely selected, before Copy. Watching
        # it would steal focus and prevent the user from copying the code.
        self.atoms=[self.x.XInternAtom(self.display,b'CLIPBOARD',0)]
        self.owners=self.sample()
    def sample(self):return tuple(self.x.XGetSelectionOwner(self.display,a) for a in self.atoms)
    def changed(self):
        owners=self.sample();changed=any(new and new!=old for old,new in zip(self.owners,owners))
        self.owners=owners;return changed
    def close(self):self.x.XCloseDisplay(self.display)


def focus_console():
    # Match our fixed WM_CLASS, never window text (which may be private).
    found=subprocess.run(['xdotool','search','--onlyvisible','--class','aguja-oauth-console'],
                         capture_output=True,timeout=2)
    for window in found.stdout.splitlines()[:1]:
        if window.isdigit():subprocess.run(['xdotool','windowactivate','--sync',window.decode()],
                                          stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=2)


def user_session(directory):
    if os.getuid()==0:return 1
    record=auth.read_record(directory/'request.json')
    if not record:return 1
    mask=os.umask(0o077);children=[];selection=None;stopping=False
    temporary=tempfile.TemporaryDirectory(prefix='browser-',dir=directory)
    def stop(*_):
        nonlocal stopping
        stopping=True
    handlers={s:signal.signal(s,stop) for s in (signal.SIGTERM,signal.SIGINT,signal.SIGHUP)}
    try:
        private=Path(temporary.name);os.environ['XDG_CACHE_HOME']=str(private/'cache')
        os.environ['XDG_CONFIG_HOME']=str(private/'config')
        # No OAuth URL in process argv, Xorg logs or any persistent HOME.
        page=private/'start.html'
        page.write_text('<!doctype html><meta charset="utf-8"><title>LA AGUJA · Login</title>'
                        '<script>location.replace('+json.dumps(record['url']).replace('<','\\u003c')+')</script>')
        children.append(subprocess.Popen(['openbox'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
        terminal_process=subprocess.Popen(['xterm','-class','aguja-oauth-console','-T',
            'LA AGUJA | misma consola | Ctrl+Shift+V pega | cerrar vuelve al texto',
            '-geometry','100x28+16+440','-xrm',
            '*VT100.translations: #override Ctrl Shift <Key>V: insert-selection(CLIPBOARD)',
            '-e','/usr/bin/python3','/usr/lib/aguja/browser.py','terminal',str(directory)],
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        children.append(terminal_process)
        selection=SelectionOwners()
        chromium=subprocess.Popen(['chromium','--user-data-dir='+str(private/'profile'),
            '--no-first-run','--no-default-browser-check','--disable-sync',
            '--ozone-platform=x11','--password-store=basic','--window-size=1000,650','--window-position=16,16',
            '--app='+page.as_uri()],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        children.append(chromium)
        while not stopping and terminal_process.poll() is None and chromium.poll() is None:
            if (directory/'browser-stop').exists() or auth.process_stamp(record['pid'])!=record['start_ticks']:break
            if selection.changed():
                try:focus_console()
                except (OSError,subprocess.TimeoutExpired):pass
            time.sleep(.1)
    finally:
        if selection:selection.close()
        for child in reversed(children):
            if child.poll() is None:
                child.terminate()
                try:child.wait(timeout=3)
                except subprocess.TimeoutExpired:child.kill();child.wait()
        temporary.cleanup()
        for sig,handler in handlers.items():signal.signal(sig,handler)
        os.umask(mask)
    return 0


def original_vt(pid):
    """Only allow a real local console in the authenticated caller ancestry."""
    for _ in range(16):
        try:
            name=os.readlink(f'/proc/{pid}/fd/0')
            if name.startswith('/dev/tty') and name[8:].isdigit() and 1<=int(name[8:])<=63:return int(name[8:])
            pid=int(Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()[1])
            if pid<=1:break
        except (OSError,ValueError,IndexError):break
    raise ValueError('Local console required')


def privileged_launch(directory):
    """Root owns Xorg/VT only. GUI browser+terminal run as caller, never root."""
    if os.getuid()!=0:return 1
    uid=int(os.environ.get('SUDO_UID','0'));user=pwd.getpwuid(uid)
    if uid==0 or directory.parent!=auth.BASE/str(uid) or directory.is_symlink():return 1
    info=directory.lstat()
    if info.st_uid!=uid or not stat.S_ISDIR(info.st_mode) or stat.S_IMODE(info.st_mode)!=0o700:return 1
    # Validate the owner-only session using its actual user identity.
    validation=subprocess.run(['runuser','-u',user.pw_name,'--','/usr/bin/python3',
        '/usr/lib/aguja/browser.py','validate',str(directory)],capture_output=True,timeout=5)
    if validation.returncode:return 1
    pid,stamp=json.loads(validation.stdout)
    oldvt=original_vt(pid)
    lock=os.open('/run/aguja-browser.lock',os.O_CREAT|os.O_WRONLY|os.O_NOFOLLOW,0o600)
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:os.close(lock);return 1
    processes=[];stopping=False
    temporary=tempfile.TemporaryDirectory(prefix='aguja-browser-x-',dir='/run')
    def stop(*_):
        nonlocal stopping
        stopping=True
    handlers={s:signal.signal(s,stop) for s in (signal.SIGTERM,signal.SIGINT,signal.SIGHUP)}
    try:
        private=Path(temporary.name);os.chown(private,0,user.pw_gid);private.chmod(0o750)
        # xauth needs to create lock/temp siblings, not just write the cookie
        # file. Keep the outer directory root-owned and give only the caller
        # a writable private subdirectory for that protocol.
        user_auth=private/'user-auth';user_auth.mkdir(mode=0o700)
        os.chown(user_auth,uid,user.pw_gid)
        authority=user_auth/'Xauthority';authority.touch(mode=0o600);os.chown(authority,uid,user.pw_gid)
        import secrets
        display=next(n for n in range(20,40) if not Path(f'/tmp/.X11-unix/X{n}').exists() and not Path(f'/tmp/.X{n}-lock').exists())
        cookie=secrets.token_hex(16)
        # Send the cookie on stdin, never argv/logs.
        subprocess.run(['runuser','-u',user.pw_name,'--','xauth','-f',str(authority)],
            input=f'add :{display} . {cookie}\n'.encode(),check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        fd=os.open('/dev/tty0',os.O_RDWR)
        try:vt=struct.unpack('i',fcntl.ioctl(fd,0x5600,bytes(4)))[0]
        finally:os.close(fd)
        if vt<=0 or vt==oldvt:raise OSError('No spare virtual console')
        server=subprocess.Popen(['/usr/bin/Xorg',f':{display}',f'vt{vt}','-nolisten','tcp',
            '-auth',str(authority),'-logfile','/dev/null','-noreset'],stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        processes.append(server)
        environment=dict(os.environ,DISPLAY=f':{display}',XAUTHORITY=str(authority),HOME=user.pw_dir)
        environment.pop('DBUS_SESSION_BUS_ADDRESS',None)
        environment.pop('WAYLAND_DISPLAY',None)
        environment['XDG_SESSION_TYPE']='x11'
        ready=False
        for _ in range(100):
            if stopping or server.poll() is not None:break
            check=subprocess.run(['runuser','-u',user.pw_name,'--','xdpyinfo'],env=environment,
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=2)
            if check.returncode==0:ready=True;break
            time.sleep(.1)
        if not ready:return 1
        gui=subprocess.Popen(['runuser','-u',user.pw_name,'--','dbus-run-session','--',
            '/usr/lib/aguja/browser-session',str(directory)],env=environment,
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        processes.append(gui)
        while not stopping and gui.poll() is None and server.poll() is None:
            if (directory/'browser-stop').exists() or auth.process_stamp(pid)!=stamp:break
            time.sleep(.1)
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
                try:process.wait(timeout=4)
                except subprocess.TimeoutExpired:process.kill();process.wait()
        temporary.cleanup()
        subprocess.run(['chvt',str(oldvt)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5)
        for sig,handler in handlers.items():signal.signal(sig,handler)
        os.close(lock)
    return 0


if __name__=='__main__':
    try:
        action=sys.argv[1];directory=Path(sys.argv[2])
        if action=='validate':
            record=auth.read_record(directory/'request.json')
            if not record:raise ValueError('Invalid session')
            print(json.dumps([record['pid'],record['start_ticks']]))
        elif action=='terminal':raise SystemExit(terminal(directory))
        elif action=='session':raise SystemExit(user_session(directory))
        elif action=='launch':raise SystemExit(privileged_launch(directory))
        else:raise ValueError('Unknown browser action')
    except (OSError,ValueError,IndexError,subprocess.SubprocessError):
        # Do not disclose URLs, cookies, codes or private profile paths.
        print('LA AGUJA: navegador no disponible; conserva el acceso nativo.',file=sys.stderr)
        raise SystemExit(1)
