'use strict';
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),crypto=require('node:crypto'),toml=require('@iarna/toml');
const core=require('./core.cjs'),fat32=require('./fat32-writer.cjs'),jsonc=require('jsonc-parser');
const storage=require('./image-storage.cjs');
const IMPORTS=Object.freeze({codex:{'.codex/auth.json':'auth','.codex/config.toml':'codex-settings'},claude:{'.claude/.credentials.json':'auth','.claude/settings.json':'claude-settings','.claude.json':'claude-onboarding'},antigravity:{'.gemini/antigravity-cli/antigravity-oauth-token':'auth','.gemini/antigravity-cli/settings.json':'antigravity-settings'},opencode:{'.local/share/opencode/auth.json':'auth','.config/opencode/opencode.json':'opencode-settings'}});
function text(v,max=8192){if(typeof v!=='string'||Buffer.byteLength(v)>max||/[\0\r\n]/.test(v))throw new Error('Configuración privada no válida.');return v;}
function endpoint(v){const u=core.httpsURL(text(v,2048));if(u.search)throw new Error('Configuración privada no válida.');return v;}
function decodeNative(raw){
 // PowerShell and Windows editors may write BOM-marked UTF-8 or UTF-16.
 // Decode data in memory, normalize the portable output to UTF-8.
 if(raw[0]===0xff&&raw[1]===0xfe)return raw.subarray(2).toString('utf16le');
 if(raw[0]===0xfe&&raw[1]===0xff){const copy=Buffer.from(raw.subarray(2));if(copy.length%2)throw new Error('Archivo de configuración privada no válido.');copy.swap16();return copy.toString('utf16le');}
 return raw.toString('utf8').replace(/^\ufeff/,'');
}
function sanitize(provider,filename,raw){
 const kind=IMPORTS[provider]?.[filename];if(!kind||raw.length>512*1024)throw new Error('Archivo de configuración privada no permitido.');
 let data;try{const decoded=decodeNative(raw);if(kind==='codex-settings')data=toml.parse(decoded);else if(kind==='opencode-settings'){const errors=[];data=jsonc.parse(decoded,errors,{allowTrailingComma:true});if(errors.length)throw Error();}else data=JSON.parse(decoded);}catch{throw new Error('Archivo de configuración privada no válido.');}
 if(!data||typeof data!=='object'||Array.isArray(data))throw new Error('Archivo de configuración privada no válido.');
 if(kind==='codex-settings'){
  const clean={};for(const k of ['model','model_reasoning_effort','model_provider'])if(k in data)clean[k]=text(data[k],256);clean.cli_auth_credentials_store='file';
  for(const [name,item]of Object.entries(data.model_providers||{})){if(!/^[a-zA-Z0-9_-]{1,64}$/.test(name)||!item||typeof item!=='object')throw new Error('Configuración privada Codex no válida.');const out={};for(const k of ['name','base_url','wire_api','env_key','requires_openai_auth'])if(k in item){if(k==='requires_openai_auth'){if(typeof item[k]!=='boolean')throw new Error('Configuración privada Codex no válida.');out[k]=item[k];}else out[k]=text(item[k],2048);}if(out.base_url)endpoint(out.base_url);(clean.model_providers||={})[name]=out;}
  return Buffer.from(toml.stringify(clean));
 }
 if(kind==='auth'){
  if(!Object.keys(data).length)throw new Error('No hay autenticación portable en este archivo.');
  if(provider==='antigravity'){
   if(Object.keys(data).sort().join(',')!=='auth_method,id_token,token'||!data.token||typeof data.token!=='object'||Object.keys(data.token).sort().join(',')!=='access_token,expiry,refresh_token,token_type')throw new Error('Autenticación privada Antigravity no válida.');
   for(const v of [...Object.values(data.token),data.auth_method,data.id_token])if(!text(v,32768))throw new Error('Autenticación privada Antigravity no válida.');
   if(!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(data.token.expiry)||!Number.isFinite(Date.parse(data.token.expiry)))throw new Error('Autenticación privada Antigravity no válida.');
  }
 }else{
  const keys={'claude-settings':['model','language','effortLevel'],'claude-onboarding':['hasCompletedOnboarding','oauthAccount'],'antigravity-settings':['model'],'opencode-settings':['model','small_model','theme']}[kind];
  data=Object.fromEntries(Object.entries(data).filter(([k])=>keys.includes(k)));if(kind==='antigravity-settings'&&'model' in data)text(data.model,256);
 }
 return Buffer.from(JSON.stringify(data));
}
function locations(provider,{home=os.homedir(),env=process.env,configDirectory}={}){
 if(!Object.hasOwn(IMPORTS,provider))throw new Error('Proveedor no válido.');
 const defaults=Object.keys(IMPORTS[provider]).map(target=>({target,source:path.join(home,...target.split('/'))}));
 return defaults.map(item=>{
  const suffix=path.basename(item.source);
  if(configDirectory){if(!path.isAbsolute(configDirectory))throw new Error('La carpeta del perfil debe ser absoluta.');item.source=path.join(configDirectory,suffix);return item;}
  if(provider==='codex'&&env.CODEX_HOME)item.source=path.join(path.resolve(env.CODEX_HOME),suffix);
  if(provider==='claude'&&env.CLAUDE_CONFIG_DIR)item.source=path.join(path.resolve(env.CLAUDE_CONFIG_DIR),item.target==='.claude.json'?'.claude.json':suffix);
  if(provider==='opencode'){
   if(item.target.startsWith('.local/share/')&&env.XDG_DATA_HOME)item.source=path.join(path.resolve(env.XDG_DATA_HOME),'opencode',suffix);
   if(item.target.startsWith('.config/')&&env.XDG_CONFIG_HOME)item.source=path.join(path.resolve(env.XDG_CONFIG_HOME),'opencode',suffix);
   if(item.target.endsWith('opencode.json')&&env.OPENCODE_CONFIG)item.source=path.resolve(env.OPENCODE_CONFIG);
   else if(item.target.endsWith('opencode.json')&&env.OPENCODE_CONFIG_DIR)item.source=path.join(path.resolve(env.OPENCODE_CONFIG_DIR),suffix);
  }return item;
 });
}
function readNative(provider,item){
 if(!Object.hasOwn(IMPORTS[provider]||{},item.target)||!path.isAbsolute(item.source))throw new Error('Ruta de configuración privada no válida.');
 const parsed=path.parse(item.source);let parent=parsed.root;
 for(const part of item.source.slice(parsed.root.length).split(path.sep).slice(0,-1)){parent=path.join(parent,part);const s=fs.lstatSync(parent);if(s.isSymbolicLink()||!s.isDirectory())throw new Error('Ruta de configuración privada no válida.');}
 const before=fs.lstatSync(item.source);if(!before.isFile()||before.isSymbolicLink()||before.size>512*1024)throw new Error('Archivo de configuración privada no válido.');
 if(process.platform!=='win32'){
  if(before.uid!==process.getuid())throw new Error('Archivo de configuración privada no permitido.');
  if(provider==='antigravity'&&IMPORTS[provider][item.target]==='auth'&&(before.mode&0o177||!(before.mode&0o400)))throw new Error('Permisos de configuración privada no válidos.');
 }
 const fd=fs.openSync(item.source,fs.constants.O_RDONLY|(fs.constants.O_NOFOLLOW||0));try{const info=fs.fstatSync(fd);if(info.ino!==before.ino||info.dev!==before.dev||info.size!==before.size||!info.isFile())throw new Error('El archivo de configuración privada cambió.');const raw=fs.readFileSync(fd);return sanitize(provider,item.target,raw);}finally{fs.closeSync(fd);}
}
function discover(provider,options){const paths=[];for(const item of locations(provider,options)){let selected=item;try{readNative(provider,selected);}catch{if(item.target.endsWith('opencode.json')&&item.source.endsWith('.json')&&!options?.env?.OPENCODE_CONFIG){selected={...item,source:item.source+'c'};try{readNative(provider,selected);}catch{continue;}}else continue;}paths.push(selected);}
 const portable=paths.some(p=>IMPORTS[provider][p.target]==='auth');return {portable,paths:portable?paths:[],summary:portable?'Credenciales nativas seleccionadas; su vigencia se comprobará en Aguja.':'No hay una sesión nativa portable válida. Inicia sesión en este PC o usa una clave API.'};
}
function windowsCandidates(provider,options={}){
 if(options.configDirectory)return [options];
 const home=options.home||os.homedir(),env=options.env||process.env,candidates=[{...options,home,env}];
 // Location overrides can survive a moved profile or an old Explorer process.
 // Try both the configured location and conventional roots of this user.
 const roots=[home,env.USERPROFILE,env.HOME,env.HOMEDRIVE&&env.HOMEPATH?env.HOMEDRIVE+env.HOMEPATH:null].filter(p=>typeof p==='string'&&path.isAbsolute(p));
 const clean={...env};for(const key of ['CODEX_HOME','CLAUDE_CONFIG_DIR','XDG_DATA_HOME','XDG_CONFIG_HOME','OPENCODE_CONFIG','OPENCODE_CONFIG_DIR'])delete clean[key];
 for(const root of new Set(roots))candidates.push({...options,home:root,env:clean});
 const directories={codex:['.codex'],claude:['.claude'],antigravity:['.gemini/antigravity-cli','.gemini/antigravity'],opencode:['.local/share/opencode','.config/opencode']}[provider];
 for(const root of new Set(roots))for(const relative of directories||[])candidates.push({...options,home:root,env:clean,configDirectory:path.join(root,...relative.split('/'))});
 for(const root of [env.APPDATA,env.LOCALAPPDATA].filter(p=>typeof p==='string'&&path.isAbsolute(p)))for(const name of {codex:['codex'],claude:['Claude','claude'],antigravity:['antigravity-cli'],opencode:['opencode']}[provider]||[])candidates.push({...options,home,env:clean,configDirectory:path.join(root,name)});
 const seen=new Set();return candidates.filter(o=>{const key=JSON.stringify(locations(provider,o).map(i=>i.source)).toLowerCase();if(seen.has(key))return false;seen.add(key);return true;});
}
function materialize(capsule,approved){const c=structuredClone(capsule);for(const [id,p]of Object.entries(c.providers))if(p.mode==='import'){
 const items=approved[id];if(!Array.isArray(items)||!items.some(i=>IMPORTS[id]?.[i.target]==='auth'))throw new Error('Importa primero una sesión nativa portable de '+id+'.');
 const files={};for(const item of items)files[item.target]=(Buffer.isBuffer(item.credential)?sanitize(id,item.target,item.credential):readNative(id,item)).toString('base64url');p.files=files;delete p.import_paths;
 }return c;
}
function seal(capsule,protection={mode:'plain'}){
 const raw=Buffer.from(JSON.stringify(capsule));if(raw.length>4*1024**2)throw new Error('El perfil privado es demasiado grande.');
 if(protection.mode==='plain')return Buffer.from(JSON.stringify({format:'aguja-profile',schema:1,protection:'plain',capsule}));
 if(protection.mode!=='encrypted'||text(protection.passphrase,1024).length<1)throw new Error('La contraseña del perfil necesita entre 1 y 1024 caracteres.');
 const salt=crypto.randomBytes(16),iv=crypto.randomBytes(12),key=crypto.scryptSync(protection.passphrase,salt,32,{N:32768,r:8,p:1,maxmem:64*1024**2});
 try{const cipher=crypto.createCipheriv('aes-256-gcm',key,iv);cipher.setAAD(Buffer.from('aguja-profile:1'));const data=Buffer.concat([cipher.update(raw),cipher.final(),cipher.getAuthTag()]);return Buffer.from(JSON.stringify({format:'aguja-profile',schema:1,protection:'encrypted',kdf:'scrypt-32768-8-1',salt:salt.toString('base64url'),iv:iv.toString('base64url'),data:data.toString('base64url')}));}finally{key.fill(0);}
}
function releaseMarker(image){const fd=fs.openSync(image,'r');try{const part=fat32.findGptPartition(fd,'AGUJA_CFG'),params=fat32.parseFat32Params(fd,part.offset);const raw=fat32.readFat32File(fd,params,'release.json');if(!raw||raw.length>65536)throw new Error();return JSON.parse(raw.toString('utf8'));}catch{throw new Error('La imagen no contiene una configuración de versión compatible.');}finally{fs.closeSync(fd);}}
function validateFeatures(image,capsule){const release=releaseMarker(image),features=release.features||[];if(!features.includes('platform-profile-v1'))throw new Error('La imagen no admite perfiles de la aplicación.');if(capsule.locale&&!features.includes('locale-profile-v1'))throw new Error('La imagen no admite idioma y teclado personalizados.');if((['zh_CN.UTF-8','ja_JP.UTF-8'].includes(capsule.locale?.language)||['cn','jp'].includes(capsule.locale?.keyboard))&&!features.includes('i18n-catalog-v1'))throw new Error('La imagen no admite este idioma o teclado.');if(capsule.providers.antigravity?.mode==='import'&&!features.includes('antigravity-oauth-file-v1'))throw new Error('La imagen no admite OAuth portable Antigravity.');if(capsule.tailscale?.enabled&&!features.includes('tailscale-profile-v1'))throw new Error('La imagen no admite alta automática Tailscale / Headscale. Descarga una imagen compatible antes de preparar el disco.');return release;}
async function prepareWindows({source,output,sha256,capsule,protection,approved={},bitlocker=null}){
 await storage.checkDestination(source,output);
 const original=await core.hashFile(source);if(original.sha256!==sha256)throw new Error('La imagen original cambió.');const release=validateFeatures(source,capsule);const publicLocale=release.features.includes('locale-preunlock-v1');if(capsule.locale&&protection.mode==='encrypted'&&!publicLocale)throw new Error('El teclado antes de desbloquear necesita Rescue Disk 0.9.7 o posterior.');
 const sealed=seal(materialize(capsule,approved),protection),temp=output+'.building-'+crypto.randomBytes(8).toString('hex');
 try{await fs.promises.copyFile(source,temp,fs.constants.COPYFILE_EXCL);if((await core.hashFile(temp)).sha256!==sha256)throw new Error('La imagen original cambió durante la copia.');fat32.writeFat32File(temp,'AGUJA_CFG','aguja-profile.json',sealed);if(publicLocale&&capsule.locale)fat32.writeFat32File(temp,'AGUJA_CFG','aguja-locale.json',Buffer.from(JSON.stringify(capsule.locale)));if(bitlocker)fat32.writeFat32File(temp,'AGUJA_CFG','bitlocker.json',Buffer.from(JSON.stringify(bitlocker)));await fs.promises.link(temp,output);}catch(e){throw storage.storageError(e);}finally{await fs.promises.unlink(temp).catch(()=>{});}
 return {profile_verified:true};
}
module.exports={IMPORTS,locations,sanitize,decodeNative,readNative,discover,windowsCandidates,materialize,seal,releaseMarker,validateFeatures,prepareWindows};
