"""USB-persistent, immutable update generations; factory/previous boot retained."""
import argparse,contextlib,fcntl,hashlib,json,os,re,shutil,signal,stat,subprocess,sys,tarfile,time,uuid
from pathlib import Path
import update_sources as sources
from i18n import t
DATA=Path('/data');CFG=Path('/config');ROOT=DATA/'updates';PIN=Path('/usr/share/aguja/release-key.json');STATE=ROOT/'state.json'
BINS={'codex':'opt/aguja/agents/codex/x86_64-unknown-linux-musl/bin/codex','claude':'opt/aguja/agents/claude/claude','antigravity':'opt/aguja/agents/antigravity/agy','opencode':'opt/aguja/agents/opencode/opencode'}
def run(args,**kw):
 timeout=kw.pop('timeout',1800);log=kw.pop('log',None)
 with subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,**kw) as process:
  try:out,err=process.communicate(timeout=timeout)
  except subprocess.TimeoutExpired:
   os.killpg(process.pid,signal.SIGTERM)
   try:process.communicate(timeout=10)
   except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.communicate()
   raise
  if log is not None:log.write_bytes((out+err)[-4*1024**2:]);log.chmod(0o600)
  if process.returncode:raise subprocess.CalledProcessError(process.returncode,args)
  return subprocess.CompletedProcess(args,0,out,err)

