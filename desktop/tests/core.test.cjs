'use strict';
const test=require('node:test');const assert=require('node:assert/strict');const crypto=require('node:crypto');const fs=require('node:fs');const os=require('node:os');const path=require('node:path');
const {verifyManifest,httpsURL,sha,hashFile,validateCapsule,flattenDisks,downloadImage,resolveProviderBinary,normalizeImageSHA,resolveImportedImage}=require('../core.cjs');
function valid(){return {schema:1,hostname:'aguja',network:{ethernet:{method:'auto'},wifi:{ssid:'FixtureWifi',password:'synthetic-test-only',security:'wpa-psk',country:'ES',hidden:false}},ssh:{password:'synthetic-ssh-only',public_key:'',port:22},providers:{codex:{mode:'none'},antigravity:{mode:'api',api_key:'SYNTHETIC-NOT-A-KEY'},claude:{mode:'none'},opencode:{mode:'none'}},remote:{enabled:false}};}
function envelope(doc,key){const payload=Buffer.from(JSON.stringify(doc));return {key_id:'fixture-key',payload:payload.toString('base64'),signature:crypto.sign(null,payload,key).toString('base64')};}
const release={version:'0.4.0',url:'https://example.invalid/aguja-0.4.0.img',bytes:1048576,sha256:'a'.repeat(64)};
test('signed Ed25519 catalog succeeds only for the pinned key and unexpired content',()=>{const {publicKey,privateKey}=crypto.generateKeyPairSync('ed25519');const pin={key_id:'fixture-key',public_key_pem:publicKey.export({type:'spki',format:'pem'})};const d={schema:1,expires_at:new Date(Date.now()+60000).toISOString(),releases:[release]};assert.equal(verifyManifest(envelope(d,privateKey),pin)[0].version,'0.4.0');const altered=envelope(d,privateKey);altered.payload=Buffer.from(JSON.stringify({...d,releases:[{...release,sha256:'b'.repeat(64)}]})).toString('base64');assert.throws(()=>verifyManifest(altered,pin));const other=crypto.generateKeyPairSync('ed25519');assert.throws(()=>verifyManifest(envelope(d,other.privateKey),pin));assert.throws(()=>verifyManifest({...envelope(d,privateKey),key_id:'wrong'},pin));assert.throws(()=>verifyManifest(envelope({...d,expires_at:'2000-01-01'},privateKey),pin));});
test('an unconfigured public pin never accepts any catalog',()=>{assert.throws(()=>verifyManifest({},{}),/clave de publicación/);});
test('download catalog rejects insecure origins, embedded credentials and malformed digests',()=>{for(const url of ['http://example.com','https://u:p@example.com','https://example.com:8443','javascript:alert(1)','https://example.com/#secret'])assert.throws(()=>httpsURL(url));assert.throws(()=>sha('zz'));assert.equal(sha('f'.repeat(64)),'f'.repeat(64));});
test('settings preserve literal secrets and reject multiline/config injection',()=>{const c=valid();c.ssh.password='literal$not-a-shell-command';assert.equal(validateCapsule(c).ssh.password,c.ssh.password);c.network.wifi.password='test\nconfig=bad';assert.throws(()=>validateCapsule(c));});
test('network and SSH validation matches usable configurations',()=>{let c=valid();c.network.ethernet={method:'manual',address:'192.0.2.10',prefix:24,gateway:'192.0.2.10',dns:['1.1.1.1']};assert.doesNotThrow(()=>validateCapsule(c));for(const change of [{address:'127.1'},{prefix:33},{gateway:'oops'},{dns:['9.9.9.bad']}]){const d=structuredClone(c);Object.assign(d.network.ethernet,change);assert.throws(()=>validateCapsule(d));}c.ssh.port=65536;assert.throws(()=>validateCapsule(c));c=valid();c.ssh.password='';assert.throws(()=>validateCapsule(c));c.ssh.public_key='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDummyFixture';assert.doesNotThrow(()=>validateCapsule(c));});
test('Wi-Fi byte length, WPA3 and open network handling',()=>{const c=valid();c.network.wifi.ssid='ñ'.repeat(17);assert.throws(()=>validateCapsule(c));c.network.wifi.ssid='fixture';c.network.wifi.security='sae';c.network.wifi.password='';assert.throws(()=>validateCapsule(c));c.network.wifi.security='open';assert.doesNotThrow(()=>validateCapsule(c));});
test('only unmounted exact-serial removable USB disks become flash candidates',()=>{const disks={blockdevices:[{path:'/dev/sda',type:'disk',tran:'sata',rm:false,serial:'internal',size:9},{path:'/dev/sdb',type:'disk',tran:'usb',rm:true,serial:'USB-A',size:8,children:[{mountpoints:['/media/mounted']}]},{path:'/dev/sdc',type:'disk',tran:'usb',rm:true,serial:'USB-B',size:7,children:[{mountpoints:[null]}]},{path:'/dev/sdd',type:'disk',tran:'usb',rm:true,serial:'',size:7}]};assert.deepEqual(flattenDisks(disks).map(x=>x.serial),['USB-B']);});
test('legacy relay opt-in is ignored, never validated or copied to newly prepared profiles',()=>{const c=valid();assert.equal(validateCapsule(c).remote.enabled,false);c.remote={enabled:true,relay_url:'invalid-old-server',ttl_seconds:3000000,device_token:'SYNTHETIC-OLD-DEVICE'};assert.deepEqual(validateCapsule(c).remote,{enabled:false});});
test('tailscale pre-provisioning validation accepts valid auth-keys and endpoints, rejects invalid',()=>{const c=valid();assert.equal(validateCapsule(c).tailscale.enabled,false);c.tailscale={enabled:true,auth_key:'tskey-auth-synthetic123456',login_server:'https://headscale.example.org',hostname:'aguja-node',ssh:true};const validated=validateCapsule(c);assert.equal(validated.tailscale.enabled,true);assert.equal(validated.tailscale.auth_key,'tskey-auth-synthetic123456');assert.equal(validated.tailscale.login_server,'https://headscale.example.org');assert.equal(validated.tailscale.hostname,'aguja-node');assert.equal(validated.tailscale.ssh,true);c.tailscale.auth_key='short';assert.throws(()=>validateCapsule(c));c.tailscale.auth_key='tskey-auth-valid';c.tailscale.login_server='http://not-https.com';assert.throws(()=>validateCapsule(c));c.tailscale.login_server='https://headscale.example.org';c.tailscale.hostname='BAD_HOST!';assert.throws(()=>validateCapsule(c));});
test('real file hashes exact bytes and reports measured progress',async()=>{const dir=fs.mkdtempSync(path.join(os.tmpdir(),'aguja-hash-'));try{const p=path.join(dir,'fixture.img');fs.writeFileSync(p,'synthetic-file-only');const events=[];const result=await hashFile(p,e=>events.push(e));assert.equal(result.sha256,crypto.createHash('sha256').update('synthetic-file-only').digest('hex'));assert.equal(result.bytes,19);assert.equal(events.at(-1).done,19);}finally{fs.rmSync(dir,{recursive:true});}});
test('download never publishes mismatched data or overwrites an existing destination',async()=>{const dir=fs.mkdtempSync(path.join(os.tmpdir(),'aguja-download-'));const oldFetch=global.fetch;try{const data=Buffer.from('synthetic-image-bytes'),r={url:'https://example.invalid/image.img',bytes:data.length,sha256:crypto.createHash('sha256').update(data).digest('hex')};global.fetch=async()=>new Response(data,{status:200});const dest=path.join(dir,'ok.img');const receipt=await downloadImage(r,dest);assert.equal(receipt.bytes,data.length);assert.deepEqual(fs.readFileSync(dest),data);await assert.rejects(()=>downloadImage(r,dest));assert.deepEqual(fs.readFileSync(dest),data);await assert.rejects(()=>downloadImage({...r,sha256:'0'.repeat(64)},path.join(dir,'bad.img')));assert.equal(fs.existsSync(path.join(dir,'bad.img')),false);assert.equal(fs.readdirSync(dir).filter(x=>x.includes('partial')).length,0);}finally{global.fetch=oldFetch;fs.rmSync(dir,{recursive:true});}});

