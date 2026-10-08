'use strict';
// Real Electron screenshots/renderer/IPC, using only synthetic private inputs.
// This does not enroll a real tailnet, authenticate a provider or write a USB.
const {_electron:electron}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const output=process.env.AGUJA_QA_ROOT||fs.mkdtempSync(path.join(os.tmpdir(),'aguja-tailnet-ui-'));
fs.mkdirSync(output,{recursive:true});
(async()=>{let app;try{
 const packaged=Boolean(process.env.AGUJA_QA_EXECUTABLE),env={...process.env};delete env.ELECTRON_RUN_AS_NODE;
 app=await electron.launch({chromiumSandbox:Boolean(process.env.AGUJA_QA_NATIVE_SANDBOX),...(packaged?{executablePath:process.env.AGUJA_QA_EXECUTABLE}:{}),args:[...(packaged?[]:[path.resolve(__dirname,'..')]),'--lang=es','--user-data-dir='+path.join(output,'private-qa-state'),...(process.platform==='linux'&&!process.env.AGUJA_QA_NATIVE_SANDBOX?['--no-sandbox']:[])],env});
 const w=await app.firstWindow();await w.setViewportSize({width:1240,height:940});await w.waitForLoadState('domcontentloaded');
 await app.evaluate(({app},root)=>{const fs=process.getBuiltinModule('node:fs'),path=process.getBuiltinModule('node:path');for(const name of ['downloads','documents']){const target=path.join(root,name);fs.mkdirSync(target,{recursive:true});app.setPath(name,target);}},output);
 await w.locator('#app-language').selectOption('es');
 const screenshot=async(name,step)=>{await w.locator('.step').nth(step).click();assert.equal(await w.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);await w.screenshot({path:path.join(output,name+'.png'),fullPage:true});};
 await screenshot('01-imagen',0);await screenshot('ia-tools',3);await w.locator('.step').nth(1).click();await w.locator('#hostname').fill('rescate-ejemplo');await screenshot('02-red',1);
 await w.locator('.step').nth(2).click();await w.locator('#ssh-password').fill('SYNTHETIC-SSH');await w.locator('#ssh-port').fill('50222');await screenshot('03-ssh',2);
 await w.locator('.step').nth(4).click();assert.equal(await w.locator('#remote-enabled').isVisible(),false);assert.equal(await w.locator('#agent-access').isVisible(),false);assert.equal(await w.locator('#tailscale-enabled').isChecked(),false);
 await w.locator('#tailscale-enabled').check();await w.locator('#tailscale-fields').waitFor({state:'visible'});assert.equal(await w.locator('#tailscale-ssh').isChecked(),false);assert.equal(await w.locator('#tailscale-accept-routes').isChecked(),false);
 await w.locator('#tailscale-auth-key').fill('SYNTHETIC-TAILNET-KEY');assert.equal(await w.locator('#tailscale-auth-key').getAttribute('type'),'password');await w.locator('#tailscale-login-server').fill('https://headscale.example.invalid');await w.locator('#tailscale-hostname').fill('rescate-ejemplo');assert.match(await w.locator('#tailscale-connect-example').innerText(),/ssh -p 50222/);
 await screenshot('04-tailnet',4);assert(!await w.locator('#summary').innerText().then(s=>s.includes('SYNTHETIC')));
 await w.locator('.step').nth(5).click();await w.locator('input[value="encrypted"]').check();await w.locator('#unlock-password').fill('SYNTHETIC-UNLOCK');await screenshot('05-perfil-cifrado',5);
 if(process.env.AGUJA_QA_IMAGE){
  const image=process.env.AGUJA_QA_IMAGE;await app.evaluate(({app,dialog},paths)=>{const req=process.getBuiltinModule('node:module').createRequire(app.getAppPath()+'/main.cjs');req(req('node:path').join(app.getAppPath(),'core.cjs')).getHTTPS=async()=>{throw Error('Offline synthetic fixture');};dialog.showOpenDialog=async()=>({canceled:false,filePaths:[paths.image]});dialog.showSaveDialog=async()=>({canceled:false,filePath:paths.output});},{image,output:path.join(output,'tailnet-encrypted.img')});
  await w.locator('.step').nth(0).click();await w.locator('#image-import').click();await w.locator('#image-status').waitFor({state:'visible'});await w.locator('.step').nth(5).click();await w.locator('#prepare').click();await w.locator('#prepared-status').filter({hasText:'tailnet-encrypted.img'}).waitFor({timeout:180000});
  await app.evaluate(({dialog},out)=>{dialog.showSaveDialog=async()=>({canceled:false,filePath:out});},path.join(output,'tailnet-plain.img'));await w.locator('input[value="plain"]').check();await w.locator('#prepare').click();await w.locator('#prepared-status').filter({hasText:'tailnet-plain.img'}).waitFor({timeout:180000});
  // Defaults may be encrypted, but the explicitly selected plain mode remains
  // supported; screenshot documentation intentionally returns to encrypted.
  await w.locator('input[value="encrypted"]').check();await screenshot('06-imagen-preparada',5);
 }
 const security=await app.evaluate(({BrowserWindow})=>{const p=BrowserWindow.getAllWindows()[0].webContents.getLastWebPreferences();return {contextIsolation:p.contextIsolation,sandbox:p.sandbox,nodeIntegration:p.nodeIntegration};});assert.deepEqual(security,{contextIsolation:true,sandbox:true,nodeIntegration:false});
 const report={ok:true,platform:process.platform,packaged,version:await w.locator('#version').innerText(),legacyControlsAbsent:true,tailnetOptIn:true,ordinaryOpenSSHDefault:true,secretMasked:true,routeAcceptanceDefault:false,imagesPrepared:Boolean(process.env.AGUJA_QA_IMAGE),physicalUsbWritten:false,tailnetEnrolled:false,security,screenshots:fs.readdirSync(output).filter(s=>s.endsWith('.png'))};fs.writeFileSync(path.join(output,'tailnet-ui-result.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
 }catch(error){if(app){try{await (await app.firstWindow()).screenshot({path:path.join(output,'failure.png'),fullPage:true});}catch{}}fs.writeFileSync(path.join(output,'tailnet-ui-result.json'),JSON.stringify({ok:false,error:error.message}));throw error;}finally{if(app)await app.close();}})().catch(e=>{console.error(e.message);process.exitCode=1;});
