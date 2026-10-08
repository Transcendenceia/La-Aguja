'use strict';
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),{spawn}=require('node:child_process'),{StringDecoder}=require('node:string_decoder');
const {powershellArgs}=require('./ai-tools.cjs');
const executable=()=>path.win32.join(process.env.SystemRoot||'C:\\Windows','System32','WindowsPowerShell','v1.0','powershell.exe');
const quote=s=>"'"+s.replace(/'/g,"''")+"'";
function plainPowerShell(script,{timeout=30000}={}){
 return new Promise((resolve,reject)=>{
  const child=spawn(executable(),powershellArgs('$ProgressPreference="SilentlyContinue";[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false);'+script),{stdio:['pipe','pipe','pipe'],windowsHide:true});
  let output='',settled=false;const decoder=new StringDecoder('utf8');
  const finish=(err,value)=>{if(settled)return;settled=true;clearTimeout(timer);err?reject(err):resolve(value);};
  const timer=setTimeout(()=>{child.kill();finish(Error('La consulta de BitLocker tardó demasiado tiempo.'));},timeout);
  child.stdin.on('error',()=>{});child.stdin.end();child.stderr.resume();
  child.stdout.on('data',data=>{output+=decoder.write(data);if(output.length>1024*1024){child.kill();finish(Error('La respuesta de BitLocker no es válida.'));}});
  child.on('error',()=>finish(Error('No se pudo iniciar PowerShell para consultar BitLocker.')));
  child.on('close',code=>{output+=decoder.end();finish(code===0?null:Error('No se pudo completar la operación de BitLocker.'),output.trim());});
 });
}
async function runPowerShell(script,{timeout=30000,elevated=false}={}){
 if(process.platform!=='win32')throw Error('BitLocker solo está disponible en Windows.');
 if(!elevated)return plainPowerShell(script,{timeout});
 const stage=await fs.promises.mkdtemp(path.join(os.tmpdir(),'aguja-bitlocker-uac-'));
 try{
  // ACL precedes all code/results. Preserve owner access; no Everyone/Users grant.
  await plainPowerShell(`$ErrorActionPreference='Stop';$owner=[Security.Principal.WindowsIdentity]::GetCurrent().User;$acl=[Security.AccessControl.DirectorySecurity]::new();$acl.SetAccessRuleProtection($true,$false);foreach($sid in @($owner,[Security.Principal.SecurityIdentifier]::new('S-1-5-18'),[Security.Principal.SecurityIdentifier]::new('S-1-5-32-544'))){$acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($sid,'FullControl','ContainerInherit,ObjectInherit','None','Allow'))};[IO.Directory]::SetAccessControl(${quote(stage)},$acl)`);
  const result=path.join(stage,'result.json'),worker=path.join(stage,'operation.ps1');
  await fs.promises.writeFile(result,'',{flag:'wx'});
  const wrapped=`$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue';try{$answer=& {\n${script}\n};$text=[string]($answer -join [Environment]::NewLine)}catch{$text=@{ok=$false;error='No se pudo completar la operación de BitLocker.'}|ConvertTo-Json -Compress};[IO.File]::WriteAllText(${quote(result)},$text,[Text.UTF8Encoding]::new($false))`;
  await fs.promises.writeFile(worker,'\ufeff'+wrapped,{flag:'wx'});
  // UAC elevates this single operation, not Electron. No key/password in argv.
  // PS5.1 can discard Win32Exception.InnerException. Use the OS-localized
  // ERROR_CANCELLED message instead of hard-coding Spanish/English text.
  const broker=`$ErrorActionPreference='Stop';try{$arguments='-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "'+${quote(worker)}+'"';$p=Start-Process -FilePath ${quote(executable())} -ArgumentList $arguments -Verb RunAs -WindowStyle Hidden -PassThru;$p.WaitForExit();if($p.ExitCode -ne 0){throw 'Operation failed'};[Console]::Out.Write([IO.File]::ReadAllText(${quote(result)},[Text.Encoding]::UTF8))}catch{$e=$_.Exception;while($e.InnerException){$e=$e.InnerException};$cancelText=[ComponentModel.Win32Exception]::new(1223).Message;$canceled=($e.NativeErrorCode -eq 1223 -or $_.Exception.Message.IndexOf($cancelText,[StringComparison]::OrdinalIgnoreCase) -ge 0);$message=if($canceled){'No se autorizó la consulta de BitLocker. Acepta el diálogo de permisos de Windows o vuelve a intentarlo.'}else{'No se pudo completar la operación de BitLocker.'};[Console]::Out.Write((@{ok=$false;canceled=$canceled;error=$message}|ConvertTo-Json -Compress))}`;
  return await plainPowerShell(broker,{timeout:Math.max(timeout,120000)});
 }finally{await fs.promises.rm(stage,{recursive:true,force:true});}
}
module.exports={runPowerShell};
