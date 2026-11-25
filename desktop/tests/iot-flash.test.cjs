'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const iotFlash = require('../iot-flash.cjs');

test('loadBoards loads full ESP32-family board catalog and families', () => {
  const catalog = iotFlash.loadBoards({ rootDir: path.resolve(__dirname, '../..') });
  assert.ok(Array.isArray(catalog.boards));
  assert.ok(catalog.boards.length >= 10, `expected >=10 ESP32 boards, got ${catalog.boards.length}`);
  const ids = catalog.boards.map((b) => b.id);
  for (const id of ['seeed-xiao-esp32c6', 'esp32s3-wroom-n16r8', 'seeed-xiao-esp32s3', 'esp32c3-supermini', 'esp32-devkit-v1', 'esp32s2-mini']) {
    assert.ok(ids.includes(id), `missing board ${id}`);
  }
  for (const fam of ['ESP32-C6', 'ESP32-S3', 'ESP32-C3', 'ESP32', 'ESP32-S2']) {
    assert.ok(catalog.families.includes(fam), `missing family ${fam}`);
  }
  assert.equal(catalog.nvsProvisioning.init_json_key, 'init_json');
  assert.equal(catalog.nvsProvisioning.softap_default_enabled, false);
});

test('matchBoardFromProbe identifies exact board from real silicon telemetry', () => {
  const catalog = iotFlash.loadBoards({ rootDir: path.resolve(__dirname, '../..') });
  const mS3 = iotFlash.matchBoardFromProbe(
    { chip_normalized: 'esp32s3', flash_mb: 16, psram_mb: 8 },
    { vid: '1a86', pid: '55d3' },
    catalog.boards,
  );
  assert.equal(mS3?.boardId, 'esp32s3-wroom-n16r8');

  const mXiaoS3 = iotFlash.matchBoardFromProbe(
    { chip_normalized: 'esp32s3', flash_mb: 8, psram_mb: 8 },
    { vid: '303a', pid: '1001' },
    catalog.boards,
  );
  assert.equal(mXiaoS3?.boardId, 'seeed-xiao-esp32s3');

  const mC6 = iotFlash.matchBoardFromProbe(
    { chip_normalized: 'esp32c6', flash_mb: 4, psram_mb: 0 },
    { vid: '303a', pid: '1001' },
    catalog.boards,
  );
  assert.equal(mC6?.boardId, 'seeed-xiao-esp32c6');

  const mC3 = iotFlash.matchBoardFromProbe(
    { chip_normalized: 'esp32c3', flash_mb: 4, psram_mb: 0 },
    { vid: '303a', pid: '1001' },
    catalog.boards,
  );
  assert.equal(mC3?.boardId, 'esp32c3-supermini');

  const mEsp32 = iotFlash.matchBoardFromProbe(
    { chip_normalized: 'esp32', flash_mb: 4, psram_mb: 0 },
    { vid: '10c4', pid: 'ea60' },
    catalog.boards,
  );
  assert.equal(mEsp32?.boardId, 'esp32-devkit-v1');
});

test('listLinuxSerialPorts discovers ttyACM/ttyUSB devices from synthetic sysfs and matches board VID:PID', () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'aguja-sysfs-'));
  try {
    const devDir = path.join(tmp, 'dev');
    const sysClassTty = path.join(tmp, 'sys/class/tty');
    const usbParent = path.join(tmp, 'usb-device');
    const ifaceDir = path.join(usbParent, '1-2:1.0');
    const ttyDev = path.join(sysClassTty, 'ttyACM0');
    fs.mkdirSync(devDir, { recursive: true });
    fs.mkdirSync(ifaceDir, { recursive: true });
    fs.mkdirSync(ttyDev, { recursive: true });
    fs.writeFileSync(path.join(devDir, 'ttyACM0'), '');
    fs.writeFileSync(path.join(usbParent, 'idVendor'), '1a86\n');
    fs.writeFileSync(path.join(usbParent, 'idProduct'), '55d3\n');
    fs.writeFileSync(path.join(usbParent, 'product'), 'USB Single Serial\n');
    fs.writeFileSync(path.join(usbParent, 'serial'), 'SYNTH12345\n');
    fs.symlinkSync(ifaceDir, path.join(ttyDev, 'device'));

    const catalog = iotFlash.loadBoards({ rootDir: path.resolve(__dirname, '../..') });
    const ports = iotFlash.listLinuxSerialPorts(catalog.boards, {
      sysClassTty,
      devDir,
      byIdDir: path.join(tmp, 'no-by-id'),
    });
    assert.equal(ports.length, 1);
    assert.equal(ports[0].path, path.join(devDir, 'ttyACM0'));
    assert.equal(ports[0].usbId, '1a86:55d3');
    assert.equal(ports[0].accessible, true);
    assert.ok(ports[0].matchedBoardIds.includes('esp32s3-wroom-n16r8'));
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});

test('fetchControlNoiseKey parses mkey: prefix from /key?v=131 and rejects invalid keys', async () => {
  const hex = '0123456789abcdef'.repeat(4);
  const fetched = await iotFlash.fetchControlNoiseKey('https://headscale.example.invalid', {
    getHTTPS: async (url) => {
      assert.equal(url, 'https://headscale.example.invalid/key?v=131');
      return { PublicKey: 'mkey:' + hex };
    },
  });
  assert.equal(fetched.host, 'headscale.example.invalid');
  assert.equal(fetched.noisePubkeyHex, hex);

  await assert.rejects(
    () => iotFlash.fetchControlNoiseKey('headscale.example.invalid', {
      getHTTPS: async () => ({ PublicKey: 'invalid' }),
    }),
    /clave Noise válida/,
  );
});
