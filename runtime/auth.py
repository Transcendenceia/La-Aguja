"""Private, volatile OAuth handoff to the local assistance browser.

No web listener, URL shortener, token exchange, input capture or activity payload.
Only provider authorization links are accepted; native CLIs own authentication.
"""
import codecs
import json
import hashlib
import os
from pathlib import Path
import re
import stat
import tempfile
import time
from urllib.parse import parse_qs, urlsplit

BASE = Path('/run/aguja-auth')
TTL = 600
MAX_URL = 2200
PROVIDERS = {'claude.com':'Claude Code','claude.ai':'Claude Code', 'console.anthropic.com':'Claude Code',
             'platform.claude.com':'Claude Code', 'accounts.google.com':'Antigravity',
             'auth.openai.com':'Codex'}
PATHS = {'claude.com':('/cai/oauth/authorize',),'claude.ai':('/oauth/authorize',), 'console.anthropic.com':('/oauth/authorize',),
         'platform.claude.com':('/oauth/authorize',),
         'accounts.google.com':('/o/oauth2/auth','/o/oauth2/v2/auth'),
         'auth.openai.com':('/oauth/authorize','/authorize','/codex/device')}


def provider(url):
    if not isinstance(url,str) or not 1<=len(url)<=MAX_URL or any(ord(c)<=32 or ord(c)>=127 for c in url):
        return None
    try:
        p=urlsplit(url)
        if p.scheme!='https' or p.username or p.password or p.port not in (None,443) or p.fragment:
            return None
        if p.hostname not in PROVIDERS or p.path.rstrip('/') not in PATHS[p.hostname]:
            return None
        q=parse_qs(p.query)
        if p.path.rstrip('/')=='/codex/device':return PROVIDERS[p.hostname]
        if not all(q.get(k) for k in ('client_id','state','response_type')) or q['response_type']!=['code']:
            return None
        if 'code_challenge' in q and len(q['code_challenge'][0])<43:return None
        # A real browser on the live host can reach the native CLI's loopback
        # callback. Preserve its state, PKCE and redirect_uri byte for byte.
        for uri in q.get('redirect_uri',[]):
            callback=urlsplit(uri)
            if callback.hostname in ('localhost','127.0.0.1','::1'):
                if callback.scheme!='http' or callback.username or callback.password or not callback.port:return None
            elif callback.hostname=='0.0.0.0':return None
        if any(k in q for k in ('access_token','refresh_token','id_token')):return None
        if 'code' in q and not (PROVIDERS[p.hostname]=='Claude Code' and q['code']==['true']):return None
        return PROVIDERS[p.hostname]
    except (ValueError,KeyError):return None


class LinkDetector:
    """Bounded output-only detector, including OSC 8 and hard-wrapped URLs."""
    def __init__(self):
        self.decoder=codecs.getincrementaldecoder('utf-8')('replace')
        self.buffer='';self.pending=None;self.changed=0;self.seen=set()
    def feed(self,data,now=None):
        now=time.monotonic() if now is None else now
        self.buffer=(self.buffer+self.decoder.decode(data))[-16384:]
        osc=re.findall(r'\x1b\]8;[^;]*;(https://[^\x07\x1b]+)(?:\x07|\x1b\\)',self.buffer)
        clean=re.sub(r'\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)','',self.buffer)
        clean=re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]','',clean).replace('\r\n','\n')
        lines=clean.split('\n');joined=[];i=0
        while i<len(lines):
            line=lines[i];i+=1
            if 'https://' in line:
                while i<len(lines) and len(line.rsplit('\n',1)[-1])>=50 and re.fullmatch(r'[A-Za-z0-9._~:/?#\[\]@!$&()*+,;=%-]+',lines[i].strip()):
                    line+=lines[i].strip();i+=1
            joined.append(line)
        candidates=osc+re.findall(r'https://[^\s<>"\x1b]+','\n'.join(joined))
        valid=[u.rstrip(').,\'') for u in candidates if provider(u.rstrip(').,\''))]
        if valid:
            candidate=valid[-1]
            if candidate!=self.pending:
                self.pending=candidate;self.changed=now
    def clear(self):
        self.buffer='';self.pending=None;self.decoder.reset()
    def poll(self,now=None):
        now=time.monotonic() if now is None else now
        if self.pending and now-self.changed>=.35 and hashlib.sha256(self.pending.encode()).digest() not in self.seen:
            url=self.pending;self.seen.add(hashlib.sha256(url.encode()).digest())
            if len(self.seen)>8:self.seen={hashlib.sha256(url.encode()).digest()}
            return url
        return None


def process_stamp(pid):
    try:return Path('/proc').joinpath(str(pid),'stat').read_text().rsplit(')',1)[1].split()[19]
    except (OSError,IndexError):return None


