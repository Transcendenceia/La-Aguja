'use strict';
const crypto = require('node:crypto');

// Pure Node.js ESP-IDF NVS v2 partition binary generator (zero external dependencies;
// identical output on Linux and Windows). Matches esp_idf_nvs_partition_gen v2.
const PAGE_SIZE = 4096;
const ENTRY_SIZE = 32;
const MAX_ENTRIES_PER_PAGE = 126;
const MAX_STRING_BYTES = 4000; // NVS v2 single-page string limit (incl. trailing NUL)
const DEFAULT_PARTITION_SIZE = 49152; // 48 KiB (0xC000) matching partitions.csv

const PAGE_STATE_ACTIVE = 0xFFFFFFFE;
const PAGE_VERSION_V2 = 0xFE;
const ENTRY_TYPE_U8 = 0x01;
const ENTRY_TYPE_SZ = 0x21;
const CHUNK_ANY = 0xFF;

// Standard IEEE 802.3 CRC32 table; ESP-IDF NVS uses zlib.crc32(data, 0xFFFFFFFF).
const CRC32_TABLE = (() => {
  const table = new Uint32Array(256);
  for (let i = 0; i < 256; i++) {
    let c = i;
    for (let k = 0; k < 8; k++) c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
    table[i] = c >>> 0;
  }
  return table;
})();

function espNvsCrc32(buf) {
  // zlib.crc32(buf, 0xFFFFFFFF) starts internal CRC register at (0xFFFFFFFF ^ 0xFFFFFFFF) = 0,
  // and finalizes with (^ 0xFFFFFFFF).
  let crc = 0x00000000;
  for (let i = 0; i < buf.length; i++) {
    crc = CRC32_TABLE[(crc ^ buf[i]) & 0xFF] ^ (crc >>> 8);
  }
  return (crc ^ 0xFFFFFFFF) >>> 0;
}

function fail(message) {
  throw new Error(message);
}

function cleanStr(val, maxLen, fieldLabel) {
  if (val === undefined || val === null) return '';
  if (typeof val !== 'string') fail(`Valor no válido en ${fieldLabel}.`);
  if (/[\0\r\n]/.test(val)) fail(`Caracteres no permitidos en ${fieldLabel}.`);
  const trimmed = val.trim();
  if (Buffer.byteLength(trimmed, 'utf8') > maxLen) {
    fail(`${fieldLabel} supera el máximo de ${maxLen} bytes.`);
  }
  return trimmed;
}

function cleanSecret(val, maxLen, fieldLabel) {
  if (val === undefined || val === null) return '';
  if (typeof val !== 'string') fail(`Valor no válido en ${fieldLabel}.`);
  if (/[\0\r\n]/.test(val)) fail(`Caracteres no permitidos en ${fieldLabel}.`);
  if (Buffer.byteLength(val, 'utf8') > maxLen) {
    fail(`${fieldLabel} supera el máximo de ${maxLen} bytes.`);
  }
  return val;
}

function normalizeControlHost(raw) {
  const s = cleanStr(raw, 128, 'servidor de control');
  if (!s) return 'controlplane.tailscale.com';
  let host = s;
  if (/^https?:\/\//i.test(host)) {
    let u;
    try { u = new URL(host); } catch { fail('La dirección del servidor de control no es válida.'); }
    if (u.protocol !== 'https:') fail('El servidor de control debe usar HTTPS.');
    host = u.hostname;
  }
  if (!/^[a-zA-Z0-9.-]{1,63}$/.test(host) || host.startsWith('.') || host.endsWith('.')) {
    fail('El dominio del servidor de control no es válido.');
  }
  return host.toLowerCase();
}

function generateApiToken() {
  return 'agj_' + crypto.randomBytes(24).toString('hex');
}

