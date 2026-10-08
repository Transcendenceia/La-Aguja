'use strict';
const {_electron:electron}=require('playwright');
const assert=require('node:assert/strict');const fs=require('node:fs');const path=require('node:path');const os=require('node:os');const crypto=require('node:crypto');
(async()=>{
 const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'aguja-import-qa-'));let application;
 try{
  const image=path.join(tmp,'aguja-0.4.1.img'),other=path.join(tmp,'other.img');
  fs.writeFileSync(image,Buffer.alloc(1048576,7));fs.writeFileSync(other,Buffer.alloc(1048576,9));
  const digest=crypto.createHash('sha256').update(fs.readFileSync(image)).digest('hex');
  application=await electron.launch({...(process.env.AGUJA_QA_EXECUTABLE?{executablePath:process.env.AGUJA_QA_EXECUTABLE}:{}),args:[path.resolve(__dirname,'..'),'--lang=es','--no-sandbox','--user-data-dir='+path.join(tmp,'state')],env:{...process.env,ELECTRON_DISABLE_SECURITY_WARNINGS:'1'}});
  const window=await application.firstWindow();await window.waitForLoadState('domcontentloaded');
  // Production pin is never modified. Main-process fixtures provide a synthetic
  // signed catalog and intercept only the fixed GET and native file chooser.
  await application.evaluate(({app,dialog},fixture)=>{
   const require=process.getBuiltinModule('node:module').createRequire(app.getAppPath()+'/main.cjs');
   const path=require('node:path'),fs=require('node:fs'),crypto=require('node:crypto'),core=require(path.join(app.getAppPath(),'core.cjs'));
   const pair=crypto.generateKeyPairSync('ed25519');const pin={key_id:'synthetic-import-fixture',public_key_pem:pair.publicKey.export({type:'spki',format:'pem'}),catalog_url:'https://example.invalid/fixed-catalog'};
   const read=fs.promises.readFile;fs.promises.readFile=async function(filename,...args){if(filename===path.join(app.getAppPath(),'resources','release-key.json'))return JSON.stringify(pin);return read.call(this,filename,...args);};
   globalThis.importFixture={...fixture,mode:'offline',calls:0,picks:0};
   dialog.showOpenDialog=async()=>{globalThis.importFixture.picks++;return {canceled:false,filePaths:[globalThis.importFixture.image]};};
   core.getHTTPS=async(url,maxBytes,timeoutMs)=>{
    if(url!==pin.catalog_url||maxBytes!==65536||timeoutMs!==4000)throw new Error('Unexpected catalog request');
    globalThis.importFixture.calls++;
    if(globalThis.importFixture.mode==='offline')throw new Error('Synthetic offline fixture');
    const payload=Buffer.from(JSON.stringify({schema:1,expires_at:new Date(Date.now()+1000).toISOString(),releases:[{version:'0.4.1',url:'https://example.invalid/aguja.img',bytes:1048576,sha256:fixture.digest}]}));
    return {key_id:pin.key_id,payload:payload.toString('base64'),signature:crypto.sign(null,payload,pair.privateKey).toString('base64')};
   };
  },{image,digest});
  assert.equal(await window.locator('.image-advanced').getAttribute('open'),null);
  assert.equal(await window.locator('#image-sha').inputValue(),'');
  await window.locator('#image-import').click();await window.locator('#image-status').filter({hasText:'SHA calculado; origen no comprobado'}).waitFor();
  const local=await window.evaluate(()=>window.aguja.importImage());assert.equal(local.ok,true);assert.equal(local.image.sha256,digest);assert.equal(local.image.trusted,false);assert.equal(local.image.verification,'calculated-sha');assert.equal(local.image.version,undefined);assert.equal(local.image.path,undefined);
  await window.locator('#next').click();await window.locator('section[data-step="1"]').waitFor({state:'visible'});await window.locator('.step').nth(0).click();
  await window.locator('.image-advanced summary').click();await window.locator('#image-sha').fill('  '+digest.toUpperCase()+'  ');await window.locator('#image-import').click();await window.locator('#image-status').filter({hasText:'SHA-256 coincidente con el indicado'}).waitFor();
  const unchanged=await window.locator('#image-status').textContent();
  await window.locator('#image-sha').fill('0'.repeat(64));await window.locator('#image-import').click();await window.locator('#notification').filter({hasText:'no coincide'}).waitFor();assert.equal(await window.locator('#image-status').textContent(),unchanged);
  const picks=await application.evaluate(()=>globalThis.importFixture.picks);
  await window.locator('#image-sha').fill('bad');await window.locator('#image-import').click();await window.locator('#notification').filter({hasText:'64 caracteres'}).waitFor();assert.equal(await application.evaluate(()=>globalThis.importFixture.picks),picks);assert.equal(await window.locator('#image-status').textContent(),unchanged);
  await window.locator('#image-sha').fill('');await window.locator('.image-advanced summary').click();
  await application.evaluate(()=>{globalThis.importFixture.mode='signed';});
  // No explicit catalog button was used: automatic signed provenance succeeds.
  await window.locator('#image-import').click();await window.locator('#image-status').filter({hasText:'Versión oficial 0.4.1'}).waitFor();
  const authenticated=await window.evaluate(()=>window.aguja.importImage(''));assert.equal(authenticated.image.trusted,true);assert.equal(authenticated.image.verification,'verified-catalog');assert.equal(authenticated.image.version,'0.4.1');
  const calls=await application.evaluate(()=>globalThis.importFixture.calls);assert(calls>=4);
  // Valid cache is reused, but a different digest with the same size is local.
  await application.evaluate(({},filename)=>{globalThis.importFixture.image=filename;},other);
  const unmatched=await window.evaluate(()=>window.aguja.importImage(''));assert.equal(unmatched.image.trusted,false);assert.equal(unmatched.image.verification,'calculated-sha');assert.equal(await application.evaluate(()=>globalThis.importFixture.calls),calls);
  await new Promise(resolve=>setTimeout(resolve,1100));
  await application.evaluate(({},filename)=>{globalThis.importFixture.mode='offline';globalThis.importFixture.image=filename;},image);
  const expired=await window.evaluate(()=>window.aguja.importImage(''));assert.equal(expired.image.trusted,false);assert.equal(expired.image.verification,'calculated-sha');assert.equal(await application.evaluate(()=>globalThis.importFixture.calls),calls+1);
  console.log(JSON.stringify({ok:true,realElectron:true,noManualShaRequired:true,offlineImport:true,manualMismatchPreservesSelection:true,malformedRejectedBeforePicker:true,automaticSignedCatalog:true,validCacheReused:true,expiredCacheNotTrusted:true,filenameNotTrusted:true,noImageMetadataUploaded:true,physicalUsbWritten:false}));
 }finally{if(application)await application.close();fs.rmSync(tmp,{recursive:true,force:true});}
})().catch(error=>{console.error(error);process.exitCode=1;});
