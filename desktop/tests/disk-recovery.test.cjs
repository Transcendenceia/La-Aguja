'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os'),crypto=require('node:crypto'),{execFileSync}=require('node:child_process');
const {normalizeRecovery,sealRecovery,recoveryFiles}=require('../disk-recovery.cjs');
const runtime=path.resolve(__dirname,'../../runtime/recovery_keys.py');
const bitlocker={type:'bitlocker',label:'Other PC',identifier:'SYNTHETIC-ID',key:Array(8).fill('000011').join('-')};
const luks={type:'luks',label:'Linux rescue target',identifier:'',key:'  SYNTHETIC LUKS key with spaces  '};
test('manual keys validate typed input, BitLocker groups and exact LUKS passphrases',()=>{
 assert.deepEqual(normalizeRecovery([luks]),[luks]);
 assert.equal(normalizeRecovery([{...bitlocker,key:bitlocker.key.replaceAll('-','\n')}])[0].key,bitlocker.key);
 for(const key of ['123456',Array(8).fill('999999').join('-'),Array(8).fill('000012').join('-')])assert.throws(()=>normalizeRecovery([{...bitlocker,key}]));
 assert.throws(()=>normalizeRecovery([{...luks,type:'shell'}]));assert.throws(()=>normalizeRecovery(Array(17).fill(luks)));assert.throws(()=>normalizeRecovery([{...luks,key:'bad\u0000key'}]));
 assert.deepEqual(Object.keys(normalizeRecovery([{...luks,hook:'NEVER-COPY'}])[0]).sort(),['identifier','key','label','type']);
});
test('plain and encrypted recovery files open in standalone Python, with no leaked encrypted key', {skip:process.platform==='win32'},()=>{
 for(const mode of ['plain','encrypted']){
  const raw=sealRecovery([bitlocker,luks],{mode,passphrase:'SYNTHETIC-PROFILE-UNLOCK'});
  if(mode==='encrypted'){assert(!raw.includes(bitlocker.key));assert(!raw.includes(luks.key));assert(!raw.includes('Other PC'));}
  const code='import sys,importlib.util,json;s=importlib.util.spec_from_file_location("recovery",sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);keys=m.open_envelope(sys.stdin.buffer.read(),"SYNTHETIC-PROFILE-UNLOCK");assert keys==json.loads(sys.argv[2]);print("verified")';
  assert.equal(execFileSync(process.env.AGUJA_PYTHON||'/usr/bin/python3',['-I','-c',code,runtime,JSON.stringify([bitlocker,luks])],{input:raw}).toString().trim(),'verified');
 }
});
test('encrypted capsule authenticates every byte and does not permit a wrong password',{skip:process.platform==='win32'},()=>{
 const raw=sealRecovery([luks],{mode:'encrypted',passphrase:'SYNTHETIC-UNLOCK'}),e=JSON.parse(raw),bytes=Buffer.from(e.data,'base64url');bytes[0]^=1;e.data=bytes.toString('base64url');
 const code='import sys,importlib.util;s=importlib.util.spec_from_file_location("recovery",sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.open_envelope(sys.stdin.buffer.read(),sys.argv[2])';
 for(const [data,password]of [[raw,'WRONG'],[Buffer.from(JSON.stringify(e)),'SYNTHETIC-UNLOCK']])assert.throws(()=>execFileSync('/usr/bin/python3',['-I','-c',code,runtime,password],{input:data,stdio:['pipe','pipe','pipe']}));
});
test('addon carries a standalone recovery tool and empty keys replace older content',()=>{
 const files=recoveryFiles([],{mode:'plain'},runtime);assert.deepEqual(JSON.parse(files['aguja-recovery.json']).keys,[]);assert(files['aguja-recovery.py'].includes(Buffer.from('cryptsetup')));assert(files['RECOVERY-KEYS.txt'].includes(Buffer.from('/config/aguja-recovery.py')));
});