test('native provider resolution uses absolute PATH then private local-bin fallback without running shell',()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'aguja-native-cli-'));
 try{
  const local=path.join(dir,'.local','bin');fs.mkdirSync(local,{recursive:true});
  const cli=path.join(local,'agy');fs.writeFileSync(cli,'synthetic non-executed fixture',{mode:0o700});
  assert.equal(resolveProviderBinary('agy',{env:{PATH:'/unavailable'},home:dir}),cli);
  assert.equal(resolveProviderBinary('agy',{env:{},home:dir}),cli);
  const other=path.join(dir,'path with spaces');fs.mkdirSync(other);const inPath=path.join(other,'agy');fs.writeFileSync(inPath,'fixture',{mode:0o700});
  assert.equal(resolveProviderBinary('agy',{env:{PATH:other},home:dir}),inPath);
  fs.chmodSync(inPath,0o600);assert.equal(resolveProviderBinary('agy',{env:{PATH:other},home:dir}),cli);
  fs.chmodSync(cli,0o600);assert.equal(resolveProviderBinary('agy',{env:{PATH:'/unavailable'},home:dir}),null);
  assert.throws(()=>resolveProviderBinary('agy; echo private',{env:{},home:dir}));
  assert.throws(()=>resolveProviderBinary('../agy',{env:{},home:dir}));
 }finally{fs.rmSync(dir,{recursive:true});}
});


