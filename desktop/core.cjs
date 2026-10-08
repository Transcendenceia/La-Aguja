'use strict';
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const net = require('node:net');
const os = require('node:os');
const {Transform} = require('node:stream');
const {pipeline,finished} = require('node:stream/promises');
const {publicResponse}=require('./public-download.cjs');
function fail(message) { throw new Error(message); }
function httpsURL(value) {
  let u; try { u=new URL(value); } catch { fail('La dirección no es válida.'); }
  if (u.protocol !== 'https:' || u.username || u.password || u.hash || u.port && u.port !== '443') fail('Utiliza una dirección HTTPS sin credenciales.');
  return u;
}
function sha(value) { if (!/^[a-f0-9]{64}$/.test(value || '')) fail('Introduce los 64 caracteres del SHA-256.'); return value; }
async function hashFile(filename, progress=()=>{}) {
  const stat=await fs.promises.lstat(filename);
  if (stat.isSymbolicLink() || !stat.isFile()) fail('Selecciona un archivo de imagen.');
  const h=crypto.createHash('sha256'); let done=0;
  for await (const data of fs.createReadStream(filename)) { h.update(data); done+=data.length; progress({done,total:stat.size}); }
  return {sha256:h.digest('hex'),bytes:stat.size};
}
function normalizeImageSHA(value='') {
  if (typeof value!=='string') fail('Introduce los 64 caracteres del SHA-256 o deja el campo vacío.');
  const expected=value.trim().toLowerCase();
  return expected?sha(expected):'';
}
// releases must come only from verifyManifest with the packaged publication pin.
// A digest computed locally is not, by itself, authentication of its origin.
function resolveImportedImage(verified, expected='', releases=[]) {
  expected=normalizeImageSHA(expected);
  if(expected && verified.sha256!==expected) fail('El SHA-256 de la imagen no coincide. No se usará.');
  const official=releases.find(r=>r.sha256===verified.sha256 && r.bytes===verified.bytes);
  return {...verified,trusted:Boolean(official),verification:official?'verified-catalog':expected?'verified-sha':'calculated-sha',...(official?{version:official.version}:{})};
}
function verifyManifest(envelope, pin) {
  if (!pin.public_key_pem || !pin.key_id || pin.key_id==='not-configured') fail('Este paquete no incluye aún una clave de publicación. Puedes importar una imagen local; su SHA-256 se calcula automáticamente.');
  if (!envelope || envelope.key_id!==pin.key_id || typeof envelope.payload!=='string' || typeof envelope.signature!=='string') fail('La firma del catálogo no coincide con esta aplicación.');
  const raw=Buffer.from(envelope.payload,'base64');
  if (!raw.length || raw.length>65536 || !crypto.verify(null,raw,pin.public_key_pem,Buffer.from(envelope.signature,'base64'))) fail('Catálogo sin firma válida. No se descarga.');
  const manifest=JSON.parse(raw.toString('utf8'));
  if (manifest.schema!==1 || !Array.isArray(manifest.releases) || manifest.releases.length>20) fail('El catálogo no es compatible.');
  if (!manifest.expires_at || !Number.isFinite(Date.parse(manifest.expires_at)) || Date.parse(manifest.expires_at)<Date.now()) fail('El catálogo ha caducado.');
  return manifest.releases.map(r=>{
    if (!/^[0-9]+\.[0-9]+\.[0-9]+(?:[-.][a-z0-9]+)*$/.test(r.version) || !Number.isSafeInteger(r.bytes) || r.bytes<1048576 || r.bytes>64*1024**3) fail('Información de versión no válida.');
    sha(r.sha256);
    const asset=value=>{const u=httpsURL(value),github=pin.repository&&u.hostname==='github.com'&&u.pathname.startsWith('/'+pin.repository+'/releases/download/');const base=pin.image_base_url?httpsURL(pin.image_base_url):null,website=base&&u.origin===base.origin&&u.pathname.startsWith(base.pathname)&&!u.pathname.slice(base.pathname.length).includes('/');if((pin.repository||base)&&!github&&!website)fail('El catálogo debe descargar desde GitHub o la web oficial de LA AGUJA.');return u.href;};
    let parts;
    if(r.parts!==undefined){
      if(!Array.isArray(r.parts)||r.parts.length<1||r.parts.length>64)fail('Partes de imagen no válidas.');
      parts=r.parts.map(part=>{if(!Number.isSafeInteger(part.bytes)||part.bytes<1||part.bytes>=2*1024**3)fail('Tamaño de parte no válido.');return {url:asset(part.url),bytes:part.bytes,sha256:sha(part.sha256)};});
      if(parts.reduce((total,part)=>total+part.bytes,0)!==r.bytes)fail('Las partes no coinciden con el tamaño de imagen.');
    }
    return {version:r.version,...(parts?{parts}:{url:asset(r.url)}),bytes:r.bytes,sha256:r.sha256,name:'LA AGUJA '+r.version,notes:String(r.notes||'').slice(0,2000)};
  });
}
async function getHTTPS(url, maxBytes=65536, timeoutMs=20000) {
  httpsURL(url); const response=await publicResponse(url,{signal:AbortSignal.timeout(timeoutMs),accept:'application/json'});
  if (!response.ok) fail('El servidor no está disponible. Intenta de nuevo.');
  const chunks=[];let n=0; for await (const data of response.body) {n+=data.length;if(n>maxBytes)fail('Respuesta demasiado grande.');chunks.push(Buffer.from(data));}
  return JSON.parse(Buffer.concat(chunks).toString('utf8'));
}
async function downloadImage(release,destination,progress=()=>{},signal,headers={}, {idleTimeoutMs=60000}={}) {
  const parts=release.parts||[{url:release.url,bytes:release.bytes,sha256:release.sha256}];
  for(const part of parts){httpsURL(part.url);sha(part.sha256);}
  sha(release.sha256);
  if(Object.keys(headers).length)fail('Las descargas públicas no aceptan credenciales de cuenta.');
  // Bound inactivity, not total transfer time: large images may legitimately
  // need hours, but a stalled response must release the UI and private partial.
  const controller=new AbortController();let timer,timedOut=false;
  const cancel=()=>controller.abort(signal.reason);
  if(signal?.aborted)cancel();else signal?.addEventListener('abort',cancel,{once:true});
  const activity=()=>{clearTimeout(timer);timer=setTimeout(()=>{timedOut=true;controller.abort();},idleTimeoutMs);};
  const tempfile=destination+'.partial-'+crypto.randomBytes(8).toString('hex');
  let written=0;const digest=crypto.createHash('sha256');
  let output;
  try {
    output=fs.createWriteStream(tempfile,{flags:'wx',mode:0o600});
    // Install an error listener before the first network await.
    let outputError;output.on('error',error=>{outputError=error;controller.abort();});
    for(const part of parts){
      activity();
      const response=await publicResponse(part.url,{signal:controller.signal});
      if(!response.ok||!response.body)fail('No se pudo descargar la imagen.');
      activity();let count=0;const partDigest=crypto.createHash('sha256');
      const meter=new Transform({transform(chunk,encoding,callback){activity();count+=chunk.length;written+=chunk.length;if(count>part.bytes||written>release.bytes)return callback(new Error('El tamaño de la descarga no coincide.'));partDigest.update(chunk);digest.update(chunk);progress({done:written,total:release.bytes});callback(null,chunk);}});
      const body=response.body?.getReader?require('node:stream').Readable.fromWeb(response.body,{signal:controller.signal}):response.body;
      await pipeline(body,meter,output,{end:false,signal:controller.signal});
      if(outputError)throw outputError;
      if(count!==part.bytes||partDigest.digest('hex')!==part.sha256)fail('La parte descargada no coincide con su SHA-256.');
    }
    output.end();await finished(output);
    if(written!==release.bytes || digest.digest('hex')!==release.sha256) fail('La descarga no coincide con su firma. No se usará.');
    // Hard link prevents overwriting any existing destination, even if it appeared during download.
    await fs.promises.link(tempfile,destination); await fs.promises.unlink(tempfile);
    return {sha256:release.sha256,bytes:written};
  } catch(e) { controller.abort();if(output){output.destroy();await finished(output).catch(()=>{});}await fs.promises.unlink(tempfile).catch(()=>{});if(timedOut)fail('La descarga no avanzó a tiempo. Comprueba la red e intenta de nuevo.');throw e; }
  finally {clearTimeout(timer);signal?.removeEventListener('abort',cancel);}
}
function cleanText(v,max=4096) {if(typeof v!=='string'||v.length>max||/[\0\r\n]/.test(v))fail('Hay un valor de configuración no válido.');return v;}
const CATALOG_FILE=process.resourcesPath && fs.existsSync(path.join(process.resourcesPath,'aguja/runtime/locale-catalog.json')) ? path.join(process.resourcesPath,'aguja/runtime/locale-catalog.json') : path.join(__dirname,'../runtime/locale-catalog.json');
const LOCALE_CATALOG=JSON.parse(fs.readFileSync(CATALOG_FILE,'utf8'));
const LOCALE_LANGUAGES=LOCALE_CATALOG.languages.map(l=>l.value);
const LOCALE_KEYBOARDS=LOCALE_CATALOG.keyboards.map(k=>k.value);
const LOCALE_VARIANTS=Object.fromEntries(LOCALE_CATALOG.keyboards.map(k=>[k.value,k.variants]));
function validateLocale(locale) {
  if(!locale || Object.keys(locale).some(k=>!['language','keyboard','variant'].includes(k)) || !LOCALE_LANGUAGES.includes(locale.language) || !LOCALE_KEYBOARDS.includes(locale.keyboard) || !LOCALE_VARIANTS[locale.keyboard]?.includes(locale.variant))fail('Comprueba el idioma, teclado y variante seleccionados.');
  return {...locale};
}
function importedLocale({language='',keyboard='',variant=''}={}) {
  // Return only recognised settings, not command output, environment or device metadata.
  const locale={},warnings=[];
  language=String(language).replace(/\.utf-?8$/i,'.UTF-8');
  if(LOCALE_LANGUAGES.includes(language))locale.language=language;else warnings.push('El idioma de este PC no está disponible; elige uno manualmente.');
  if(LOCALE_KEYBOARDS.includes(keyboard)) {locale.keyboard=keyboard;if(LOCALE_VARIANTS[keyboard].includes(variant))locale.variant=variant;else warnings.push('La variante de este PC no está disponible; elige una manualmente.');}
  else warnings.push('No se pudo importar un teclado compatible; elige uno manualmente.');
  return {locale,warning:warnings.join(' ')};
}
function validateCapsule(input) {
  const c=structuredClone(input);
  if(!c || c.schema!==1 || !/^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/.test(c.hostname||''))fail('El nombre admite letras minúsculas, números y guiones.');
  if(c.locale!==undefined)c.locale=validateLocale(c.locale);
  const eth=c.network?.ethernet;
  if(!eth || !['auto','manual'].includes(eth.method)) fail('Elige DHCP o una dirección fija.');
  if(eth.method==='manual') {if(net.isIP(eth.address)!==4 || !Number.isInteger(eth.prefix)||eth.prefix<1||eth.prefix>32 || eth.gateway && net.isIP(eth.gateway)!==4 || !Array.isArray(eth.dns)||eth.dns.length>4||eth.dns.some(x=>net.isIP(x)!==4))fail('Comprueba la dirección, prefijo, puerta de enlace y DNS.');}
  const wifi=c.network.wifi;
  if(wifi) {cleanText(wifi.ssid,32);cleanText(wifi.password,64);if(Buffer.byteLength(wifi.ssid)>32||!['wpa-psk','sae','open'].includes(wifi.security)||!/^[A-Z]{2}$/.test(wifi.country)||typeof wifi.hidden!=='boolean')fail('Comprueba la configuración Wi-Fi.');if(wifi.ssid && wifi.security==='wpa-psk' && !(Buffer.byteLength(wifi.password)>=8 && Buffer.byteLength(wifi.password)<=63 || /^[a-fA-F0-9]{64}$/.test(wifi.password)))fail('La contraseña Wi-Fi necesita entre 8 y 63 caracteres.'); if(wifi.ssid&&wifi.security==='sae'&&!wifi.password)fail('WPA3 necesita una contraseña.');}
  if(!c.ssh||!Number.isInteger(c.ssh.port)||c.ssh.port<1||c.ssh.port>65535)fail('El puerto SSH debe estar entre 1 y 65535.');
  cleanText(c.ssh.password,256); cleanText(c.ssh.public_key,8192);
  if(c.ssh.public_key&&!/^(ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp(256|384|521)) [A-Za-z0-9+/=]+(?: [^\r\n]*)?$/.test(c.ssh.public_key))fail('Pega una clave pública SSH completa.');
  if(!c.ssh.password&&!c.ssh.public_key)fail('Configura una contraseña SSH o una clave pública.');
  if(!c.providers||Object.keys(c.providers).some(p=>!['codex','antigravity','claude','opencode'].includes(p)))fail('Proveedor no válido.');
  for(const [name,p] of Object.entries(c.providers)) {if(!['none','api','import'].includes(p.mode))fail('Método de autenticación no válido.');for(const k of ['api_key','base_url','model'])cleanText(p[k]||'',4096);if(p.mode==='api'&&!p.api_key)fail('Falta la clave API de '+name+'.');if(p.base_url&&httpsURL(p.base_url).search)fail('El endpoint API no debe llevar parámetros de acceso en la URL.');}
  // Legacy relay choices are deliberately ignored for every newly prepared
  // image/profile. Existing user-data credentials remain available for revoke.
  if(c.tailscale!==undefined && (!c.tailscale || typeof c.tailscale!=='object' || Array.isArray(c.tailscale) || typeof c.tailscale.enabled!=='boolean'))fail('Configuración Tailscale no válida.');
  if(c.tailscale?.enabled) {
    if(typeof c.tailscale.auth_key!=='string'||c.tailscale.auth_key.length<10||c.tailscale.auth_key.length>1024||/\s/.test(c.tailscale.auth_key))fail('Introduce una clave de autenticación Tailscale válida, sin espacios.');
    cleanText(c.tailscale.auth_key,1024);
    for(const field of ['login_server','hostname'])if(c.tailscale[field]!==undefined)cleanText(c.tailscale[field],field==='hostname'?63:2048);
    if(c.tailscale.login_server) {
      cleanText(c.tailscale.login_server,2048);
      const tsURL=httpsURL(c.tailscale.login_server);
      if(tsURL.search||tsURL.pathname!=='/')fail('El servidor Headscale debe ser un origen HTTPS sin ruta ni parámetros.');
    }
    if(c.tailscale.hostname) {
      if(!/^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/.test(c.tailscale.hostname))fail('El nombre de nodo Tailscale admite letras minúsculas, números y guiones.');
      cleanText(c.tailscale.hostname,63);
    }
    for(const flag of ['ssh','accept_routes'])if(c.tailscale[flag]!==undefined&&typeof c.tailscale[flag]!=='boolean')fail('Opción SSH o rutas de Tailscale no válida.');
  }
  // Reusable profiles and helper input must never carry account sessions or
  // renderer-injected remote/provider credentials in unknown fields.
  const pick=(value,keys)=>Object.fromEntries(keys.filter(k=>value?.[k]!==undefined).map(k=>[k,value[k]]));
  return {schema:1,hostname:c.hostname,...(c.locale?{locale:c.locale}:{}),network:{ethernet:pick(eth,['method','address','prefix','gateway','dns']),...(wifi?{wifi:pick(wifi,['ssid','password','security','country','hidden'])}:{})},ssh:pick(c.ssh,['password','public_key','port']),providers:Object.fromEntries(Object.entries(c.providers).map(([name,p])=>[name,pick(p,['mode','api_key','base_url','model'])])),remote:{enabled:false},tailscale:c.tailscale?.enabled?{...pick(c.tailscale,['enabled','auth_key','login_server','hostname']),ssh:c.tailscale.ssh??false,accept_routes:c.tailscale.accept_routes??false}:{enabled:false}};
}
function resolveProviderBinary(binary,{env=process.env,home=os.homedir(),platform=process.platform}={}) {
  if(!/^[a-zA-Z0-9_-]+$/.test(binary)) fail('Proveedor no válido.');
  // Desktop launchers often omit ~/.local/bin. Resolve once to an absolute
  // executable path; terminal launch receives argv directly, never shell code.
  const windows=platform==='win32',p=windows?path.win32:path;
  const environmentPath=env.PATH||env.Path||env.path||'';
  const directories=[...environmentPath.split(windows?';':':').map(s=>s.replace(/^"(.*)"$/,'$1')).filter(s=>s&&p.isAbsolute(s)),p.join(home,'.local','bin'),p.join(home,'.opencode','bin')];
  if(windows)directories.push(p.join(env.APPDATA||p.join(home,'AppData','Roaming'),'npm'),p.join(env.LOCALAPPDATA||p.join(home,'AppData','Local'),'agy','bin'),p.join(env.LOCALAPPDATA||p.join(home,'AppData','Local'),'Programs','nodejs'),p.join(env.ProgramFiles||'C:\\Program Files','nodejs'));
  const extensions=windows?['.exe','.cmd','.bat','']:[''];
  for(const directory of directories) {
    for(const extension of extensions){const candidate=p.resolve(directory,binary+extension);
    try {if(!fs.statSync(candidate).isFile())continue;fs.accessSync(candidate,windows?fs.constants.F_OK:fs.constants.X_OK);return candidate;}catch{}}
  }
  return null;
}
function flattenDisks(tree) {const out=[];for(const disk of tree.blockdevices||[]){if(disk.type!=='disk')continue;const mounted=x=>(x.mountpoints||[]).some(Boolean)||(x.children||[]).some(mounted);if(disk.tran==='usb'&&disk.rm&&disk.serial&&!mounted(disk))out.push({device:disk.path,serial:disk.serial,size:disk.size,model:String(disk.model||'USB').trim(),eligible:true});}return out;}
module.exports={LOCALE_CATALOG,LOCALE_LANGUAGES,LOCALE_KEYBOARDS,validateLocale,importedLocale,httpsURL,sha,normalizeImageSHA,resolveImportedImage,hashFile,verifyManifest,getHTTPS,downloadImage,validateCapsule,flattenDisks,resolveProviderBinary};
