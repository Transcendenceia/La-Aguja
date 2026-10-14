#!/usr/bin/python3
"""Identity-bound CFG-only USB editing. Inputs/results use a private pipe."""
import base64,contextlib,fcntl,hashlib,json,os,re,stat,subprocess,sys,tempfile,uuid
from pathlib import Path
FILES=('aguja-profile.json','aguja-recovery.json','aguja-locale.json','aguja.conf')
MAX=4*1024**2

def digest(data):return hashlib.sha256(data).hexdigest()
def syncdir(path):
 fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
def read(path):
 try:
  fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
 except FileNotFoundError:return None
 try:
  st=os.fstat(fd)
  if not stat.S_ISREG(st.st_mode) or st.st_size>MAX:raise ValueError('Archivo de configuración no válido')
  with os.fdopen(os.dup(fd),'rb') as f:return f.read(MAX+1)
 finally:os.close(fd)
def atomic(path,data):
 fd,name=tempfile.mkstemp(prefix='.aguja-',dir=path.parent)
 try:
  os.fchmod(fd,0o600)
  with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
  os.replace(name,path);syncdir(path.parent)
 finally:
  if os.path.exists(name):os.unlink(name)
def recover(folder):
 journal=folder/'aguja-config-transaction.json';raw=read(journal)
 if raw is None:return
 j=json.loads(raw);backup=j.get('backup','')
 if not isinstance(backup,str) or not re.fullmatch(r'aguja-config-backup-[a-f0-9]{32}',backup) or j.get('schema')!=1 or j.get('state') not in ('prepared','committed') or set(j.get('original',{}))!=set(FILES) or any(v is not None and not re.fullmatch('[a-f0-9]{64}',v) for v in j['original'].values()):raise ValueError('Transacción de configuración no válida')
 if j.get('state')=='prepared':
  for name in FILES:
   item=j['original'][name]
   if item is None:(folder/name).unlink(missing_ok=True)
   else:
    data=read(folder/backup/name)
    if data is None or digest(data)!=item:raise ValueError('Respaldo de configuración no válido')
    atomic(folder/name,data)
 journal.unlink();syncdir(folder)
def snapshot(folder):
 files={n:read(folder/n) for n in FILES};release=read(folder/'release.json')
 if not release or 'platform-profile-v1' not in json.loads(release).get('features',[]):raise ValueError('El USB no contiene una versión compatible')
 hashes={n:digest(v) if v is not None else None for n,v in files.items()}
 return files,digest(json.dumps(hashes,sort_keys=True).encode())
def edit(folder,request):
 recover(folder);files,token=snapshot(folder)
 if request['operation']=='read':return {'files':{n:base64.b64encode(v).decode() for n,v in files.items() if v is not None},'snapshot':token}
 if request['operation']!='write' or request.get('snapshot')!=token:raise ValueError('La configuración del USB cambió; vuelve a leerla')
 payload=request.get('files',{})
 if set(payload)!=set(FILES):raise ValueError('Archivos de configuración no válidos')
 new={n:base64.b64decode(v,validate=True) for n,v in payload.items()}
 if any(len(v)>MAX for v in new.values()):raise ValueError('Perfil privado demasiado grande')
 backup='aguja-config-backup-'+uuid.uuid4().hex;target=folder/backup;target.mkdir(mode=0o700)
 for n,v in files.items():
  if v is not None:atomic(target/n,v)
 journal=folder/'aguja-config-transaction.json';j={'schema':1,'backup':backup,'state':'prepared','original':{n:digest(v) if v is not None else None for n,v in files.items()}}
 atomic(journal,json.dumps(j).encode())
 try:
  for n,v in new.items():atomic(folder/n,v)
  if any(read(folder/n)!=v for n,v in new.items()):raise ValueError('La lectura de configuración no coincide')
  j['state']='committed';atomic(journal,json.dumps(j).encode());journal.unlink();syncdir(folder)
 except BaseException:recover(folder);raise
 return {'verified':True,'backup':backup,'snapshot':snapshot(folder)[1]}
def identify(device,serial,size):
 d=json.loads(subprocess.check_output(['lsblk','--tree','-b','-J','-o','PATH,TYPE,SERIAL,TRAN,RM,SIZE,LABEL,FSTYPE,MOUNTPOINTS',device]))['blockdevices'][0]
 if d['path']!=str(Path(device).resolve()) or d['type']!='disk' or d.get('tran')!='usb' or not d.get('rm') or d.get('serial')!=serial or d['size']!=size:raise ValueError('El USB cambió o no es extraíble')
 parts=[c for c in d.get('children',[]) if c.get('label')=='AGUJA_CFG' and c.get('fstype')=='vfat']
 if len(parts)!=1:raise ValueError('No se encontró la configuración de LA AGUJA en este USB')
 return parts[0]
def main():
 if os.geteuid()!=0:raise ValueError('Falta permiso para configurar el USB')
 raw=sys.stdin.buffer.read(8*1024**2+1)
 if len(raw)>8*1024**2:raise ValueError('Petición demasiado grande')
 r=json.loads(raw);part=identify(r['device'],r['serial'],r['size'])
 mounts=[x for x in part.get('mountpoints',[]) if x]
 with tempfile.TemporaryDirectory(prefix='aguja-config-',dir='/run') as temp:
  own=not mounts;folder=Path(mounts[0] if mounts else temp)
  if own:subprocess.run(['mount','-o','rw,umask=0077,nosuid,nodev,noexec',part['path'],str(folder)],check=True,capture_output=True)
  try:
   identify(r['device'],r['serial'],r['size'])
   # Lock the exact block device, not a persistent plaintext sidecar.
   with open(part['path'],'rb') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);result=edit(folder,r)
   print(json.dumps({'ok':True,**result}))
  finally:
   if own:subprocess.run(['umount',str(folder)],check=True,capture_output=True)
if __name__=='__main__':
 try:main()
 except Exception:print(json.dumps({'ok':False,'error':'No se pudo leer o guardar la configuración del USB. Comprueba permisos y vuelve a leer el dispositivo.'}));sys.exit(1)
