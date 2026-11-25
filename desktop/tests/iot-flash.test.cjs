'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const iotFlash = require('../iot-flash.cjs');

test('loadBoards loads iot/boards.json including ESP32-C6 and ESP32-S3-WROOM-1', () => {
  const catalog = iotFlash.loadBoards({ rootDir: path.resolve(__dirname, '../..') });
  assert.ok(Array.isArray(catalog.boards));
  const ids = catalog.boards.map((b) => b.id);
  assert.ok(ids.includes('seeed-xiao-esp32c6'));
  assert.ok(ids.includes('esp32s3-wroom-n16r8'));
  assert.equal(catalog.nvsProvisioning.init_json_key, 'init_json');
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
