'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const {findGptPartition, parseFat32Params, writeFat32File, readFat32File, formatShortName} = require('../fat32-writer.cjs');

test('formatShortName formats 8.3 accurately', () => {
  assert.equal(formatShortName('bitlocker.json'), 'BITLOCKEJSO');
  assert.equal(formatShortName('test.txt'), 'TEST    TXT');
  assert.equal(formatShortName('aguja.conf'), 'AGUJA   CON');
});

test('GPT and FAT32 writing into a synthetic disk image', () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'aguja-fat32-test-'));
  const imgPath = path.join(tmpDir, 'test.img');

  try {
    // Crear imagen sintética con GPT y partición FAT32 mínima
    const totalSectors = 20480; // 10MB
    const sectorSize = 512;
    const imgSize = totalSectors * sectorSize;
    const buf = Buffer.alloc(imgSize, 0);

    // LBA 1: GPT Header
    const gptHeader = Buffer.alloc(512);
    gptHeader.write('EFI PART', 0, 8, 'ascii');
    gptHeader.writeUInt32LE(0x00010000, 8); // Revision
    gptHeader.writeUInt32LE(92, 12); // Header size
    gptHeader.writeBigUInt64LE(1n, 24); // MyLBA
    gptHeader.writeBigUInt64LE(2n, 72); // PartitionEntryLBA
    gptHeader.writeUInt32LE(128, 80); // NumberOfPartitionEntries
    gptHeader.writeUInt32LE(128, 84); // SizeOfPartitionEntry
    gptHeader.copy(buf, 512);

    // LBA 2: Partition Entry 0 (AGUJA_CFG)
    const partEntry = Buffer.alloc(128);
    // Type GUID: Basic Data Partition (EBD0A0A2-B9E5-4433-87C0-68B6B72699C7)
    partEntry.writeUInt8(0xa2, 0); partEntry.writeUInt8(0xa0, 1); partEntry.writeUInt8(0xd0, 2); partEntry.writeUInt8(0xeb, 3);
    // Start LBA: 100, End LBA: 20000
    partEntry.writeBigUInt64LE(100n, 32);
    partEntry.writeBigUInt64LE(20000n, 40);
    // Partition name: AGUJA_CFG
    const labelBuf = Buffer.from('AGUJA_CFG\0', 'utf16le');
    labelBuf.copy(partEntry, 56);
    partEntry.copy(buf, 1024);

    // Partición en LBA 100 (offset 51200): FAT32 Boot Sector
    const partOffset = 100 * sectorSize;
    const boot = Buffer.alloc(512);
    boot.writeUInt16LE(512, 11); // Bytes per sector
    boot.writeUInt8(1, 13); // Sectors per cluster
    boot.writeUInt16LE(32, 14); // Reserved sectors
    boot.writeUInt8(2, 16); // Number of FATs
    boot.writeUInt32LE(100, 36); // Sectors per FAT
    boot.writeUInt32LE(2, 44); // Root cluster
    boot.write('FAT32   ', 82, 8, 'ascii');
    boot.copy(buf, partOffset);

    // Inicializar FAT1 y FAT2 con cluster 2 marcado como EOF (0x0FFFFFFF)
    const fat1Offset = partOffset + 32 * sectorSize;
    const fat2Offset = fat1Offset + 100 * sectorSize;
    // Cluster 0: Media descriptor (0x0FFFFFF8)
    buf.writeUInt32LE(0x0ffffff8, fat1Offset);
    buf.writeUInt32LE(0x0ffffff8, fat2Offset);
    // Cluster 1: Dirty bit / reserved (0x0FFFFFFF)
    buf.writeUInt32LE(0x0fffffff, fat1Offset + 4);
    buf.writeUInt32LE(0x0fffffff, fat2Offset + 4);
    // Cluster 2: Root directory EOF (0x0FFFFFFF)
    buf.writeUInt32LE(0x0fffffff, fat1Offset + 8);
    buf.writeUInt32LE(0x0fffffff, fat2Offset + 8);

    fs.writeFileSync(imgPath, buf);

    // Probar escribir un archivo JSON en la partición FAT32
    const testPayload = JSON.stringify({
      version: 1,
      name: 'bitlocker-test',
      keys: ['328526-103598-611028-671770-213730-124663-548845-598488']
    }, null, 2);

    const result = writeFat32File(imgPath, 'AGUJA_CFG', 'bitlock.jso', Buffer.from(testPayload, 'utf8'));
    assert.equal(result.ok, true);
    assert.equal(result.bytes, Buffer.byteLength(testPayload));

    // Leer de vuelta y verificar
    const fd = fs.openSync(imgPath, 'r');
    const partition = findGptPartition(fd, 'AGUJA_CFG');
    const params = parseFat32Params(fd, partition.offset);
    const readback = readFat32File(fd, params, 'bitlock.jso');
    fs.closeSync(fd);

    assert.ok(readback);
    assert.equal(readback.toString('utf8'), testPayload);
  } finally {
    fs.rmSync(tmpDir, {recursive: true, force: true});
  }
});
