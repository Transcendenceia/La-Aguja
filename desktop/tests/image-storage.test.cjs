'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const storage=require('../image-storage.cjs');
test('space budget includes a private copy, reports required and available bytes without paths',async()=>{
 const sourceBytes=3882876928;
 await assert.rejects(()=>storage.checkSpace('unused',sourceBytes,{statfs:async()=>({bavail:235343n,bsize:4096n})}),e=>/3\.68 GiB/.test(e.message)&&/0\.90 GiB/.test(e.message)&&/USB no se ha grabado/.test(e.message)&&!e.message.includes('unused'));
 await storage.checkSpace('unused',sourceBytes,{statfs:async()=>({bavail:20n*1024n**3n,bsize:1n})});
});
test('existing destination preserved and rejected before reading source or copying',async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'aguja-destination-'));const output=path.join(dir,'existing.img');fs.writeFileSync(output,'KEEP');
 try{await assert.rejects(()=>storage.checkDestination(path.join(dir,'missing-source.img'),output),/Ya existe.*no se ha sobrescrito/);assert.equal(fs.readFileSync(output,'utf8'),'KEEP');assert.deepEqual(fs.readdirSync(dir),['existing.img']);}finally{fs.rmSync(dir,{recursive:true,force:true});}
});
test('write-time full disk and filesystem/permission failures have actionable secret-free messages',()=>{
 for(const [code,pattern]of [['ENOSPC',/espacio suficiente.*USB no se ha grabado/],['EACCES',/permiso.*otra carpeta/],['EPERM',/permiso.*otra carpeta/],['EFBIG',/NTFS o exFAT/],['EEXIST',/otro nombre/]])assert.match(storage.storageError(Object.assign(new Error('PRIVATE-PATH'),{code})).message,pattern);
 const unknown=new Error('unknown');assert.equal(storage.storageError(unknown),unknown);
});
test('unsupported statfs falls back to exclusive copy while permission failures remain explicit',async()=>{
 await storage.checkSpace('unused',100,{statfs:async()=>{throw Object.assign(new Error(),{code:'ENOSYS'});}});
 await assert.rejects(()=>storage.checkSpace('unused',100,{statfs:async()=>{throw Object.assign(new Error(),{code:'EACCES'});}}),/permiso/);
});
