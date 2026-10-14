'use strict';
const fs=require('node:fs'),path=require('node:path');const {runPowerShell}=require('./windows-privileged.cjs'),{withPrivilegedHelper}=require('./linux-privileged.cjs');
async function devices(platform,run){
 if(platform==='win32'){
  const raw=await runPowerShell(`@(Get-Disk|Where-Object{$_.BusType-eq'USB'-and-not$_.IsBoot-and-not$_.IsSystem}|ForEach-Object{$d=$_;$cfg=@(Get-Partition -DiskNumber $d.Number|Get-Volume -ErrorAction SilentlyContinue|Where-Object{$_.FileSystemLabel-eq'AGUJA_CFG'-and$_.FileSystem-eq'FAT32'});if($cfg.Count-eq1){@{device="\\\\.\\PhysicalDrive$($d.Number)";serial=$(if($d.SerialNumber){$d.SerialNumber.Trim()}else{"USB-$($d.Number)"});size=[int64]$d.Size;model=$d.FriendlyName}}})|ConvertTo-Json -Depth 4 -Compress`);
  const parsed=raw?JSON.parse(raw):[];return Array.isArray(parsed)?parsed:[parsed];
 }
 const tree=JSON.parse(await run('/usr/bin/lsblk',['--tree','-b','-J','-o','PATH,TYPE,SERIAL,TRAN,RM,SIZE,MODEL,LABEL,FSTYPE,MOUNTPOINTS']));
 return tree.blockdevices.filter(d=>d.type==='disk'&&d.tran==='usb'&&d.rm&&d.serial&&(d.children||[]).filter(p=>p.label==='AGUJA_CFG'&&p.fstype==='vfat').length===1).map(d=>({device:d.path,serial:d.serial,size:d.size,model:String(d.model||'USB').trim()}));
}
async function operation(request,{platform=process.platform,run,root}={}){
 const all=await devices(platform,run),d=all.find(d=>d.device===request.device&&d.serial===request.serial&&d.size===request.size);if(!d)throw Error('El USB cambió. Vuelve a seleccionarlo.');
 let raw;
 if(platform==='win32'){
  const script=await fs.promises.readFile(path.join(root,fs.existsSync(path.join(root,'usb-config.ps1'))?'usb-config.ps1':'desktop/usb-config.ps1'),'utf8');const encoded=Buffer.from(JSON.stringify(request)).toString('base64');
  // The elevated bridge writes a private worker; secrets never enter argv.
  raw=await runPowerShell(`& {${script}\n} -RequestBase64 '${encoded}'`,{elevated:true,operation:'usb-config',timeout:120000});
 }else raw=await withPrivilegedHelper(path.join(root,'scripts','usb-config.py'),staged=>run('/usr/bin/pkexec',['/usr/bin/python3',staged],request,{timeout:120000,phase:'helper',limit:8*1024**2}));
 const result=JSON.parse(raw);if(result.ok!==true)throw Error('No se pudo leer o guardar la configuración del USB. Comprueba permisos y vuelve a leer el dispositivo.');return result;
}
module.exports={devices,operation};
