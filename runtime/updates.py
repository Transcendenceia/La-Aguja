"""USB-persistent, immutable update generations; factory/previous boot retained."""
import argparse,selectors,contextlib,fcntl,functools,hashlib,json,os,re,shutil,signal,stat,subprocess,sys,tarfile,time,uuid
from pathlib import Path
import update_sources as sources
from i18n import t
import update_progress as progress
DATA=Path('/data');CFG=Path('/config');ROOT=DATA/'updates';PIN=Path('/usr/share/aguja/release-key.json');STATE=ROOT/'state.json';RUN=Path('/run/aguja-updates');NOTICE=Path('/run/aguja-update-status.json')
BINS={'codex':'opt/aguja/agents/codex/x86_64-unknown-linux-musl/bin/codex','claude':'opt/aguja/agents/claude/claude','antigravity':'opt/aguja/agents/antigravity/agy','opencode':'opt/aguja/agents/opencode/opencode'}
def run(args,**kw):
 timeout=kw.pop('timeout',1800);log=kw.pop('log',None)
 with subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,**kw) as process:
  try:
   if not progress.active():out,err=process.communicate(timeout=timeout)
   else:
    parts={process.stdout:bytearray(),process.stderr:bytearray()};lines={f:b'' for f in parts};deadline=time.monotonic()+timeout
    with selectors.DefaultSelector() as selector:
     for stream in parts:selector.register(stream,selectors.EVENT_READ)
     while selector.get_map():
      if time.monotonic()>deadline:raise subprocess.TimeoutExpired(args,timeout)
      for key,_ in selector.select(.2):
       raw=os.read(key.fileobj.fileno(),65536)
       if not raw:selector.unregister(key.fileobj);continue
       parts[key.fileobj].extend(raw)
       if len(parts[key.fileobj])>4*1024**2:del parts[key.fileobj][:-4*1024**2]
       pending=lines[key.fileobj]+raw
       for line in pending.split(b'\n')[:-1]:progress.apt_line(line.decode(errors='replace'))
       lines[key.fileobj]=pending.split(b'\n')[-1][-4096:]
    process.wait(timeout=max(.1,deadline-time.monotonic()));out,err=map(bytes,(parts[process.stdout],parts[process.stderr]))
  except (subprocess.TimeoutExpired,KeyboardInterrupt):
   os.killpg(process.pid,signal.SIGTERM)
   try:process.communicate(timeout=10)
   except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.communicate()
   raise
  if log is not None:log.write_bytes((out+err)[-4*1024**2:]);log.chmod(0o600)
  if process.returncode:raise subprocess.CalledProcessError(process.returncode,args)
  return subprocess.CompletedProcess(args,0,out,err)

def boot_pair(root):
 # Kernel installation/copy times do not establish Debian version order.
 kernels=list((root/'boot').glob('vmlinuz-*'))
 if not kernels:raise ValueError('Kernel actualizado no disponible')
 def compare(left,right):
  a,b=(p.name.removeprefix('vmlinuz-') for p in (left,right))
  result=subprocess.run(['dpkg','--compare-versions',a,'gt',b],capture_output=True)
  if result.returncode not in (0,1):raise ValueError('Versión del kernel no válida')
  if result.returncode==0:return 1
  return 0 if a==b else -1
 kernel=max(kernels,key=functools.cmp_to_key(compare))
 release=kernel.name.removeprefix('vmlinuz-')
 initrd=kernel.with_name('initrd.img-'+release)
 if not initrd.is_file():raise ValueError('Falta el initramfs del kernel seleccionado')
 listing=run(['lsinitramfs',str(initrd)]).stdout.decode()
 modules=set(re.findall(r'^(?:usr/)?lib/modules/([^/\n]+)',listing,re.M))
 if modules!={release}:raise ValueError('El kernel y los módulos del initramfs no coinciden; no se activó la generación')
 return kernel,initrd

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
 return {'disk':disk,'config':cfg[0],'data':data[0]}

