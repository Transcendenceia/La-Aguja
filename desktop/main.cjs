'use strict';
const {app,BrowserWindow,ipcMain,dialog,clipboard,shell}=require('electron');
const fs=require('node:fs'); const path=require('node:path');const os=require('node:os');const crypto=require('node:crypto');const {spawn}=require('node:child_process');
const {StringDecoder}=require('node:string_decoder');
// Preserve local preferences and private images; legacy account/relay files are never read.
if(app.commandLine?.hasSwitch && !app.commandLine.hasSwitch('user-data-dir') && app.setPath)app.setPath('userData',path.join(app.getPath('appData'),'Aguja Companion'));
const core=require('./core.cjs');
const bitlocker=require('./bitlocker.cjs');
const fat32=require('./fat32-writer.cjs');
const provisioning=require('./provisioning.cjs');
const {flashWindows}=require('./windows-flash.cjs');
const {AITools,provider,powershellArgs,windowsPowerShell,openWindowsLoginTerminal}=require('./ai-tools.cjs');
const isWindows=process.platform==='win32';
const i18n=require('./ui/i18n.js');
let uiLanguage='es';
function translate(source){return i18n.translation(core.LOCALE_CATALOG,uiLanguage,source);}
function publicDialog(options){const result={...options};for(const key of ['title','message','detail','buttonLabel'])if(typeof result[key]==='string')result[key]=translate(result[key]);if(result.buttons)result.buttons=result.buttons.map(translate);return result;}
const showMessageBox=(target,options)=>dialog.showMessageBox(target,publicDialog(options));
const showSaveDialog=(target,options)=>dialog.showSaveDialog(target,publicDialog(options));
const showOpenDialog=(target,options)=>dialog.showOpenDialog(target,publicDialog(options));
const providerBins={codex:'codex',antigravity:'agy',claude:'claude',opencode:'opencode'};
const aiTools=new AITools({directory:app.getPath('userData'),run,progress});
const ROOT=app.isPackaged?path.join(process.resourcesPath,'aguja'):path.resolve(__dirname,'..');
let win; let selectedImage=null;let prepared=null;let releases=[];let verifiedCatalog=null;let working=false;let approvedImports={};
// No crash reporter, analytics, renderer remote content, credentials in command arguments or logs.
function receipt(ok,data={},error=''){return ok?{ok:true,...data}:{ok:false,error};}
function message(e){return /signature|SHA|contraseña|clave|nombre|Wi-Fi|puerto|perfil|catálogo|imagen|dirección|servidor|USB|consentimiento|red |sesión|autenticación|cápsula|passphrase|falt|ruta|pendiente|idioma|teclado|variante|capacidad|carpeta|cabe|cambió|grabación|permiso|herramienta|operación|respaldo|backup|cuenta|correo|túnel|navegador|agente|configuración privada/i.test(e.message||'')?String(e.message).slice(0,300):'No se completó la operación. Revisa los datos e intenta de nuevo.';}
function progress(phase,detail={}){if(win&&!win.isDestroyed())win.webContents.send('progress',{phase,...detail,...(detail.message?{message:translate(detail.message)}:{})});}
function handle(channel,callback){ipcMain.handle(channel,async(event,...args)=>{
 if(event.sender!==win.webContents || event.senderFrame!==win.webContents.mainFrame)throw new Error('Origen no autorizado.');
 try{return receipt(true,await callback(...args));}catch(e){return receipt(false,{},translate(message(e)));}
});}
async function exclusive(fn){if(working)throw new Error('Espera a que termine la operación actual.');working=true;try{return await fn();}finally{working=false;}}
function run(command,args,input=null,{timeout=120000,limit=4*1024*1024,phase='working',env={}}={}){return new Promise((resolve,reject)=>{
 const childEnv={...process.env,...env};if(isWindows&&env.PATH)for(const key of Object.keys(childEnv))if(key.toLowerCase()==='path'&&key!=='PATH')delete childEnv[key];
 const proc=spawn(command,args,{stdio:['pipe','pipe','pipe'],env:childEnv,windowsHide:true});let stdout='',stderr='',pending='',ended=false;const stdoutDecoder=new StringDecoder('utf8'),stderrDecoder=new StringDecoder('utf8');
 const finish=(error,value)=>{if(ended)return;ended=true;clearTimeout(timer);error?reject(error):resolve(value);};
 const timer=setTimeout(()=>{proc.kill('SIGTERM');finish(new Error('La operación tardó demasiado. Puedes volver a intentarlo.'));},timeout);
 proc.stdout.on('data',data=>{const decoded=stdoutDecoder.write(data);stdout+=decoded;pending+=decoded;let newline;while((newline=pending.indexOf('\n'))>=0){const line=pending.slice(0,newline);pending=pending.slice(newline+1);try{const value=JSON.parse(line);const captions={verify:'Comprobando imagen…',backup:'Respaldando USB…',write:'Grabando USB…',readback:'Verificando lectura del USB…',expand:'Ampliando la partición de datos…'};if(value.type==='progress'&&phase==='flash'&&captions[value.stage])progress('flash',{message:captions[value.stage]});}catch{}}if(stdout.length>limit){proc.kill();finish(new Error('La respuesta no es válida.'));}});
 proc.stderr.on('data',data=>{stderr+=stderrDecoder.write(data);if(stderr.length>limit)stderr=stderr.slice(-limit);});
 proc.on('error',()=>finish(new Error('Falta una herramienta local necesaria.')));
 proc.on('close',code=>{stdout+=stdoutDecoder.end();stderr+=stderrDecoder.end();if(code!==0){
  if(['helper','flash'].includes(phase)){for(const line of stdout.trim().split('\n').reverse()){try{const result=JSON.parse(line);if(result.ok===false&&typeof result.error==='string')return finish(new Error(result.error.slice(0,300)));}catch{}}}
  if(phase==='flash'&&[126,127].includes(code))return finish(new Error('No se autorizó la grabación. Acepta el diálogo de permisos de Linux o vuelve a intentarlo.'));
  return finish(new Error(phase==='wifi'?'No se pudo importar la red activa. Puedes escribirla manualmente.':'La operación no se completó. Comprueba las herramientas locales y los permisos.'));
 }finish(null,stdout);});
 // Credentials go only to a pipe, never argv; child output never console-logged.
 proc.stdin.on('error',()=>{});proc.stdin.end(input===null?'':JSON.stringify(input));
 });}
