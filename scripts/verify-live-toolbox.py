#!/usr/bin/python3
"""Run inside a disposable booted live: native QEMU/firmware and SSH orientation.
No disks, downloaded tools, external networks or AI requests are used.
"""
from pathlib import Path
import json,os,shutil,socket,subprocess,tempfile,time
binaries=('qemu-system-x86_64','qemu-img','qemu-nbd')
versions={b:subprocess.check_output([b,'--version'],text=True).splitlines()[0] for b in binaries}
assert all(shutil.which(b) for b in binaries)
guides=('AGENT-CONTEXT.md','QUICKSTART.md','TOOLBOX.md','SSH-WELCOME.txt')
assert all((Path('/usr/share/aguja')/g).is_file() for g in guides)
assert 'morluto/rea' in Path('/usr/share/aguja/TOOLBOX.md').read_text()
config=subprocess.check_output(['sudo','-n','/usr/sbin/sshd','-T'],text=True)
assert 'banner /usr/share/aguja/SSH-WELCOME.txt' in config
firmware_files=subprocess.check_output(['dpkg','-L','ovmf'],text=True).splitlines()
code=next(Path(p) for p in firmware_files if p.endswith('OVMF_CODE_4M.fd'))
variables=next(Path(p) for p in firmware_files if p.endswith('OVMF_VARS_4M.fd'))
started=[]
with tempfile.TemporaryDirectory(prefix='aguja-virt-qa-') as directory:
 root=Path(directory)
 for firmware in ('bios','uefi'):
  qmp=root/(firmware+'.sock');args=['qemu-system-x86_64','-machine','q35','-accel','tcg','-m','64','-nodefaults','-display','none','-S','-qmp',f'unix:{qmp},server=on,wait=off']
  if firmware=='uefi':
   var=root/'vars.fd';shutil.copyfile(variables,var)
   args+=['-drive',f'if=pflash,format=raw,readonly=on,file={code}','-drive',f'if=pflash,format=raw,file={var}']
  proc=subprocess.Popen(args,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
  try:
   end=time.monotonic()+15
   while not qmp.exists() and proc.poll() is None and time.monotonic()<end:time.sleep(.1)
   with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:
    s.settimeout(5);s.connect(str(qmp));f=s.makefile('rwb');json.loads(f.readline());f.write(b'{"execute":"qmp_capabilities"}\n');f.flush()
    while 'return' not in json.loads(f.readline()):pass
    f.write(b'{"execute":"query-status"}\n');f.flush()
    while True:
     r=json.loads(f.readline())
     if 'return' in r:assert r['return']['running'] is False;break
   started.append(firmware)
  finally:
   proc.terminate()
   try:proc.wait(timeout=5)
   except subprocess.TimeoutExpired:proc.kill();proc.wait()
print(json.dumps({'ok':True,'versions':versions,'native_qemu_firmware_started':started,'kvm_device_access':os.access('/dev/kvm',os.R_OK|os.W_OK),'guides':list(guides),'ssh_banner':True,'optional_tools_installed_by_test':False,'physical_disks_used':False}))