def capacity(required):
 if not os.path.ismount(DATA) or not os.path.ismount(CFG):raise ValueError('Actualización persistente requiere CFG y DATA del USB montadas')
 if shutil.disk_usage(DATA).free<required+512*1024**2:raise ValueError('No hay espacio suficiente en DATA; se conserva la versión actual')
 available=next(int(x.split()[1])*1024 for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:'))
 if available<768*1024**2:raise ValueError('RAM insuficiente; cierra otras tareas antes de actualizar')
def generation_live(generation):
 if not re.fullmatch('gen-[a-f0-9]{32}',generation):raise ValueError('Generación no válida')
 folder=ROOT/generation;m=metadata(folder/'manifest.json')
 if folder.is_symlink():raise ValueError('Generación no válida')
 for name in ('filesystem.squashfs','vmlinuz','initrd.img'):
  if (folder/'live'/name).is_symlink() or hashfile(folder/'live'/name)!=m['files'][name]:raise ValueError('La generación seleccionada no supera la verificación.')
 return folder/'live'

def source_live():
 active=state()['active']
 if active:return generation_live(active)
 params=dict(x.split('=',1) for x in Path('/proc/cmdline').read_text().split() if '=' in x);folder=params.get('live-media-path','/live')
 if folder!='/live' and not re.fullmatch('/updates/gen-[a-f0-9]{32}/live',folder):raise ValueError('Generación de arranque no válida')
 root=Path('/run/live/medium')/folder.lstrip('/')
 for name in ('filesystem.squashfs','vmlinuz','initrd.img'):
  if not (root/name).is_file() or (root/name).is_symlink():raise ValueError('Base de arranque no disponible')
 return root
@contextlib.contextmanager
def lock(check_capacity=True):
 if check_capacity:
  capacity(128*1024**2);verify_persistent_target();ROOT.mkdir(mode=0o700,exist_ok=True)
  if ROOT.is_symlink() or ROOT.stat().st_uid!=0:raise ValueError('Área de actualizaciones no válida')
 RUN.mkdir(mode=0o700,exist_ok=True)
 if RUN.is_symlink() or RUN.stat().st_uid!=os.geteuid():raise ValueError('Área temporal de actualizaciones no válida')
 with (RUN/'lock').open('a+b') as f:
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
 lists=RUN/'checks/lists';(lists/'partial').mkdir(parents=True,exist_ok=True)
 opts=['-o','Dir::State::lists='+str(lists),'-o','Acquire::Retries=1','-o','Acquire::http::Timeout=20','-o','Acquire::https::Timeout=20']
 if refresh:run(['apt-get',*opts,'update'],timeout=180)
 text=run(['apt-get',*opts,'-s','upgrade'],timeout=60).stdout.decode(errors='replace');packages=[]
 for line in text.splitlines():
  m=re.match(r'Inst (\S+) (?:\[([^]]+)\] )?\((\S+)',line)
  if m:packages.append({'name':m[1],'current':m[2] or '', 'latest':m[3]})
 return packages

def check():
 with lock(check_capacity=False):
  result={'schema':1,'checked_at':int(time.time()),'errors':{},'packages':[],'harnesses':{},'release':None,'restart_required':state()['active']!=running_generation()}
  progress.emit('check','Rescue Disk')
  try:
   releases=sources.catalog(json.loads(PIN.read_text()));current=Path('/usr/share/aguja/VERSION').read_text().strip();latest=releases[0]['version'];result['release']={'current':current,'latest':latest,'available':sources.semver(latest)>sources.semver(current)}
  except Exception:result['errors']['release']='No se pudo verificar el catálogo firmado.'
  progress.emit('check','Paquetes del sistema')
  try:result['packages']=package_check()
  except Exception:result['errors']['packages']='No se pudieron consultar los repositorios del sistema.'
  current=installed()
  for name in BINS:
   progress.emit('check',name)
   try:
    v=sources.harnesses([name])[name]
    result['harnesses'][name]={'current':current[name],'latest':v['version'],'available':current[name] is not None and sources.semver(v['version'])>sources.semver(current[name]),'candidate':v}
   except Exception:result['errors'][name]='No se pudo consultar este proveedor.'
  atomic(RUN/'checks.json',result)
  count=len(result['packages'])+sum(x['available'] for x in result['harnesses'].values())+int(bool(result['release'] and result['release']['available']))
  atomic(NOTICE,{'available_count':count,'checked_at':result['checked_at'],'partial':bool(result['errors'])});NOTICE.chmod(0o644)
  return result

def data_partuuid(device):
 value=subprocess.check_output(['blkid','-s','PARTUUID','-o','value',device],text=True).strip()
 if re.fullmatch('[a-fA-F0-9-]{36}',value):return value.lower()
 # Fresh Windows media grows DATA while the whole ISO disk is mounted. The
 # kernel may not refresh partition GUID properties until reboot; the synced
 # GPT already contains the preserved GUID used on that next boot.
 number=Path('/sys/class/block/'+Path(device).name+'/partition').read_text().strip()
 parent=subprocess.check_output(['lsblk','-ndo','PKNAME',device],text=True).strip()
 if number!='5' or not re.fullmatch('[A-Za-z0-9_-]+',parent):raise ValueError('Identidad DATA no válida')
 text=subprocess.check_output(['sgdisk','-i',number,'/dev/'+parent],text=True)
 match=re.search(r'Partition unique GUID:\s*([a-fA-F0-9-]{36})',text)
 if not match:raise ValueError('Identidad DATA no válida')
 return match[1].lower()

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
  partuuid=data_partuuid(device)
  if not re.fullmatch('[a-fA-F0-9-]{36}',partuuid):raise ValueError('Identidad DATA no válida')
  encrypted=' aguja.snapshot=1' if m.get('kind')=='snapshot-luks2' else ''
  if encrypted:label='Cambios guardados' if field=='active' else 'Cambios anteriores'
  text+=f"menuentry 'LA AGUJA · {label}' --id aguja-{'current' if field=='active' else 'previous'} {{\n linux ($aguja_drive,gpt5)/updates/{g}/live/vmlinuz boot=live components live-media=/dev/disk/by-partuuid/{partuuid} live-media-path=/updates/{g}/live aguja.generation={g} aguja.sha256={m['files']['filesystem.squashfs']}{encrypted} quiet splash console=ttyS0,115200n8 console=tty0\n initrd ($aguja_drive,gpt5)/updates/{g}/live/initrd.img\n}}\n"
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

def release_update(expected_version=None,stage_only=False,stage_ram=False):
 with lock(check_capacity=not stage_ram):
  progress.emit('download','Descargando Rescue Disk')
  r=sources.catalog(json.loads(PIN.read_text()))[0];current=Path('/usr/share/aguja/VERSION').read_text().strip()
  if expected_version is not None and r['version']!=expected_version:raise ValueError('El catálogo cambió. Comprueba de nuevo y revisa la versión antes de aplicar.')
  if sources.semver(r['version'])<=sources.semver(current):raise ValueError('El Rescue Disk está actualizado')
  g='gen-'+uuid.uuid4().hex
  if stage_ram:
   import update_tasks
   update_tasks.verify_live_ram();parent=update_tasks.STAGE;parent.mkdir(mode=0o700,parents=True,exist_ok=True)
   backing=json.loads(run(['findmnt','-J','-o','TARGET,FSTYPE','--target',str(parent)]).stdout)['filesystems'][0]
   if backing['target']!='/' or backing['fstype']!='overlay':raise ValueError('La preparación de Rescue debe usar la capa RAM del live.')
   if shutil.disk_usage(parent).free<r['bytes']*2+512*1024**2:raise ValueError('RAM insuficiente para preparar la imagen completa. No se escribió en el pendrive.')
   folder=parent/('release-'+g[4:])
  else:capacity(r['bytes']+3*1024**3);folder=ROOT/g
  folder.mkdir(mode=0o700);image=folder/'download.img';h=hashlib.sha256();received=0
  try:
   with image.open('xb') as out:
    for i,p in enumerate(r['parts']):
     piece=folder/('part-'+str(i));sources.fetch(p['url'],piece,'sha256',p['sha256'],p['bytes'],2*1024**3,progress=lambda done,total,offset=received:progress.emit('download','Rescue Disk',completed=offset+done,total=r['bytes'],unit='bytes'));received+=p['bytes']
     with piece.open('rb') as f:
      while b:=f.read(4194304):h.update(b);out.write(b)
     piece.unlink()
    out.flush();os.fsync(out.fileno())
   if h.hexdigest()!=r['sha256']:raise ValueError('Imagen descargada no válida')
   run(['xorriso','-osirrox','on','-indev',str(image),'-extract','/live',str(folder/'live')])
   packed_version=run(['unsquashfs','-cat',str(folder/'live/filesystem.squashfs'),'usr/share/aguja/VERSION']).stdout.decode().strip()
   protocol=json.loads(run(['unsquashfs','-cat',str(folder/'live/filesystem.squashfs'),'usr/share/aguja/update-protocol.json']).stdout)
   if packed_version!=r['version'] or protocol!={'schema':1,'profile_schema':1,'config_partition':4,'data_partition':5}:raise ValueError('La imagen nueva no admite este protocolo de configuración')
   if (CFG/'aguja-profile.luks').exists():
    gate=run(['unsquashfs','-cat',str(folder/'live/filesystem.squashfs'),'usr/lib/aguja/profile_vault.py']).stdout
    if not gate or b'early-profile-gate-v1' not in run(['unsquashfs','-cat',str(folder/'live/filesystem.squashfs'),'usr/share/aguja/capabilities.json']).stdout:raise ValueError('La versión nueva no declara soporte para este perfil LUKS')
   progress.emit('verify','Verificando Rescue Disk');files=manifest(folder,r['version'],'release');image.unlink()
   if stage_ram:
    atomic(RUN/'pending-release.json',{'folder':str(folder),'version':r['version'],'files':files})
    return {'ok':True,'mode':'session','version':r['version'],'staged':True,'reboot_required':False,'persistence_required':True}
   if stage_only:return {'ok':True,'generation':g,'version':r['version'],'staged':True,'reboot_required':False}
   progress.emit('activate','Preparando el próximo arranque');active=activate(g)
   return {'ok':True,'generation':g,'version':r['version'],'reboot_required':True,'state':active}
  except Exception:
   # Failed staging is retained for explicit inspection/cleanup; active stays.
   raise

def install_codex_metadata(root,descriptor,cache):
 sources.semver(descriptor['version']);sources.url(descriptor['url'])
 if descriptor['algorithm']!='sha512' or not re.fullmatch('[a-f0-9]{128}',descriptor['digest']):raise ValueError('Integridad de metadatos Codex no válida')
 archive=cache/('codex-package-'+uuid.uuid4().hex+'.tgz')
 try:
  sources.fetch(descriptor['url'],archive,'sha512',descriptor['digest'],limit=2*1024**2)
  with tarfile.open(archive,'r:gz') as tar:
   entry=tar.getmember('package/package.json')
   if not entry.isfile() or entry.size>65536:raise ValueError('Metadatos Codex no válidos')
   raw=tar.extractfile(entry).read();value=json.loads(raw)
  if value.get('name')!='@openai/codex' or value.get('version')!=descriptor['version']:raise ValueError('Metadatos Codex no coinciden con el ejecutable')
  target=root/'opt/aguja/agents/codex/package.json'
  if target.is_symlink():raise ValueError('Metadatos Codex no válidos')
  target.parent.mkdir(parents=True,exist_ok=True);atomic(target,raw);target.chmod(0o644)
 finally:archive.unlink(missing_ok=True)

def install_harnesses(root,items,cache,reserve=3*1024**3):
 for name,r in items.items():
  if shutil.disk_usage(cache).free<reserve:raise ValueError('Espacio insuficiente para descargar arneses; se conserva la versión actual')
  progress.emit('download',name)
  archive=cache/(name+'.tgz');sources.fetch(r['url'],archive,r['algorithm'],r['digest'],r.get('bytes'),progress=lambda done,total:progress.emit('download',name,completed=done,total=total,unit='bytes'))
  with tarfile.open(archive,'r:gz') as tar:
   member=tar.getmember(r['member'])
   if not member.isfile() or member.size>1024**3 or shutil.disk_usage(root).free<member.size+reserve:raise ValueError('Binario nativo no válido')
   target=root/BINS[name];target.parent.mkdir(parents=True,exist_ok=True)
   if target.is_symlink():raise ValueError('Destino nativo inesperado')
   temporary=target.with_name(target.name+'.aguja-update-'+uuid.uuid4().hex)
   try:
    with tar.extractfile(member) as src,temporary.open('xb') as out:shutil.copyfileobj(src,out,1024**2);out.flush();os.fsync(out.fileno())
    temporary.chmod(0o755);os.replace(temporary,target)
   finally:
    if temporary.exists():temporary.unlink()
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
  if name=='codex':
   descriptor=r.get('npm') or sources.codex_metadata(r['version'])
   if descriptor['version']!=r['version']:raise ValueError('Metadatos Codex no coinciden con el ejecutable')
   install_codex_metadata(root,descriptor,cache)
 record=root/'usr/share/aguja/installed-harnesses.json'
 if record.is_symlink() or record.exists() and record.stat().st_size>1048576:raise ValueError('Metadatos nativos no válidos')
 prior=json.loads(record.read_text()).get('providers',{}) if record.exists() else {}
 atomic(record,{'schema':1,'providers':{**prior,**items}})

def verify_harnesses(root,items):
 # Native runtimes (notably Bun/Claude) require /dev even for --version.
 # Validate inside the same minimal-device namespace as package staging.
 raw=run(['nice','-n','10','unshare','--mount','--pid','--fork','--propagation','private','/usr/lib/aguja/update-root-worker.sh',str(root),'verify']).stdout
 actual=json.loads(raw)
 if any(actual.get(name)!=item['version'] for name,item in items.items()):raise ValueError('La versión nativa no coincide con la descarga verificada')

def verify_packages(root,items):
 for item in items:
  version=run(['chroot',str(root),'/usr/bin/dpkg-query','-W','-f=${Version}',item['name']]).stdout.decode().strip()
  if version!=item['version']:raise ValueError('La versión del paquete no coincide con la selección: '+item['name'])

PUBLIC_MANAGER_FILES={"usr/lib/aguja/"+n for n in ['tailnet_config.py', 'gui_session.py', 'desk.py', 'desk_backend.py', 'desk_i18n.py', 'web.py', 'file_open.py', 'file_manager.py', 'persistence.py', 'power.py', 'profile_vault.py', 'hardware.py', 'storage.py', 'agent_context.py', 'secret_inventory.py', 'recovery_state.py', 'i18n.py', 'updates.py', 'update_sources.py', 'update_tasks.py', 'update_progress.py', 'update_ui.py', 'update_jobs.py', 'tailnet_identity.py', 'tailscale_service.py', 'profile_cli.py', 'boot.py', 'profile.py', 'profile_extensions.py', 'network.py', 'display.py', 'cockpit.py', 'update-root-worker.sh', 'update-session-worker.sh', 'snapshot-initrd.sh', 'locale-catalog.json']}|set(['usr/share/aguja/capabilities.json', 'usr/share/aguja/ODD.md', 'usr/share/aguja/MISSIONS.md', 'usr/share/aguja/BACKUP.md', 'usr/share/aguja/AGENT-CONTEXT.md', 'usr/share/aguja/SSH-WELCOME.txt', 'etc/systemd/system/aguja-boot.service', 'usr/share/aguja/UPDATES.md', 'usr/share/aguja/skills/live-updates/SKILL.md', 'usr/lib/live/boot/9999-aguja-update.sh', 'etc/initramfs-tools/hooks/aguja-update', 'etc/systemd/system/aguja-tailscale.service', 'etc/systemd/system/aguja-tailscaled.service', 'etc/systemd/system/aguja-tailnet-save.service', 'etc/systemd/system/aguja-tailnet-save.path', 'etc/systemd/system/aguja-tailnet-save.timer', 'etc/systemd/system/aguja-update-check.service', 'etc/systemd/system/aguja-update-check.timer', 'etc/systemd/system/aguja-update-job@.service'])

def refresh_manager(root,source=Path('/')):
 record=source/'usr/share/aguja/update-runtime.json'
 if not record.exists():return
 if record.is_symlink() or record.stat().st_size>16384 or record.stat().st_uid!=os.geteuid() or record.stat().st_mode&0o022:raise ValueError('Manifiesto del actualizador no válido')
 manifest=json.loads(record.read_text())
 if manifest.get('schema')!=1 or set(manifest.get('files',{}))!=PUBLIC_MANAGER_FILES:raise ValueError('Inventario del actualizador no válido')
 # Only this fixed list of public code/docs, never the RAM overlay, HOME,
 # profiles, installed credentials or owner workspace, may accompany a new root.
 payload={}
 for name,digest in manifest['files'].items():
  path=source/name
  if any(p.is_symlink() for p in [path,*list(path.parents)[:-1]]) or not path.is_file() or path.stat().st_uid!=os.geteuid() or path.stat().st_mode&0o022 or path.stat().st_size>2*1024**2 or hashfile(path)!=digest:raise ValueError('El actualizador instalado no coincide con su manifiesto')
  payload[name]=path.read_bytes()
 for name,raw in payload.items():
  target=root/name
  if target.is_symlink():raise ValueError('Destino del actualizador inesperado')
  target.parent.mkdir(parents=True,exist_ok=True);atomic(target,raw);target.chmod(0o755 if name.endswith(('.py','.sh')) or name=='etc/initramfs-tools/hooks/aguja-update' else 0o644)
 atomic(root/'usr/share/aguja/update-runtime.json',record.read_bytes());(root/'usr/share/aguja/update-runtime.json').chmod(0o644)
 for target,unit in [('multi-user.target','aguja-tailnet-save.path'),('timers.target','aguja-tailnet-save.timer'),('timers.target','aguja-update-check.timer')]:
  link=root/'etc/systemd/system'/(target+'.wants')/unit;link.parent.mkdir(parents=True,exist_ok=True)
  if not link.exists() and not link.is_symlink():link.symlink_to('../'+unit)

def package_generation(packages,harnesses,package_items=None,harness_items=None,base_generation=None):
 with lock():
  capacity(7*1024**3);base=generation_live(base_generation) if base_generation else source_live();g='gen-'+uuid.uuid4().hex;folder=ROOT/g;folder.mkdir(mode=0o700);root=folder/'root';cache=folder/'downloads';cache.mkdir();live=folder/'live';live.mkdir()
  progress.emit('prepare','Preparando un sistema limpio')
  run(['nice','-n','10','unsquashfs','-processors','1','-d',str(root),str(base/'filesystem.squashfs')])
  refresh_manager(root)
  items=(harness_items if harness_items is not None else sources.harnesses()) if harnesses else {}
  superseded=[]
  if base_generation:
   # The new Rescue can already contain the reviewed component versions or newer.
   # Never downgrade its packages/providers merely to match an older inventory.
   selected=[]
   for item in package_items or []:
    installed_package=subprocess.run(['chroot',str(root),'/usr/bin/dpkg-query','-W','-f=${Version}',item['name']],capture_output=True)
    covered=installed_package.returncode==0 and subprocess.run(['dpkg','--compare-versions',installed_package.stdout.decode().strip(),'ge',item['version']],capture_output=True).returncode==0
    if covered:superseded.append('package:'+item['name'])
    else:selected.append(item)
   package_items=selected
   native=root/'usr/share/aguja/installed-harnesses.json'
   prior=json.loads(native.read_text()).get('providers',{}) if native.exists() else {}
   for name in list(items):
    try:covered=sources.semver(prior[name]['version'])>=sources.semver(items[name]['version'])
    except (KeyError,ValueError,TypeError):covered=False
    if covered:superseded.append('harness:'+name);items.pop(name)
   packages=bool(package_items)
  if items:install_harnesses(root,items,cache)
  worker=Path('/usr/lib/aguja/update-root-worker.sh')
  if package_items is not None:
   atomic(root/'var/lib/aguja-update-packages.json',package_items)
  progress.emit('install','Instalando las actualizaciones seleccionadas')
  mode=('selected' if package_items is not None else 'yes') if packages else 'no'
  run(['nice','-n','10','unshare','--mount','--pid','--fork','--propagation','private',str(worker),str(root),mode],log=folder/'build.log')
  if items:verify_harnesses(root,items)
  if package_items:verify_packages(root,package_items)
  kernel,initrd=boot_pair(root);shutil.copy2(kernel,live/'vmlinuz');shutil.copy2(initrd,live/'initrd.img')
  # This root originated from clean squashfs; never the running RAM overlay.
  for private in ['home/aguja/.ssh/authorized_keys','home/aguja/.codex/auth.json','home/aguja/.claude/.credentials.json','run/aguja-recovery/keys.json']:
   if (root/private).exists() and (root/private).stat().st_size:raise ValueError('No se empaqueta una raíz con secretos')
  root_bytes=sum(p.stat().st_size for p in root.rglob('*') if p.is_file() and not p.is_symlink())
  if shutil.disk_usage(DATA).free<root_bytes+512*1024**2:raise ValueError('No hay margen suficiente para empaquetar; se conserva la versión actual')
  progress.emit('save','Guardando el sistema en el pendrive')
  run(['nice','-n','10','mksquashfs',str(root),str(live/'filesystem.squashfs'),'-noappend','-processors','1','-mem','256M','-comp','zstd','-Xcompression-level','3','-no-progress','-wildcards','-e','tmp/*','var/tmp/*','var/cache/apt','var/lib/apt/lists','run/*','root/*'])
  version=(root/'usr/share/aguja/VERSION').read_text().strip();progress.emit('verify','Verificando los archivos guardados');manifest(folder,version,'packages+harnesses');shutil.rmtree(root);shutil.rmtree(cache);progress.emit('activate','Preparando el próximo arranque');active=activate(g)
  return {'ok':True,'generation':g,'reboot_required':True,'state':active,'already_covered_by_rescue':superseded}

def rollback():
 with lock():
  s=state();new={'schema':1,'active':s['previous'],'previous':s['active']}
  pointer=boot_pointer(new)
  commit_state(new,pointer);return {'ok':True,'reboot_required':True,'state':new}

def status_unlocked():
 s=state();checkfile=RUN/'checks.json' if (RUN/'checks.json').is_file() else ROOT/'checks.json';cached=metadata(checkfile) if checkfile.is_file() else None
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

def menu(language=None):
 import update_ui
 return update_ui.menu(language=language)

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

def elevated_command(argv):
 command=['sudo','--']
 actual=os.environ.get('AGUJA_CONSOLE_TTY','') if os.environ.get('AGUJA_LOCAL_CONSOLE')=='1' else ''
 if not os.environ.get('SSH_CONNECTION'):
  try:
   tty=os.ttyname(0)
   if re.fullmatch('/dev/tty[1-9][0-9]*',tty):actual=tty
  except OSError:pass
 if re.fullmatch('/dev/tty[1-9][0-9]*',actual) and not os.environ.get('SSH_CONNECTION'):
  command+=['/usr/bin/env','AGUJA_LOCAL_CONSOLE=1','AGUJA_CONSOLE_TTY='+actual]
 return command+[sys.executable,str(Path(__file__).resolve()),*argv]

def main(argv=None):
 argv=sys.argv[1:] if argv is None else argv
 p=argparse.ArgumentParser(prog='aguja update');p.add_argument('operation',choices=['menu','status','check','packages','harnesses','all','release','rollback','cleanup'],nargs='?',default='status');p.add_argument('--json',action='store_true');p.add_argument('--language',choices=['es','en','fr','de','pt','it','zh']);a=p.parse_args(argv)
 if os.geteuid()!=0:return subprocess.call(elevated_command(argv))
 try:
  if a.operation=='menu':return menu(a.language)
  if a.operation=='status':result=status()
  elif a.operation=='check':result=check()
  elif a.operation=='release':result=release_update(stage_ram=True)
  elif a.operation=='rollback':result=rollback()
  elif a.operation=='cleanup':result=cleanup()
  else:
   import update_tasks
   inventory=check();items=[r for r in update_tasks.rows(inventory) if r['kind']!='release' and (a.operation=='all' or r['kind']=={'packages':'package','harnesses':'harness'}[a.operation])]
   result=update_tasks.apply(items,{r['id']:'session' for r in items})
  if a.json:print(json.dumps(result,ensure_ascii=False))
  else:show(result)
  return 0
 except Exception as e:
  # Package/upstream logs stay in the manager, never an owner's token-bearing
  # environment; only controlled ValueError text can reach the panel.
  message=str(e) if isinstance(e,ValueError) else 'No se completó la actualización. Se conserva el arranque anterior.'
  print(json.dumps({'ok':False,'error':message},ensure_ascii=False));return 1
if __name__=='__main__':sys.exit(main())
