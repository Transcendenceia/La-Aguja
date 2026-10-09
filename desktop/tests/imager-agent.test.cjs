'use strict';
const test = require('node:test'), assert = require('node:assert/strict');
const fs = require('node:fs'), os = require('node:os'), path = require('node:path'), crypto = require('node:crypto');
const {spawnSync,execFileSync} = require('node:child_process');
const fat = require('../fat32-writer.cjs');
const ROOT = path.resolve(__dirname,'../..');
const cli = path.join(ROOT,'skills/flash-imager/scripts/imager.cjs');
function call(command,request,script=cli) {
  const r=spawnSync(process.execPath,[script,command],{input:request===undefined?undefined:JSON.stringify(request),encoding:'utf8'});
  const lines=r.stdout.trim().split('\n').map(x=>JSON.parse(x));
  return {status:r.status,stdout:r.stdout,stderr:r.stderr,result:lines.at(-1)};
}
function synthetic(dir) {
  const image=path.join(dir,'factory.img'),part=path.join(dir,'cfg.fat');
  fs.writeFileSync(image,'');fs.truncateSync(image,96*1024**2);
  execFileSync('/usr/sbin/sgdisk',['-o','-n','1:2048:+64M','-t','1:0700','-c','1:AGUJA_CFG',image],{stdio:'pipe'});
  fs.writeFileSync(part,'');fs.truncateSync(part,64*1024**2);
  execFileSync('/usr/sbin/mkfs.vfat',['-F','32','-n','AGUJA_CFG',part],{stdio:'pipe'});
  const fd=fs.openSync(image,'r+'),b=fs.readFileSync(part);fs.writeSync(fd,b,0,b.length,1048576);fs.closeSync(fd);
  fat.writeFat32File(image,'AGUJA_CFG','release.json',JSON.stringify({version:'0.9.0',features:['platform-profile-v1','locale-profile-v1','locale-preunlock-v1','i18n-catalog-v1','tailscale-profile-v1']}));
  return image;
}
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
function request(source,output) {
  return {image_path:source,output_path:output,image_sha256:hash(source),capsule:{schema:1,hostname:'agent-fixture',locale:{language:'es_ES.UTF-8',keyboard:'es',variant:''},network:{ethernet:{method:'auto'}},ssh:{password:'',public_key:'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITestFixtureOnly',port:22},providers:{},tailscale:{enabled:false}},protection:{mode:'plain'},import_providers:[]};
}
test('agent help, doctor and locale discovery do not need a GUI or stdin',()=>{
  for(const op of ['--help','doctor','locales']){const r=call(op);assert.equal(r.status,0);assert.equal(r.result.ok,true);}
});
test('malformed input and unknown operation fail without leaking input',()=>{
  const sentinel='SYNTHETIC-SECRET-NOT-FOR-OUTPUT';
  for(const op of ['prepare','inspect','unknown']){const r=call(op,{capsule:sentinel});assert.equal(r.status,1);assert(!r.stdout.includes(sentinel));assert.equal(r.stderr,'');}
});
test('real file preparation, encrypted runtime interoperability, no overwrite and no source mutation', {skip:process.platform==='win32'},()=>{
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),"aguja agent á & ' "));
  try {
    const source=synthetic(dir),before=hash(source),output=path.join(dir,'private.img'),r=request(source,output);
    const result=call('prepare',r);assert.equal(result.status,0,result.stdout);assert.equal(result.result.profile_verified,true);assert.equal(result.result.device_written,false);assert.equal(hash(output),result.result.sha256);assert.equal(hash(source),before);assert.equal(fs.statSync(output).mode&0o777,0o600);
    assert.equal(call('prepare',r).status,1);assert.equal(hash(output),result.result.sha256);
    const bad=request(source,path.join(dir,'bad.img'));bad.image_sha256='0'.repeat(64);assert.equal(call('prepare',bad).status,1);assert(!fs.existsSync(bad.output_path));
    const secret=request(source,path.join(dir,'encrypted.img'));secret.capsule.ssh.password='SYNTHETIC-SSH-PRIVATE';secret.capsule.providers={codex:{mode:'api',api_key:'SYNTHETIC-API-PRIVATE'}};
    assert.equal(call('prepare',secret).status,1);assert(!fs.existsSync(secret.output_path));
    secret.protection={mode:'encrypted',passphrase:'SYNTHETIC-UNLOCK-PRIVATE'};
    const encrypted=call('prepare',secret);assert.equal(encrypted.status,0,encrypted.stdout);assert(!encrypted.stdout.includes('SYNTHETIC'));assert.equal(encrypted.stderr,'');
    const raw=execFileSync('mtype',['-i',secret.output_path+'@@1048576','::/aguja-profile.json']);assert(!raw.includes('SYNTHETIC-API-PRIVATE'));
    const py='import sys;sys.path.insert(0,sys.argv[1]);from profile import open_capsule;c=open_capsule(sys.stdin.buffer.read(),"SYNTHETIC-UNLOCK-PRIVATE");assert c["providers"]["codex"]["api_key"]=="SYNTHETIC-API-PRIVATE";assert c["hostname"]=="agent-fixture";print("opened")';
    assert.equal(execFileSync('/usr/bin/python3',['-I','-c',py,path.join(ROOT,'runtime')],{input:raw}).toString().trim(),'opened');
    const link=path.join(dir,'link.img');fs.symlinkSync(source,link);const linked=request(source,path.join(dir,'from-link.img'));linked.image_path=link;assert.equal(call('prepare',linked).status,1);
    const unselected=request(source,path.join(dir,'unselected.img'));unselected.capsule.providers.codex={mode:'import'};assert.equal(call('prepare',unselected).status,1);
    assert.equal(hash(source),before);assert(!fs.readdirSync(dir).some(x=>x.startsWith('.aguja-agent-')));
  } finally {fs.rmSync(dir,{recursive:true,force:true});}
});
test('standalone distributable prepares an image without checkout or npm install', {skip:process.platform==='win32'},()=>{
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'aguja-agent-bundle-'));
  try {
    const output=path.join(dir,'assets');execFileSync('python3',[path.join(ROOT,'scripts/package-imager-skill.py'),output]);
    const extracted=path.join(dir,'standalone');execFileSync('python3',['-c','import sys,zipfile;zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])',path.join(output,'aguja-flash-imager-skill-1.0.1.zip'),extracted]);
    const script=path.join(extracted,'flash-imager/scripts/imager.cjs');assert.equal(call('doctor',undefined,script).status,0);
    const source=synthetic(dir),r=request(source,path.join(dir,'standalone-private.img'));
    assert.equal(call('prepare',r,script).status,0);assert(fs.existsSync(r.output_path));
    const second=path.join(dir,'second');execFileSync('python3',[path.join(ROOT,'scripts/package-imager-skill.py'),second]);
    for(const name of fs.readdirSync(output))assert.equal(hash(path.join(output,name)),hash(path.join(second,name)));
  } finally {fs.rmSync(dir,{recursive:true,force:true});}
});
