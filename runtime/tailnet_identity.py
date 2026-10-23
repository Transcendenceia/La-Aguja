#!/usr/bin/python3
"""USB-specific native node state; asynchronous verified checkpoints, no host state."""
import base64,contextlib,fcntl,hashlib,hmac,json,os,stat,sys,time
from pathlib import Path
CFG=Path('/config');PRIVATE=Path('/run/aguja-tailnet-private');RUN=Path('/run/aguja-tailscale')
from profile_vault import settings_root
SAVED=settings_root()/'aguja-tailnet-identity.json';STATE=RUN/'tailscaled.state';SETTINGS=PRIVATE/'persistence.json';KEY=PRIVATE/'persistence.key'
RESTORED=PRIVATE/'restored';STATUS=Path('/run/aguja-tailnet-persistence.json');AAD=b'aguja-tailnet-state:1';LIMIT=1024**2

def read(path):
 if any(p.is_symlink() for p in (path,*path.parents)):raise ValueError('Invalid identity path')
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
 with os.fdopen(fd,'rb') as f:
  s=os.fstat(f.fileno())
  if not stat.S_ISREG(s.st_mode) or s.st_uid!=os.geteuid() or s.st_mode&0o077 or s.st_size>LIMIT:raise ValueError('Invalid private identity file')
  return f.read(LIMIT+1)
def write(path,raw):
 from config_transaction import atomic
 atomic(path,raw)
def status(value,**values):
 from profile import private_write
 private_write(STATUS,json.dumps({'state':value,'checked_at':int(time.time()),**values}));STATUS.chmod(0o644)
def target():
 from updates import verify_persistent_target
 return verify_persistent_target()
def configure(capsule,envelope,passphrase=None):
 """Called only with the already validated/unlocked profile, before daemon start."""
 config=capsule.get('tailscale',{}) if capsule else {}
 PRIVATE.mkdir(mode=0o700,parents=True,exist_ok=True)
 if not config.get('enabled'):
  KEY.unlink(missing_ok=True);SETTINGS.unlink(missing_ok=True);RESTORED.unlink(missing_ok=True);status('disabled');return
 mode=json.loads(envelope).get('protection','plain')
 binding=hashlib.sha256(json.dumps({k:config.get(k,'') for k in ('login_server','hostname','auth_key')},sort_keys=True).encode()).hexdigest()
 if mode=='encrypted':
  if passphrase is None:raise ValueError('Protected identity requires the profile unlock')
  from profile import unb64
  from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
  e=json.loads(envelope);native=Scrypt(salt=unb64(e['salt']),length=32,n=32768,r=8,p=1).derive(passphrase.encode())
  write(KEY,hmac.new(native,b'aguja-tailnet-persistence:v1',hashlib.sha256).digest())
 else:KEY.unlink(missing_ok=True)
 write(SETTINGS,json.dumps({'schema':1,'protection':mode,'binding':binding}).encode());RESTORED.unlink(missing_ok=True);status('pending')

def settings():
 s=json.loads(read(SETTINGS))
 if s.get('schema')!=1 or s.get('protection') not in ('plain','encrypted'):raise ValueError('Invalid identity configuration')
 return s

def decode(raw,s):
 e=json.loads(raw)
 if e.get('schema')!=1 or e.get('binding')!=s['binding'] or e.get('protection')!=s['protection']:raise ValueError('Saved identity belongs to another profile')
 if s['protection']=='encrypted':
  from cryptography.hazmat.primitives.ciphers.aead import AESGCM
  raw=AESGCM(read(KEY)).decrypt(base64.b64decode(e['iv'],validate=True),base64.b64decode(e['data'],validate=True),AAD+s['binding'].encode())
 else:raw=base64.b64decode(e['data'],validate=True)
 validate(raw);return raw

def validate(raw):
 if len(raw)>LIMIT:raise ValueError('Identity too large')
 value=json.loads(raw)
 if not isinstance(value,dict) or not value:raise ValueError('Invalid native state')
 return raw

def encode(raw,s):
 e={'schema':1,'binding':s['binding'],'protection':s['protection']}
 if s['protection']=='encrypted':
  from cryptography.hazmat.primitives.ciphers.aead import AESGCM
  nonce=os.urandom(12);raw=AESGCM(read(KEY)).encrypt(nonce,raw,AAD+s['binding'].encode());e['iv']=base64.b64encode(nonce).decode()
 e['data']=base64.b64encode(raw).decode();return json.dumps(e).encode()

@contextlib.contextmanager
def lock():
 PRIVATE.mkdir(mode=0o700,parents=True,exist_ok=True)
 with (PRIVATE/'persistence.lock').open('a+b') as f:
  os.fchmod(f.fileno(),0o600);fcntl.flock(f,fcntl.LOCK_EX);yield

def restore():
 if not SETTINGS.exists():return False
 with lock():
  s=settings()
  if STATE.exists():validate(read(STATE));return True
  if not SAVED.exists():status('pending');return False
  # Never silently replace an unreadable/encrypted/mismatched saved node.
  target();raw=decode(read(SAVED),s);RUN.mkdir(mode=0o755,parents=True,exist_ok=True);write(STATE,raw)
  write(RESTORED,b'1');status('saved',restored=True);return True

def restored():
 return RESTORED.exists() and read(RESTORED)==b'1'

def save():
 if not SETTINGS.exists() or not STATE.exists():return False
 with lock():
  s=settings();raw=validate(read(STATE));target()
  if SAVED.exists() and decode(read(SAVED),s)==raw:
   status('saved');return True
  status('saving');sealed=encode(raw,s);write(SAVED,sealed)
  if decode(read(SAVED),s)!=raw:raise ValueError('Identity readback failed')
  # atomic() fsyncs both file and directory before we publish success.
  status('saved');return True

def request_save():
 import subprocess
 if SETTINGS.exists():
  # A pre-auth machine key may already have a checkpoint; enrolling adds new
  # credentials. Do not present that older snapshot as preserved authentication.
  status('pending')
  subprocess.run(['systemctl','--no-block','start','aguja-tailnet-save.service'],capture_output=True,timeout=5)

def main(argv=None):
 try:
  {'restore':restore,'save':save}[(argv or sys.argv[1:])[0]]();return 0
 except Exception:
  try:status('error')
  except OSError:pass
  print('LA AGUJA: tailnet identity could not be restored or preserved; check the USB/profile.',file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
