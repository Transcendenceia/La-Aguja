'use strict';
// Native CLI installation and launch. No credential ever enters an argument or log.
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),crypto=require('node:crypto');
const core=require('./core.cjs');
const PROVIDERS=Object.freeze({codex:{bin:'codex',name:'Codex',package:'@openai/codex',login:['login','--device-auth'],docs:'https://learn.chatgpt.com/docs/codex/cli'},antigravity:{bin:'agy',name:'Antigravity',login:[],docs:'https://antigravity.google/docs/cli/install/'},claude:{bin:'claude',name:'Claude Code',package:'@anthropic-ai/claude-code',login:['auth','login'],docs:'https://code.claude.com/docs/en/setup'},opencode:{bin:'opencode',name:'OpenCode',package:'opencode-ai',login:['auth','login'],docs:'https://opencode.ai/docs/'}});
function provider(id){if(!Object.hasOwn(PROVIDERS,id))throw new Error('Proveedor no válido.');return PROVIDERS[id];}
const psQuote=s=>"'"+String(s).replace(/'/g,"''")+"'";
function networkError(error){
 // Errors can contain private URLs/headers in message, stack and cause. Read
 // only bounded, whitelisted codes (including Node's AggregateError causes).
 const codes=new Set(),seen=new Set(),queue=[error];let networkFailure=false;
 for(let count=0;queue.length&&count<32;count++){
  const item=queue.shift();if(!item||typeof item!=='object'||seen.has(item))continue;seen.add(item);
  if(['EACCES','EPERM','ENOTFOUND','EAI_AGAIN','ETIMEDOUT','UND_ERR_CONNECT_TIMEOUT','ECONNREFUSED','ECONNRESET','CERT_HAS_EXPIRED','DEPTH_ZERO_SELF_SIGNED_CERT','UNABLE_TO_VERIFY_LEAF_SIGNATURE'].includes(item.code))codes.add(item.code);
  if(item.name==='TimeoutError')codes.add('ETIMEDOUT');
  if(item.message==='fetch failed')networkFailure=true;
  if(item.cause)queue.push(item.cause);if(Array.isArray(item.errors))queue.push(...item.errors.slice(0,8));
 }
 let message;
 if(codes.has('EACCES')||codes.has('EPERM'))message='El sistema ha denegado la conexión HTTPS para descargar la herramienta. Revisa los permisos de red de esta VM/equipo; puedes seguir preparando una imagen local.';
 else if(codes.has('ENOTFOUND')||codes.has('EAI_AGAIN'))message='No se pudo resolver el servidor de descarga de la herramienta. Comprueba la conexión y el DNS; puedes seguir preparando una imagen local.';
 else if(codes.has('ETIMEDOUT')||codes.has('UND_ERR_CONNECT_TIMEOUT'))message='La conexión HTTPS de descarga de la herramienta tardó demasiado. Comprueba la red y vuelve a intentarlo; puedes seguir preparando una imagen local.';
 else if(['CERT_HAS_EXPIRED','DEPTH_ZERO_SELF_SIGNED_CERT','UNABLE_TO_VERIFY_LEAF_SIGNATURE'].some(code=>codes.has(code)))message='No se pudo verificar el certificado HTTPS de descarga de la herramienta. Comprueba la fecha y la configuración de red; no se ha desactivado la verificación TLS.';
 else if(codes.size||networkFailure)message='No se pudo establecer la conexión HTTPS para descargar la herramienta. Comprueba la red y vuelve a intentarlo; puedes seguir preparando una imagen local.';
 return message?new Error(message):error;
}
async function networkOperation(operation){try{return await operation();}catch(error){throw networkError(error);}}
async function* networkBody(body){const iterator=body[Symbol.asyncIterator]();try{while(true){const next=await networkOperation(()=>iterator.next());if(next.done)return;yield next.value;}}finally{try{await iterator.return?.();}catch{}}}
function powershellArgs(script,{visible=false}={}){
 // Direct spawn passes the script as one argv element: no shell quoting or
 // policy override is needed for inline queries. The visible console broker
 // still needs encoding to cross Start-Process's single ArgumentList string.
 return visible?['-NoProfile','-NoExit','-EncodedCommand',Buffer.from(script,'utf16le').toString('base64')]:['-NoProfile','-NonInteractive','-Command',script];
}
function invocation(binary,args=[],{env=process.env,home=os.homedir(),platform=process.platform,node=null}={}){
 if(platform!=='win32'||! /\.(cmd|bat)$/i.test(binary))return {command:binary,args};
 // npm shims are launched via Node, not cmd.exe string interpolation.
 const dir=path.dirname(binary),base=path.basename(binary,path.extname(binary));
 const packages={codex:['@openai/codex','bin/codex.js'],claude:['@anthropic-ai/claude-code','cli.js'],opencode:['opencode-ai','bin/opencode'],npm:['npm','bin/npm-cli.js']};
 const item=packages[base];if(item){
  const packageRoot=path.join(dir,'node_modules',item[0]);let relative=item[1];
  // npm packages can change from JS launchers to native binaries. Read their
  // declared entry point and bypass cmd.exe shims, including in paths with &.
  try{const metadata=JSON.parse(fs.readFileSync(path.join(packageRoot,'package.json'),'utf8'));relative=typeof metadata.bin==='string'?metadata.bin:metadata.bin?.[base]||relative;}catch{}
  const entry=path.resolve(packageRoot,relative);
  if(entry.startsWith(path.resolve(packageRoot)+path.sep)&&fs.existsSync(entry)){
   if(/\.exe$/i.test(entry))return {command:entry,args};
   const runtime=node||core.resolveProviderBinary('node',{env,home,platform});if(runtime)return {command:runtime,args:[entry,...args]};
  }
 }
 return {command:windowsPowerShell(env),args:powershellArgs('$ErrorActionPreference="Stop"; & '+[binary,...args].map(psQuote).join(' ')+'; if($LASTEXITCODE){exit $LASTEXITCODE}')};
}
function windowsPowerShell(env=process.env){return path.win32.join(env.SystemRoot||env.WINDIR||'C:\\Windows','System32','WindowsPowerShell','v1.0','powershell.exe');}
async function openWindowsLoginTerminal(launch,{env=process.env,cwd=os.homedir(),name='CLI',run}){
 // The invisible broker must not be the login process. Direct spawn with
 // stdio:'ignore' gives the CLI NUL handles, even if a console window appears.
 // Start-Process creates a separate console with its own interactive handles.
 const script='$ErrorActionPreference="Stop"; [Console]::OutputEncoding=[Text.UTF8Encoding]::new($false); $OutputEncoding=[Console]::OutputEncoding; $Host.UI.RawUI.WindowTitle='+psQuote('LA AGUJA · Iniciar sesión · '+name)+'; & '+[launch.command,...launch.args].map(psQuote).join(' ');
 const args=powershellArgs(script,{visible:true}).join(' ');
 const broker='$ErrorActionPreference="Stop"; $p=Start-Process -FilePath '+psQuote(windowsPowerShell(env))+' -ArgumentList '+psQuote(args)+' -WorkingDirectory '+psQuote(cwd)+' -WindowStyle Normal -PassThru; @{launched=$true;pid=$p.Id}|ConvertTo-Json -Compress';
 try{const response=JSON.parse((await run(windowsPowerShell(env),powershellArgs(broker),null,{env,timeout:15000})).trim());if(response.launched!==true||!Number.isInteger(response.pid)||response.pid<=0)throw Error();return {launched:true,pid:response.pid};}
 catch{throw new Error('No se pudo abrir el terminal de Windows para iniciar sesión.');}
}
class AITools{
 constructor({directory,run,progress=()=>{},platform=process.platform,home=os.homedir(),env=process.env,arch=process.arch}){Object.assign(this,{directory,run,progress,platform,home,arch});this.env={...env};this.root=path.join(directory,'ai-tools');}
 prefix(){return path.join(this.root,'npm');}
 environment(){const delimiter=this.platform==='win32'?';':':';const nodeDirs=fs.existsSync(this.root)?fs.readdirSync(this.root).filter(n=>/^node-v\d+/.test(n)).map(n=>path.join(this.root,n,this.platform==='win32'?'':'bin')):[];const env={...this.env};if(this.platform==='win32')for(const key of Object.keys(env))if(key.toLowerCase()==='path')delete env[key];return {...env,PATH:[path.join(this.root,'agy'),this.platform==='win32'?this.prefix():path.join(this.prefix(),'bin'),...nodeDirs,this.env.PATH||this.env.Path||''].join(delimiter)};}
 resolve(id){return core.resolveProviderBinary(provider(id).bin,{env:this.environment(),home:this.home,platform:this.platform});}
 status(){return Object.fromEntries(Object.keys(PROVIDERS).map(id=>[id,{installed:Boolean(this.resolve(id)),name:provider(id).name}]));}
 async execute(binary,args,options={}){const env=this.environment(),call=invocation(binary,args,{env,home:this.home,platform:this.platform});return this.run(call.command,call.args,null,{...options,env});}
 async download(url,dest,max=100*1024**2){
  if(new URL(url).protocol!=='https:')throw new Error('La descarga de la herramienta requiere HTTPS.');
  const response=await networkOperation(()=>fetch(url,{signal:AbortSignal.timeout(10*60*1000),redirect:'error'}));if(!response.ok)throw new Error('No se pudo descargar la herramienta oficial.');
  const handle=await fs.promises.open(dest,'wx',0o600);let size=0;try{for await(const chunk of networkBody(response.body)){size+=chunk.length;if(size>max)throw new Error('La descarga de la herramienta es demasiado grande.');await handle.writeFile(Buffer.from(chunk));}}finally{await handle.close();}return dest;
 }
 async nodeRuntime(){
  // Use existing Node/npm only when both exist and Node meets the CLI minimum.
  const env=this.environment(),node=core.resolveProviderBinary('node',{env,home:this.home,platform:this.platform}),npm=core.resolveProviderBinary('npm',{env,home:this.home,platform:this.platform});
  if(node&&npm){try{const version=await this.run(node,['--version'],null,{timeout:15000,env});if(Number(version.trim().match(/^v(\d+)/)?.[1])>=22)return {node,npm};}catch{}}
  this.progress('cli',{message:'Descargando el runtime oficial de Node.js…'});
  if(!['linux','win32'].includes(this.platform)||!['x64','arm64'].includes(this.arch))throw new Error('Plataforma no compatible con la instalación de esta herramienta.');
  const base='https://nodejs.org/dist/latest-v22.x/';
  const response=await networkOperation(()=>fetch(base+'SHASUMS256.txt',{redirect:'error',signal:AbortSignal.timeout(30000)}));if(!response.ok)throw new Error('No se pudo comprobar el runtime oficial.');
  const sums=await networkOperation(()=>response.text());if(sums.length>65536)throw new Error('La respuesta de la herramienta no es válida.');
  const pattern=new RegExp('^([a-f0-9]{64})\\s+(node-v22\\.[0-9]+\\.[0-9]+-'+(this.platform==='win32'?'win':'linux')+'-'+this.arch+'\\.'+(this.platform==='win32'?'zip':'tar.xz')+')$','m');
  const match=sums.match(pattern);if(!match)throw new Error('No hay runtime oficial compatible.');
  const folder=match[2].replace(/\.(zip|tar\.xz)$/,''),dest=path.join(this.root,folder),nodePath=path.join(dest,this.platform==='win32'?'node.exe':'bin/node'),npmPath=path.join(dest,this.platform==='win32'?'npm.cmd':'bin/npm');
  if(fs.existsSync(nodePath)&&fs.existsSync(npmPath))return {node:nodePath,npm:npmPath};
  const stage=await fs.promises.mkdtemp(path.join(this.root,'.node-'));try{
   const archive=await this.download(base+match[2],path.join(stage,match[2]));const digest=await core.hashFile(archive);if(digest.sha256!==match[1])throw new Error('El SHA-256 del runtime no coincide.');
   if(this.platform==='win32')await this.run(windowsPowerShell(this.env),powershellArgs('$ErrorActionPreference="Stop"; Expand-Archive -LiteralPath '+psQuote(archive)+' -DestinationPath '+psQuote(stage)),null,{timeout:120000});
   else await this.run('/usr/bin/tar',['-xJf',archive,'-C',stage],null,{timeout:120000});
   await fs.promises.rename(path.join(stage,folder),dest);
  }finally{await fs.promises.rm(stage,{recursive:true,force:true});}
  return {node:nodePath,npm:npmPath};
 }
 async install(id){
  const p=provider(id);if(this.resolve(id))return {installed:true,alreadyInstalled:true};
  await fs.promises.mkdir(this.root,{recursive:true,mode:0o700});
  this.progress('cli',{message:'Descargando e instalando '+p.name+'…'});
  if(id==='antigravity'){
   if(!['linux','win32'].includes(this.platform)||!['x64','arm64'].includes(this.arch))throw new Error('Plataforma no compatible con esta herramienta.');
   const platform=(this.platform==='win32'?'windows':'linux')+'_'+(this.arch==='x64'?'amd64':'arm64')+(this.platform==='linux'&&(fs.existsSync('/lib/libc.musl-x86_64.so.1')||fs.existsSync('/lib/libc.musl-aarch64.so.1'))?'_musl':'');
   const manifest=await networkOperation(()=>core.getHTTPS('https://antigravity-cli-auto-updater-974169037036.us-central1.run.app/manifests/'+platform+'.json'));
   core.httpsURL(manifest.url);if(!/^[a-f0-9]{128}$/.test(manifest.sha512||''))throw new Error('El catálogo de la herramienta no es válido.');
   const stage=await fs.promises.mkdtemp(path.join(this.root,'.agy-'));try{
    const archive=await this.download(manifest.url,path.join(stage,'payload'),512*1024**2);
    const digest=crypto.createHash('sha512');for await(const chunk of fs.createReadStream(archive))digest.update(chunk);if(digest.digest('hex')!==manifest.sha512)throw new Error('El SHA-512 de la herramienta no coincide.');
    let binary=archive;if(manifest.url.endsWith('.tar.gz')){await this.run('/usr/bin/tar',['-xzf',archive,'-C',stage,'antigravity'],null,{timeout:120000});binary=path.join(stage,'antigravity');}
    const directory=path.join(this.root,'agy');await fs.promises.mkdir(directory,{recursive:true,mode:0o700});const dest=path.join(directory,this.platform==='win32'?'agy.exe':'agy');await fs.promises.copyFile(binary,dest,fs.constants.COPYFILE_EXCL);if(this.platform!=='win32')await fs.promises.chmod(dest,0o700);
   }finally{await fs.promises.rm(stage,{recursive:true,force:true});}
  }else{
   const runtime=await this.nodeRuntime();const call=invocation(runtime.npm,['install','--global','--prefix',this.prefix(),'--registry=https://registry.npmjs.org','--no-audit','--no-fund',p.package+'@latest'],{platform:this.platform,node:runtime.node,env:this.environment(),home:this.home});
   await this.run(call.command,call.args,null,{timeout:15*60*1000,env:this.environment()});
  }
  const binary=this.resolve(id);if(!binary)throw new Error('La herramienta se descargó, pero no se encontró su ejecutable. Reintenta la comprobación.');
  await this.execute(binary,['--version'],{timeout:30000});return {installed:true};
 }
 loginCommand(id){const p=provider(id),binary=this.resolve(id);if(!binary)throw new Error('Instala primero el CLI oficial de este proveedor.');return invocation(binary,p.login,{platform:this.platform,env:this.environment(),home:this.home});}
}
module.exports={AITools,PROVIDERS,provider,psQuote,powershellArgs,windowsPowerShell,openWindowsLoginTerminal,invocation,networkError};
