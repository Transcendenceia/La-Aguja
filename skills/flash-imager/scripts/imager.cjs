#!/usr/bin/env node
'use strict';
// Harness-neutral interface to the SAME file preparation and IoT NVS engines as Flash Imager.
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
const reusableProfile = require(path.join(root,'desktop/reusable-profile.cjs'));
const iotNvs = require(path.join(root, 'desktop/iot-nvs.cjs'));
const VERSION = '1.3.0';
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
function destination(value, ext = '.img') {
  requireValue(typeof value === 'string' && path.isAbsolute(value) && path.extname(value).toLowerCase() === ext);
  const parent = fs.realpathSync(path.dirname(value));
  requireValue(fs.statSync(parent).isDirectory());
  const result = path.join(parent, path.basename(value));
  try { fs.lstatSync(result); throw Error('exists'); } catch (e) { if (e.code !== 'ENOENT') throw e; }
  return result;
}
function loadIotBoards() {
  const file = path.join(root, 'iot/boards.json');
  const raw = JSON.parse(fs.readFileSync(file, 'utf8'));
  requireValue(raw && Array.isArray(raw.boards));
  return raw;
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
async function buildIotNvs(r) {
  keys(r, ['board_id','output_path','wifi_profiles','ap','tailnet','hw','agent']);
  const registry = loadIotBoards();
  const board = registry.boards.find(b => b.id === r.board_id);
  requireValue(Boolean(board));
  const out = destination(r.output_path, '.bin');
  requireValue(Array.isArray(r.wifi_profiles) && r.wifi_profiles.length >= 1 && r.wifi_profiles.length <= 8);
  for (const w of r.wifi_profiles) keys(w, ['ssid','password']);
  if (r.ap !== undefined) keys(r.ap, ['enabled','ssid','password','channel']);
  keys(r.tailnet, ['hostname','ctrl_host','login_server','ctrl_noise_pubkey_hex','auth_key','derp_region','exit_node_enabled','advertise_upstream_subnet','advertise_ap_subnet','extra_routes','dns_relay_enabled','dns_upstream']);
  if (r.hw !== undefined) keys(r.hw, ['antenna_external']);
  if (r.agent !== undefined) keys(r.agent, ['api_token','http_allow_lan','beacon_enabled','beacon_ip','beacon_port']);
  const apiTokenSupplied = Boolean(r.agent?.api_token && String(r.agent.api_token).trim());
  const built = iotNvs.buildProvisioningNvs({
    wifiProfiles: r.wifi_profiles.map(w => ({ ssid: w.ssid, password: w.password || '' })),
    ap: r.ap ? { enabled: Boolean(r.ap.enabled), ssid: r.ap.ssid, password: r.ap.password, channel: r.ap.channel } : { enabled: false },
    tailnet: {
      hostname: r.tailnet.hostname,
      ctrlHost: r.tailnet.ctrl_host || r.tailnet.login_server || '',
      ctrlNoisePubkeyHex: r.tailnet.ctrl_noise_pubkey_hex || '',
      authKey: r.tailnet.auth_key,
      derpRegion: r.tailnet.derp_region,
      exitNodeEnabled: r.tailnet.exit_node_enabled !== false,
      advertiseUpstreamSubnet: r.tailnet.advertise_upstream_subnet !== false,
      advertiseApSubnet: Boolean(r.tailnet.advertise_ap_subnet),
      extraRoutes: r.tailnet.extra_routes || '',
      dnsRelayEnabled: r.tailnet.dns_relay_enabled !== false,
      dnsUpstream: r.tailnet.dns_upstream || '1.1.1.1',
    },
    hw: { antennaExternal: Boolean(r.hw?.antenna_external) },
    agent: {
      apiToken: r.agent?.api_token || '',
      httpAllowLan: Boolean(r.agent?.http_allow_lan),
      beaconEnabled: Boolean(r.agent?.beacon_enabled),
      beaconIp: r.agent?.beacon_ip || '',
      beaconPort: r.agent?.beacon_port,
    },
  }, board, { sizeBytes: registry.nvs_provisioning?.size_bytes || iotNvs.DEFAULT_PARTITION_SIZE });
  await fs.promises.writeFile(out, built.partition, { flag: 'wx', mode: 0o600 });
  return {
    ok: true,
    output_path: out,
    bytes: built.partition.length,
    sha256: built.sha256,
    json_bytes: built.jsonBytes,
    board_id: board.id,
    chip: board.chip,
    firmware_profile: board.firmware_profile,
    nvs_offset: board.flash_offsets?.nvs || registry.nvs_provisioning?.offset || '0x9000',
    hostname: built.config.tailnet.hostname,
    ctrl_host: built.config.tailnet.ctrl_host,
    wifi_count: built.config.wifi.profiles.length,
    ap_enabled: built.config.ap.enabled,
    exit_node_enabled: built.config.tailnet.exit_node_enabled,
    advertise_upstream_subnet: built.config.tailnet.advertise_upstream_subnet,
    dns_relay_enabled: built.config.tailnet.dns_relay_enabled,
    api_token_generated: !apiTokenSupplied,
    secret_values_returned: false,
    device_written: false,
  };
}
async function main() {
  requireValue(Number(process.versions.node.split('.')[0]) >= 22);
  const [operation, ...extra] = process.argv.slice(2); requireValue(extra.length === 0);
  if (operation === '--help') return {ok:true,version:VERSION,operations:['doctor','locales','catalog','download','inspect','prepare','save-profile','profile-info','iot-boards','iot-nvs'],input:'JSON stdin for download, inspect, prepare, save-profile, profile-info and iot-nvs',usb_writing:false,serial_flashing:false};
  if (operation === 'doctor') {
    const iot = loadIotBoards();
    return {ok:true,version:VERSION,imager_version:engineVersion,recovery_types:['bitlocker','luks'],node:process.versions.node,platform:process.platform,engine:'Flash Imager GPT/FAT32 + ESP-IDF NVS v2',profile_extensions:['wifi_profiles','environment','storage','tailscale'],extended_profile_feature:'imager-profile-v2',iot_nvs:true,iot_boards_count:iot.boards.length,usb_writing:false,serial_flashing:false};
  }
  if (operation === 'locales') return {ok:true,languages:core.LOCALE_CATALOG.languages,keyboards:core.LOCALE_CATALOG.keyboards};
  if (operation === 'catalog') return {ok:true,signature_verified:true,releases:await catalog()};
  if (operation === 'iot-boards') {
    const iot = loadIotBoards();
    return {ok:true,schema_version:iot.schema_version,nvs_provisioning:iot.nvs_provisioning,boards:iot.boards};
  }
  const r = await input();
  if(operation==='save-profile')return saveProfile(r);
  if(operation==='profile-info'){keys(r,['profile_path']);const e=readSavedProfile(r.profile_path);requireValue(e.format==='aguja-profile-aes256gcm'&&e.schema===1);return {ok:true,schema:e.schema,protection:'encrypted',secret_values_returned:false};}
  if (operation === 'iot-nvs') return buildIotNvs(r);
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
  emit({ok:false,error:'Operation failed. Check command, JSON schema, image SHA-256, new destination, profile/IoT settings and Node >=22. See references/interface.md and references/iot.md.'}); process.exitCode = 1;
});