test('local import calculates provenance separately from digest matching',()=>{
 const measured={sha256:release.sha256,bytes:release.bytes};
 assert.deepEqual(resolveImportedImage(measured),{...measured,trusted:false,verification:'calculated-sha'});
 assert.equal(resolveImportedImage(measured,'').verification,'calculated-sha');
 assert.equal(resolveImportedImage(measured,'  '+release.sha256.toUpperCase()+'  ').verification,'verified-sha');
 assert.equal(resolveImportedImage(measured,release.sha256).trusted,false);
 const official=resolveImportedImage(measured,'',[release]);
 assert.equal(official.trusted,true);assert.equal(official.verification,'verified-catalog');assert.equal(official.version,release.version);
 assert.equal(resolveImportedImage(measured,release.sha256,[release]).verification,'verified-catalog');
 for(const candidate of [{...release,bytes:release.bytes+1},{...release,sha256:'b'.repeat(64)}])assert.equal(resolveImportedImage(measured,'',[candidate]).trusted,false);
 assert.throws(()=>resolveImportedImage(measured,'b'.repeat(64),[release]),/no coincide/);
 for(const invalid of ['bad','g'.repeat(64),{},[],null,42])assert.throws(()=>normalizeImageSHA(invalid),/64 caracteres/);
 assert.equal(normalizeImageSHA(undefined),'');assert.equal(normalizeImageSHA('  '),'');
});

test('local hash rejects directories and symlinks without following them',async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'aguja-image-type-'));
 try{const file=path.join(dir,'file.img');fs.writeFileSync(file,'fixture');const link=path.join(dir,'link.img');fs.symlinkSync(file,link);await assert.rejects(()=>hashFile(dir),/archivo de imagen/);await assert.rejects(()=>hashFile(link),/archivo de imagen/);}finally{fs.rmSync(dir,{recursive:true});}
});

test('automatic catalog request uses a bounded timeout and GET with no uploaded image metadata',async()=>{
 const oldFetch=global.fetch;
 try{global.fetch=async(url,options)=>{assert.equal(url,'https://example.invalid/catalog');assert.equal(options.method,undefined);assert.equal(options.body,undefined);assert.equal(options.redirect,'error');assert(options.signal);return new Response(JSON.stringify({fixture:true}),{status:200});};assert.deepEqual(await require('../core.cjs').getHTTPS('https://example.invalid/catalog',65536,4000),{fixture:true});}finally{global.fetch=oldFetch;}
});


test('locale accepts supported pairs, preserves selection and rejects injection or unsupported variants',()=>{
 const {validateLocale}=require('../core.cjs');
 for(const locale of [{language:'es_CO.UTF-8',keyboard:'latam',variant:'nodeadkeys'},{language:'en_US.UTF-8',keyboard:'us',variant:'intl'},{language:'de_DE.UTF-8',keyboard:'de',variant:''}]){assert.deepEqual(validateLocale(locale),locale);const c=valid();c.locale=locale;assert.deepEqual(validateCapsule(c).locale,locale);}
 for(const change of [{language:'es_ES;id'},{keyboard:'../../etc'},{variant:'intl'},{timezone:'UTC'}])assert.throws(()=>validateLocale({language:'es_ES.UTF-8',keyboard:'es',variant:'',...change}));
});
test('locale import exposes only recognised values and does not invent unsupported host settings',()=>{
 const {importedLocale}=require('../core.cjs');
 assert.deepEqual(importedLocale({language:'es_CO.utf8',keyboard:'latam',variant:'nodeadkeys'}),{locale:{language:'es_CO.UTF-8',keyboard:'latam',variant:'nodeadkeys'},warning:''});
 const unsupported=importedLocale({language:'zh_CN.UTF-8',keyboard:'ru',variant:'SYNTHETIC-PRIVATE-SETTING'});assert.deepEqual(unsupported.locale,{language:'zh_CN.UTF-8'});assert(unsupported.warning);assert(!JSON.stringify(unsupported).includes('SYNTHETIC-PRIVATE-SETTING'));
 const variant=importedLocale({language:'en_US.UTF-8',keyboard:'us',variant:'dvorak'});assert.equal(variant.locale.variant,undefined);assert(variant.warning);
});

test('public downloads reject every credential header before making any request',async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'aguja-public-download-')),oldFetch=global.fetch;let requests=0;
 const release={url:'https://github.com/Transcendenceia/La-Aguja/releases/download/v0.9.0/image.img',bytes:8,sha256:'a'.repeat(64)};
 try{global.fetch=async()=>{requests++;throw Error('must not request');};
 for(const headers of [{Authorization:'Bearer SYNTHETIC-SESSION'},{Cookie:'SYNTHETIC-COOKIE'}])await assert.rejects(()=>downloadImage(release,path.join(dir,'image.img'),()=>{},undefined,headers),/no aceptan credenciales/);
 assert.equal(requests,0);
 }finally{global.fetch=oldFetch;fs.rmSync(dir,{recursive:true,force:true});}
});
