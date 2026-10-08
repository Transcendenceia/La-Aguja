'use strict';
// Run ONLY in a real interactive Windows desktop against the packaged EXE.
// The caller may use ELECTRON_RUN_AS_NODE=1 to run this file; it is removed
// from the launched application. No provider login, real account or USB write.
// AGUJA_QA_IMAGE must be a SYNTHETIC GPT/FAT image, never a user's image.
const {_electron:electron}=require('playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os'),crypto=require('node:crypto');
const phase=process.env.AGUJA_QA_PHASE||'final';
const root=process.env.AGUJA_QA_ROOT||fs.mkdtempSync(path.join(os.tmpdir(),'aguja-windows-ui-'));
const executable=process.env.AGUJA_QA_EXECUTABLE,image=process.env.AGUJA_QA_IMAGE;
const secret={wifi:'SYNTHETIC-WIFI-ONLY',ssh:'SYNTHETIC-SSH-ONLY',api:'SYNTHETIC-API-ONLY',tailnet:'SYNTHETIC-TAILNET-ONLY',unlock:'SYNTHETIC-UNLOCK-ONLY'};
const report={ok:false,phase,platform:process.platform,packaged:false,checks:[],screenshots:[],physicalUsbWritten:false,tailnetEnrolled:false,providerAuthenticated:false,harnessCredentials:'synthetic only',realBitlockerSecretsExported:false,startupBitlockerAutoReadNotMeasured:true,officialAccountVerified:false};
let app,w;
const digest=async filename=>{const hash=crypto.createHash('sha256');for await(const chunk of fs.createReadStream(filename))hash.update(chunk);return hash.digest('hex');};
const check=async(name,fn)=>{try{const result=await fn();report.checks.push({name,ok:true,...(result||{})});}catch(error){report.checks.push({name,ok:false,error:String(error.message).slice(0,600)});throw error;}};
const idle=()=>w.waitForFunction(()=>!document.getElementById('prepare').disabled,null,{timeout:180000});
const step=async n=>{await idle();await w.locator('.step').nth(n).click();};
const screenshot=async name=>{
 // Mask all credentials, not just password controls. No screenshots of decoded
 // profiles or native auth files are taken, including on failure.
 const masks=w.locator('input[type="password"], #wifi-password, #ssh-password, #tailscale-auth-key, [id^="key-"], #unlock-password, #profile-password, #share-url, #bitlocker-key-display, #account-code');
 const filename=name+'.png';await w.screenshot({path:path.join(root,filename),fullPage:true,mask:[masks]});report.screenshots.push(filename);
};
const setDialogs=async settings=>app.evaluate(({dialog},s)=>{Object.assign(globalThis.windowsQA,s);dialog.showOpenDialog=async()=>globalThis.windowsQA.cancelOpen?{canceled:true,filePaths:[]}:{canceled:false,filePaths:[globalThis.windowsQA.openPath]};dialog.showSaveDialog=async()=>globalThis.windowsQA.cancelSave?{canceled:true}:{canceled:false,filePath:globalThis.windowsQA.savePath};},settings);
function input(mode='plain'){return {capsule:{schema:1,hostname:'aguja-windows-qa',locale:{language:'es_CO.UTF-8',keyboard:'latam',variant:'nodeadkeys'},network:{ethernet:{method:'auto'},wifi:{ssid:'QA-NOT-A-REAL-WIFI',password:secret.wifi,security:'wpa-psk',country:'ES',hidden:false}},ssh:{password:secret.ssh,public_key:'',port:50222},providers:{codex:{mode:'api',api_key:secret.api,base_url:'',model:''},claude:{mode:'none'},antigravity:{mode:'none'},opencode:{mode:'none'}},remote:{enabled:false},tailscale:{enabled:true,auth_key:secret.tailnet,login_server:'https://headscale.example.invalid',hostname:'aguja-windows-qa',ssh:false,accept_routes:false}},protection:{mode,passphrase:mode==='encrypted'?secret.unlock:''}};}
async function readProfile(filename,mode,imports=false){
 return app.evaluate(({app},{filename,mode,secret,imports})=>{
  const req=process.getBuiltinModule('node:module').createRequire(app.getAppPath()+'/main.cjs'),p=req('node:path'),fs=req('node:fs'),crypto=req('node:crypto');
  const fat=req(p.join(app.getAppPath(),'fat32-writer.cjs')),provisioning=req(p.join(app.getAppPath(),'provisioning.cjs'));
  const fd=fs.openSync(filename,'r');let raw;try{const part=fat.findGptPartition(fd,'AGUJA_CFG'),params=fat.parseFat32Params(fd,part.offset);raw=fat.readFat32File(fd,params,'aguja-profile.json');}finally{fs.closeSync(fd);}
  if(!raw)throw Error('No FAT profile readback');const envelope=JSON.parse(raw),assert=req('node:assert/strict');assert.equal(envelope.protection,mode);
  let capsule,decoder='packaged FAT + crypto envelope verification';
  if(mode==='plain')capsule=envelope.capsule;
  else {
   for(const value of Object.values(secret))assert(!raw.includes(value),'Credential leaked into encrypted envelope');
   // Prefer an exported production decoder if the repaired package provides it;
   // otherwise independently verify its documented runtime-compatible envelope.
   if(typeof provisioning.openCapsule==='function'){assert.throws(()=>provisioning.openCapsule(raw,'SYNTHETIC-WRONG-PASSWORD'));capsule=provisioning.openCapsule(raw,secret.unlock);decoder='packaged provisioning.openCapsule';}
   else if(typeof provisioning.unseal==='function'){assert.throws(()=>provisioning.unseal(raw,'SYNTHETIC-WRONG-PASSWORD'));capsule=provisioning.unseal(raw,secret.unlock);decoder='packaged provisioning.unseal';}
   else{
    assert.equal(envelope.kdf,'scrypt-32768-8-1');const salt=Buffer.from(envelope.salt,'base64url'),iv=Buffer.from(envelope.iv,'base64url'),data=Buffer.from(envelope.data,'base64url');assert.equal(salt.length,16);assert.equal(iv.length,12);
    const open=passphrase=>{const key=crypto.scryptSync(passphrase,salt,32,{N:32768,r:8,p:1,maxmem:64*1024**2});try{const d=crypto.createDecipheriv('aes-256-gcm',key,iv);d.setAAD(Buffer.from('aguja-profile:1'));d.setAuthTag(data.subarray(-16));return JSON.parse(Buffer.concat([d.update(data.subarray(0,-16)),d.final()]));}finally{key.fill(0);}};
    assert.throws(()=>open('SYNTHETIC-WRONG-PASSWORD'));capsule=open(secret.unlock);
   }
  }
  assert.equal(capsule.hostname,'aguja-windows-qa');assert.deepEqual(capsule.locale,{language:'es_CO.UTF-8',keyboard:'latam',variant:'nodeadkeys'});assert.equal(capsule.network.wifi.password,secret.wifi);assert.equal(capsule.ssh.password,secret.ssh);assert.equal(capsule.ssh.port,50222);assert.equal(capsule.tailscale.auth_key,secret.tailnet);assert.equal(capsule.tailscale.login_server,'https://headscale.example.invalid');assert.equal(capsule.tailscale.ssh,false);assert.equal(capsule.tailscale.accept_routes,false);assert.deepEqual(capsule.remote,{enabled:false});
  if(!imports)assert.equal(capsule.providers.codex.api_key,secret.api);
  else{
   assert.deepEqual(capsule.providers,globalThis.windowsQA.expectedImports);
   for(const id of ['codex','claude','antigravity','opencode']){assert.equal(capsule.providers[id].mode,'import');assert(Object.keys(capsule.providers[id].files).length);}
  }
  return {protection:mode,fatReadback:true,credentialsMatch:true,importedProvidersMatch:imports,decoder,wrongPasswordRejected:mode==='encrypted'};
 },{filename,mode,secret,imports});
}
(async()=>{
 fs.mkdirSync(root,{recursive:true});
 try{
  assert.equal(process.platform,'win32','Windows QA must run on Windows, not a local Linux Electron');assert(executable&&fs.existsSync(executable),'Set AGUJA_QA_EXECUTABLE to the unpacked packaged Windows EXE');assert(image&&fs.existsSync(image),'Set AGUJA_QA_IMAGE to the synthetic GPT/FAT fixture');assert(['baseline','final'].includes(phase),'AGUJA_QA_PHASE must be baseline or final');
  const originalHash=await digest(image),env={...process.env};delete env.ELECTRON_RUN_AS_NODE;
  app=await electron.launch({executablePath:executable,args:['--lang=es','--user-data-dir='+path.join(root,'private-qa-state')],env,timeout:60000});
  // Keep the package intact. Only isolate native dialogs, provider fixture paths
  // and synthetic catalog networking inside this one QA application process.
  await app.evaluate(({app,dialog},root)=>{
   const req=process.getBuiltinModule('node:module').createRequire(app.getAppPath()+'/main.cjs'),p=req('node:path'),fs=req('node:fs');
   const provisioning=req(p.join(app.getAppPath(),'provisioning.cjs')),core=req(p.join(app.getAppPath(),'core.cjs')),bitlocker=req(p.join(app.getAppPath(),'bitlocker.cjs'));
   globalThis.windowsQA={root,confirmations:0,cancelOpen:false,cancelSave:false};
   // Never touch BitLocker recovery secrets or change protection during this QA.
   bitlocker.getBitLockerStatus=async()=>({available:true,volumes:[]});bitlocker.getRecoveryKey=async()=>{throw Error('Real BitLocker keys are excluded from synthetic QA');};
   dialog.showMessageBox=async()=>{globalThis.windowsQA.confirmations++;return {response:0};};
   core.getHTTPS=async()=>{throw Error('Synthetic offline fixture; official catalog is a separate QA lane');};
   for(const name of ['downloads','documents']){const target=p.join(root,name);fs.mkdirSync(target,{recursive:true});app.setPath(name,target);}
   const home=p.join(root,'synthetic-provider-home');fs.mkdirSync(home,{recursive:true});
   const fixtures={'.codex/auth.json':{tokens:{access_token:'SYNTHETIC-CODEX-ACCESS',refresh_token:'SYNTHETIC-CODEX-REFRESH',id_token:'SYNTHETIC-CODEX-ID'}},'.claude/.credentials.json':{claudeAiOauth:{accessToken:'SYNTHETIC-CLAUDE-ACCESS',refreshToken:'SYNTHETIC-CLAUDE-REFRESH'}},'.claude/settings.json':{model:'qa-model',env:{DONT_IMPORT:'SYNTHETIC-EXTRA'}},'.gemini/antigravity-cli/antigravity-oauth-token':{auth_method:'oauth',id_token:'SYNTHETIC-AG-ID',token:{access_token:'SYNTHETIC-AG-ACCESS',refresh_token:'SYNTHETIC-AG-REFRESH',token_type:'Bearer',expiry:'2099-01-01T00:00:00Z'}},'.gemini/antigravity-cli/settings.json':{model:'qa-model',history:'SYNTHETIC-NOT-IMPORTED'},'.local/share/opencode/auth.json':{openai:{type:'api',key:'SYNTHETIC-OPENCODE-API'}},'.config/opencode/opencode.json':{model:'qa/model',permission:{all:'allow'}},'.codex/config.toml':'model = "qa-model"\ncli_auth_credentials_store = "file"\n\n[mcp_servers.do_not_import]\ncommand = "SYNTHETIC-NOT-IMPORTED"\n','.codex/extra-secret.txt':'SYNTHETIC-NOT-IMPORTED'};
   for(const [target,value]of Object.entries(fixtures)){const filename=p.join(home,...target.split('/'));fs.mkdirSync(p.dirname(filename),{recursive:true});fs.writeFileSync(filename,typeof value==='string'?value:JSON.stringify(value),{mode:0o600,flag:'wx'});}
   const discover=provisioning.discover;globalThis.windowsQA.discover=discover;
   provisioning.discover=id=>discover(id,{home,env:{}});globalThis.windowsQA.home=home;
  },root);
  w=await app.firstWindow();await w.reload();await w.waitForLoadState('domcontentloaded');await w.locator('.step').nth(5).waitFor({timeout:30000});await w.setViewportSize({width:1240,height:940});await w.locator('#app-language').selectOption('es');
  await check('real Windows packaged runtime and renderer isolation',async()=>{
   const runtime=await app.evaluate(({app,BrowserWindow})=>{const p=BrowserWindow.getAllWindows()[0].webContents.getLastWebPreferences();return {platform:process.platform,packaged:app.isPackaged,version:app.getVersion(),security:{sandbox:p.sandbox,contextIsolation:p.contextIsolation,nodeIntegration:p.nodeIntegration}};});assert.equal(runtime.platform,'win32');assert.equal(runtime.packaged,true);assert.deepEqual(runtime.security,{sandbox:true,contextIsolation:true,nodeIntegration:false});report.packaged=true;report.version=runtime.version;return runtime;
  });
  await check('synthetic compatible release marker',async()=>{const marker=await app.evaluate(({app},image)=>{const req=process.getBuiltinModule('node:module').createRequire(app.getAppPath()+'/main.cjs');return req(req('node:path').join(app.getAppPath(),'provisioning.cjs')).releaseMarker(image);},image);assert.equal(marker.qa_fixture,'synthetic-windows-ui');assert(marker.features.includes('tailscale-profile-v1'));return {synthetic:true,features:marker.features};});
  await setDialogs({openPath:image});await w.locator('#image-import').click();await w.locator('#image-status').waitFor({state:'visible',timeout:30000});await idle();
  await check('cancel import preserves selected image',async()=>{const prior=await w.locator('#image-status').textContent();await setDialogs({cancelOpen:true});await w.locator('#image-import').click();await idle();assert.equal(await w.locator('#image-status').textContent(),prior);await setDialogs({cancelOpen:false});});
  await screenshot('01-windows-image');await step(1);await w.locator('#hostname').fill('aguja-windows-qa');await w.locator('#locale-language').selectOption('es_CO.UTF-8');await w.locator('#locale-keyboard').selectOption('latam');await w.locator('#locale-variant').selectOption('nodeadkeys');await w.locator('#wifi-ssid').fill('QA-NOT-A-REAL-WIFI');await w.locator('#wifi-password').fill(secret.wifi);await w.locator('#wifi-country').fill('ES');await screenshot('02-windows-network');
  await step(2);await w.locator('#ssh-password').fill(secret.ssh);await w.locator('#ssh-port').fill('50222');await screenshot('03-windows-ssh');await step(3);await w.locator('#mode-codex').selectOption('api');await w.locator('#key-codex').fill(secret.api);await screenshot('04-windows-ai');
  await step(4);await w.locator('#tailscale-enabled').check();await w.locator('#tailscale-auth-key').fill(secret.tailnet);await w.locator('#tailscale-login-server').fill('https://headscale.example.invalid');await w.locator('#tailscale-hostname').fill('aguja-windows-qa');await check('secrets masked and summary excludes secret values',async()=>{for(const id of ['wifi-password','ssh-password','key-codex','tailscale-auth-key'])assert.equal(await w.locator('#'+id).getAttribute('type'),'password');const summary=await w.locator('#summary').innerText();for(const value of Object.values(secret))assert(!summary.includes(value));assert.equal(await w.locator('#tailscale-ssh').isChecked(),false);assert.equal(await w.locator('#tailscale-accept-routes').isChecked(),false);});await screenshot('05-windows-tailnet');
  await step(5);await w.locator('input[value="plain"]').check();await setDialogs({cancelSave:true});await check('cancel prepare preserves source selection and creates no output',async()=>{const prior=await w.locator('#image-status').textContent();const before=fs.readdirSync(root);await w.locator('#prepare').click();await idle();assert.equal(await w.locator('#image-status').textContent(),prior);assert.deepEqual(fs.readdirSync(root),before);});await setDialogs({cancelSave:false});
  for(const mode of ['plain','encrypted']){
   const filename=path.join(root,'windows-'+mode+'.img');assert(!fs.existsSync(filename),'Use a fresh AGUJA_QA_ROOT per run');await w.locator('input[value="'+mode+'"]').check();if(mode==='encrypted')await w.locator('#unlock-password').fill(secret.unlock);await setDialogs({savePath:filename});
   await check('prepare '+mode+' through real renderer and IPC',async()=>{await w.locator('#prepare').click();await idle();assert.equal(fs.existsSync(filename),true,await w.locator('#notification').textContent());await w.locator('#prepared-status').filter({hasText:path.basename(filename)}).waitFor({timeout:180000});assert.equal(await digest(image),originalHash);assert.notEqual(await digest(filename),originalHash);return await readProfile(filename,mode);});await screenshot('06-windows-'+mode+'-prepared');
  }
  await check('cancel prepare retains previously prepared selection',async()=>{const prior=await w.locator('#prepared-status').textContent();await setDialogs({cancelSave:true});await w.locator('#prepare').click();await idle();assert.equal(await w.locator('#prepared-status').textContent(),prior);await setDialogs({cancelSave:false});});
  await check('configuration changes invalidate prepared image',async()=>{await step(1);await w.locator('#hostname').fill('aguja-windows-qa-changed');await step(5);assert.match(await w.locator('#prepared-status').textContent(),/configuración cambió/);assert.match(await w.locator('#flash').textContent(),/Preparar y grabar/);await step(1);await w.locator('#hostname').fill('aguja-windows-qa');await step(5);});
  await check('real Windows internal disks excluded and invalid identity rejected before confirmation',async()=>{
   const inventory=await app.evaluate(async({app})=>{const req=process.getBuiltinModule('node:module').createRequire(app.getAppPath()+'/main.cjs'),cp=req('node:child_process');return new Promise((resolve,reject)=>cp.execFile('powershell.exe',['-NoProfile','-NonInteractive','-Command',"@(Get-Disk | Select-Object Number,@{Name='BusType';Expression={$_.BusType.ToString()}},IsBoot,IsSystem) | ConvertTo-Json -Compress"],{windowsHide:true},(err,out)=>{if(err)return reject(err);try{const parsed=JSON.parse(out.trim()||'[]');resolve(Array.isArray(parsed)?parsed:[parsed]);}catch(e){reject(e);}}));});
   const found=await w.evaluate(()=>window.aguja.disks());assert.equal(found.ok,true);for(const disk of found.disks){const number=Number(disk.device.match(/PhysicalDrive(\d+)$/)?.[1]),raw=inventory.find(d=>d.Number===number);assert(raw,'Eligible disk absent from Get-Disk');assert.equal(raw.BusType,'USB');assert.equal(raw.IsBoot,false);assert.equal(raw.IsSystem,false);}
   const before=await app.evaluate(()=>globalThis.windowsQA.confirmations);const rejected=await w.evaluate(settings=>window.aguja.flash({...settings,backup:false,device:'\\\\.\\PhysicalDrive0',serial:'QA-INVALID-IDENTITY-NEVER-MATCH'}),input('encrypted'));assert.equal(rejected.ok,false);assert.match(rejected.error,/USB|seleccion/);assert.equal(await app.evaluate(()=>globalThis.windowsQA.confirmations),before);assert.equal(await digest(image),originalHash);return {eligibleCount:found.disks.length,internalCount:inventory.filter(d=>d.BusType!=='USB'||d.IsBoot||d.IsSystem).length,rejectedBeforeConfirmation:true};
  });
  await check('synthetic provider imports use approved files only',async()=>{
   const results=await app.evaluate(async({app},{root,capsule,originalHash})=>{
    const req=process.getBuiltinModule('node:module').createRequire(app.getAppPath()+'/main.cjs'),assert=req('node:assert/strict'),p=req('node:path'),fs=req('node:fs'),provisioning=req(p.join(app.getAppPath(),'provisioning.cjs'));const approved={};
    for(const id of ['codex','claude','antigravity','opencode']){const found=provisioning.discover(id);assert.equal(found.portable,true,id+' synthetic fixture not discovered');assert(found.paths.every(item=>p.resolve(item.source).startsWith(p.resolve(globalThis.windowsQA.home)+p.sep)));approved[id]=found.paths;capsule.providers[id]={mode:'import',api_key:'',base_url:'',model:''};}
    const materialized=provisioning.materialize(capsule,approved);globalThis.windowsQA.expectedImports=materialized.providers;for(const [id,provider]of Object.entries(materialized.providers)){assert(provider.files&&Object.keys(provider.files).length);assert(Object.keys(provider.files).every(name=>Object.hasOwn(provisioning.IMPORTS[id],name)));}
    assert.throws(()=>provisioning.materialize(capsule,{}),/Importa primero/);const codex=Buffer.from(materialized.providers.codex.files['.codex/config.toml'],'base64url').toString();assert(!codex.includes('mcp_servers'));assert(!Object.hasOwn(materialized.providers.codex.files,'.codex/extra-secret.txt'));
    assert(!Buffer.from(materialized.providers.claude.files['.claude/settings.json'],'base64url').toString().includes('DONT_IMPORT'));assert(!Buffer.from(materialized.providers.antigravity.files['.gemini/antigravity-cli/settings.json'],'base64url').toString().includes('history'));assert(!Buffer.from(materialized.providers.opencode.files['.config/opencode/opencode.json'],'base64url').toString().includes('permission'));
    return {providers:Object.keys(approved),selectiveFiles:true,unapprovedImportRejected:true,fixturesOnly:true};
   },{root,capsule:input().capsule,originalHash});
   await step(3);for(const id of results.providers){await w.locator('#mode-'+id).selectOption('import');await w.locator('#import-btn-'+id).click();await idle();assert.match(await w.locator('#import-state-'+id).textContent(),/Credenciales nativas seleccionadas/);}
   const filename=path.join(root,'windows-imports-encrypted.img');await step(5);await setDialogs({savePath:filename});await w.locator('#prepare').click();await idle();assert(fs.existsSync(filename),await w.locator('#notification').textContent());await w.locator('#prepared-status').filter({hasText:path.basename(filename)}).waitFor({timeout:180000});assert.equal(await digest(image),originalHash);return {...results,...await readProfile(filename,'encrypted',true)};
  });
  await screenshot('07-windows-imports-prepared');report.sourceSha256=originalHash;report.sourceUnchanged=await digest(image)===originalHash;report.ok=report.checks.every(c=>c.ok);
 }catch(error){report.error=String(error.message).slice(0,600);if(w)try{await screenshot('failure-masked');}catch{}}
 finally{if(app)try{await app.close();}catch{}fs.writeFileSync(path.join(root,'windows-ui-result.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));if(!report.ok)process.exitCode=1;}
})();