function buildInitConfig(input, board = null) {
  if (!input || typeof input !== 'object') fail('Falta la configuración IoT.');

  // 1. Wi-Fi profiles (1..8)
  const rawWifi = Array.isArray(input.wifiProfiles) ? input.wifiProfiles : [];
  const profiles = [];
  const seen = new Set();
  for (const row of rawWifi) {
    if (!row || typeof row !== 'object') continue;
    const ssid = cleanStr(row.ssid, 32, 'nombre de red Wi-Fi');
    const pass = cleanSecret(row.password ?? row.pass ?? '', 64, 'contraseña Wi-Fi');
    if (!ssid) continue;
    if (seen.has(ssid)) continue;
    seen.add(ssid);
    profiles.push({ ssid, pass });
    if (profiles.length >= 8) break;
  }
  if (!profiles.length) {
    fail('Añade al menos una red Wi-Fi para que el microcontrolador pueda conectarse.');
  }

  // 2. SoftAP bridge / fallback (disabled by default)
  const apIn = input.ap || {};
  const apEnabled = Boolean(apIn.enabled);
  const apSsid = cleanStr(apIn.ssid || 'Aguja-IoT-AP', 32, 'nombre del SoftAP') || 'Aguja-IoT-AP';
  const apPass = cleanSecret(apIn.password ?? apIn.pass ?? '', 64, 'contraseña del SoftAP');
  if (apEnabled && apPass.length > 0 && apPass.length < 8) {
    fail('La contraseña del SoftAP debe tener al menos 8 caracteres (o quedar vacía para red abierta).');
  }
  const apChannel = Number.isInteger(Number(apIn.channel)) && Number(apIn.channel) >= 1 && Number(apIn.channel) <= 13
    ? Number(apIn.channel)
    : 6;

  // 3. Tailnet / Headscale & proxy settings
  const tnIn = input.tailnet || {};
  const hostname = cleanStr(tnIn.hostname || 'aguja-iot', 47, 'nombre del nodo') || 'aguja-iot';
  if (!/^[a-zA-Z0-9][a-zA-Z0-9-]{0,46}$/.test(hostname)) {
    fail('El nombre del nodo solo puede tener letras, números y guiones.');
  }
  const ctrlHost = normalizeControlHost(tnIn.ctrlHost || tnIn.loginServer || '');
  const noiseHex = cleanStr(tnIn.ctrlNoisePubkeyHex || '', 64, 'clave Noise').toLowerCase();
  if (noiseHex && !/^[0-9a-f]{64}$/.test(noiseHex)) {
    fail('La clave Noise del servidor debe tener exactamente 64 caracteres hexadecimales.');
  }
  const authKey = cleanSecret(tnIn.authKey || '', 127, 'clave de alta Tailscale / Headscale').trim();
  if (!authKey) {
    fail('Introduce la clave de alta (auth key / pre-auth key) de Tailscale o Headscale.');
  }
  const derpRegion = Number(tnIn.derpRegion || (ctrlHost === 'controlplane.tailscale.com' ? 9 : 999));
  if (!Number.isInteger(derpRegion) || derpRegion < 1 || derpRegion > 65535) {
    fail('La región DERP debe ser un número entero entre 1 y 65535.');
  }
  const extraRoutes = cleanStr(tnIn.extraRoutes || '', 127, 'rutas extra');
  const dnsUpstream = cleanStr(tnIn.dnsUpstream || '1.1.1.1', 19, 'DNS upstream') || '1.1.1.1';

  // 4. Hardware options
  const hwIn = input.hw || {};
  const antennaExternal = Boolean(board?.has_rf_switch && hwIn.antennaExternal);

  // 5. Agent control plane
  const agIn = input.agent || {};
  let apiToken = cleanSecret(agIn.apiToken || '', 64, 'token API del agente').trim();
  if (!apiToken) apiToken = generateApiToken();
  if (apiToken.length < 8) fail('El token API del agente debe tener al menos 8 caracteres.');
  const beaconEnabled = Boolean(agIn.beaconEnabled && agIn.beaconIp);
  const beaconIp = cleanStr(agIn.beaconIp || '', 19, 'IP del beacon UDP');
  const beaconPort = Number(agIn.beaconPort || 9420);
  if (beaconEnabled && (!Number.isInteger(beaconPort) || beaconPort < 1 || beaconPort > 65535)) {
    fail('El puerto del beacon UDP debe estar entre 1 y 65535.');
  }

  return {
    wifi: {
      profiles,
      tx_power_dbm: 20,
      ps_mode: 0,
    },
    ap: {
      enabled: apEnabled,
      ssid: apSsid,
      pass: apPass,
      channel: apChannel,
      max_conn: 4,
    },
    tailnet: {
      hostname,
      ctrl_host: ctrlHost,
      ctrl_noise_pubkey_hex: noiseHex,
      auth_key: authKey,
      derp_region: derpRegion,
      exit_node_enabled: tnIn.exitNodeEnabled !== false,
      advertise_upstream_subnet: tnIn.advertiseUpstreamSubnet !== false,
      advertise_ap_subnet: apEnabled && Boolean(tnIn.advertiseApSubnet),
      extra_routes: extraRoutes,
      dns_relay_enabled: tnIn.dnsRelayEnabled !== false,
      dns_upstream: dnsUpstream,
    },
    hw: {
      antenna_external: antennaExternal,
      led_mode: 0,
    },
    agent: {
      api_token: apiToken,
      http_allow_lan: Boolean(agIn.httpAllowLan),
      beacon_enabled: beaconEnabled,
      beacon_ip: beaconIp,
      beacon_port: beaconEnabled ? beaconPort : 9420,
      beacon_interval_s: 60,
    },
  };
}

function makeKeyBytes(key) {
  const raw = Buffer.from(key, 'utf8');
  if (raw.length === 0 || raw.length > 15) {
    fail(`Clave NVS inválida: ${key}`);
  }
  const out = Buffer.alloc(16, 0x00);
  raw.copy(out, 0);
  return out;
}

function finalizeEntryCrc(entry) {
  const crcInput = Buffer.concat([entry.subarray(0, 4), entry.subarray(8, 32)]);
  entry.writeUInt32LE(espNvsCrc32(crcInput), 4);
}

