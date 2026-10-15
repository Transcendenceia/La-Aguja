"""Explicit No / session / persistent update plans; no implicit all-upgrade."""
import json,os,re,shutil,tempfile,uuid
from pathlib import Path
import updates as u
import update_progress as progress
MODES=('no','session','persistent')
PACKAGE=re.compile(r'[a-z0-9][a-z0-9+.-]*(?::[a-z0-9][a-z0-9-]*)?')
VERSION=re.compile(r'[A-Za-z0-9][A-Za-z0-9.+:~_-]{0,199}')
def rows(inventory):
 result=[]
 for p in inventory.get('packages',[]):
  if not PACKAGE.fullmatch(p['name']) or not VERSION.fullmatch(p['latest']):raise ValueError('Paquete de actualización no válido')
  result.append({'id':'package:'+p['name'],'kind':'package',**p})
 for name,h in inventory.get('harnesses',{}).items():
  if name not in u.BINS:raise ValueError('Proveedor no válido')
  if h['available']:result.append({'id':'harness:'+name,'kind':'harness','name':name,**h})
 r=inventory.get('release')
 if r and r['available']:result.append({'id':'release:rescue','kind':'release','name':'Rescue Disk',**r})
 if len({r['id'] for r in result})!=len(result):raise ValueError('Inventario de actualización duplicado')
 return result

def plan(items,choices):
 known={r['id']:r for r in items}
 if not set(choices)<=set(known) or any(v not in MODES for v in choices.values()):raise ValueError('Selección de actualización no válida')
 result={mode:[dict(r) for r in items if choices.get(r['id'],'no')==mode] for mode in MODES[1:]}
 if any(r['kind']=='release' for r in result['session']):raise ValueError('El Rescue Disk completo requiere Sí persistente y el próximo arranque.')
 if any(r['kind']=='release' for r in result['persistent']) and len(result['persistent'])>1:raise ValueError('Actualiza Rescue Disk o los componentes por separado, no en la misma operación.')
 return result

def verify_live_ram():
 if 'boot=live' not in Path('/proc/cmdline').read_text().split():raise ValueError('Esta operación solo se realiza en el Linux live de LA AGUJA.')
 root=json.loads(u.run(['findmnt','-J','-o','TARGET,FSTYPE,OPTIONS','--target','/']).stdout)['filesystems'][0]
 if root['fstype']!='overlay':raise ValueError('La sesión no usa una capa temporal en RAM.')
 upper=next((x.split('=',1)[1] for x in root['options'].split(',') if x.startswith('upperdir=')),None)
 if not upper or not upper.startswith('/run/'):raise ValueError('La sesión no usa una capa temporal en RAM.')
 backing=json.loads(u.run(['findmnt','-J','-o','FSTYPE','--target',upper]).stdout)['filesystems'][0]['fstype']
 if backing not in ('tmpfs','ramfs'):raise ValueError('La sesión no usa una capa temporal en RAM.')

def package_items(items):
 result=[]
 for r in items:
  if r['kind']=='package':
   if not PACKAGE.fullmatch(r['name']) or not VERSION.fullmatch(r['latest']):raise ValueError('Paquete de actualización no válido')
   result.append({'name':r['name'],'version':r['latest']})
 return result

def harness_items(items):
 result={}
 for r in items:
  if r['kind']!='harness':continue
  name=r['name'];candidate=r.get('candidate')
  if name not in u.BINS or not candidate or candidate['version']!=r['latest']:raise ValueError('Repite la consulta antes de instalar este proveedor.')
  u.sources.url(candidate['url']);u.sources.semver(candidate['version'])
  if candidate['algorithm'] not in ('sha256','sha512') or not re.fullmatch('[a-f0-9]{64}' if candidate['algorithm']=='sha256' else '[a-f0-9]{128}',candidate['digest']):raise ValueError('Integridad nativa no válida')
  result[name]=candidate
 return result

def session_update(items):
 packages=package_items(items);harnesses=harness_items(items)
 with u.lock(check_capacity=False):
  verify_live_ram();folder=u.RUN/('session-'+uuid.uuid4().hex);folder.mkdir(mode=0o700);cache=folder/'downloads';cache.mkdir(mode=0o700)
  if packages:
   progress.emit('install','Actualizando los paquetes en RAM',mode='session')
   selection=folder/'packages.json';u.atomic(selection,packages)
   u.run(['unshare','--mount','--pid','--fork','--propagation','private','/usr/lib/aguja/update-session-worker.sh',str(selection)],log=folder/'build.log')
   u.verify_packages(Path('/'),packages)
  if harnesses:
   required=sum(int(x.get('bytes',200*1024**2))*3 for x in harnesses.values())+256*1024**2
   if shutil.disk_usage(cache).free<required:raise ValueError('RAM insuficiente para descargar y verificar los clientes seleccionados.')
   backups={}
   try:
    for name in harnesses:
     target=Path('/')/u.BINS[name];backup=folder/(name+'.before');shutil.copy2(target,backup);backups[target]=backup
    record=Path('/usr/share/aguja/installed-harnesses.json');record_before=record.read_bytes() if record.exists() else None
    u.install_harnesses(Path('/'),harnesses,cache,reserve=128*1024**2)
    progress.emit('verify','Verificando las versiones de esta sesión',mode='session')
    for name,item in harnesses.items():
     raw=u.run(['/'+u.BINS[name],'--version'],timeout=30,env={'PATH':'/usr/local/bin:/usr/bin:/bin','HOME':'/nonexistent','AGY_CLI_DISABLE_AUTO_UPDATE':'true','DISABLE_AUTOUPDATER':'1'}).stdout.decode(errors='replace')
     match=re.search(r'\d+\.\d+\.\d+',raw)
     if not match or match.group()!=item['version']:raise ValueError('La versión nativa no coincide con la descarga verificada')
   except Exception:
    for target,backup in backups.items():os.replace(backup,target)
    if 'record_before' in locals() and record_before is not None:u.atomic(record,record_before)
    raise
   finally:
    for backup in backups.values():
     if backup.exists():backup.unlink()
  # Session files are RAM-only. Keep bounded receipts/logs, not download archives.
  shutil.rmtree(cache)
  return {'ok':True,'mode':'session','items':[r['id'] for r in items],'reboot_required':False}

def apply(items,choices):
 selected=plan(items,choices);completed=[];results=[]
 if not any(selected.values()):return {'ok':True,'completed':[],'results':[],'no_changes':True}
 for mode in ('persistent','session'):
  group=selected[mode]
  if not group:continue
  progress.emit('start','Sí persistente' if mode=='persistent' else 'Sí · solo esta sesión',mode=mode,items=[r['id'] for r in group])
  try:
   if mode=='session':result=session_update(group)
   elif group[0]['kind']=='release':result=u.release_update()
   else:
    packages=package_items(group);harnesses=harness_items(group)
    result=u.package_generation(bool(packages),bool(harnesses),package_items=packages,harness_items=harnesses)
   results.append({'mode':mode,**result});completed.extend(r['id'] for r in group)
   progress.emit('group_done','Guardado y verificado' if mode=='persistent' else 'Actualizado en RAM',mode=mode,items=[r['id'] for r in group])
  except Exception as error:
   message=str(error) if isinstance(error,ValueError) else 'No se completó esta operación. Revisa el estado antes de reintentar.'
   return {'ok':False,'completed':completed,'results':results,'failed_mode':mode,'error':message,'session_may_be_partial':mode=='session'}
 return {'ok':True,'completed':completed,'results':results,'reboot_required':any(r.get('reboot_required') for r in results)}