def own_directory():
    root=BASE/str(os.getuid())
    try:root.mkdir(mode=0o700,parents=False,exist_ok=True)
    except FileNotFoundError:raise OSError('Auth runtime directory unavailable') from None
    s=root.lstat()
    if not stat.S_ISDIR(s.st_mode) or s.st_uid!=os.getuid() or stat.S_IMODE(s.st_mode)!=0o700:
        raise OSError('Invalid auth runtime ownership')
    return root


class Session:
    def __init__(self):
        self.directory=Path(tempfile.mkdtemp(prefix='session-',dir=own_directory()))
        self.pid=os.getpid();self.stamp=process_stamp(self.pid)
    def offer(self,url):return offer(self.directory,url,self.pid,self.stamp)
    def close(self):
        # Only our ephemeral record and browser shim, never provider credentials.
        for name in ('request.json','request.tmp','xdg-open','console.sock','browser-stop'):
            (self.directory/name).unlink(missing_ok=True)
        self.directory.rmdir()


def offer(directory,url,pid,stamp):
    name=provider(url)
    if not name or not stamp:return False
    record={'url':url,'provider':name,'pid':pid,'start_ticks':stamp,'expires':time.monotonic()+TTL}
    fd,filename=tempfile.mkstemp(prefix='offer-',dir=directory)
    temp=Path(filename)
    try:
        os.fchmod(fd,0o600)
        with os.fdopen(fd,'w') as f:json.dump(record,f)
        temp.replace(directory/'request.json')
    except BaseException:
        temp.unlink(missing_ok=True);raise
    return True


def read_record(path):
    try:
        if path.parent.lstat().st_uid!=os.getuid() or path.parent.is_symlink():return None
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
        with os.fdopen(fd) as f:
            st=os.fstat(f.fileno())
            if not stat.S_ISREG(st.st_mode) or st.st_uid!=os.getuid() or stat.S_IMODE(st.st_mode)!=0o600:return None
            if st.st_size>16384:return None
            record=json.load(f)
        if not isinstance(record,dict) or not provider(record.get('url')):return None
        if not isinstance(record.get('expires'),(float,int)):return None
        if not time.monotonic()<record['expires']<=time.monotonic()+TTL+1:
            if path.name=='request.json':path.unlink(missing_ok=True)
            return None
        pid=record.get('pid')
        if not isinstance(pid,int) or Path('/proc',str(pid)).stat().st_uid!=os.getuid() or process_stamp(pid)!=record.get('start_ticks'):return None
        record['provider']=provider(record['url'])
        return record
    except (OSError,ValueError,KeyError,TypeError):return None


def current():
    try:paths=list(own_directory().glob('session-*/request.json'))
    except OSError:return None
    rows=[r for p in paths if (r:=read_record(p))]
    return max(rows,key=lambda r:r['expires']) if rows else None


def capture_browser(args):
    # Called by a CLI browser opener. Never echo or log the authorization URL.
    directory=os.environ.get('AGUJA_AUTH_DIR','')
    try:
        path=Path(directory)
        if not path.is_absolute() or path.parent!=own_directory() or path.is_symlink() or path.stat().st_uid!=os.getuid():return 1
        pid=int(os.environ['AGUJA_AUTH_PID']);stamp=os.environ['AGUJA_AUTH_STAMP']
        if process_stamp(pid)!=stamp or Path('/proc',str(pid)).stat().st_uid!=os.getuid():return 1
        return 0 if len(args)==1 and offer(path,args[0],pid,stamp) else 1
    except (OSError,KeyError,ValueError):return 1


def render(width,height,record,return_hint='A / Esc: volver al panel'):
    from PIL import Image,ImageDraw,ImageFont
    image=Image.new('RGB',(width,height),'#07131b');draw=ImageDraw.Draw(image)
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',max(12,min(26,width//42)))
    def text(x,y,s,color='#dfeef3'):draw.text((x,y),s,font=font,fill=color)
    text(24,18,'LA AGUJA · NAVEGADOR DE AUTENTICACIÓN','#75e3da')
    if not record:
        text(24,85,'No hay un acceso pendiente.')
        text(24,130,'Consola: aguja login claude / antigravity / codex')
        text(24,height-50,return_hint);return image
    text(24,62,record['provider']+' · '+urlsplit(record['url']).hostname,'#ffc767')
    text(24,130,'Vuelve al agente y pulsa Ctrl+] para abrir su navegador.')
    text(24,height-100,'Copia el código; Ctrl+Shift+V en la misma consola del agente.')
    text(24,height-65,'Por SSH se conserva el enlace nativo. No se generan códigos.','#9ab0bc')
    text(24,height-32,return_hint,'#75e3da');return image


def terminal_lines(record,columns,lines):
    if not record:return ['No hay un acceso pendiente.']
    return ['Navegador local: vuelve al agente y pulsa Ctrl+].',
            'Al copiar: vuelve la consola; pega con Ctrl+Shift+V.',
            'SSH: utiliza el enlace y el modo remoto oficial del proveedor.']
