'use strict';
const assert=require('node:assert/strict'),path=require('node:path'),fs=require('node:fs');
const {chromium}=require('playwright'),catalog=require('../../runtime/locale-catalog.json');
(async()=>{
 const out=process.env.AGUJA_QA_RESULT_DIR;const browser=await chromium.launch({headless:true,executablePath:process.env.AGUJA_QA_BROWSER||'/usr/bin/chromium'});let views=0;
 try{for(const platform of ['linux','win32']){
  const page=await browser.newPage({viewport:{width:1240,height:960},locale:'es-ES'});
  await page.addInitScript(({catalog,platform})=>{
   const ok=async()=>({ok:true});window.__calls=[];const volume={mountPoint:'C:',volumeType:'OperatingSystem',volumeStatus:'FullyEncrypted',protectionStatus:'On',encryptionMethod:'XtsAes128',encryptionPercentage:100,hasRecoveryPassword:true,keyProtectorId:'SYNTHETIC-ID',capacityGB:128};
   window.aguja={i18nCatalog:async()=>({ok:true,catalog,language:'es',systemLanguage:'es'}),i18nLanguage:ok,info:async()=>({ok:true,version:'synthetic',platform,bitlockerAvailable:platform==='win32'}),bitlockerStatus:async()=>({ok:true,available:true,volumes:[volume]}),providerStatus:async()=>({ok:true,providers:{codex:{installed:false,imported:false}}}),invalidatePrepared:ok,onProgress:fn=>window.__progress=fn,importImage:async()=>({ok:true,image:{name:'SYNTHETIC.img',bytes:1024,verification:'calculated-sha'}}),disks:async()=>({ok:true,disks:[{device:'SYNTHETIC-USB',serial:'SYNTHETIC-SERIAL',size:1024**3,model:'Synthetic'}]}),flash:async input=>{window.__calls.push(input);return {ok:true,verified:true,backupVerified:false};},importLocale:async()=>({ok:true,locale:{language:'es_ES.UTF-8',keyboard:'es',variant:''}})};
  },{catalog,platform});
  await page.goto('file://'+path.resolve(__dirname,'../ui/index.html'));await page.locator('.step').nth(6).waitFor();
  await page.locator('#image-import').click();await page.locator('.step').nth(5).click();assert(await page.locator('#disk-recovery-card').isVisible());
  await page.locator('.recovery-type').selectOption('luks');await page.locator('.recovery-label').fill('Tu tailnet, tu control.');await page.locator('.recovery-key').fill('  SYNTHETIC-SECRET-EXACT  ');
  await page.locator('.step').nth(6).click();await page.locator('#disks-refresh').click();await page.locator('#usb-disks').selectOption('0');await page.locator('#flash').click();await page.locator('#notification.success').waitFor();
  assert((await page.locator('#notification').textContent()).includes('USB grabado'));
  for(const language of ['en','zh','fr','pt','de','it','es','en']){
   await page.locator('#app-language').selectOption(language);await page.waitForFunction(code=>document.documentElement.lang===code,language);
   assert.equal(await page.locator('.recovery-key').inputValue(),'  SYNTHETIC-SECRET-EXACT  ');assert.equal(await page.locator('.recovery-key').getAttribute('type'),'password');assert.equal(await page.locator('.recovery-label').inputValue(),'Tu tailnet, tu control.');
   if(language!=='es'){const text=require('../ui/i18n.js').translation(catalog,language,'USB grabado y lectura verificada.');assert((await page.locator('#notification').textContent()).startsWith(text));assert.notEqual(await page.locator('#flash-platform-hint').textContent(),'Linux pedirá permiso. La aplicación no desmonta ni selecciona discos internos automáticamente.');}
   for(let step=0;step<9;step++){
    await page.locator('.step').nth(step).click();assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);views++;
    if(language!=='es')assert(!(await page.locator('.view.active').textContent()).includes('Añade claves del equipo'));
    if(step===4&&language!=='es'){assert(!(await page.locator('.view.active h1').textContent()).includes('Tu tailnet'));assert(!(await page.locator('.tailscale-card').textContent()).includes('Desactivada por defecto'));}
   }
   if(language==='en'&&out){await page.locator('.step').nth(4).click();await page.screenshot({path:path.join(out,platform+'-english-tailnet.png'),fullPage:true});}
  }
  await page.locator('.step').nth(6).click();await page.locator('#flash').click();const input=await page.evaluate(()=>window.__calls.at(-1));assert.equal(input.diskRecovery[0].key,'  SYNTHETIC-SECRET-EXACT  ');assert.equal(input.diskRecovery[0].label,'Tu tailnet, tu control.');
  if(out)await page.screenshot({path:path.join(out,platform+'-manual-recovery.png'),fullPage:true,mask:[page.locator('input[type=password]')]});await page.close();
 }}finally{await browser.close();}
 const report={ok:true,views,platforms:['linux','win32'],languages:['es','en','zh','fr','pt','de','it'],secretsPreserved:true,bannerRetranslated:true,manualKeysBothPlatforms:true,physicalUsbWritten:false};if(out)fs.writeFileSync(path.join(out,'i18n-recovery-ui.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
})().catch(e=>{console.error(e.stack);process.exitCode=1;});
