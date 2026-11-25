'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const iotNvs = require('../iot-nvs.cjs');

test('buildInitConfig normalizes Wi-Fi, Headscale/Tailscale proxy defaults, and generates API token', () => {
  const board = { id: 'seeed-xiao-esp32c6', has_rf_switch: true };
  const cfg = iotNvs.buildInitConfig({
    wifiProfiles: [
      { ssid: 'FieldNet', password: 'synthetic-wifi-pass' },
      { ssid: 'FieldNet', password: 'duplicate-ignored' },
      { ssid: 'BackupNet', password: '' },
    ],
    ap: { enabled: true, ssid: 'Aguja-Field', password: 'synthetic-ap-pass', channel: 11 },
    tailnet: {
      hostname: 'aguja-field-01',
      ctrlHost: 'https://headscale.example.invalid/',
      ctrlNoisePubkeyHex: 'a'.repeat(64),
      authKey: 'synthetic-preauth-key-0001',
      derpRegion: 999,
      exitNodeEnabled: true,
      advertiseUpstreamSubnet: true,
      advertiseApSubnet: true,
      dnsRelayEnabled: true,
      dnsUpstream: '1.1.1.1',
    },
    hw: { antennaExternal: true },
    agent: { httpAllowLan: false },
  }, board);

  assert.equal(cfg.wifi.profiles.length, 2);
  assert.equal(cfg.wifi.profiles[0].ssid, 'FieldNet');
  assert.equal(cfg.wifi.profiles[1].ssid, 'BackupNet');
  assert.equal(cfg.ap.channel, 11);
  assert.equal(cfg.tailnet.ctrl_host, 'headscale.example.invalid');
  assert.equal(cfg.tailnet.ctrl_noise_pubkey_hex, 'a'.repeat(64));
  assert.equal(cfg.tailnet.exit_node_enabled, true);
  assert.equal(cfg.tailnet.advertise_upstream_subnet, true);
  assert.equal(cfg.tailnet.advertise_ap_subnet, true);
  assert.equal(cfg.tailnet.dns_relay_enabled, true);
  assert.equal(cfg.hw.antenna_external, true);
  assert.match(cfg.agent.api_token, /^agj_[0-9a-f]{48}$/);
});

test('buildInitConfig disables SoftAP and AP subnet by default', () => {
  const cfg = iotNvs.buildInitConfig({
    wifiProfiles: [{ ssid: 'FieldNet', password: 'synthetic-wifi-pass' }],
    tailnet: { authKey: 'synthetic-key-123' },
  });
  assert.equal(cfg.ap.enabled, false);
  assert.equal(cfg.tailnet.advertise_ap_subnet, false);
  assert.equal(cfg.tailnet.exit_node_enabled, true);
  assert.equal(cfg.tailnet.advertise_upstream_subnet, true);
  assert.equal(cfg.tailnet.dns_relay_enabled, true);
});

test('buildInitConfig rejects missing Wi-Fi, missing auth key, non-HTTPS control server, and short SoftAP password', () => {
  assert.throws(() => iotNvs.buildInitConfig({ wifiProfiles: [], tailnet: { authKey: 'k' } }), /al menos una red Wi-Fi/);
  assert.throws(() => iotNvs.buildInitConfig({ wifiProfiles: [{ ssid: 'Net' }], tailnet: { authKey: '' } }), /clave de alta/);
  assert.throws(() => iotNvs.buildInitConfig({ wifiProfiles: [{ ssid: 'Net' }], tailnet: { ctrlHost: 'http://insecure.example', authKey: 'k' } }), /HTTPS/);
  assert.throws(() => iotNvs.buildInitConfig({ wifiProfiles: [{ ssid: 'Net' }], ap: { enabled: true, password: 'short' }, tailnet: { authKey: 'k' } }), /al menos 8 caracteres/);
  assert.throws(() => iotNvs.buildInitConfig({ wifiProfiles: [{ ssid: 'Net' }], tailnet: { ctrlNoisePubkeyHex: 'not-hex', authKey: 'k' } }), /64 caracteres hexadecimales/);
});

test('buildProvisioningNvs produces a valid 48 KiB ESP-IDF NVS v2 binary with CRC32 headers', () => {
  const result = iotNvs.buildProvisioningNvs({
    wifiProfiles: [{ ssid: 'LabWiFi', password: 'synthetic-password-123' }],
    tailnet: {
      hostname: 'aguja-test',
      ctrlHost: 'controlplane.tailscale.com',
      authKey: 'synthetic-auth-key-123',
      derpRegion: 9,
    },
  });

  assert.equal(result.partition.length, 49152);
  assert.equal(result.partition.readUInt32LE(0), 0xFFFFFFFE); // ACTIVE
  assert.equal(result.partition.readUInt32LE(4), 0);          // seq 0
  assert.equal(result.partition[8], 0xFE);                    // NVS v2
  assert.equal(result.partition.readUInt32LE(28), iotNvs.espNvsCrc32(result.partition.subarray(4, 28)));
  assert.match(result.sha256, /^[0-9a-f]{64}$/);
  assert.equal(result.partition.toString('utf8').includes('"hostname":"aguja-test"'), true);

  // Cross-verify against ESP-IDF's official nvs_partition_gen.py when installed locally
  const idfPy = path.join(os.homedir(), '.espressif/python_env/idf5.5_py3.13_env/bin/python');
  const genPy = path.join(os.homedir(), 'esp/esp-idf/components/nvs_flash/nvs_partition_generator/nvs_partition_gen.py');
  if (fs.existsSync(idfPy) && fs.existsSync(genPy)) {
    const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'aguja-nvs-test-'));
    try {
      const json = JSON.stringify(result.config);
      const csvPath = path.join(tmp, 'in.csv');
      const refBin = path.join(tmp, 'ref.bin');
      fs.writeFileSync(csvPath, `key,type,encoding,value\naguja_cfg,namespace,,\ninit_json,data,string,"${json.replaceAll('"', '""')}"\n`);
      const proc = spawnSync(idfPy, [genPy, 'generate', csvPath, refBin, '0xC000'], { encoding: 'utf8' });
      assert.equal(proc.status, 0, proc.stderr);
      const expected = fs.readFileSync(refBin);
      assert.equal(Buffer.compare(result.partition, expected), 0, 'NVS binary must match ESP-IDF nvs_partition_gen byte-for-byte');
    } finally {
      fs.rmSync(tmp, { recursive: true, force: true });
    }
  }
});
