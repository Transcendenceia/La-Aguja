"""Interactive-only CLI relay with an optional private local browser.

Non-TTY/print/JSON invocations never pass through this relay. Keystrokes and CLI
output are not logged; native CLIs retain ownership of tokens and code exchange.
"""
import fcntl
import os
import pty
import select
import signal
import termios
import time
import subprocess
import tty
import re

import auth


class NativeLoginChoice:
    """The explicit Google-login menu action selects only the native method.

    This never signs in, approves consent, submits a code or sends a model prompt.
    Ordinary agent launches keep the provider's full native method selector.
    """
    def __init__(self,name,login):
        self.active=name=='antigravity' and login
        self.buffer=b''
    def feed(self,data):
        if not self.active:return None
        self.buffer=(self.buffer+data)[-8192:]
        clean=re.sub(rb'\x1b\[[0-?]*[ -/]*[@-~]',b'',self.buffer).decode(errors='replace')
        if 'Select login method:' in clean and re.search(r'[>❯›]\s*1\.\s*Google OAuth',clean):
            self.active=False;self.buffer=b'';return b'\r'
        return None


def write_all(fd,data):
    while data:
        try:
            n=os.write(fd,data)
            if n<=0:raise OSError('Terminal write failed')
            data=data[n:]
        except InterruptedError:continue


def interactive(argv):
    if not (os.isatty(0) and os.isatty(1)):return False
    extras=argv[1:]
    return not any(a in ('-p','--print','--prompt','--output-format','--input-format','exec','exec-server') or a.startswith(('--output-format=','--input-format=')) for a in extras)


def run(argv,name,login=False):
    session=auth.Session()
    environment=os.environ.copy()
    environment.update(AGUJA_AUTH_DIR=str(session.directory),AGUJA_AUTH_PID=str(session.pid),AGUJA_AUTH_STAMP=session.stamp,
                       BROWSER='/usr/local/bin/aguja-auth-open')
    shim=session.directory/'xdg-open';shim.write_text('#!/bin/sh\nexec /usr/local/bin/aguja-auth-open "$@"\n');shim.chmod(0o700)
    environment['PATH']=str(session.directory)+os.pathsep+environment.get('PATH',os.defpath)
    approvals=None
    if name=='codex' and environment.get('AGUJA_EXECUTION_MODE')=='safe' and not login:
        from approval_broker import Broker
        approvals=Broker(session.directory)
        environment['AGUJA_APPROVAL_SOCKET']=str(approvals.path)
    attributes=termios.tcgetattr(0);size=fcntl.ioctl(0,termios.TIOCGWINSZ,bytes(8))
    pid,master=pty.fork()
    if pid==0:
        termios.tcsetattr(0,termios.TCSANOW,attributes);fcntl.ioctl(0,termios.TIOCSWINSZ,size)
        os.execvpe(argv[0],argv,environment)
    def send_signal(signum):
        try:os.killpg(pid,signum)
        except ProcessLookupError:pass
    def resize(*_):
        try:fcntl.ioctl(master,termios.TIOCSWINSZ,fcntl.ioctl(0,termios.TIOCGWINSZ,bytes(8)))
        except OSError:pass
    previous={signal.SIGWINCH:signal.signal(signal.SIGWINCH,resize)}
    for sig in (signal.SIGHUP,signal.SIGTERM,signal.SIGINT,signal.SIGQUIT):
        previous[sig]=signal.signal(sig,lambda signum,frame:send_signal(signum))
    import browser
    relay=browser.Relay(session.directory)
    detector=auth.LinkDetector();seen=None;announced=None;reaped=False;gui=None
    login_choice=NativeLoginChoice(name,login)
    expected={"claude":"Claude Code","antigravity":"Antigravity","codex":"Codex"}[name]
    def open_browser():
        nonlocal gui
        record=auth.read_record(session.directory/"request.json")
        if not record or record["provider"]!=expected:return
        if gui is not None and gui.poll() is None:
            return
        if browser.available():
            gui=browser.launch(session.directory)
            write_all(1,b"\r\nLA AGUJA: abriendo navegador local. Copia el codigo para enviarlo automaticamente al mismo CLI. Cierra la consola grafica para volver.\r\n")
        else:
            write_all(1,b"\r\nLA AGUJA: sin navegador local (SSH, serie o display no disponible). Conserva el enlace nativo y el modo remoto oficial; los callbacks localhost requieren un navegador en este host o reenvio local explicito.\r\n")
    try:
        tty.setraw(0,when=termios.TCSANOW)
        inputs=[0,master]
        while master in inputs:
            if approvals:approvals.poll(lambda data:write_all(1,data))
            ready,_,_=select.select(inputs,[],[],.1)
            for fd in ready:
                try:data=os.read(fd,4096)
                except OSError:data=b''
                if not data:
                    inputs.remove(fd)
                    if fd==0:send_signal(signal.SIGHUP)
                    continue
                if fd==master:
                    detector.feed(data)
                    write_all(1,data);relay.output(data)
                    choice=login_choice.feed(data)
                    if choice:write_all(master,choice)
                else:
                    # Ctrl+] is an explicit request, never a model-output action.
                    for part_index,part in enumerate(data.split(b'\x1d')):
                        if part_index:open_browser()
                        if part:write_all(master,part)
            relay.poll(master)
            detected=detector.poll()
            if detected and auth.provider(detected)==expected:session.offer(detected)
            record=auth.read_record(session.directory/'request.json')
            if record and record['provider']==expected:
                if record['url']!=seen:
                    seen=record['url']
                    # The owner requested automatic native authentication handoff.
                    # Only the exact provider allowlist above can open a browser.
                    open_browser()
            else:
                if seen:detector.clear();seen=None;announced=None
            if gui is not None and gui.poll() is not None:
                if gui.returncode:
                    write_all(1,b'\r\nLA AGUJA: navegador no iniciado; usa el enlace original.\r\n')
                gui=None
                fcntl.ioctl(master,termios.TIOCSWINSZ,size)
                send_signal(signal.SIGWINCH)
        _,status=os.waitpid(pid,0);reaped=True
        return os.waitstatus_to_exitcode(status)
    finally:
        if not reaped:
            send_signal(signal.SIGHUP)
            deadline=time.monotonic()+1
            while time.monotonic()<deadline:
                try:
                    if os.waitpid(pid,os.WNOHANG)[0]:reaped=True;break
                except ChildProcessError:reaped=True;break
                time.sleep(.02)
            if not reaped:
                send_signal(signal.SIGKILL)
                try:os.waitpid(pid,0)
                except ChildProcessError:pass
        (session.directory/"browser-stop").touch(mode=0o600)
        if gui is not None:
            try:gui.wait(timeout=12)
            except subprocess.TimeoutExpired:pass
        if approvals:approvals.close()
        relay.close()
        termios.tcsetattr(0,termios.TCSANOW,attributes)
        for sig,handler in previous.items():signal.signal(sig,handler)
        os.close(master)
        # No provider files, tokens, HOME or unrelated sessions are removed.
        session.close()