async function helper(operation,fields){if(operation==='prepare'&&fields.protection?.mode==='encrypted'){try{await run('/usr/bin/python3',['-c','import cryptography.hazmat.primitives.ciphers.aead'],null,{timeout:10000});}catch{throw new Error('Falta Python cryptography para cifrar la cápsula. Instala python-cryptography en Cachy/Arch o python3-cryptography en Debian/Ubuntu.');}}const helperPath=path.join(ROOT,'scripts','platform-profile.py');
 if(!fs.existsSync(helperPath))throw new Error('El preparador de imágenes aún no está instalado en este paquete.');
 const output=await run('/usr/bin/python3',['-I',helperPath],{op:operation,...fields},{timeout:30*60*1000,phase:'helper'});
 // Helper contract permits JSONL progress; only accepted public receipt keys survive IPC.
 const lines=output.trim().split('\n');let final;for(const line of lines){let obj;try{obj=JSON.parse(line);}catch{continue;}if(obj.event==='progress'||obj.type==='progress')progress('prepare',{message:String(obj.message||'Preparando imagen…').slice(0,150)});else final=obj;}
 if(!final || final.ok===false)throw new Error(final?.error||'El preparador no devolvió una imagen verificada.');return final;
}
async function chooseSave(title,defaultPath,extensions){const out=await showSaveDialog(win,{title,defaultPath,filters:[{name:'Archivo de LA AGUJA',extensions}]});return out.canceled?null:out.filePath;}
function secretPassword(){return crypto.randomBytes(18).toString('base64url');}
function validateProvider(p){provider(p);return p;}
function providerFound(p){return aiTools.resolve(p);}
function profileEncrypt(capsule,passphrase){if(typeof passphrase!=='string'||passphrase.length<12||passphrase.length>1024)throw new Error('La contraseña del perfil necesita al menos 12 caracteres.');const salt=crypto.randomBytes(16),iv=crypto.randomBytes(12);const key=crypto.scryptSync(passphrase,salt,32,{N:32768,r:8,p:1,maxmem:64*1024**2});const cipher=crypto.createCipheriv('aes-256-gcm',key,iv);const data=Buffer.concat([cipher.update(JSON.stringify(capsule),'utf8'),cipher.final()]);key.fill(0);return {schema:1,format:'aguja-profile-aes256gcm',salt:salt.toString('base64'),iv:iv.toString('base64'),tag:cipher.getAuthTag().toString('base64'),data:data.toString('base64')};}
function profileDecrypt(envelope,passphrase){if(envelope.format!=='aguja-profile-aes256gcm'||typeof passphrase!=='string'||JSON.stringify(envelope).length>1048576)throw new Error('Perfil cifrado no válido.');try{const salt=Buffer.from(envelope.salt,'base64'),iv=Buffer.from(envelope.iv,'base64'),tag=Buffer.from(envelope.tag,'base64');if(salt.length!==16||iv.length!==12||tag.length!==16)throw Error();const key=crypto.scryptSync(passphrase,salt,32,{N:32768,r:8,p:1,maxmem:64*1024**2});const decipher=crypto.createDecipheriv('aes-256-gcm',key,iv);decipher.setAuthTag(tag);const data=Buffer.concat([decipher.update(Buffer.from(envelope.data,'base64')),decipher.final()]);key.fill(0);return core.validateCapsule(JSON.parse(data));}catch{throw new Error('La contraseña del perfil no coincide o el archivo fue alterado.');}}
async function loadVerifiedCatalog({refresh=false,timeoutMs=20000}={}) {
 const pin=JSON.parse(await fs.promises.readFile(path.join(__dirname,'resources','release-key.json'),'utf8'));
 // Only signed envelopes are cached in memory, and expiry/signature are checked
 // on every reuse. No image path, filename or digest is sent to the catalog.
 if(!refresh && verifiedCatalog){try{return core.verifyManifest(verifiedCatalog,pin);}catch{verifiedCatalog=null;}}
 const envelope=await core.getHTTPS(pin.catalog_url,65536,timeoutMs);
 const verified=core.verifyManifest(envelope,pin);verifiedCatalog=envelope;return verified;
}
function prepareInput(input,{pendingRemote=false}={}) {
 if(!selectedImage)throw new Error('Selecciona primero una imagen.');
 const capsule=core.validateCapsule(input?.capsule),protection=input.protection||{mode:'plain'};
 if(!['plain','encrypted'].includes(protection.mode))throw new Error('Elige cómo desbloquear las credenciales.');
 if(protection.mode==='encrypted'&&(typeof protection.passphrase!=='string'||protection.passphrase.length<12||protection.passphrase.length>1024))throw new Error('El desbloqueo necesita una contraseña de entre 12 y 1024 caracteres.');
 // New images use the user's own tailnet. Never enroll, claim or copy
 // proprietary relay credentials even if an old renderer/profile requests it.
 capsule.remote={enabled:false};
 for(const [p,settings]of Object.entries(capsule.providers))if(settings.mode==='import'){if(!approvedImports[p])throw new Error('Importa primero la autenticación de '+p+'.');if(!isWindows)settings.import_paths=approvedImports[p];}
 const bitlockerData=input?.bitlocker&&Array.isArray(input.bitlocker)&&input.bitlocker.length>0?bitlocker.buildBitLockerPayload(input.bitlocker):null;
 const fingerprint=crypto.createHash('sha256').update(JSON.stringify({capsule,protection,image:selectedImage.sha256,bitlocker:bitlockerData})).digest('hex');
 return {capsule,protection,fingerprint,bitlocker:bitlockerData};
}
async function prepareImage(settings,output) {
 if(output===selectedImage.path)throw new Error('La imagen privada debe tener otro nombre.');
 prepared=null;progress('prepare',{message:'Preparando tu imagen privada…'});
 if(isWindows){
  await provisioning.prepareWindows({source:selectedImage.path,output,sha256:selectedImage.sha256,capsule:settings.capsule,protection:settings.protection,approved:approvedImports,bitlocker:settings.bitlocker});
 }else{
  const result=await helper('prepare',{image_path:selectedImage.path,output_path:output,image_sha256:selectedImage.sha256,capsule:settings.capsule,protection:settings.protection});
  if(settings.bitlocker){
   fat32.writeFat32File(output,'AGUJA_CFG','bitlocker.json',Buffer.from(JSON.stringify(settings.bitlocker,null,2),'utf8'));
  }
 }
 const checked=await core.hashFile(output,d=>progress('verify',d));
 await fs.promises.chmod(output,0o600).catch(()=>{});
 prepared={path:output,...checked,fingerprint:settings.fingerprint};
 return {name:path.basename(output),...checked};
}
async function privateOutput() {
 const dir=path.join(app.getPath('userData'),'private-images');await fs.promises.mkdir(dir,{recursive:true,mode:0o700});
 const stat=await fs.promises.lstat(dir);if(!stat.isDirectory()||stat.isSymbolicLink())throw new Error('La carpeta de imágenes privadas no es válida.');await fs.promises.chmod(dir,0o700);
 return path.join(dir,'aguja-personal-'+crypto.randomBytes(16).toString('hex')+'.img');
}
async function availableDisks(){
 if(isWindows){
  const psScript=`
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
Get-Disk | Where-Object { $_.BusType -eq 'USB' } | ForEach-Object {
    [PSCustomObject]@{
        device = "\\\\.\\PhysicalDrive$($_.Number)"
        number = $_.Number
        serial = if ($_.SerialNumber) { $_.SerialNumber.Trim() } else { "USB-$($_.Number)" }
        size = [int64]$_.Size
        model = if ($_.FriendlyName) { $_.FriendlyName.Trim() } else { "USB Drive" }
        eligible = (-not $_.IsBoot -and -not $_.IsSystem)
    }
} | ConvertTo-Json -Depth 3
`;
  try{
   const output=await run(windowsPowerShell(),powershellArgs(psScript),null,{timeout:10000});
   if(!output.trim())return [];
   const parsed=JSON.parse(output.trim());
   const list=Array.isArray(parsed)?parsed:[parsed];
   return list.filter(d=>d.eligible).map(d=>({device:d.device,serial:d.serial,size:Number(d.size),model:d.model,eligible:true}));
  }catch{return [];}
 }
 return core.flattenDisks(JSON.parse(await run('/usr/bin/lsblk',['--tree','-b','-J','-o','PATH,TYPE,SERIAL,TRAN,RM,SIZE,MODEL,MOUNTPOINTS'])));
}
async function selectedDisk(input,identity=null) {
 if(!input||typeof input.serial!=='string'||typeof input.device!=='string')throw new Error('Selecciona el USB que quieres grabar.');
 const disk=(await availableDisks()).find(d=>d.serial===input.serial&&d.device===input.device);
 if(!disk || identity&&(disk.model!==identity.model||disk.size!==identity.size))throw new Error('El USB cambió o tiene particiones montadas. Vuelve a seleccionarlo.');
 return disk;
}
async function importLocale() {
 if(isWindows){
  const lang=app.getLocale()||'es';
  const normalizedLang=lang.startsWith('es')?'es_ES.UTF-8':(lang.replace('-','_')+'.UTF-8');
  const keyboard=lang.startsWith('es')?'es':'us';
  return core.importedLocale({language:normalizedLang,keyboard,variant:''});
 }
 let language=process.env.LC_ALL||process.env.LANG||'',keyboard='',variant='',status='';
 try{status=await run('/usr/bin/localectl',['--no-pager','status'],null,{timeout:5000,limit:65536});}catch{}
 if(!language) {try{const defaults=await fs.promises.readFile('/etc/default/locale','utf8');language=(defaults.match(/^LANG=["']?([^"'\r\n]+)/m)||[])[1]||'';}catch{} }
 if(!language)language=(status.match(/LANG=([^\s]+)/)||[])[1]||'';
 // Hyprland can override localectl at runtime; inspect only the active main keyboard.
 const hyprctl=core.resolveProviderBinary('hyprctl');
 if(hyprctl&&process.env.HYPRLAND_INSTANCE_SIGNATURE)try{const devices=JSON.parse(await run(hyprctl,['-j','devices'],null,{timeout:5000,limit:65536}));const k=(devices.keyboards||[]).find(k=>k.main)||devices.keyboards?.[0];if(k){keyboard=k.layout||'';variant=k.variant||'';}}catch{}
 if(!keyboard){keyboard=(status.match(/X11 Layout:\s*([^\s]+)/)||[])[1]||'';variant=(status.match(/X11 Variant:\s*([^\s]+)/)||[])[1]||'';}
 if(!keyboard){try{const vc=await fs.promises.readFile('/etc/vconsole.conf','utf8');const keymap=(vc.match(/^KEYMAP=["']?([^"'\r\n]+)/m)||[])[1]||'';keyboard=({es:'es',us:'us',uk:'gb',fr:'fr',de:'de',it:'it','br-abnt2':'br','la-latin1':'latam'})[keymap]||'';}catch{}}
 return core.importedLocale({language,keyboard,variant});
}
function installIPC(){
 handle('info',async()=>({version:app.getVersion(),platform:process.platform,prepareAvailable:isWindows||fs.existsSync(path.join(ROOT,'scripts','platform-profile.py')),bitlockerAvailable:isWindows}));
 handle('i18n-catalog',async()=>({catalog:core.LOCALE_CATALOG,language:uiLanguage,systemLanguage:app.getLocale?.()||'es'}));
 handle('i18n-language',async(value)=>{if(typeof value!=='string'||!['es',...Object.keys(core.LOCALE_CATALOG.translations)].includes(value))throw new Error('Idioma no compatible.');uiLanguage=value;await fs.promises.writeFile(path.join(app.getPath('userData'),'ui-language.json'),JSON.stringify({language:value}),{mode:0o600});return {language:value};});
 handle('catalog',async()=>{releases=await loadVerifiedCatalog({refresh:true});return {releases};});
 handle('download',async(index)=>exclusive(async()=>{if(!Number.isInteger(index)||!releases[index])throw new Error('Selecciona una versión del catálogo firmado.');const r=releases[index];const dest=await chooseSave('Guardar imagen pública',path.join(app.getPath('downloads'),'aguja-'+r.version+'.img'),['img']);if(!dest)return {canceled:true};progress('download',{done:0,total:r.bytes});const verified=await core.downloadImage(r,dest,d=>progress('download',d),undefined);selectedImage={path:dest,...verified,version:r.version,trusted:true,verification:'verified-catalog'};prepared=null;return {image:{name:path.basename(dest),...verified,version:r.version,trusted:true,verification:'verified-catalog'}};}));
 handle('import-image',async(expected='')=>exclusive(async()=>{
  expected=core.normalizeImageSHA(expected);
  const pick=await showOpenDialog(win,{title:'Importar imagen de LA AGUJA',properties:['openFile'],filters:[{name:'Imagen sin comprimir',extensions:['img']}]});
  if(pick.canceled)return {canceled:true};
  const filename=pick.filePaths[0];if(typeof filename!=='string'||path.extname(filename).toLowerCase()!=='.img')throw new Error('Selecciona un archivo de imagen .img sin comprimir.');
  progress('verify');
  // Fetch the fixed catalog in parallel with local hashing. Offline, expired or
  // invalid catalogs never prevent local use and never mark it as official.
  const [verified,official]=await Promise.all([core.hashFile(filename,d=>progress('verify',d)),loadVerifiedCatalog({timeoutMs:4000}).catch(()=>[])]);
  const imported=core.resolveImportedImage(verified,expected,official);
  selectedImage={path:filename,...imported};prepared=null;
  return {image:{name:path.basename(filename),...imported}};
 }));
 handle('import-locale',async()=>exclusive(importLocale));
 handle('generate-password',async()=>({password:secretPassword()}));
 handle('import-wifi',async()=>exclusive(async()=>{
  if(isWindows){
   const psScript=`
$net = netsh wlan show interfaces
$ssidMatch = ($net | Select-String -Pattern '^\\s*SSID\\s*:\\s*(.+)$')
if ($ssidMatch) {
    $ssid = $ssidMatch.Matches[0].Groups[1].Value.Trim()
    $profile = netsh wlan show profile name="$ssid" key=clear
    $keyMatch = ($profile | Select-String -Pattern '^\\s*(?:Contenido de la clave|Key Content)\\s*:\\s*(.+)$')
    $key = if ($keyMatch) { $keyMatch.Matches[0].Groups[1].Value.Trim() } else { "" }
    [PSCustomObject]@{
        ssid = $ssid
        password = $key
        security = "wpa-psk"
        country = "ES"
        hidden = $false
    } | ConvertTo-Json
}
`;
   const output=await run('powershell.exe',['-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-Command',psScript],null,{phase:'wifi'});
   if(!output.trim())throw new Error('No se detectó ninguna red Wi-Fi activa.');
   return {wifi:JSON.parse(output.trim())};
  }
  if(process.platform!=='linux')throw new Error('La importación Wi-Fi está disponible en Linux y Windows.');
  const script=app.isPackaged?path.join(ROOT,'wifi-helper.py'):path.join(__dirname,'wifi-helper.py');
  const data=JSON.parse(await run('/usr/bin/pkexec',['/usr/bin/python3','-I',script],null,{phase:'wifi'}));
  return {wifi:data};
 }));
 handle('bitlocker-status',async(authorize=false)=>bitlocker.getBitLockerStatus({authorize:authorize===true}));
 handle('bitlocker-suspend',async(mountPoint,rebootCount)=>exclusive(async()=>bitlocker.suspendBitLocker(mountPoint,rebootCount)));
 handle('bitlocker-resume',async(mountPoint)=>exclusive(async()=>bitlocker.resumeBitLocker(mountPoint)));
 handle('bitlocker-key',async(mountPoint)=>exclusive(async()=>bitlocker.getRecoveryKey(mountPoint)));
 handle('bitlocker-export-text',async(mountPoint)=>exclusive(async()=>{
  const keyInfo=await bitlocker.getRecoveryKey(mountPoint);
  const clean=keyInfo.mountPoint.replace(/[^A-Z]/gi,'');
  const dest=await chooseSave('Guardar clave de respaldo de BitLocker',path.join(app.getPath('documents'),`bitlocker-recovery-${clean}.txt`),['txt']);
  if(!dest)return {canceled:true};
  const textContent=[
   '================================================================================',
   'LA AGUJA - CLAVE DE RECUPERACION DE BITLOCKER (RESPALDO DE RESCATE)',
   '================================================================================',
   '',
   `Unidad:                 ${keyInfo.mountPoint}`,
   `Metodo de cifrado:      ${keyInfo.encryptionMethod}`,
   `Identificador de clave: ${keyInfo.keyProtectorId}`,
   `Fecha de exportacion:   ${new Date().toISOString()}`,
   '',
   'CONTRASENA DE RECUPERACION (48 DIGITOS):',
   keyInfo.recoveryPassword,
   '',
   '--------------------------------------------------------------------------------',
   'Guarda este archivo en un lugar seguro. Nunca lo compartas con personas no autorizadas.',
   '================================================================================'
  ].join('\r\n');
  await fs.promises.writeFile(dest,textContent,{flag:'wx',mode:0o600});
  return {exported:true,path:dest};
 }));
 handle('provider-status',async()=>{const providers={};for(const p of Object.keys(providerBins))providers[p]={installed:Boolean(providerFound(p)),imported:Boolean(approvedImports[p])};return {providers};});
 handle('provider-install',async(id)=>exclusive(async()=>{validateProvider(id);const answer=await showMessageBox(win,{type:'question',title:'Instalar herramienta IA',message:'Descargar e instalar '+provider(id).name+' en este PC',detail:'Se utilizará la fuente oficial y una instalación de usuario. No se iniciará sesión ni se copiarán credenciales. Tus ajustes de la imagen no cambian.',buttons:['Cancelar','Descargar e instalar'],defaultId:0,cancelId:0});if(answer.response!==1)return {canceled:true};return aiTools.install(id);}));
 handle('provider-docs',async(id)=>{await shell.openExternal(provider(id).docs);return {opened:true};});
 handle('provider-login',async(id)=>{validateProvider(id);const launch=aiTools.loginCommand(id),env=aiTools.environment();
   // Native visible terminal; user performs consent directly. No account or token captured here.
   if(isWindows)return openWindowsLoginTerminal(launch,{env,cwd:os.homedir(),name:provider(id).name,run});
   const terminals=[['/usr/bin/kitty',['--',launch.command,...launch.args]],['/usr/bin/konsole',['-e',launch.command,...launch.args]],['/usr/bin/gnome-terminal',['--',launch.command,...launch.args]],['/usr/bin/xterm',['-e',launch.command,...launch.args]]];
   const terminal=terminals.find(t=>fs.existsSync(t[0]));if(!terminal)throw new Error('Abre un terminal y ejecuta el inicio de sesión del CLI oficial. No hay un terminal compatible instalado.');
   const child=spawn(terminal[0],terminal[1],{detached:true,stdio:'ignore',env,cwd:os.homedir()});await new Promise((resolve,reject)=>{child.once('spawn',resolve);child.once('error',()=>reject(new Error('No se pudo abrir el terminal del CLI.')));});child.unref();return {launched:true};});
 handle('import-provider',async(provider)=>exclusive(async()=>{validateProvider(provider);prepared=null;delete approvedImports[provider];const response=isWindows?provisioning.discover(provider):await helper('import-provider',{provider});if(!response.portable)throw new Error('No hay una sesión nativa portable válida para importar. Comprueba el login y los permisos del archivo, o inicia sesión en el disco.');approvedImports[provider]=isWindows?response.paths:response.import_paths;return {portable:true,summary:String(response.summary||'Perfil local disponible para la imagen.').slice(0,250)};}));
 handle('invalidate-prepared',async()=>{if(working)throw new Error('Espera a que termine la operación actual.');prepared=null;return {invalidated:true};});
 handle('prepare',async(input)=>exclusive(async()=>{prepareInput(input,{pendingRemote:true});const output=await chooseSave('Guardar imagen privada configurada',path.join(app.getPath('downloads'),'aguja-personal.img'),['img']);if(!output)return {canceled:true};const settings=prepareInput(input);return {prepared:await prepareImage(settings,output)};}));
 handle('export-profile',async(input)=>{const capsule=core.validateCapsule(input.capsule);capsule.remote={enabled:false};const encrypted=profileEncrypt(capsule,input.passphrase);const file=await chooseSave('Guardar perfil cifrado',path.join(app.getPath('documents'),'aguja-perfil.aguja'),['aguja']);if(!file)return {canceled:true};await fs.promises.writeFile(file,JSON.stringify(encrypted),{flag:'wx',mode:0o600});return {name:path.basename(file)};});
 handle('import-profile',async(passphrase)=>{const pick=await showOpenDialog(win,{title:'Abrir perfil cifrado',properties:['openFile'],filters:[{name:'Perfil de LA AGUJA',extensions:['aguja']}]});if(pick.canceled)return {canceled:true};const st=await fs.promises.stat(pick.filePaths[0]);if(st.size>1048576)throw new Error('El perfil es demasiado grande.');return {capsule:profileDecrypt(JSON.parse(await fs.promises.readFile(pick.filePaths[0],'utf8')),passphrase)};});
 handle('disks',async()=>({disks:await availableDisks()}));
 handle('flash',async(input)=>exclusive(async()=>{
  if(isWindows&&input?.backup===true)throw new Error('El respaldo previo de USB aún no está disponible en Windows. No se ha grabado nada.');
  let settings=prepareInput(input,{pendingRemote:true});const disk=await selectedDisk(input);
  if(selectedImage.bytes>disk.size || prepared?.fingerprint===settings.fingerprint&&prepared.bytes>disk.size)throw new Error('La imagen no cabe en este USB. Elige uno con más capacidad.');
  const ready=prepared?.fingerprint===settings.fingerprint;
  const backup=input.backup===true;
  const action=backup?'Respaldar y grabar este USB':'Borrar y grabar este USB';
  const answer=await showMessageBox(win,{type:'warning',title:'Grabar '+disk.model,message:'¿Borrar y grabar este USB?',detail:`Modelo: ${disk.model}\nCapacidad: ${(disk.size/1024**3).toFixed(2)} GiB\nDispositivo: ${disk.device}\nSerie: ${disk.serial}\n\n${ready?'Tu imagen privada está lista.':'Prepararemos tu imagen privada automáticamente.'} ${backup?'Se hará y verificará un respaldo antes de borrar.':'Se borrará el contenido anterior SIN RESPALDO.'} Después se verificará la grabación. Ningún disco interno es elegible.`,buttons:['Cancelar',action],defaultId:0,cancelId:0});
  if(answer.response!==1)return {canceled:true};
  let backupDir=null;
  if(backup){const pick=await showOpenDialog(win,{title:'Destino del respaldo completo del USB',properties:['openDirectory','createDirectory']});if(pick.canceled)return {canceled:true};backupDir=pick.filePaths[0];}
  await selectedDisk(input,disk);
  settings=prepareInput(input);
  // Native dialogs can outlive configuration changes. Recheck the private
  // image fingerprint after confirmation; no network enrollment is performed.
  let preparedReceipt;if(!prepared||prepared.fingerprint!==settings.fingerprint)preparedReceipt=await prepareImage(settings,await privateOutput());
  if(prepared.bytes>disk.size)throw new Error('La imagen privada no cabe en este USB. Elige uno con más capacidad.');
  await selectedDisk(input,disk);
  const checked=await core.hashFile(prepared.path,d=>progress('verify',d));if(checked.sha256!==prepared.sha256||checked.bytes!==prepared.bytes)throw new Error('La imagen privada cambió. Prepara otra antes de grabar.');
  const reportDir=path.join(app.getPath('userData'),'flash-reports');await fs.promises.mkdir(reportDir,{recursive:true,mode:0o700});
  if(isWindows){
   progress('flash',{message:'Autorización de Windows para grabar USB…'});
   const ps1Path=app.isPackaged?path.join(ROOT,'flash-windows.ps1'):path.join(__dirname,'flash-windows.ps1');
   const output=await flashWindows({image:prepared,disk,directory:reportDir,writer:ps1Path,run});
   let result;for(const line of output.trim().split('\n')){try{const val=JSON.parse(line);if(typeof val.ok==='boolean')result=val;}catch{}}
   if(!result?.ok||!result.verified)throw new Error(result?.error||'La grabación en Windows no devolvió una lectura verificada.');
   return {verified:true,backupVerified:false,device:disk.device,serial:disk.serial,...(preparedReceipt?{prepared:preparedReceipt}:{})};
  }
  progress('flash',{message:'Autorización de Linux para grabar…'});
  const args=['/usr/bin/python3','-I',path.join(ROOT,'scripts','flash-usb.py'),prepared.path,disk.device,'--serial',disk.serial,'--sha256',prepared.sha256,'--report-dir',reportDir,'--confirm','FLASH:'+disk.serial];
  if(backupDir)args.push('--backup-dir',backupDir);
  const output=await run('/usr/bin/pkexec',args,null,{timeout:4*60*60*1000,limit:4*1024*1024,phase:'flash'});
  let result;for(const line of output.trim().split('\n')){try{const value=JSON.parse(line);if(typeof value.ok==='boolean')result=value;}catch{}}
  if(!result?.ok||!result.verified)throw new Error(result?.error||'La grabación no devolvió una lectura verificada. Revisa el USB antes de intentarlo de nuevo.');
  return {verified:true,backupVerified:result.backup_verified===true,device:disk.device,serial:disk.serial,...(preparedReceipt?{prepared:preparedReceipt}:{})};
 }));
}
app.whenReady().then(async()=>{uiLanguage=i18n.language(core.LOCALE_CATALOG,app.getLocale?.()||'es');try{const preference=JSON.parse(await fs.promises.readFile(path.join(app.getPath('userData'),'ui-language.json'),'utf8'));uiLanguage=i18n.language(core.LOCALE_CATALOG,preference.language);}catch{}installIPC();win=new BrowserWindow({width:1240,height:880,minWidth:960,minHeight:700,title:'LA AGUJA Flash Imager',backgroundColor:'#0e1220',icon:path.join(__dirname,'ui/assets/icon.png'),webPreferences:{preload:path.join(__dirname,'preload.cjs'),contextIsolation:true,sandbox:true,nodeIntegration:false,webSecurity:true}});win.removeMenu();win.webContents.setWindowOpenHandler(()=>({action:'deny'}));win.webContents.on('will-navigate',(event,url)=>{if(url!==win.webContents.getURL())event.preventDefault();});win.webContents.on('will-attach-webview',event=>event.preventDefault());win.loadFile(path.join(__dirname,'ui/index.html'));});
app.on('window-all-closed',()=>{selectedImage=null;prepared=null;approvedImports={};app.quit();});
