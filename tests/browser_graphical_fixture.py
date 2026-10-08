#!/usr/bin/python3
"""Synthetic graphical fixture, ONLY in an isolated QA guest.

Production URL validation stays intact. In this test client only, an already
validated synthetic provider request is rendered as a local HTTP test page.
There is no provider consent, real authorization code, token or account here.

Copy this file to /tmp/aguja-browser-fixture.py in the QA guest. Temporarily
replace /usr/lib/aguja/browser-session there (back up/restore it) with:
  #!/bin/sh
  exec python3 /tmp/aguja-browser-fixture.py session "$@"
On the real guest console as aguja: python3 /tmp/aguja-browser-fixture.py run
Use the page buttons: callback, Copy; console should focus. Ctrl+Shift+V then
Enter explicitly pastes the synthetic code into that same CLI PTY. Test events:
/run/aguja-auth/<uid>/graphical-fixture-events.json (booleans only).
Capture QMP screendump while the page and console are visible. Restore the
production browser-session afterwards. Never apply the override to real media.
"""
import hashlib
import html
import http.server
import json
import os
from pathlib import Path
import sys
import threading
from urllib.parse import parse_qs,urlsplit

sys.path.insert(0,'/usr/lib/aguja')
import auth
import auth_pty
import browser

CODE='AGUJA-SYNTHETIC-CODE-NOT-A-CREDENTIAL'
STATE='aguja-synthetic-state'
EVENTS=auth.BASE/str(os.getuid())/'graphical-fixture-events.json'
lock=threading.Lock()


def event(**values):
    with lock:
        try:current=json.loads(EVENTS.read_text())
        except (OSError,ValueError):current={}
        current.update(values)
        fd=os.open(EVENTS,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
        with os.fdopen(fd,'w') as output:json.dump(current,output)


class Page(http.server.BaseHTTPRequestHandler):
    def log_message(self,*_):pass
    def do_GET(self):
        parsed=urlsplit(self.path)
        if parsed.path=='/callback':
            event(native_loopback_callback=parse_qs(parsed.query).get('state')==[STATE])
            body=b'Callback sintetico recibido (no autenticacion real).'
        else:
            body=('''<!doctype html><meta charset="utf-8"><title>LA AGUJA · QA sintético</title>
<style>body{background:#13141b;color:#eee;font:22px sans-serif;padding:30px}button{font:22px sans-serif;padding:18px;margin:18px}small{display:block;color:#aaa}</style>
<h1>LA AGUJA · Navegador de acceso</h1>
<p>Prueba sintética: NO es una cuenta ni autorización de un proveedor.</p>
<button onclick="fetch('/callback?state='''+STATE+'''').then(()=>this.textContent='Callback local OK')">1. Probar callback localhost</button>
<button onclick="navigator.clipboard.writeText('''+html.escape(json.dumps(CODE),quote=True)+''').then(()=>this.textContent='Copiado: vuelve a la misma consola')">2. Copiar código sintético</button>
<p>La consola debe recibir el foco. Pega allí con Ctrl+Shift+V y Enter.</p>
<small>Copiar solo cambia el foco; no pega ni ejecuta automáticamente.</small>''').encode()
        self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8')
        self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)


def session(directory):
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Page)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    real_read=auth.read_record;real_focus=browser.focus_console
    def read(path):
        record=real_read(path)
        if record:record=dict(record,url=f'http://127.0.0.1:{server.server_port}/fixture')
        return record
    def focus():
        real_focus();event(clipboard_owner_returned_focus=True)
    auth.read_record=read;browser.focus_console=focus
    event(fixture_only=True,normal_user=os.getuid()!=0,browser_ready=True)
    try:return browser.user_session(directory)
    finally:server.shutdown();server.server_close()


def native_cli():
    print('LA AGUJA · CLI sintético. Sin cuenta real. El proceso espera el código en ESTA PTY.',flush=True)
    url='https://claude.com/cai/oauth/authorize?client_id=aguja-fixture&response_type=code&state='+STATE+'&code=true'
    print(url,flush=True)
    value=input('Pega el código sintético con Ctrl+Shift+V y Enter: ')
    success=hashlib.sha256(value.encode()).digest()==hashlib.sha256(CODE.encode()).digest()
    event(explicit_paste_same_native_pty=success)
    print('MISMA PTY: '+('OK' if success else 'FALLO'),flush=True)
    input('Enter para cerrar la prueba y volver al VT de texto: ')
    return 0 if success else 1


if __name__=='__main__':
    if sys.argv[1]=='session':raise SystemExit(session(Path(sys.argv[2])))
    elif sys.argv[1]=='cli':raise SystemExit(native_cli())
    elif sys.argv[1]=='run':
        EVENTS.unlink(missing_ok=True)
        raise SystemExit(auth_pty.run([sys.executable,str(Path(__file__).resolve()),'cli'],'claude',login=True))
    raise SystemExit('fixture run|session DIR|cli')
