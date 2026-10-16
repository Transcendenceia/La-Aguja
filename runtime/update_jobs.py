#!/usr/bin/python3
"""Detached update jobs: private plans/results, public bounded progress, UI reattach."""
import contextlib,fcntl,json,os,re,stat,subprocess,sys,time,uuid
from pathlib import Path
ROOT=Path('/run/aguja-update-jobs');ACTIVE=ROOT/'active.json';PUBLIC=Path('/run/aguja-update-job.json')
TERMINAL={'done','failed'}

def read(path):
 if any(p.is_symlink() for p in (path,*path.parents)):raise ValueError('Invalid update job path')
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
 with os.fdopen(fd,'rb') as f:
  s=os.fstat(f.fileno())
  if not stat.S_ISREG(s.st_mode) or s.st_uid!=os.geteuid() or s.st_mode&0o077 or s.st_size>4*1024**2:raise ValueError('Invalid private update job')
  return json.load(f)
def atomic(path,value):
 from config_transaction import atomic as write
 write(path,json.dumps(value).encode())
@contextlib.contextmanager
def lock():
 ROOT.mkdir(mode=0o700,parents=True,exist_ok=True)
 if ROOT.is_symlink() or ROOT.stat().st_uid!=os.geteuid():raise ValueError('Invalid update job directory')
 with (ROOT/'submit.lock').open('a+b') as f:
  os.fchmod(f.fileno(),0o600);fcntl.flock(f,fcntl.LOCK_EX);yield

def job_id(value):
 if not re.fullmatch('[a-f0-9]{32}',value):raise ValueError('Invalid update job identifier')
 return value

def current():
 if not ACTIVE.exists():return None
 record=read(ACTIVE);job_id(record['id']);return record

def publish(record,event=None,result=None):
 snapshot={k:record[k] for k in ('id','operation','state','started_at','updated_at')}
 if event:
  # Only our structured, bounded progress: never process output/URLs/tokens.
  snapshot['event']={k:v for k,v in event.items() if k in ('stage','detail','mode','completed','total','unit')}
 if result is not None:
  snapshot.update(ok=result.get('ok',record['operation']=='check'),reboot_required=bool(result.get('reboot_required')),available_count=len(result.get('packages',[]))+sum(bool(h.get('available')) for h in result.get('harnesses',{}).values())+int(bool((result.get('release') or {}).get('available'))))
 atomic(PUBLIC,snapshot);PUBLIC.chmod(0o644)

def status():
 record=current()
 if not record:return None
 folder=ROOT/record['id'];status=read(folder/'status.json')
 if status['state'] not in TERMINAL and time.time()-status['updated_at']>10:
  unit='aguja-update-job@'+record['id']+'.service'
  try:
   check=subprocess.run(['systemctl','is-active',unit],capture_output=True,text=True,timeout=5)
   if check.stdout.strip() in ('inactive','failed','unknown'):
    status.update(state='failed',updated_at=time.time(),result={'ok':False,'error':'La tarea se interrumpió. Revisa el estado antes de reintentar.'});atomic(folder/'status.json',status);publish(status,result=status['result'])
  except (OSError,subprocess.TimeoutExpired):pass
 return status

def submit(operation,items=None,choices=None):
 if operation not in ('check','apply'):raise ValueError('Invalid update operation')
 import update_tasks
 if operation=='apply':
  selected=update_tasks.plan(items or [],choices or {})
  if not any(selected.values()):raise ValueError('Selecciona al menos una actualización.')
 with lock():
  previous=status()
  if previous and previous['state'] not in TERMINAL:
   if operation=='check' and previous['operation']=='check':return previous
   raise ValueError('Hay una tarea de actualización en segundo plano. Abre Actualizaciones para seguirla.')
  id=uuid.uuid4().hex;folder=ROOT/id;folder.mkdir(mode=0o700)
  request={'schema':1,'operation':operation,'items':items or [],'choices':choices or {}}
  atomic(folder/'request.json',request)
  now=time.time();record={'id':id,'operation':operation,'state':'queued','started_at':now,'updated_at':now}
  atomic(folder/'status.json',record);atomic(ACTIVE,record);publish(record)
  try:
   result=subprocess.run(['systemctl','--no-block','start','aguja-update-job@'+id+'.service'],capture_output=True,timeout=10)
   if result.returncode:raise ValueError('No se pudo iniciar la tarea en segundo plano.')
  except (OSError,subprocess.TimeoutExpired,ValueError):
   record.update(state='failed',updated_at=time.time(),result={'ok':False,'error':'No se pudo iniciar la tarea en segundo plano.'});atomic(folder/'status.json',record);publish(record,result=record['result']);raise ValueError(record['result']['error']) from None
  return record

def worker(id):
 id=job_id(id);folder=ROOT/id
 # Defense against duplicate unit starts; job output never goes to the TTY.
 with (folder/'worker.lock').open('a+b') as guard:
  os.fchmod(guard.fileno(),0o600)
  try:fcntl.flock(guard,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:return 1
  record=read(folder/'status.json')
  if record['state'] in TERMINAL:return 0
  request=read(folder/'request.json');record.update(state='running',updated_at=time.time());atomic(folder/'status.json',record);publish(record)
  import update_progress,updates,update_tasks
  def progress(event):
   record.update(event=event,updated_at=time.time());atomic(folder/'status.json',record);publish(record,event=event)
  try:
   with update_progress.listen(progress):
    if request['operation']=='check':result=updates.check()
    else:result=update_tasks.apply(request['items'],request['choices'])
   record.update(state='done' if result.get('ok',True) else 'failed',result=result,updated_at=time.time())
  except Exception:
   record.update(state='failed',updated_at=time.time(),result={'ok':False,'error':'No se completó esta operación. Revisa el estado antes de reintentar.'})
  atomic(folder/'status.json',record);publish(record,event=record.get('event'),result=record['result'])
  return 0 if record['state']=='done' else 1

def finalize(id):
 id=job_id(id);folder=ROOT/id;record=read(folder/'status.json')
 if record['state'] not in TERMINAL:
  record.update(state='failed',updated_at=time.time(),result={'ok':False,'error':'La tarea se interrumpió. Revisa el estado antes de reintentar.'})
  atomic(folder/'status.json',record);publish(record,result=record['result'])
 return 0

def cached_inventory():
 import updates
 try:return updates.metadata(updates.RUN/'checks.json')
 except (OSError,ValueError):return None

def main(argv=None):
 args=argv or sys.argv[1:]
 try:
  if args==['check']:submit('check');return 0
  if len(args)==2 and args[0]=='worker':return worker(args[1])
  if len(args)==2 and args[0]=='finalize':return finalize(args[1])
  if args==['status']:print(json.dumps(status()));return 0
  return 2
 except Exception:
  print('LA AGUJA: background update job unavailable.',file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
