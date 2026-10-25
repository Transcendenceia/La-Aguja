#!/usr/bin/env node
'use strict';
// Harness-neutral interface to the SAME file preparation engine as Flash Imager.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const bundled = path.join(__dirname, 'lib');
const root = fs.existsSync(bundled) ? bundled : path.resolve(__dirname, '../../..');
const core = require(path.join(root, 'desktop/core.cjs'));
const provisioning = require(path.join(root, 'desktop/provisioning.cjs'));
const fat = require(path.join(root, 'desktop/fat32-writer.cjs'));
const recovery = require(path.join(root, 'desktop/disk-recovery.cjs'));
const engineVersion = JSON.parse(fs.readFileSync(path.join(root,'desktop/package.json'))).version;
const pin = JSON.parse(fs.readFileSync(path.join(root, 'desktop/resources/release-key.json')));
const reusableProfile=require(path.join(root,'desktop/reusable-profile.cjs'));
const VERSION = '1.2.0';
function emit(value) { process.stdout.write(JSON.stringify(value) + '\n'); }
function requireValue(ok) { if (!ok) throw Error('invalid'); }
function keys(value, allowed) {
  requireValue(value && typeof value === 'object' && !Array.isArray(value));
  requireValue(Object.keys(value).every(k => allowed.includes(k)));
}
async function input() {
  let size = 0; const chunks = [];
  for await (const chunk of process.stdin) {
    size += chunk.length; requireValue(size <= 8 * 1024 ** 2); chunks.push(chunk);
  }
  return JSON.parse(Buffer.concat(chunks).toString('utf8'));
}
function sourceFile(value) {
  requireValue(typeof value === 'string' && path.isAbsolute(value) && path.extname(value).toLowerCase() === '.img');
  const s = fs.lstatSync(value);
  requireValue(s.isFile() && !s.isSymbolicLink());
  return fs.realpathSync(value);
}
function destination(value) {
  requireValue(typeof value === 'string' && path.isAbsolute(value) && path.extname(value).toLowerCase() === '.img');
  const parent = fs.realpathSync(path.dirname(value));
  requireValue(fs.statSync(parent).isDirectory());
  const result = path.join(parent, path.basename(value));
  try { fs.lstatSync(result); throw Error('exists'); } catch (e) { if (e.code !== 'ENOENT') throw e; }
  return result;
}
async function catalog() {
  return core.verifyManifest(await core.getHTTPS(pin.catalog_url), pin);
}
function readProfile(image, filename='aguja-profile.json') {
  const fd = fs.openSync(image, 'r');
  try {
    const p = fat.findGptPartition(fd), params = fat.parseFat32Params(fd, p.offset);
    return fat.readFat32File(fd, params, filename);
  } finally { fs.closeSync(fd); }
}
function privateConfig(c, imports) {
  return Boolean(imports.length || c.network.wifi?.password || c.ssh.password ||
    Object.values(c.providers).some(p => p.api_key) || c.tailscale?.enabled ||
    c.extensions?.wifi_profiles?.some(w => w.password) ||
    Object.keys(c.extensions?.environment || {}).length || c.extensions?.storage?.length);
}
async function prepare(r) {
  keys(r, ['image_path','output_path','image_sha256','capsule','protection','import_providers','allow_plain_secrets','disk_recovery','profile_path','profile_passphrase']);
  if(r.profile_path!==undefined){requireValue(r.capsule===undefined && r.disk_recovery===undefined);const saved=reusableProfile.open(readSavedProfile(r.profile_path),r.profile_passphrase);r.disk_recovery=saved.disk_recovery||[];delete saved.disk_recovery;r.capsule=saved;}
  const source = sourceFile(r.image_path), output = destination(r.output_path);
  const expected = core.sha(r.image_sha256);
  const capsule = core.validateCapsule(r.capsule);
  const diskRecovery = recovery.normalizeRecovery(r.disk_recovery || []);
  // These values must also survive the live runtime's literal INI reader.
  for (const v of [capsule.ssh.password,capsule.ssh.public_key,...Object.values(capsule.network.wifi || {}).filter(v=>typeof v==='string')]) requireValue(v === v.trim());
  const oc = capsule.providers.opencode;
  if (oc?.mode === 'api' && oc.base_url) requireValue(Boolean(oc.model));
  const protection = r.protection || {mode:'plain'};
  keys(protection, ['mode','passphrase']);
  requireValue(['plain','encrypted'].includes(protection.mode));
  const imports = r.import_providers || [];
  requireValue(Array.isArray(imports) && imports.length <= 4 && new Set(imports).size === imports.length);
  requireValue(imports.every(id => Object.hasOwn(provisioning.IMPORTS, id)));
  requireValue(Object.entries(capsule.providers).every(([id,p]) => (p.mode === 'import') === imports.includes(id)));
  if ((privateConfig(capsule, imports) || diskRecovery.length) && protection.mode !== 'encrypted') requireValue(r.allow_plain_secrets === true);
  const approved = {};
  for (const id of imports) {
    const discovered = provisioning.discover(id);
    requireValue(discovered.portable); approved[id] = discovered.paths;
  }
  // A 0700 staging directory protects the engine's intermediate copy on POSIX.
  // On Windows the destination directory must already have private user ACLs.
  const work = fs.mkdtempSync(path.join(path.dirname(output), '.aguja-agent-'));
  const temp = path.join(work, 'private.img');
  fs.chmodSync(work, 0o700);
  try {
    emit({type:'progress',stage:'prepare'});
    const addonFiles=recovery.recoveryFiles(diskRecovery,protection,path.join(root,'runtime/recovery_keys.py'));
    addonFiles['bitlocker.json']=Buffer.from(JSON.stringify({schema:1,volumes:[],source:'See aguja-recovery.json'}));
    await provisioning.prepareWindows({source,output:temp,sha256:expected,capsule,protection,approved,addonFiles});
    fs.chmodSync(temp, 0o600);
    const raw = readProfile(temp);
    requireValue(raw && JSON.parse(raw).protection === protection.mode);
    if (protection.mode === 'plain') requireValue(JSON.stringify(JSON.parse(raw).capsule) === JSON.stringify(provisioning.materialize(capsule,approved)));
    else {
      const e = JSON.parse(raw), key = crypto.scryptSync(protection.passphrase,Buffer.from(e.salt,'base64url'),32,{N:32768,r:8,p:1,maxmem:64*1024**2});
      try {
        const data = Buffer.from(e.data,'base64url'), decipher = crypto.createDecipheriv('aes-256-gcm',key,Buffer.from(e.iv,'base64url'));
        decipher.setAAD(Buffer.from('aguja-profile:1')); decipher.setAuthTag(data.subarray(-16));
        const opened = JSON.parse(Buffer.concat([decipher.update(data.subarray(0,-16)),decipher.final()]));
        requireValue(JSON.stringify(opened) === JSON.stringify(provisioning.materialize(capsule,approved)));
      } finally { key.fill(0); }
    }
    const recoveryRaw=readProfile(temp,'aguja-recovery.json');
    requireValue(recoveryRaw && recoveryRaw.equals(addonFiles['aguja-recovery.json']));
    for(const name of ['aguja-recovery.py','RECOVERY-KEYS.txt','bitlocker.json'])requireValue(readProfile(temp,name).equals(addonFiles[name]));
    const checked = await core.hashFile(temp);
    requireValue((await core.hashFile(source)).sha256 === expected);
    fs.linkSync(temp, output); // Atomic: never replace an existing file.
    return {ok:true,output_path:output,...checked,profile_verified:true,recovery_verified:true,recovery_count:diskRecovery.length,protection:protection.mode,source_unchanged:true,device_written:false};
  } finally { fs.rmSync(work, {recursive:true,force:true}); }
}
function readSavedProfile(value){
 requireValue(typeof value==='string'&&path.isAbsolute(value));const fd=fs.openSync(value,fs.constants.O_RDONLY|(fs.constants.O_NOFOLLOW||0));try{const stat=fs.fstatSync(fd);requireValue(stat.isFile()&&stat.size<=1048576);return JSON.parse(fs.readFileSync(fd,'utf8'));}finally{fs.closeSync(fd);}
}
async function saveProfile(r){
 keys(r,['capsule','disk_recovery','passphrase','output_path']);requireValue(typeof r.output_path==='string'&&path.isAbsolute(r.output_path)&&path.extname(r.output_path)==='.aguja');const parent=fs.realpathSync(path.dirname(r.output_path));requireValue(fs.statSync(parent).isDirectory());const out=path.join(parent,path.basename(r.output_path));const data=reusableProfile.seal(r.capsule,r.passphrase,r.disk_recovery||[]);await fs.promises.writeFile(out,JSON.stringify(data),{flag:'wx',mode:0o600});return {ok:true,output_path:out,protection:'encrypted',secret_values_returned:false};
}
async function main() {
  requireValue(Number(process.versions.node.split('.')[0]) >= 22);
  const [operation, ...extra] = process.argv.slice(2); requireValue(extra.length === 0);
  if (operation === '--help') return {ok:true,version:VERSION,operations:['doctor','locales','catalog','download','inspect','prepare','save-profile','profile-info'],input:'JSON stdin for download, inspect, prepare, save-profile and profile-info',usb_writing:false};
  if (operation === 'doctor') return {ok:true,version:VERSION,imager_version:engineVersion,recovery_types:['bitlocker','luks'],node:process.versions.node,platform:process.platform,engine:'Flash Imager GPT/FAT32',profile_extensions:['wifi_profiles','environment','storage','tailscale'],extended_profile_feature:'imager-profile-v2',usb_writing:false};
  if (operation === 'locales') return {ok:true,languages:core.LOCALE_CATALOG.languages,keyboards:core.LOCALE_CATALOG.keyboards};
  if (operation === 'catalog') return {ok:true,signature_verified:true,releases:await catalog()};
  const r = await input();
  if(operation==='save-profile')return saveProfile(r);
  if(operation==='profile-info'){keys(r,['profile_path']);const e=readSavedProfile(r.profile_path);requireValue(e.format==='aguja-profile-aes256gcm'&&e.schema===1);return {ok:true,schema:e.schema,protection:'encrypted',secret_values_returned:false};}
  if (operation === 'download') {
    keys(r,['version','output_path']);
    const dest = destination(r.output_path), releases = await catalog();
    const selected = releases.find(item => item.version === r.version); requireValue(selected);
    const checked = await core.downloadImage(selected,dest,p => emit({type:'progress',stage:'download',...p}));
    return {ok:true,output_path:dest,...checked,signature_verified:true,version:selected.version};
  }
  if (operation === 'inspect') {
    keys(r,['image_path','image_sha256']);
    const image = sourceFile(r.image_path), checked = await core.hashFile(image);
    if (r.image_sha256 !== undefined) requireValue(checked.sha256 === core.sha(r.image_sha256));
    const release = provisioning.releaseMarker(image);
    return {ok:true,...checked,version:String(release.version || ''),features:release.features,hash_matches:r.image_sha256 !== undefined,signature_verified:false};
  }
  if (operation === 'prepare') return prepare(r);
  throw Error('operation');
}
if (require.main === module) main().then(emit).catch(() => {
  // Never echo native errors, input, credentials, paths or provider files.
  emit({ok:false,error:'Operation failed. Check command, JSON schema, image SHA-256, new destination, profile and Node >=22. See references/interface.md.'}); process.exitCode = 1;
});
