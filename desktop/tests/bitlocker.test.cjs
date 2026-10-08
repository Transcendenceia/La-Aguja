'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const bitlocker = require('../bitlocker.cjs');

test('cleanMountPoint normalizes drive letters correctly', () => {
  assert.equal(bitlocker.cleanMountPoint('c'), 'C:');
  assert.equal(bitlocker.cleanMountPoint('C:'), 'C:');
  assert.equal(bitlocker.cleanMountPoint('d:'), 'D:');
  assert.throws(() => bitlocker.cleanMountPoint('invalid'), /Punto de montaje no válido/);
  assert.throws(() => bitlocker.cleanMountPoint('1:'), /Punto de montaje no válido/);
});

test('buildBitLockerPayload builds standard JSON payload', () => {
  const payload = bitlocker.buildBitLockerPayload([
    {
      mountPoint: 'C:',
      keyProtectorId: '{B9F9EEAC-589B-4D50-9F0D-5A5543F729AF}',
      recoveryPassword: '328526-103598-611028-671770-213730-124663-548845-598488',
      encryptionMethod: 'Aes128'
    }
  ]);

  assert.equal(payload.schema, 1);
  assert.equal(payload.source, 'LA AGUJA Flash Imager (Windows)');
  assert.ok(payload.exportedAt);
  assert.equal(payload.volumes.length, 1);
  assert.equal(payload.volumes[0].mountPoint, 'C:');
  assert.equal(payload.volumes[0].recoveryPassword, '328526-103598-611028-671770-213730-124663-548845-598488');
});

test('on non-Windows, BitLocker status reports unavailable gracefully', async () => {
  if (process.platform !== 'win32') {
    const status = await bitlocker.getBitLockerStatus();
    assert.equal(status.available, false);
    assert.deepEqual(status.volumes, []);
    await assert.rejects(async () => bitlocker.suspendBitLocker('C:'), /BitLocker solo está disponible en Windows/);
    await assert.rejects(async () => bitlocker.getRecoveryKey('C:'), /BitLocker solo está disponible en Windows/);
  }
});

test('limited Windows query explicitly requires UAC instead of falsely reporting no units',async()=>{
 let elevated;
 const status=await bitlocker.getBitLockerStatus({platform:'win32',query:async(script,options)=>{elevated=options.elevated;return JSON.stringify({available:true,requiresElevation:true,volumes:[]});}});
 assert.equal(elevated,false);assert.equal(status.requiresElevation,true);assert.equal(status.available,true);
});
test('authorized status projects public metadata only, never recovery material',async()=>{
 let elevated;
 const status=await bitlocker.getBitLockerStatus({authorize:true,platform:'win32',query:async(script,options)=>{elevated=options.elevated;return JSON.stringify({available:true,requiresElevation:false,volumes:[{mountPoint:'C:',volumeType:'OperatingSystem',volumeStatus:'FullyEncrypted',protectionStatus:'On',encryptionPercentage:100,hasRecoveryPassword:true,recoveryPassword:'SYNTHETIC-SECRET'}]});}});
 assert.equal(elevated,true);assert.equal(status.volumes[0].protectionStatus,'On');assert.equal(status.volumes[0].encryptionPercentage,100);assert(!JSON.stringify(status).includes('SYNTHETIC-SECRET'));
 assert(!bitlocker.STATUS_SCRIPT.includes('.RecoveryPassword'));
});
test('cancelled UAC and malformed status remain retryable failures, not empty successful inventory',async()=>{
 const canceled=await bitlocker.getBitLockerStatus({authorize:true,platform:'win32',query:async()=>JSON.stringify({ok:false,canceled:true,error:'Permission cancelled'})});
 assert.equal(canceled.available,true);assert.equal(canceled.requiresElevation,true);assert.equal(canceled.canceled,true);assert.equal(canceled.error,'Permission cancelled');
 for(const response of ['','{}','garbled']){const invalid=await bitlocker.getBitLockerStatus({platform:'win32',query:async()=>response});assert(invalid.error);assert.equal(invalid.available,true);}
});
