'use strict';
const { _electron: electron }=require('playwright');const assert=require('node:assert/strict');const fs=require('node:fs');const path=require('node:path');const os=require('node:os');const crypto=require('node:crypto');const {execFileSync}=require('node:child_process');
const sha=file=>crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
(async()=>{
 const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'aguja-image-qa-'));let application;
 try{
 const image=path.join(tmp,'synthetic-factory.img'),partition=path.join(tmp,'cfg.fat'),output=path.join(tmp,'personal.img');
 fs.writeFileSync(image,'');fs.truncateSync(image,96*1024**2);
 execFileSync('/usr/sbin/sgdisk',['-o','-n','1:2048:+64M','-t','1:0700','-c','1:AGUJA_CFG',image],{stdio:'pipe'});
 fs.writeFileSync(partition,'');fs.truncateSync(partition,64*1024**2);execFileSync('/usr/sbin/mkfs.vfat',['-F','32','-n','AGUJA_CFG',partition],{stdio:'pipe'});
 const marker=path.join(tmp,'release.json');fs.writeFileSync(marker,JSON.stringify({schema:1,version:'0.4.3',features:['platform-profile-v1','locale-profile-v1','locale-preunlock-v1']}));execFileSync('mcopy',['-i',partition,marker,'::/release.json'],{stdio:'pipe'});
 // All work is on ordinary synthetic files, no loop mounts or block devices.
 const dst=fs.openSync(image,'r+');const data=fs.readFileSync(partition);fs.writeSync(dst,data,0,data.length,1048576);fs.closeSync(dst);
 const originalHash=sha(image);
 application=await electron.launch({...(process.env.AGUJA_QA_EXECUTABLE?{executablePath:process.env.AGUJA_QA_EXECUTABLE}:{}),args:[path.resolve(__dirname,'..'),'--lang=es','--no-sandbox','--user-data-dir='+path.join(tmp,'state')],env:{...process.env,ELECTRON_DISABLE_SECURITY_WARNINGS:'1'}});
 await application.evaluate(({app})=>{const require=process.getBuiltinModule('node:module').createRequire(app.getAppPath()+'/main.cjs');require(require('node:path').join(app.getAppPath(),'core.cjs')).getHTTPS=async()=>{throw new Error('Synthetic offline fixture');};});
 const window=await application.firstWindow();await window.waitForLoadState('domcontentloaded');await window.locator('#app-language').selectOption('es');await window.waitForFunction(()=>document.documentElement.lang==='es');
 await application.evaluate(({dialog},paths)=>{dialog.showOpenDialog=async()=>({canceled:false,filePaths:[paths.image]});dialog.showSaveDialog=async()=>({canceled:false,filePath:paths.output});},{image,output});
 assert.equal(await window.locator('#image-sha').inputValue(),'');await window.locator('#image-import').click();await window.locator('#image-status').waitFor({state:'visible'});assert((await window.locator('#image-status').textContent()).includes('SHA calculado; origen no comprobado'));
 await window.locator('.step').nth(1).click();await window.locator('#hostname').fill('aguja-fixture');await window.locator('#locale-language').selectOption('es_CO.UTF-8');await window.locator('#locale-keyboard').selectOption('latam');await window.locator('#locale-variant').selectOption('nodeadkeys');await window.locator('#wifi-ssid').fill('Fixture-only');await window.locator('#wifi-password').fill('SYNTHETIC-WIFI-ONLY');
 await window.locator('.step').nth(2).click();await window.locator('#ssh-password').fill('SYNTHETIC-SSH-ONLY');
 await window.locator('.step').nth(3).click();await window.locator('#mode-codex').selectOption('api');await window.locator('#key-codex').fill('SYNTHETIC-API-ONLY');
 await window.locator('.step').nth(5).click();await window.locator('input[name=protection][value=plain]').check();await window.locator('#prepare').click();await window.locator('#prepared-status').waitFor({state:'visible',timeout:60000});
 assert.equal(sha(image),originalHash);assert.notEqual(sha(output),originalHash);assert.equal(fs.statSync(output).mode&0o777,0o600);
 const readback=path.join(tmp,'profile.json');execFileSync('mcopy',['-i',output+'@@1048576','::/aguja-profile.json',readback],{stdio:'pipe'});const profile=JSON.parse(fs.readFileSync(readback,'utf8'));
 assert.equal(profile.protection,'plain');assert.deepEqual(profile.capsule.locale,{language:'es_CO.UTF-8',keyboard:'latam',variant:'nodeadkeys'});assert.equal(profile.capsule.hostname,'aguja-fixture');assert.equal(profile.capsule.network.wifi.password,'SYNTHETIC-WIFI-ONLY');assert.equal(profile.capsule.providers.codex.api_key,'SYNTHETIC-API-ONLY');assert.deepEqual(profile.capsule.remote,{enabled:false});
 // Even a direct narrow IPC request cannot flash an internal disk or bypass target selection.
 const rejected=await window.evaluate(()=>window.aguja.flash({device:'/dev/sda',serial:'INTERNAL-FIXTURE',confirm:'FLASH:INTERNAL-FIXTURE'}));assert.equal(rejected.ok,false);
 // A second image seals every credential; source remains untouched and no secret occurs in raw capsule.
 const encrypted=path.join(tmp,'encrypted.img');await application.evaluate(({dialog},filename)=>{dialog.showSaveDialog=async()=>({canceled:false,filePath:filename});},encrypted);
 await window.locator('input[value="encrypted"]').check();assert.equal(await window.locator('#unlock-password').inputValue(),'aguja');await window.locator('#prepare').click();await window.locator('#prepared-status').filter({hasText:'encrypted.img'}).waitFor({timeout:60000});
 const sealed=path.join(tmp,'sealed.json');execFileSync('mcopy',['-i',encrypted+'@@1048576','::/aguja-profile.json',sealed],{stdio:'pipe'});const raw=fs.readFileSync(sealed,'utf8');assert(!raw.includes('SYNTHETIC-WIFI-ONLY'));assert(!raw.includes('SYNTHETIC-API-ONLY'));assert.equal(JSON.parse(raw).protection,'encrypted');assert.equal(sha(image),originalHash);
 const localeReadback=path.join(tmp,'locale.json');execFileSync('mcopy',['-i',encrypted+'@@1048576','::/aguja-locale.json',localeReadback],{stdio:'pipe'});assert.deepEqual(JSON.parse(fs.readFileSync(localeReadback)),{language:'es_CO.UTF-8',keyboard:'latam',variant:'nodeadkeys'});
 const unlocked=execFileSync('python3',['-c',"import sys,json;sys.path.insert(0,sys.argv[1]);import profile;print(json.dumps(profile.open_capsule(open(sys.argv[2],'rb').read(),'aguja')))",path.resolve(__dirname,'../../runtime'),sealed],{encoding:'utf8'});assert.equal(JSON.parse(unlocked).providers.codex.api_key,'SYNTHETIC-API-ONLY');

 console.log(JSON.stringify({ok:true,realElectron:true,plainImagePrepared:true,encryptedImagePrepared:true,sourceUnchanged:true,mode600:true,profileReadbackVerified:true,internalDiskRejected:true,physicalUsbWritten:false,fixturesOnly:true}));
 }finally{if(application)await application.close();fs.rmSync(tmp,{recursive:true,force:true});}
})().catch(error=>{console.error('Image integration verification did not complete: '+error.message);process.exitCode=1;});
