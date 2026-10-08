'use strict';
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),crypto=require('node:crypto'),toml=require('@iarna/toml');
const provisioning=require('./provisioning.cjs'),{powershellArgs,windowsPowerShell}=require('./ai-tools.cjs');
const AUTH={codex:'.codex/auth.json',antigravity:'.gemini/antigravity-cli/antigravity-oauth-token'};
const PRIVATE_ERROR='No se pudo leer la sesión del Administrador de credenciales. Abre el Imager con el mismo usuario de Windows que inició sesión en el CLI y vuelve a comprobar.';
function codexHome(options){return options.configDirectory||options.env?.CODEX_HOME||path.join(options.home||os.homedir(),'.codex');}
function codexStoreKey(home,realpath=fs.realpathSync.native){
 let canonical;try{canonical=realpath(home);if(!canonical.startsWith('\\\\?\\'))canonical=canonical.startsWith('\\\\')?'\\\\?\\UNC\\'+canonical.slice(2):'\\\\?\\'+canonical;}catch{canonical=home;}
 return crypto.createHash('sha256').update(canonical).digest('hex').slice(0,16);
}
async function readCredential(run,request,env=process.env){
 let result;try{const script=fs.readFileSync(path.join(__dirname,'windows-credentials.ps1'),'utf8');result=JSON.parse((await run(windowsPowerShell(env),powershellArgs(script),request,{env,timeout:15000,limit:1024*1024})).replace(/^\ufeff/,''));}catch{throw new Error(PRIVATE_ERROR);}
 if(result?.status==='missing')return null;
 if(result?.status!=='found'||typeof result.blob!=='string'||result.blob.length>700000||! /^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(result.blob))throw new Error(PRIVATE_ERROR);
 return Buffer.from(result.blob,'base64');
}
function decodeBlob(raw,provider){
 // Rust keyring-rs set_password stores UTF-16LE without a BOM. Go uses UTF-8.
 return provider==='codex'?raw.toString('utf16le'):provisioning.decodeNative(raw);
}
function authBuffer(provider,value){
 let data;try{data=JSON.parse(value);}catch{throw new Error('La sesión nativa contiene un formato de autenticación no válido.');}
 if(provider==='antigravity'){
  if(!data||typeof data!=='object')throw new Error('La sesión Antigravity no es válida.');
  // Native keyring also stores project/region/tier metadata; export only OAuth.
  data={token:data.token&&Object.fromEntries(['access_token','refresh_token','token_type','expiry'].map(key=>[key,data.token[key]])),auth_method:data.auth_method,id_token:data.id_token};
 }
 if(provider==='codex'&&!(typeof data?.OPENAI_API_KEY==='string'&&data.OPENAI_API_KEY||typeof data?.tokens?.access_token==='string'&&data.tokens.access_token))throw new Error('No hay autenticación Codex en la entrada nativa.');
 return provisioning.sanitize(provider,AUTH[provider],Buffer.from(JSON.stringify(data)));
}
function readLocalFile(filename){
 const parsed=path.parse(filename);let parent=parsed.root;
 for(const part of filename.slice(parsed.root.length).split(path.sep)){parent=path.join(parent,part);const info=fs.lstatSync(parent);if(info.isSymbolicLink())throw new Error('El perfil nativo no puede ser un enlace.');}
 const before=fs.lstatSync(filename);if(!before.isFile()||before.size>512*1024)throw new Error('El perfil nativo no es válido.');
 const fd=fs.openSync(filename,'r');try{const info=fs.fstatSync(fd);if(info.ino!==before.ino||info.size!==before.size||info.dev!==before.dev)throw Error();return fs.readFileSync(fd);}finally{fs.closeSync(fd);}
}
async function decryptCodexAge(ciphertext,passphrase){
 try {
  // Bound scrypt memory/CPU for an untrusted profile; Codex uses age's scrypt
  // recipient, never an Imager-specific cipher. Authentication tags are checked.
  const header=ciphertext.subarray(0,1024).toString('ascii');const stanza=header.match(/^-> scrypt [A-Za-z0-9+/]+ (\d+)\r?$/m);
  if(!stanza||Number(stanza[1])>20)throw Error();
  const {Decrypter}=await import('age-encryption');const d=new Decrypter();d.addPassphrase(passphrase);
  const plaintext=await d.decrypt(ciphertext);try{const data=JSON.parse(Buffer.from(plaintext).toString('utf8'));if(![0,1].includes(data.version)||typeof data.secrets?.['global/CODEX_AUTH']!=='string')throw Error();return authBuffer('codex',data.secrets['global/CODEX_AUTH']);}finally{plaintext.fill(0);}
 }catch{throw new Error('No se pudo descifrar la sesión nativa de Codex. No se ha modificado el perfil original.');}
}
async function discover(provider,options={},dependencies={}){
 if((dependencies.platform||process.platform)!=='win32')return provisioning.discover(provider,options);
 if(!Object.hasOwn(provisioning.IMPORTS,provider))throw new Error('Proveedor no válido.');
 const portable=provisioning.discover(provider,options);
 if(!AUTH[provider])return portable; // Claude/OpenCode use their native auth files.
 // A manually chosen Antigravity folder explicitly requests portable file auth.
 if(provider==='antigravity'&&options.configDirectory)return portable;
 const reader=dependencies.readCredential||((request)=>readCredential(dependencies.run,request,options.env));
 let auth=null;
 if(provider==='antigravity'){
  const blob=await reader({provider});if(blob)try{auth=authBuffer(provider,decodeBlob(blob,provider));}finally{blob.fill(0);}
 }else{
  const home=codexHome(options);let config={};const settings=path.join(home,'config.toml');
  if(fs.existsSync(settings))try{config=toml.parse(provisioning.decodeNative(readLocalFile(settings)));}catch{throw new Error('La configuración nativa de Codex no es válida.');}
  const mode=config.cli_auth_credentials_store||'file';
  if(mode==='file')return portable;
  if(mode==='ephemeral')throw new Error('Codex usa una sesión efímera: no hay credenciales persistidas para importar.');
  if(!['auto','keyring'].includes(mode))throw new Error('El almacén de autenticación de Codex no es válido.');
  const key=codexStoreKey(home,dependencies.realpath);const encrypted=path.join(home,'secrets','codex_auth.age');
  // Prefer the explicitly selected backend; older Codex versions use direct
  // keyring storage. Never import another namespace (MCP/general secrets).
  const useAge=config.features?.secret_auth_storage===true||(config.features?.secret_auth_storage!==false&&fs.existsSync(encrypted));
  if(useAge&&!fs.existsSync(encrypted))return mode==='auto'?portable:{portable:false,paths:[],summary:'No se encontró el perfil cifrado de Codex en el almacén seleccionado.'};
  try{
   const target=useAge?'secrets|'+key+'.codex':'cli|'+key+'.Codex Auth';const blob=await reader({provider,target});
   if(blob)try{auth=useAge?await decryptCodexAge(readLocalFile(encrypted),decodeBlob(blob,provider)):authBuffer(provider,decodeBlob(blob,provider));}finally{blob.fill(0);}
  }catch(error){if(mode!=='auto'||!portable.portable)throw error;}
  if(!auth&&mode==='keyring')return {portable:false,paths:[],summary:'No se encontró la sesión de Codex en el almacén seleccionado de este usuario.'};
 }
 if(!auth)return portable;
 const settings=provisioning.locations(provider,options).filter(item=>provisioning.IMPORTS[provider][item.target]!=='auth').filter(item=>{try{provisioning.readNative(provider,item);return true;}catch{return false;}});
 return {portable:true,paths:[{target:AUTH[provider],credential:auth},...settings],summary:'Sesión del Administrador de credenciales importada; su vigencia se comprobará en Aguja.'};
}
function clear(items){for(const item of items||[])if(Buffer.isBuffer(item.credential))item.credential.fill(0);}
module.exports={discover,readCredential,codexStoreKey,authBuffer,decryptCodexAge,clear};