def hashfile(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  while b:=f.read(4194304):h.update(b)
 return h.hexdigest()
def atomic(p,value):
 from config_transaction import atomic as write
 write(p,json.dumps(value).encode() if not isinstance(value,bytes) else value)
def metadata(path,limit=1048576):
 for parent in [path,*path.parents]:
  if parent.is_symlink():raise ValueError('Metadatos de actualización no válidos')
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
 try:
  st=os.fstat(fd)
  if not stat.S_ISREG(st.st_mode) or st.st_size>limit or st.st_uid!=os.geteuid() or st.st_mode&0o077:raise ValueError('Metadatos de actualización no privados')
  with os.fdopen(os.dup(fd),'rb') as f:return json.loads(f.read(limit+1))
 finally:os.close(fd)
def validate_state(s):
 if not isinstance(s,dict) or set(s)!={'schema','active','previous'} or s['schema']!=1:raise ValueError('Estado de actualización no válido')
 for field in ('active','previous'):
  if s[field] is not None and not re.fullmatch('gen-[a-f0-9]{32}',s[field]):raise ValueError('Estado de actualización no válido')
 return s

def state():
 pending=ROOT/'pending-state.json'
 if pending.is_file():
  commit=metadata(pending);validate_state(commit['state']);
  if set(commit)!={'state','cfg_sha256'} or not re.fullmatch('[a-f0-9]{64}',commit['cfg_sha256']):raise ValueError('Activación pendiente no válida')
  pointer=CFG/'aguja-update.cfg'
  if pointer.is_file() and hashfile(pointer)==commit['cfg_sha256']:atomic(STATE,commit['state'])
  pending.unlink()
 if not STATE.exists():return {'schema':1,'active':None,'previous':None}
 return validate_state(metadata(STATE))
def running_generation():
 for item in Path('/proc/cmdline').read_text().split():
  if item.startswith('aguja.generation='):
   value=item.split('=',1)[1]
   if not re.fullmatch('gen-[a-f0-9]{32}',value):raise ValueError('Generación en ejecución no válida')
   return value
 return None

def verify_persistent_target():
 # Mounted directories alone do not establish ownership. Re-observe the boot
 # disk, CFG/DATA siblings and any byte-range loop views before mutations.
 observed=Path('/run/aguja-data-device').read_text().strip()
 def source(where):return subprocess.check_output(['findmnt','-n','-o','SOURCE','--target',where],text=True).strip().split('[')[0]
 medium=source('/run/live/medium')
 if not re.fullmatch('/dev/[A-Za-z0-9_-]+',medium):raise ValueError('Medio de arranque no válido')
 parent=subprocess.check_output(['lsblk','-ndo','PKNAME',medium],text=True).strip();disk='/dev/'+parent if parent else medium
 tree=json.loads(subprocess.check_output(['lsblk','--tree','-J','-o','PATH,TYPE,TRAN,RM,LABEL',disk],text=True))['blockdevices'][0]
 if tree['type']!='disk' or tree.get('tran')!='usb' or not tree.get('rm'):raise ValueError('Las actualizaciones persistentes solo escriben en el USB de arranque extraíble')
 children=tree.get('children',[]);cfg=[x['path'] for x in children if x.get('label')=='AGUJA_CFG'];data=[x['path'] for x in children if x.get('label')=='AGUJA_DATA']
 if len(cfg)!=1 or data!=[observed]:raise ValueError('CFG y DATA no pertenecen al mismo USB de arranque')
 for where,partition in [('/config',cfg[0]),('/data',data[0])]:
  mounted=source(where)
  if mounted==partition:continue
  if not re.fullmatch('/dev/loop[0-9]+',mounted):raise ValueError('Montaje persistente ajeno al USB de arranque')
  loop=json.loads(subprocess.check_output(['losetup','--json','--output','BACK-FILE,OFFSET',mounted],text=True))['loopdevices'][0]
  offset=int(Path('/sys/class/block/'+Path(partition).name+'/start').read_text())*512
  if loop['back-file']!=disk or int(loop['offset'])!=offset:raise ValueError('Vista de partición persistente no válida')
 if 'persistent-updates-v1' not in json.loads((CFG/'release.json').read_text()).get('features',[]):raise ValueError('Este USB necesita la infraestructura de arranque 1.0')

def capacity(required):
 if not os.path.ismount(DATA) or not os.path.ismount(CFG):raise ValueError('Actualización persistente requiere CFG y DATA del USB montadas')
 if shutil.disk_usage(DATA).free<required+512*1024**2:raise ValueError('No hay espacio suficiente en DATA; se conserva la versión actual')
 available=next(int(x.split()[1])*1024 for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:'))
 if available<768*1024**2:raise ValueError('RAM insuficiente; cierra otras tareas antes de actualizar')
def source_live():
 params=dict(x.split('=',1) for x in Path('/proc/cmdline').read_text().split() if '=' in x);folder=params.get('live-media-path','/live')
 if folder!='/live' and not re.fullmatch('/updates/gen-[a-f0-9]{32}/live',folder):raise ValueError('Generación de arranque no válida')
 root=Path('/run/live/medium')/folder.lstrip('/')
 for name in ('filesystem.squashfs','vmlinuz','initrd.img'):
  if not (root/name).is_file() or (root/name).is_symlink():raise ValueError('Base de arranque no disponible')
 return root
@contextlib.contextmanager
def lock(check_capacity=True):
 if check_capacity:capacity(128*1024**2);verify_persistent_target()
 ROOT.mkdir(mode=0o700,exist_ok=True)
 if ROOT.is_symlink() or ROOT.stat().st_uid!=0:raise ValueError('Área de actualizaciones no válida')
 with (ROOT/'lock').open('a+b') as f:
  try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:raise ValueError('Ya hay una operación de actualización en curso; espera a que termine.')
  yield

def installed():
 result={}
 for name,path in BINS.items():
  try:
   raw=run(['/'+path,'--version'],timeout=15,env={'PATH':'/usr/local/bin:/usr/bin:/bin','HOME':'/nonexistent','AGY_CLI_DISABLE_AUTO_UPDATE':'true','DISABLE_AUTOUPDATER':'1'}).stdout.decode(errors='replace');m=re.search(r'\d+\.\d+\.\d+',raw);result[name]=m.group() if m else None
  except Exception:result[name]=None
 return result

def package_check(refresh=True):
 lists=ROOT/'checks/lists';(lists/'partial').mkdir(parents=True,exist_ok=True)
 opts=['-o','Dir::State::lists='+str(lists),'-o','Acquire::Retries=1','-o','Acquire::http::Timeout=20','-o','Acquire::https::Timeout=20']
 if refresh:run(['apt-get',*opts,'update'],timeout=180)
 text=run(['apt-get',*opts,'-s','upgrade'],timeout=60).stdout.decode(errors='replace');packages=[]
 for line in text.splitlines():
  m=re.match(r'Inst (\S+) (?:\[([^]]+)\] )?\((\S+)',line)
  if m:packages.append({'name':m[1],'current':m[2] or '', 'latest':m[3]})
 return packages

def check():
 with lock():
  result={'schema':1,'checked_at':int(time.time()),'errors':{},'packages':[],'harnesses':{},'release':None,'restart_required':state()['active']!=running_generation()}
  try:result['packages']=package_check()
  except Exception:result['errors']['packages']='No se pudieron consultar los repositorios del sistema.'
  try:
   current=installed();result['harnesses']={n:{'current':current[n],'latest':v['version'],'available':current[n] is not None and sources.semver(v['version'])>sources.semver(current[n])} for n,v in sources.harnesses().items()}
  except Exception:result['errors']['harnesses']='No se pudieron consultar todos los proveedores.'
  try:
   releases=sources.catalog(json.loads(PIN.read_text()));current=Path('/usr/share/aguja/VERSION').read_text().strip();latest=releases[0]['version'];result['release']={'current':current,'latest':latest,'available':sources.semver(latest)>sources.semver(current)}
  except Exception:result['errors']['release']='No se pudo verificar el catálogo firmado.'
  atomic(ROOT/'checks.json',result)
  count=len(result['packages'])+sum(x['available'] for x in result['harnesses'].values())+int(bool(result['release'] and result['release']['available']))
  atomic(Path('/run/aguja-update-status.json'),{'available_count':count,'checked_at':result['checked_at'],'partial':bool(result['errors'])});Path('/run/aguja-update-status.json').chmod(0o644)
  return result

def boot_pointer(s):
 # GRUB resolves this DATA partition as a sibling of the boot medium, not by
 # searching labels across every internal disk attached to the rescue target.
 validate_state(s)
 text='set default='+('aguja-current' if s.get('active') else 'aguja-factory')+'\n'
 for field,label in [('active','Actualizada'),('previous','Anterior')]:
  if not s.get(field):continue
  g=s[field]
  try:
   m=metadata(ROOT/g/'manifest.json')
   if m.get('schema')!=1 or set(m.get('files',{}))!={'vmlinuz','initrd.img','filesystem.squashfs'}:raise ValueError('Manifiesto de generación incompleto')
   for name,digest in m['files'].items():
    if not re.fullmatch('[a-f0-9]{64}',digest) or (ROOT/g/'live'/name).is_symlink() or hashfile(ROOT/g/'live'/name)!=digest:raise ValueError('Generación dañada; no se activa')
  except (ValueError,OSError):
   if field=='active':raise
   # A damaged retained previous generation must not prevent selecting the
   # immutable factory or activating a valid new generation. Never erase it.
   text+='# Retained previous generation failed verification; use factory.\n';continue
  device=subprocess.check_output(['findmnt','-n','-o','SOURCE','--target','/data'],text=True).strip()
  if device.startswith('/dev/loop'):device=subprocess.check_output(['losetup','-n','-O','BACK-FILE',device],text=True).strip()
  # boot.py records the observed sibling DATA block path even for loop views.
  device=Path('/run/aguja-data-device').read_text().strip()
  partuuid=subprocess.check_output(['blkid','-s','PARTUUID','-o','value',device],text=True).strip()
  if not re.fullmatch('[a-fA-F0-9-]{36}',partuuid):raise ValueError('Identidad DATA no válida')
  text+=f"menuentry 'LA AGUJA · {label}' --id aguja-{'current' if field=='active' else 'previous'} {{\n linux ($aguja_drive,gpt5)/updates/{g}/live/vmlinuz boot=live components live-media=/dev/disk/by-partuuid/{partuuid} live-media-path=/updates/{g}/live aguja.generation={g} aguja.sha256={m['files']['filesystem.squashfs']} quiet splash console=tty0 console=ttyS0,115200n8\n initrd ($aguja_drive,gpt5)/updates/{g}/live/initrd.img\n}}\n"
 return text.encode()
def commit_state(new,pointer):
 pending=ROOT/'pending-state.json';atomic(pending,{'state':new,'cfg_sha256':hashlib.sha256(pointer).hexdigest()})
 atomic(CFG/'aguja-update.cfg',pointer);atomic(STATE,new);pending.unlink();os.sync()

def activate(g):
 old=state();new={'schema':1,'active':g,'previous':old['active']}
 pointer=boot_pointer(new)
 # Boot cfg is the commit point. A power interruption before it leaves the old
 # entry; a subsequent reconciliation reads the cfg's generation independently.
 commit_state(new,pointer);return new

def manifest(folder,version,kind):
 files={n:hashfile(folder/'live'/n) for n in ('vmlinuz','initrd.img','filesystem.squashfs')}
 atomic(folder/'manifest.json',{'schema':1,'version':version,'kind':kind,'files':files,'created_at':int(time.time())});return files

def release_update():
 with lock():
  r=sources.catalog(json.loads(PIN.read_text()))[0];current=Path('/usr/share/aguja/VERSION').read_text().strip()
  if sources.semver(r['version'])<=sources.semver(current):raise ValueError('El Rescue Disk está actualizado')
  capacity(r['bytes']+3*1024**3);g='gen-'+uuid.uuid4().hex;folder=ROOT/g;folder.mkdir(mode=0o700);image=folder/'download.img';h=hashlib.sha256()
  try:
   with image.open('xb') as out:
    for i,p in enumerate(r['parts']):
     piece=folder/('part-'+str(i));sources.fetch(p['url'],piece,'sha256',p['sha256'],p['bytes'],2*1024**3)
     with piece.open('rb') as f:
      while b:=f.read(4194304):h.update(b);out.write(b)
     piece.unlink()
    out.flush();os.fsync(out.fileno())
   if h.hexdigest()!=r['sha256']:raise ValueError('Imagen descargada no válida')
   run(['xorriso','-osirrox','on','-indev',str(image),'-extract','/live',str(folder/'live')])
   packed_version=run(['unsquashfs','-cat',str(folder/'live/filesystem.squashfs'),'usr/share/aguja/VERSION']).stdout.decode().strip()
   protocol=json.loads(run(['unsquashfs','-cat',str(folder/'live/filesystem.squashfs'),'usr/share/aguja/update-protocol.json']).stdout)
   if packed_version!=r['version'] or protocol!={'schema':1,'profile_schema':1,'config_partition':4,'data_partition':5}:raise ValueError('La imagen nueva no admite este protocolo de configuración')
   manifest(folder,r['version'],'release');image.unlink();active=activate(g)
   return {'ok':True,'generation':g,'version':r['version'],'reboot_required':True,'state':active}
  except Exception:
   # Failed staging is retained for explicit inspection/cleanup; active stays.
   raise

def install_harnesses(root,items,cache):
 for name,r in items.items():
  if shutil.disk_usage(cache).free<3*1024**3:raise ValueError('Espacio insuficiente para descargar arneses; se conserva la versión actual')
  archive=cache/(name+'.tgz');sources.fetch(r['url'],archive,r['algorithm'],r['digest'],r.get('bytes'))
  with tarfile.open(archive,'r:gz') as tar:
   member=tar.getmember(r['member'])
   if not member.isfile() or member.size>1024**3 or shutil.disk_usage(root).free<member.size+2*1024**3:raise ValueError('Binario nativo no válido')
   target=root/BINS[name];target.parent.mkdir(parents=True,exist_ok=True)
   if target.is_symlink():raise ValueError('Destino nativo inesperado')
   with tar.extractfile(member) as src,target.open('wb') as out:shutil.copyfileobj(src,out,1024**2)
   target.chmod(0o755)
  # Only known metadata regular files, never arbitrary archive extraction.
  with tarfile.open(archive,'r:gz') as tar:
   for member_name in ('package/package.json','package/LICENSE.md','package/LICENSE','package/README.md'):
    try:entry=tar.getmember(member_name)
    except KeyError:continue
    if not entry.isfile() or entry.size>1048576:raise ValueError('Metadatos nativos no válidos')
    target=root/BINS[name];dest=target.parent/Path(member_name).name
    if dest.is_symlink():raise ValueError('Destino nativo inesperado')
    dest.write_bytes(tar.extractfile(entry).read());dest.chmod(0o644)
  archive.unlink()
 atomic(root/'usr/share/aguja/installed-harnesses.json',{'schema':1,'providers':items})

def verify_harnesses(root,items):
 # Native runtimes (notably Bun/Claude) require /dev even for --version.
 # Validate inside the same minimal-device namespace as package staging.
 raw=run(['nice','-n','10','unshare','--mount','--pid','--fork','--propagation','private','/usr/lib/aguja/update-root-worker.sh',str(root),'verify']).stdout
 actual=json.loads(raw)
 if actual!={name:item['version'] for name,item in items.items()}:raise ValueError('La versión nativa no coincide con la descarga verificada')

def package_generation(packages,harnesses):
 with lock():
  capacity(7*1024**3);base=source_live();g='gen-'+uuid.uuid4().hex;folder=ROOT/g;folder.mkdir(mode=0o700);root=folder/'root';cache=folder/'downloads';cache.mkdir();live=folder/'live';live.mkdir()
  run(['nice','-n','10','unsquashfs','-processors','1','-d',str(root),str(base/'filesystem.squashfs')])
  items=sources.harnesses() if harnesses else {}
  if items:install_harnesses(root,items,cache)
  worker=Path('/usr/lib/aguja/update-root-worker.sh')
  run(['nice','-n','10','unshare','--mount','--pid','--fork','--propagation','private',str(worker),str(root),'yes' if packages else 'no'],log=folder/'build.log')
  if items:verify_harnesses(root,items)
  kernels=sorted((root/'boot').glob('vmlinuz-*'),key=lambda p:p.stat().st_mtime)
  if not kernels:raise ValueError('Kernel actualizado no disponible')
  kernel=kernels[-1];initrd=root/'boot'/('initrd.img-'+kernel.name.removeprefix('vmlinuz-'));shutil.copy2(kernel,live/'vmlinuz');shutil.copy2(initrd,live/'initrd.img')
  # This root originated from clean squashfs; never the running RAM overlay.
  for private in ['home/aguja/.ssh/authorized_keys','home/aguja/.codex/auth.json','home/aguja/.claude/.credentials.json','run/aguja-recovery/keys.json']:
   if (root/private).exists() and (root/private).stat().st_size:raise ValueError('No se empaqueta una raíz con secretos')
  root_bytes=sum(p.stat().st_size for p in root.rglob('*') if p.is_file() and not p.is_symlink())
  if shutil.disk_usage(DATA).free<root_bytes+512*1024**2:raise ValueError('No hay margen suficiente para empaquetar; se conserva la versión actual')
  run(['nice','-n','10','mksquashfs',str(root),str(live/'filesystem.squashfs'),'-noappend','-processors','1','-mem','256M','-comp','zstd','-Xcompression-level','3','-no-progress','-wildcards','-e','tmp/*','var/tmp/*','var/cache/apt','var/lib/apt/lists','run/*','root/*'])
  version=(root/'usr/share/aguja/VERSION').read_text().strip();manifest(folder,version,'packages+harnesses');shutil.rmtree(root);shutil.rmtree(cache);active=activate(g)
  return {'ok':True,'generation':g,'reboot_required':True,'state':active}

def rollback():
 with lock():
  s=state();new={'schema':1,'active':s['previous'],'previous':s['active']}
  pointer=boot_pointer(new)
  commit_state(new,pointer);return {'ok':True,'reboot_required':True,'state':new}

def status_unlocked():
 s=state();checkfile=ROOT/'checks.json';cached=metadata(checkfile) if checkfile.is_file() else None
 if cached is not None and (not isinstance(cached,dict) or set(cached)!={'schema','checked_at','errors','packages','harnesses','release','restart_required'}):raise ValueError('Inventario de actualización no válido')
 return {'persistent_available':os.path.ismount(DATA) and os.path.ismount(CFG),'state':s,'running_generation':running_generation(),'reboot_required':s['active']!=running_generation(),'check':cached}

def status():
 # Pending-state recovery shares the activation lock: a simultaneous status
 # reader must not retire an in-flight transaction before its CFG commit.
 if os.path.ismount(DATA) and os.path.ismount(CFG) and ROOT.exists():
  with lock(check_capacity=False):return status_unlocked()
 return status_unlocked()

def cleanup():
 with lock():
  s=state();keep={s['active'],s['previous']}
  params=Path('/proc/cmdline').read_text().split()
  keep.update(x.split('=',1)[1] for x in params if x.startswith('aguja.generation='))
  removed=[]
  for folder in ROOT.iterdir():
   if re.fullmatch('gen-[a-f0-9]{32}',folder.name) and folder.name not in keep and folder.is_dir() and not folder.is_symlink():
    # A staging worker must have exited before its mounted trees can be retired.
    references=False
    for info in Path('/proc').glob('[0-9]*/mountinfo'):
     try:references |= str(folder) in info.read_text()
     except (OSError,PermissionError):continue
    if references:continue
    shutil.rmtree(folder);removed.append(folder.name)
  return {'ok':True,'removed':removed,'active_and_previous_preserved':True}

def menu():
 print(t('LA AGUJA · Actualizaciones persistentes del USB'))
 print(t('1 Consultar actualizaciones / 2 Paquetes del sistema / 3 Arneses / 4 Paquetes y arneses / 5 Rescue Disk / 6 Volver a versión anterior / 7 Retirar generaciones inactivas / Enter Salir'))
 choice=input(t('Opción: ')).strip();actions={'1':'check','2':'packages','3':'harnesses','4':'all','5':'release','6':'rollback','7':'cleanup'}
 if choice not in actions:return {'canceled':True}
 if choice!='1':
  print(t('Solo se retirarán generaciones inactivas de actualizaciones; no se borran perfiles ni archivos personales.') if choice=='7' else t('Se guardará una generación en DATA. El cambio se aplicará al próximo arranque; no se reinicia ahora. Se conserva fábrica y la versión anterior.'))
  if input(t('Continuar [s/N]: ')).strip().lower() not in ('s','y','yes','si','sí'):return {'canceled':True}
 return main([actions[choice]])

def show(result):
 if 'packages' in result:
  print(t('Paquetes del sistema disponibles:'),len(result['packages']))
  for package in result['packages'][:30]:print('  '+package['name']+': '+package['current']+' → '+package['latest'])
  for name,h in result['harnesses'].items():print(name+': '+str(h['current'])+' → '+h['latest']+(t(' · disponible') if h['available'] else t(' · actualizado')))
  release=result.get('release')
  if release:print('Rescue Disk: '+release['current']+' → '+release['latest']+(t(' · disponible') if release['available'] else t(' · actualizado')))
  for error in result['errors'].values():print(t(error))
 elif result.get('reboot_required'):print(t('Cambio guardado y verificado. Reinicia cuando quieras para aplicarlo. Fábrica y la versión anterior siguen disponibles.'))
 elif 'removed' in result:print(t('Generaciones inactivas retiradas:'),len(result['removed']))
 else:print(t('Generación actual:'),result.get('state',{}).get('active') or t('fábrica'))

def main(argv=None):
 argv=sys.argv[1:] if argv is None else argv
 p=argparse.ArgumentParser(prog='aguja update');p.add_argument('operation',choices=['menu','status','check','packages','harnesses','all','release','rollback','cleanup'],nargs='?',default='status');p.add_argument('--json',action='store_true');a=p.parse_args(argv)
 if os.geteuid()!=0:return subprocess.call(['sudo','--',sys.executable,str(Path(__file__).resolve()),*argv])
 try:
  if a.operation=='menu':return menu()
  if a.operation=='status':result=status()
  elif a.operation=='check':result=check()
  elif a.operation=='release':result=release_update()
  elif a.operation=='rollback':result=rollback()
  elif a.operation=='cleanup':result=cleanup()
  else:result=package_generation(a.operation in ('packages','all'),a.operation in ('harnesses','all'))
  if a.json:print(json.dumps(result,ensure_ascii=False))
  else:show(result)
  return 0
 except Exception as e:
  # Package/upstream logs stay in the manager, never an owner's token-bearing
  # environment; only controlled ValueError text can reach the panel.
  message=str(e) if isinstance(e,ValueError) else 'No se completó la actualización. Se conserva el arranque anterior.'
  print(json.dumps({'ok':False,'error':message},ensure_ascii=False));return 1
if __name__=='__main__':sys.exit(main())