function generateNvsPartition(entries, { sizeBytes = DEFAULT_PARTITION_SIZE } = {}) {
  if (!Number.isInteger(sizeBytes) || sizeBytes < PAGE_SIZE * 3 || (sizeBytes % PAGE_SIZE) !== 0) {
    fail('El tamaño de la partición NVS debe ser múltiplo de 4096 bytes (mínimo 12 KiB).');
  }
  const partition = Buffer.alloc(sizeBytes, 0xFF);
  const page = partition.subarray(0, PAGE_SIZE);

  // Page 0 header (bytes 0..31)
  page.writeUInt32LE(PAGE_STATE_ACTIVE, 0);
  page.writeUInt32LE(0, 4); // seq = 0
  page[8] = PAGE_VERSION_V2;
  const headerCrc = espNvsCrc32(page.subarray(4, 28));
  page.writeUInt32LE(headerCrc, 28);

  // Entry state bitmap (bytes 32..63), all 0xFF initially
  let entryNum = 0;
  function markWritten(count) {
    for (let i = 0; i < count; i++) {
      const bitnum = (entryNum + i) * 2;
      const byteIdx = 32 + (bitnum >> 3);
      const bitOff = bitnum & 7;
      page[byteIdx] &= ~(1 << bitOff);
    }
  }
  function writeRawSlots(buf, count) {
    if (entryNum + count > MAX_ENTRIES_PER_PAGE) {
      fail('La configuración NVS excede una página (4000 bytes). Reduce rutas o redes Wi-Fi.');
    }
    const offset = 64 + entryNum * ENTRY_SIZE;
    buf.copy(page, offset);
    markWritten(count);
    entryNum += count;
  }

  const namespaces = new Map();
  let nextNsIdx = 1;

  for (const item of entries) {
    const ns = item.namespace || 'aguja_cfg';
    let nsIdx = namespaces.get(ns);
    if (!nsIdx) {
      nsIdx = nextNsIdx++;
      namespaces.set(ns, nsIdx);
      const nsEntry = Buffer.alloc(ENTRY_SIZE, 0xFF);
      nsEntry[0] = 0; // namespace table lives in ns 0
      nsEntry[1] = ENTRY_TYPE_U8;
      nsEntry[2] = 1; // span = 1
      nsEntry[3] = CHUNK_ANY;
      makeKeyBytes(ns).copy(nsEntry, 8);
      nsEntry.writeUInt8(nsIdx, 24);
      finalizeEntryCrc(nsEntry);
      writeRawSlots(nsEntry, 1);
    }

    if (item.type === 'string') {
      const dataWithNul = Buffer.concat([Buffer.from(String(item.value), 'utf8'), Buffer.from([0x00])]);
      if (dataWithNul.length > MAX_STRING_BYTES) {
        fail(`El valor de ${item.key} supera el límite de ${MAX_STRING_BYTES} bytes de NVS.`);
      }
      const dataEntries = Math.ceil(dataWithNul.length / ENTRY_SIZE);
      const header = Buffer.alloc(ENTRY_SIZE, 0xFF);
      header[0] = nsIdx;
      header[1] = ENTRY_TYPE_SZ;
      header[2] = 1 + dataEntries;
      header[3] = CHUNK_ANY;
      makeKeyBytes(item.key).copy(header, 8);
      header.writeUInt16LE(dataWithNul.length, 24);
      header.writeUInt32LE(espNvsCrc32(dataWithNul), 28);
      finalizeEntryCrc(header);

      const paddedData = Buffer.alloc(dataEntries * ENTRY_SIZE, 0xFF);
      dataWithNul.copy(paddedData, 0);

      writeRawSlots(header, 1);
      writeRawSlots(paddedData, dataEntries);
    } else if (item.type === 'u8') {
      const entry = Buffer.alloc(ENTRY_SIZE, 0xFF);
      entry[0] = nsIdx;
      entry[1] = ENTRY_TYPE_U8;
      entry[2] = 1;
      entry[3] = CHUNK_ANY;
      makeKeyBytes(item.key).copy(entry, 8);
      entry.writeUInt8(Number(item.value) & 0xFF, 24);
      finalizeEntryCrc(entry);
      writeRawSlots(entry, 1);
    } else {
      fail(`Tipo NVS no soportado: ${item.type}`);
    }
  }

  return partition;
}

function buildProvisioningNvs(configInput, board = null, { sizeBytes = DEFAULT_PARTITION_SIZE } = {}) {
  const config = buildInitConfig(configInput, board);
  const json = JSON.stringify(config);
  const partition = generateNvsPartition([
    { namespace: 'aguja_cfg', key: 'init_json', type: 'string', value: json },
  ], { sizeBytes });
  return {
    config,
    jsonBytes: Buffer.byteLength(json, 'utf8'),
    partition,
    sha256: crypto.createHash('sha256').update(partition).digest('hex'),
  };
}

module.exports = {
  PAGE_SIZE,
  DEFAULT_PARTITION_SIZE,
  espNvsCrc32,
  generateApiToken,
  normalizeControlHost,
  buildInitConfig,
  generateNvsPartition,
  buildProvisioningNvs,
};
