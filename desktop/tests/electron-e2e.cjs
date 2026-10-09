'use strict';
const { _electron: electron }=require('playwright');const assert=require('node:assert/strict');const fs=require('node:fs');const path=require('node:path');const os=require('node:os');
(async()=>{
 const temp=fs.mkdtempSync(path.join(os.tmpdir(),'aguja-electron-qa-'));let application;
 const home=path.join(temp,'native-home'),authDir=path.join(home,'.gemini','antigravity-cli');fs.mkdirSync(authDir,{recursive:true});
 const auth=path.join(authDir,'antigravity-oauth-token'),marker='SYNTHETIC-PRIVATE-OAUTH-IPC';
 const native={token:{access_token:marker,token_type:'Bearer',refresh_token:marker,expiry:'2020-01-01T00:00:00Z'},auth_method:'consumer',id_token:marker};
 fs.writeFileSync(auth,JSON.stringify(native),{mode:0o600});
 const bin=path.join(home,'.local','bin');fs.mkdirSync(bin,{recursive:true});fs.writeFileSync(path.join(bin,'agy'),'synthetic fixture never executed',{mode:0o700});
 try{
 application=await electron.launch({...(process.env.AGUJA_QA_EXECUTABLE?{executablePath:process.env.AGUJA_QA_EXECUTABLE}:{}),args:[path.resolve(__dirname,'..'),'--lang=es','--no-sandbox','--user-data-dir='+path.join(temp,'user-data')],env:{...process.env,ELECTRON_RUN_AS_NODE:undefined,HOME:home,ELECTRON_DISABLE_SECURITY_WARNINGS:'1'}});
 const window=await application.firstWindow();await window.waitForLoadState('domcontentloaded');await window.locator('#app-language').selectOption('es');await window.waitForFunction(()=>document.documentElement.lang==='es');
 await window.locator('h1').first().waitFor();
 assert.equal(await window.locator('input[value=encrypted]').isChecked(),true);assert.equal(await window.locator('#unlock-password').inputValue(),'aguja');
 await application.evaluate(({shell})=>{globalThis.agujaDonationOpened='';shell.openExternal=async url=>{globalThis.agujaDonationOpened=url;};});
 await window.locator('#donate-open').click();await window.locator('#donation-dialog').waitFor({state:'visible'});assert.equal(await window.locator('#donation-dialog img').evaluate(image=>image.complete&&image.naturalWidth>0),true);await window.locator('#donate-link').click();assert.equal(await application.evaluate(()=>globalThis.agujaDonationOpened),'https://ko-fi.com/transcendenceia');await window.locator('#donation-dialog form button').click();await window.locator('#donation-dialog').waitFor({state:'hidden'});

 const security=await application.evaluate(({BrowserWindow})=>{const w=BrowserWindow.getAllWindows()[0],p=w.webContents.getLastWebPreferences();return {contextIsolation:p.contextIsolation,sandbox:p.sandbox,nodeIntegration:p.nodeIntegration};});
 assert.deepEqual(security,{contextIsolation:true,sandbox:true,nodeIntegration:false});
 assert.equal(await window.evaluate(()=>typeof window.require),'undefined');
 // A real IPC request validates and rejects the bad checksum before showing any file dialog.
 assert.equal(await window.locator('.image-advanced').getAttribute('open'),null);await window.locator('.image-advanced summary').click();await window.locator('#image-sha').fill('bad');await window.locator('#image-import').click();await window.locator('#notification').filter({hasText:'64 caracteres'}).waitFor();
 await window.locator('.step').nth(1).click();await window.locator('#eth-method').selectOption('manual');await window.locator('#static-fields').waitFor({state:'visible'});await window.getByRole('heading',{name:'Idioma y teclado'}).waitFor();await window.locator('#locale-language').selectOption('es_CO.UTF-8');await window.locator('#locale-keyboard').selectOption('latam');await window.locator('#locale-variant').selectOption('nodeadkeys');await window.locator('#locale-keyboard').selectOption('us');assert.equal(await window.locator('#locale-variant').inputValue(),'');await window.locator('#locale-variant').selectOption('intl');await window.locator('#locale-keyboard').selectOption('gb');assert.equal(await window.locator('#locale-variant option').count(),1);assert.equal(await window.locator('#locale-variant').inputValue(),'');
 await window.locator('#wifi-password').fill('SYNTHETIC-WIFI-NOT-A-SECRET');assert.equal(await window.locator('#wifi-password').getAttribute('type'),'password');await window.locator('[data-for="wifi-password"]').click();assert.equal(await window.locator('#wifi-password').getAttribute('type'),'text');await window.locator('[data-for="wifi-password"]').click();
 await window.locator('.step').nth(2).click();const before=await window.locator('#ssh-password').inputValue();await window.locator('#ssh-generate').click();await window.locator('#notification.success').waitFor();const after=await window.locator('#ssh-password').inputValue();assert.notEqual(before,after);assert(after.length>=20);assert.equal(await window.locator('#ssh-password').getAttribute('type'),'password');
 await window.locator('.step').nth(3).click();await window.locator('#mode-antigravity').selectOption('import');await window.locator('#import-antigravity').waitFor({state:'visible'});assert((await window.locator('#import-antigravity').textContent()).includes('Comprobar e importar'));
 // Native credential import is exercised through real helper + IPC, never renderer secrets.
 let imported=await window.evaluate(()=>window.aguja.importProvider('antigravity'));
 assert.equal(imported.ok,true);assert.equal(imported.portable,true);assert.equal(JSON.stringify(imported).includes(marker),false);
 const status=await window.evaluate(()=>window.aguja.providerStatus());assert.equal(status.providers.antigravity.installed,true);
 for(const invalid of ['{"'+marker+'":',JSON.stringify({...native,token:{...native.token,refresh_token:[]}})]){
  fs.writeFileSync(auth,invalid);imported=await window.evaluate(()=>window.aguja.importProvider('antigravity'));
  assert.equal(imported.ok,false);assert.equal(JSON.stringify(imported).includes(marker),false);
 }
 fs.writeFileSync(auth,JSON.stringify(native));fs.chmodSync(auth,0o644);
 imported=await window.evaluate(()=>window.aguja.importProvider('antigravity'));assert.equal(imported.ok,false);
 fs.chmodSync(auth,0o600);fs.renameSync(auth,auth+'.fixture');fs.symlinkSync(auth+'.fixture',auth);
 imported=await window.evaluate(()=>window.aguja.importProvider('antigravity'));assert.equal(imported.ok,false);
 fs.unlinkSync(auth);fs.renameSync(auth+'.fixture',auth);
 await window.locator('#mode-claude').selectOption('api');await window.locator('#key-claude').fill('SYNTHETIC-API-NOT-A-KEY');assert.equal(await window.locator('#key-claude').getAttribute('type'),'password');
 await window.locator('.step').nth(4).click();assert.equal(await window.locator('#remote-enabled').isVisible(),false);assert.equal(await window.locator('#tailscale-enabled').isChecked(),false);await window.locator('#tailscale-enabled').check();await window.locator('#tailscale-fields').waitFor({state:'visible'});assert.equal(await window.locator('#tailscale-ssh').isChecked(),false);await window.locator('#tailscale-enabled').uncheck();
 await window.locator('.step').nth(5).click();await window.locator('input[value="encrypted"]').check();await window.locator('#unlock-fields').waitFor({state:'visible'});await window.locator('#prepare').click();await window.locator('#notification').filter({hasText:'Selecciona primero una imagen'}).waitFor();assert(await window.locator('#flash').isDisabled());assert.equal(await window.locator('#usb-confirm').count(),0);assert((await window.locator('#flash-status').textContent()).includes('Selecciona una imagen'));
 const viewport=await window.evaluate(()=>({width:innerWidth,height:innerHeight}));const overflow=await window.evaluate(()=>document.documentElement.scrollWidth>innerWidth);assert.equal(overflow,false);
 await window.locator('.step').nth(0).click();await window.locator('#image-sha').fill('');await window.locator('.image-advanced summary').click();await window.evaluate(()=>document.getElementById('notification').hidden=true);
 // Screenshot contains fixtures only, no account credentials or actual OAuth links.
 await window.screenshot({path:path.join(__dirname,'linux-wizard.fixture.png'),fullPage:true});
 console.log(JSON.stringify({ok:true,checks:38,security,viewport,realElectron:true,physicalUsbWritten:false,nativeAccountsAuthorized:false}));
 }finally{if(application)await application.close();fs.rmSync(temp,{recursive:true,force:true});}
})().catch(error=>{console.error(error.stack);process.exitCode=1;});
