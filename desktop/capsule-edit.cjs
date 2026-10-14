'use strict';
const crypto=require('node:crypto'),core=require('./core.cjs'),provisioning=require('./provisioning.cjs'),recovery=require('./disk-recovery.cjs');
function open(raw,format,passphrase=''){
 const e=JSON.parse(Buffer.isBuffer(raw)?raw.toString('utf8'):raw);if(e.format!==format||e.schema!==1)throw Error('Perfil cifrado no válido.');
 if(e.protection==='plain')return format==='aguja-profile'?e.capsule:e.keys;
 if(e.protection!=='encrypted'||e.kdf!=='scrypt-32768-8-1'||typeof passphrase!=='string')throw Error('Perfil cifrado no válido.');
 const salt=Buffer.from(e.salt,'base64url'),iv=Buffer.from(e.iv,'base64url'),data=Buffer.from(e.data,'base64url');if(salt.length!==16||iv.length!==12||data.length<16||data.length>4*1024**2)throw Error('Perfil cifrado no válido.');
 const key=crypto.scryptSync(passphrase,salt,32,{N:32768,r:8,p:1,maxmem:64*1024**2});try{const c=crypto.createDecipheriv('aes-256-gcm',key,iv);c.setAAD(Buffer.from(format+':1'));c.setAuthTag(data.subarray(-16));const value=JSON.parse(Buffer.concat([c.update(data.subarray(0,-16)),c.final()]).toString('utf8'));if(format==='aguja-disk-recovery'){if(value.schema!==1)throw Error();return value.keys;}return value;}catch{throw Error('La contraseña del perfil no coincide o el archivo fue alterado.');}finally{key.fill(0);}
}
function literalConfig(files){
 const raw=files['aguja.conf']?Buffer.from(files['aguja.conf'],'base64').toString('utf8').replace(/^\ufeff/,''):'';const values={};let section=false;
 for(const line of raw.split(/\r?\n/)){if(!line.trim()||/^[\s]*[#;]/.test(line))continue;if(line.trim()==='[aguja]'&&!section){section=true;continue;}const m=/^\s*([a-z_]+)\s*[=:]\s*(.*)$/.exec(line);if(!section||!m||Object.hasOwn(values,m[1]))throw Error('Perfil cifrado no válido.');values[m[1]]=m[2].trim();}
 if(raw&&!section)throw Error('Perfil cifrado no válido.');return values;
}
function originalCapsule(files,passphrase){
 if(files['aguja-profile.json'])return open(Buffer.from(files['aguja-profile.json'],'base64'),'aguja-profile',passphrase);
 const c=literalConfig(files),key=c.ssh_public_key||'',password=c.ssh_password||(!key?'aguja':'');
 return {schema:1,hostname:c.hostname||'aguja',network:{ethernet:{method:'auto'},wifi:{ssid:c.wifi_ssid||'',password:c.wifi_password||'',security:c.wifi_security||'wpa-psk',country:c.wifi_country||'ES',hidden:c.wifi_hidden==='yes'}},ssh:{public_key:key,password,port:Number(c.ssh_port||22)},providers:{}};
}
function decode(files,passphrase){
 const original=originalCapsule(files,passphrase),capsule=core.validateCapsule(original);
 const keys=files['aguja-recovery.json']?recovery.normalizeRecovery(open(Buffer.from(files['aguja-recovery.json'],'base64'),'aguja-disk-recovery',passphrase)):[];
 return {capsule,diskRecovery:keys,protection:files['aguja-profile.json']?JSON.parse(Buffer.from(files['aguja-profile.json'],'base64')).protection:'plain',imported:Object.entries(original.providers||{}).filter(([,p])=>p.mode==='import'&&p.files).map(([id])=>id)};
}
function encode(input,oldFiles,oldPassphrase){
 const original=originalCapsule(oldFiles,oldPassphrase),capsule=core.validateCapsule(input.capsule);
 for(const [id,p]of Object.entries(capsule.providers)){if(p.mode==='import'){
  const old=original.providers?.[id];if(!old?.files)throw Error('Importa primero la autenticación de '+id+'.');const files={};for(const [name,value]of Object.entries(old.files)){if(!Object.hasOwn(provisioning.IMPORTS[id],name)||typeof value!=='string')throw Error('Configuración privada no válida.');files[name]=provisioning.sanitize(id,name,Buffer.from(value,'base64url')).toString('base64url');}capsule.providers[id]={...p,files};
 }}
 const diskRecovery=recovery.normalizeRecovery(input.diskRecovery||[]);const files={'aguja-profile.json':provisioning.seal(capsule,input.protection),'aguja-recovery.json':recovery.sealRecovery(diskRecovery,input.protection)};
 // Encrypted profile's public pre-unlock locale must follow a configuration edit.
 files['locale.json']=Buffer.from(JSON.stringify({schema:1,...(capsule.locale||core.LOCALE_CATALOG.default)}));
 // Legacy literals may contain old credentials; erase them only when replacing
 // the profile, keeping just the harmless template consumed by old live readers.
 const legacy=literalConfig(oldFiles),home=input.protection.mode==='plain'&&legacy.persistent_home==='yes'?'yes':'no',harness=['menu','shell','codex','antigravity','claude','opencode'].includes(legacy.default_harness)?legacy.default_harness:'menu',agentMode=legacy.agent_mode==='full'?'full':'ask';files['aguja.conf']=Buffer.from('[aguja]\nhostname=aguja\npersistent_home='+home+'\nssh_password=\nssh_public_key=\ndefault_harness='+harness+'\nagent_mode='+agentMode+'\n');
 return Object.fromEntries(Object.entries(files).map(([n,v])=>[n,v.toString('base64')]));
}
module.exports={open,decode,encode};
