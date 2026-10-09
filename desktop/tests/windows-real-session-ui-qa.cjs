'use strict';
// Private live QA: reads the owner's chosen provider, never logs credential data.
const {_electron:electron}=require('playwright'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const root=process.env.AGUJA_QA_ROOT,env={...process.env};delete env.ELECTRON_RUN_AS_NODE;
const native=require('../windows-native-import.cjs'),{run}=require('./windows-vault-fixture.cjs')(env);
(async()=>{let app,original,after,step='read-real-vault';try{
 original=await native.readCredential(run,{provider:'antigravity',store:'current'},env);assert(original,'Real session absent');
 const expected=native.authBuffer('antigravity',original.toString('utf8'));
 step='launch-packaged';app=await electron.launch({executablePath:process.env.AGUJA_QA_EXECUTABLE,args:['--lang=es','--user-data-dir='+path.join(root,'real-state')],env});
 const w=await app.firstWindow();await w.waitForLoadState('domcontentloaded');
 // Point isolated application preferences at the existing real CLI installation.
 // No mocked executable, discovery, credential reader or provider import.
 await app.evaluate(({app})=>{const req=process.getBuiltinModule('node:module').createRequire(app.getAppPath()+'/main.cjs'),proto=req('./ai-tools.cjs').AITools.prototype,original=proto.environment;proto.environment=function(){this.root=req('node:path').join(process.env.APPDATA,'Aguja Companion','ai-tools');return original.call(this);};});
 step='provider-detection';const status=await w.evaluate(()=>window.aguja.providerStatus());assert(status.providers.antigravity.installed,'Installed agy unavailable');
 step='click-real-import';await w.locator('.step').nth(3).click();await w.locator('#mode-antigravity').selectOption('import');await w.locator('#import-btn-antigravity').click();
 await w.locator('#badge-antigravity').filter({hasText:'Importación preparada'}).waitFor({timeout:45000});
 await w.waitForFunction(()=>!document.getElementById('import-btn-antigravity').disabled);
 const receipt=await w.evaluate(()=>window.aguja.importProvider('antigravity'));assert(receipt.ok,'Real import failed');
 const token=JSON.parse(expected).token;assert(!JSON.stringify(receipt).includes(token.access_token));assert(!JSON.stringify(receipt).includes(token.refresh_token));
 await app.evaluate(({dialog},root)=>{dialog.showOpenDialog=async()=>({canceled:false,filePaths:[root+'/factory.img']});dialog.showSaveDialog=async()=>({canceled:false,filePath:root+'/private-real.img'});},root);
 step='select-factory';const image=await w.evaluate(()=>window.aguja.importImage());assert(image.ok,'Factory image unavailable');
 const input={capsule:{schema:1,hostname:'aguja-live-import-qa',locale:{language:'es_ES.UTF-8',keyboard:'es',variant:''},network:{ethernet:{method:'auto'},wifi:{ssid:'',password:'',security:'wpa-psk',country:'ES',hidden:false}},ssh:{password:'SYNTHETIC-LOCAL-QA',public_key:'',port:22},providers:{codex:{mode:'none'},claude:{mode:'none'},antigravity:{mode:'import'},opencode:{mode:'none'}},remote:{enabled:false},tailscale:{enabled:false}},protection:{mode:'encrypted',passphrase:crypto.randomBytes(32).toString('base64url')},backup:false};
 step='prepare-encrypted-image';const prepared=await w.evaluate(input=>window.aguja.prepare(input),input);assert(prepared.ok,'Encrypted image preparation failed');
 step='verify-session-equality';const fat=require('../fat32-writer.cjs'),fd=fs.openSync(path.join(root,'private-real.img'),'r');let sealed;try{const p=fat.findGptPartition(fd,'AGUJA_CFG');sealed=fat.readFat32File(fd,fat.parseFat32Params(fd,p.offset),'aguja-profile.json');}finally{fs.closeSync(fd);}
 assert(!sealed.includes(token.access_token));assert(!sealed.includes(token.refresh_token));
 const e=JSON.parse(sealed),key=crypto.scryptSync(input.protection.passphrase,Buffer.from(e.salt,'base64url'),32,{N:32768,r:8,p:1,maxmem:64*1024**2}),d=crypto.createDecipheriv('aes-256-gcm',key,Buffer.from(e.iv,'base64url')),data=Buffer.from(e.data,'base64url');d.setAAD(Buffer.from('aguja-profile:1'));d.setAuthTag(data.subarray(-16));
 const raw=Buffer.concat([d.update(data.subarray(0,-16)),d.final()]);key.fill(0);const capsule=JSON.parse(raw);raw.fill(0);
 assert(Buffer.from(capsule.providers.antigravity.files['.gemini/antigravity-cli/antigravity-oauth-token'],'base64url').equals(expected),'Imported session mismatch');expected.fill(0);
 step='check-original-vault';after=await native.readCredential(run,{provider:'antigravity',store:'current'},env);assert(after&&original.equals(after),'Original vault entry changed');
 await w.screenshot({path:path.join(root,'real-import-approved.png'),fullPage:true});
 const report={ok:true,version:'0.9.5',packaged:true,realAccount:true,syntheticSession:false,installedCli:true,buttonImported:true,receiptContainsNoTokens:true,encryptedImageSessionMatches:true,originalVaultUnchanged:true,physicalUsbWritten:false};fs.writeFileSync(path.join(root,'real-result.json'),JSON.stringify(report));
 }catch{fs.writeFileSync(path.join(root,'real-result.json'),JSON.stringify({ok:false,realAccount:true,step}));process.exitCode=1;}
 finally{original?.fill(0);after?.fill(0);if(app)await app.close();}
})();
