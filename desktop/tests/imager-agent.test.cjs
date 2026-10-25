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
    secret.disk_recovery=[{type:'luks',label:'Other machine',identifier:'',key:'  SYNTHETIC LUKS ñ exact  '}];
    const encrypted=call('prepare',secret);assert.equal(encrypted.status,0,encrypted.stdout);assert.equal(encrypted.result.recovery_verified,true);assert.equal(encrypted.result.recovery_count,1);assert(!encrypted.stdout.includes('SYNTHETIC'));assert.equal(encrypted.stderr,'');
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
    const output=path.join(dir,'assets');const built=JSON.parse(execFileSync('python3',[path.join(ROOT,'scripts/package-imager-skill.py'),output]).toString());
    const extracted=path.join(dir,'standalone');execFileSync('python3',['-c','import sys,zipfile;zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])',built.archives.find(p=>p.endsWith('.zip')),extracted]);
    const script=path.join(extracted,'flash-imager/scripts/imager.cjs');const doctor=call('doctor',undefined,script);assert.equal(doctor.status,0);
    const manifest=JSON.parse(fs.readFileSync(path.join(extracted,'flash-imager/BUNDLE-MANIFEST.json')));
    const skillVersion=fs.readFileSync(path.join(extracted,'flash-imager/SKILL.md'),'utf8').match(/^  version: "([^"]+)"$/m)[1];
    assert.equal(doctor.result.version,manifest.skill_version);assert.equal(manifest.skill_version,skillVersion);assert.equal(doctor.result.imager_version,manifest.imager_version);
    assert(fs.existsSync(path.join(extracted,'flash-imager/scripts/lib/desktop/profile-extensions.cjs')));
    for(const [name,expected] of Object.entries(manifest.files)){assert.equal(hash(path.join(extracted,name)),expected,name);}
    const source=synthetic(dir),r=request(source,path.join(dir,'standalone-private.img'));
    r.disk_recovery=[{type:'bitlocker',label:'Other Windows',identifier:'',key:Array(8).fill('000011').join('-')}];
    assert.equal(call('prepare',r,script).status,1);
    r.protection={mode:'encrypted',passphrase:'SYNTHETIC-BUNDLE-UNLOCK'};
    assert.equal(call('prepare',r,script).status,0);assert(fs.existsSync(r.output_path));
    verifyExtended(dir,script);
    const second=path.join(dir,'second');execFileSync('python3',[path.join(ROOT,'scripts/package-imager-skill.py'),second]);
    for(const name of fs.readdirSync(output))assert.equal(hash(path.join(output,name)),hash(path.join(second,name)));
  } finally {fs.rmSync(dir,{recursive:true,force:true});}
});

function verifyExtended(dir,script=cli){
  const source=synthetic(dir);fat.writeFat32File(source,'AGUJA_CFG','release.json',JSON.stringify({version:'1.1.1',features:['platform-profile-v1','locale-profile-v1','locale-preunlock-v1','imager-profile-v2']}));
  const before=hash(source),r=request(source,path.join(dir,'extended.img'));
  const extras={wifi_profiles:[{ssid:'Public-fixture',password:'',security:'open',country:'ES',hidden:false},{ssid:'Private-fixture',password:'SYNTHETIC-WIFI-SECONDARY',security:'wpa-psk',country:'ES',hidden:false}],environment:{SYNTHETIC_VALUE:'literal-${HOME}-$(touch /NEVER-EXECUTE)'},storage:[{name:'Fixture NAS',type:'smb',fields:{host:'nas.example',user:'fixture',pass:'SYNTHETIC-NAS-PRIVATE'},obscured:false}],tailscale:{accept_dns:false,advertise_routes:'192.0.2.0/24',advertise_tags:'tag:fixture',forwarding:false}};
  for(const extensions of [{wifi_profiles:extras.wifi_profiles},{environment:extras.environment},{storage:extras.storage}]){
    const probe={...r,capsule:{...r.capsule,extensions}};const blocked=call('prepare',probe,script);assert.equal(blocked.status,1,blocked.stdout);assert(!fs.existsSync(r.output_path));assert(!blocked.stdout.includes('SYNTHETIC'));
  }
  r.capsule.extensions=extras;r.protection={mode:'encrypted',passphrase:'SYNTHETIC-EXTENDED-UNLOCK'};
  const saved=path.join(dir,'extended.aguja'),save=call('save-profile',{capsule:r.capsule,disk_recovery:[],passphrase:r.protection.passphrase,output_path:saved},script);assert.equal(save.status,0,save.stdout);
  const viaSaved={...r,profile_path:saved,profile_passphrase:r.protection.passphrase};delete viaSaved.capsule;
  const prepared=call('prepare',viaSaved,script);assert.equal(prepared.status,0,prepared.stdout);assert.equal(prepared.result.profile_verified,true);assert.equal(prepared.result.source_unchanged,true);assert.equal(prepared.result.device_written,false);assert(!prepared.stdout.includes('SYNTHETIC'));assert.equal(prepared.stderr,'');
  const raw=execFileSync('mtype',['-i',r.output_path+'@@1048576','::/aguja-profile.json']);assert(!raw.includes('SYNTHETIC'));
  const py='import sys;sys.path.insert(0,sys.argv[1]);from profile import open_capsule;c=open_capsule(sys.stdin.buffer.read(),"SYNTHETIC-EXTENDED-UNLOCK");e=c["extensions"];assert e["wifi_profiles"][1]["password"]=="SYNTHETIC-WIFI-SECONDARY";assert e["storage"][0]["fields"]["pass"]=="SYNTHETIC-NAS-PRIVATE";assert e["environment"]["SYNTHETIC_VALUE"]=="literal-${HOME}-$(touch /NEVER-EXECUTE)";assert e["tailscale"]["advertise_routes"]=="192.0.2.0/24";print("extended runtime opened")';
  assert.equal(execFileSync('/usr/bin/python3',['-I','-c',py,path.join(ROOT,'runtime')],{input:raw}).toString().trim(),'extended runtime opened');
  const plain={...r,output_path:path.join(dir,'extended-explicit-plain.img'),protection:{mode:'plain'},allow_plain_secrets:true};const allowed=call('prepare',plain,script);assert.equal(allowed.status,0,allowed.stdout);assert.equal(allowed.result.protection,'plain');
  const old=path.join(dir,'old.img');fs.copyFileSync(source,old);fat.writeFat32File(old,'AGUJA_CFG','release.json',JSON.stringify({version:'1.1.0',features:['platform-profile-v1','locale-profile-v1']}));const rejected=call('prepare',{...r,image_path:old,image_sha256:hash(old),output_path:path.join(dir,'old-rejected.img')},script);assert.equal(rejected.status,1);assert(!fs.existsSync(path.join(dir,'old-rejected.img')));assert.equal(hash(source),before);
}
test('extended profile CLI preserves literal settings and enforces private protection', {skip:process.platform==='win32'},()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'aguja-agent-extended-'));try{verifyExtended(dir);}finally{fs.rmSync(dir,{recursive:true,force:true});}
});
