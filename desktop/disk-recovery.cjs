'use strict';
const crypto=require('node:crypto'),fs=require('node:fs');
const FORMAT='aguja-disk-recovery',AAD='aguja-disk-recovery:1';
function normalizeRecovery(entries=[]){
 if(!Array.isArray(entries)||entries.length>16)throw Error('Añade como máximo 16 claves de recuperación.');
 return entries.map(entry=>{
  if(!entry||!['bitlocker','luks'].includes(entry.type))throw Error('Elige BitLocker o LUKS para la clave de recuperación.');
  const label=String(entry.label||'').trim(),identifier=String(entry.identifier||'').trim();
  if(!label||Buffer.byteLength(label)>128||Buffer.byteLength(identifier)>128||/[\x00-\x1f\x7f]/.test(label+identifier))throw Error('Indica un nombre de equipo o disco válido para la clave de recuperación.');
  let key=entry.key;
  if(typeof key!=='string'||!key||Buffer.byteLength(key)>4096||(entry.type==='luks'&&/[\x00-\x1f\x7f]/.test(key)))throw Error('Introduce una clave de recuperación válida, sin saltos de línea.');
  if(entry.type==='bitlocker'){
   const digits=key.replace(/[\s-]/g,'');
   if(!/^\d{48}$/.test(digits))throw Error('La clave BitLocker necesita 48 dígitos en ocho grupos de seis.');
   const groups=digits.match(/.{6}/g);
   if(groups.some(s=>Number(s)>720885||Number(s)%11!==0))throw Error('La clave BitLocker tiene un grupo inválido. Revisa los 48 dígitos.');
   key=groups.join('-');
  }
  return {type:entry.type,label,identifier,key};
 });
}
function sealRecovery(entries,protection){
 const keys=normalizeRecovery(entries),raw=Buffer.from(JSON.stringify({schema:1,keys}));
 if(protection.mode==='plain')return Buffer.from(JSON.stringify({format:FORMAT,schema:1,protection:'plain',keys}));
 if(protection.mode!=='encrypted'||typeof protection.passphrase!=='string'||!protection.passphrase||protection.passphrase.length>1024)throw Error('La contraseña de desbloqueo de las claves de recuperación no es válida.');
 const salt=crypto.randomBytes(16),iv=crypto.randomBytes(12),key=crypto.scryptSync(protection.passphrase,salt,32,{N:32768,r:8,p:1,maxmem:64*1024**2});
 try{const cipher=crypto.createCipheriv('aes-256-gcm',key,iv);cipher.setAAD(Buffer.from(AAD));const data=Buffer.concat([cipher.update(raw),cipher.final(),cipher.getAuthTag()]);return Buffer.from(JSON.stringify({format:FORMAT,schema:1,protection:'encrypted',kdf:'scrypt-32768-8-1',salt:salt.toString('base64url'),iv:iv.toString('base64url'),data:data.toString('base64url')}));}
 finally{key.fill(0);raw.fill(0);}
}
function recoveryFiles(entries,protection,helperPath){
 const keys=normalizeRecovery(entries);
 return {'aguja-recovery.json':sealRecovery(keys,protection),'aguja-recovery.py':fs.readFileSync(helperPath),'RECOVERY-KEYS.txt':Buffer.from('LA AGUJA disk recovery keys / Claves de recuperación\n\nOn Rescue Disk / En Rescue Disk:\n  sudo python3 /config/aguja-recovery.py list\n  sudo python3 /config/aguja-recovery.py export\n  sudo python3 /config/aguja-recovery.py open 1 /dev/DEVICE\n\nEncrypted keys prompt for the image unlock password. Export goes to private RAM only: /run/aguja-recovery/keys.json (0600). Open is read-only; --writable is explicit. No automatic disk selection or decryption.\nLas claves cifradas piden la contraseña de la imagen. Exportación solo a RAM privada; apertura de disco en solo lectura, --writable explícito. No se seleccionan ni descifran discos automáticamente.\n')};
}
module.exports={normalizeRecovery,sealRecovery,recoveryFiles};
