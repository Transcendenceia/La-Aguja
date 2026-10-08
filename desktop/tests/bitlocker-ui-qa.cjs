'use strict';
// Actual limited Windows, actual C: encrypted, actual UAC. No recovery key read.
const {_electron:electron}=require('playwright'),fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=process.env.AGUJA_QA_ROOT,exe=process.env.AGUJA_QA_EXECUTABLE;
if(process.platform!=='win32'||!root||!exe)throw Error('Windows QA required');
(async()=>{let app;try{
 fs.mkdirSync(root,{recursive:true});const env={...process.env};delete env.ELECTRON_RUN_AS_NODE;
 app=await electron.launch({executablePath:exe,chromiumSandbox:true,args:['--lang=es','--user-data-dir='+path.join(root,'isolated-state')],env});
 await app.evaluate(({app})=>{const req=process.getBuiltinModule('node:module').createRequire(app.getAppPath()+'/main.cjs'),bl=req('./bitlocker.cjs');globalThis.bitlockerSecretReads=0;bl.getRecoveryKey=async()=>{globalThis.bitlockerSecretReads++;throw Error('Actual recovery secrets excluded from QA');};});
 const w=await app.firstWindow();await w.waitForLoadState('domcontentloaded');await w.locator('#app-language').selectOption('es');
 const step=await w.locator('#bitlocker-card').evaluate(e=>Number(e.closest('[data-step]').dataset.step));await w.locator('.step').nth(step).click();
 await w.locator('#bitlocker-badge').filter({hasText:'Pendiente de autorización'}).waitFor();assert.equal(await w.locator('#bitlocker-inject').isChecked(),false);assert.equal(await app.evaluate(()=>globalThis.bitlockerSecretReads),0);
 await w.locator('#bitlocker-check-btn').click();fs.writeFileSync(path.join(root,'phase.json'),JSON.stringify({phase:'cancel-uac'}));
 await w.waitForFunction(()=>!document.getElementById('bitlocker-check-btn').disabled,{},{timeout:120000});
 const cancelMessage=await w.locator('#bitlocker-vol-status').innerText();fs.writeFileSync(path.join(root,'cancel-status.json'),JSON.stringify({message:cancelMessage}));
 assert(/autoriz|operación|comprobar/i.test(cancelMessage),'Cancellation must explain permission/query failure');assert(!cancelMessage.includes('No se detectaron'));assert(await w.locator('#bitlocker-card').isVisible());
 await w.locator('#bitlocker-check-btn').click();fs.writeFileSync(path.join(root,'phase.json'),JSON.stringify({phase:'accept-uac'}));
 await w.locator('#bitlocker-badge').filter({hasText:'Protegido'}).waitFor({timeout:120000});const status=await w.locator('#bitlocker-vol-status').innerText();assert(status.includes('C:'));assert(status.includes('100 %'));assert(status.includes('Protección activada'));
 assert.equal(await app.evaluate(()=>globalThis.bitlockerSecretReads),0);assert(await w.locator('#bitlocker-suspend-btn').isVisible());assert(await w.locator('#bitlocker-resume-btn').isHidden());assert.equal(await w.locator('#bitlocker-view-key-btn').isDisabled(),false);assert.equal(await w.locator('#bitlocker-inject').isChecked(),false);
 await w.screenshot({path:path.join(root,'bitlocker-protected.png'),fullPage:true,mask:[w.locator('#bitlocker-key-display')]});
 fs.writeFileSync(path.join(root,'result.json'),JSON.stringify({ok:true,limitedRequiresUAC:true,cancelStaysRetryable:true,realStatus:{mountPoint:'C:',protection:'On',encryptionPercentage:100},automaticSecretReads:0,protectionChanged:false,packaged:true},null,2));
 }catch(e){fs.writeFileSync(path.join(root,'result.json'),JSON.stringify({ok:false,error:e.message}));throw e;}finally{if(app)await app.close();}})().catch(e=>{console.error(e.message);process.exitCode=1;});
