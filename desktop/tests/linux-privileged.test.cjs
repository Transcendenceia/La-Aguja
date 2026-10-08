'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os'),{execFileSync}=require('node:child_process');
const {withPrivilegedHelper}=require('../linux-privileged.cjs');
test('elevated helper is staged outside an AppImage mount, private, byte-identical and removed on success/failure',{skip:process.platform==='win32'},async()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'aguja-helper-qa-'));try{
  const mount=path.join(root,'.mount_fixture');fs.mkdirSync(mount);const source=path.join(mount,'helper.py');fs.writeFileSync(source,'print("SYNTHETIC-HELPER-OK")\n');let target;
  const result=await withPrivilegedHelper(source,async staged=>{target=staged;assert(!staged.startsWith(mount+path.sep));assert.equal(fs.statSync(path.dirname(staged)).mode&0o777,0o700);assert.equal(fs.statSync(staged).mode&0o777,0o600);assert.deepEqual(fs.readFileSync(staged),fs.readFileSync(source));return execFileSync('/usr/bin/python3',['-I',staged]).toString().trim();},{directory:root});
  assert.equal(result,'SYNTHETIC-HELPER-OK');assert(!fs.existsSync(target));
  await assert.rejects(()=>withPrivilegedHelper(source,async staged=>{target=staged;throw Error('cancelled authorization');},{directory:root}));assert(!fs.existsSync(target));assert(fs.existsSync(source));
  const link=path.join(root,'link.py');fs.symlinkSync(source,link);await assert.rejects(()=>withPrivilegedHelper(link,()=>{}));
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});
