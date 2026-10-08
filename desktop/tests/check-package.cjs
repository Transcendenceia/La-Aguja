'use strict';
const fs=require('node:fs');const path=require('node:path');const assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../dist/linux-unpacked/resources');
for(const filename of ['scripts/platform-profile.py','scripts/flash-usb.py','runtime/i18n.py','runtime/profile.py','runtime/config.py','runtime/locale-catalog.json','wifi-helper.py'])assert(fs.statSync(path.join(root,'aguja',filename)).isFile(),filename);
const pkg=JSON.parse(fs.readFileSync(path.resolve(__dirname,'../package.json'),'utf8'));
assert.equal(pkg.devDependencies.electron,'40.10.6');assert.equal(pkg.devDependencies['electron-builder'],'26.15.3');
const pin=JSON.parse(fs.readFileSync(path.resolve(__dirname,'../resources/release-key.json'),'utf8'));assert(pin.public_key_pem.includes('BEGIN PUBLIC KEY'));
console.log(JSON.stringify({ok:true,helperFilesPresent:7,pinnedReleaseKey:true,portableLinuxFolder:true}));
