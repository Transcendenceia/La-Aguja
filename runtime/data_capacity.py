"""One-time initialization of fresh USB DATA, including Windows-written media."""
import json,re,subprocess
from pathlib import Path
STATUS=Path('/run/aguja-data-initialization.json')

def deferred():
 from config_transaction import atomic
 atomic(STATUS,json.dumps({'schema':1,'state':'deferred','reason':'boot-medium-not-removable-usb','disk_modified':False}).encode())
 STATUS.chmod(0o644)
 print('LA AGUJA: DATA no se amplía en un disco fijo o USB no extraíble; el arranque continúa con su capacidad actual.',flush=True)

def initialize(cfg,disk,data):
 marker=Path(cfg)/'data-initialize.json'
 if not marker.is_file() or json.loads(marker.read_text()).get('state')!='pending':return None
 release=json.loads((Path(cfg)/'release.json').read_text())
 if 'persistent-updates-v1' not in release.get('features',[]):raise ValueError('Inicialización no compatible')
 doc=json.loads(subprocess.check_output(['lsblk','--tree','-b','-J','-o','PATH,TYPE,TRAN,RM,SIZE,LABEL',disk]))['blockdevices'][0]
 if doc['path']!=disk or doc['type']!='disk':raise ValueError('Medio de arranque no válido para DATA')
 if doc.get('tran')!='usb' or not doc.get('rm'):
  # The boot medium already has usable factory DATA. Defer expansion without
  # writing its partition table; a VM bus mismatch is not an unlock failure.
  deferred();return None
 children=doc.get('children',[])
 if int(Path('/sys/class/block/'+Path(data).name+'/partition').read_text())!=5 or any(int(Path('/sys/class/block/'+Path(x['path']).name+'/partition').read_text())>5 for x in children):raise ValueError('No se inicializa un diseño distinto al de fábrica')
 if len([x for x in children if x.get('label')=='AGUJA_CFG'])!=1 or len([x for x in children if x['path']==data and x.get('label')=='AGUJA_DATA'])!=1:raise ValueError('Particiones de arranque no válidas')
 # No workspace/profile is migrated. This marker comes only from the freshly
 # prepared 1.0 factory; never install it during an existing USB config edit.
 backup=Path(cfg)/'data-initialize-gpt.backup'
 if not backup.exists():subprocess.run(['sgdisk','--backup='+str(backup),disk],check=True,capture_output=True)
 info=subprocess.check_output(['sgdisk','-i','5',disk],text=True)
 start=int(re.search(r'First sector:\s*(\d+)',info)[1]);guid=re.search(r'Partition unique GUID:\s*([A-Fa-f0-9-]+)',info)[1]
 subprocess.run(['sgdisk','-e',disk],check=True,capture_output=True)
 # Preserve the partition identity used by future generation boot entries.
 subprocess.run(['sgdisk','-d','5','-n',f'5:{start}:0','-t','5:8300','-c','5:AGUJA_DATA','-u','5:'+guid,disk],check=True,capture_output=True)
 info=subprocess.check_output(['sgdisk','-i','5',disk],text=True);end=int(re.search(r'Last sector:\s*(\d+)',info)[1])
 if end<start or (end+1)*512>doc['size']:raise ValueError('DATA fuera de límites')
 loop=subprocess.check_output(['losetup','--find','--show','--offset',str(start*512),'--sizelimit',str((end-start+1)*512),disk],text=True).strip()
 try:
  check=subprocess.run(['e2fsck','-p',loop],capture_output=True)
  if check.returncode not in (0,1):raise ValueError('DATA requiere revisión; no se inicializa')
  subprocess.run(['resize2fs',loop],check=True,capture_output=True)
  from config_transaction import atomic
  atomic(marker,json.dumps({'schema':1,'state':'complete','bytes':(end-start+1)*512}).encode())
  return loop
 except BaseException:
  subprocess.run(['losetup','-d',loop],check=True,capture_output=True);raise
