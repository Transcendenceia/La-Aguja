'use strict';
// Real Electron/IPC on both OSes; synthetic image and mocked USB helpers only.
const {_electron:electron}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
(async()=>{
 const temp=fs.mkdtempSync(path.join(os.tmpdir(),'aguja-result-ui-')),image=path.join(temp,'fixture.img'),bootstrap=path.join(temp,'bootstrap.cjs'),root=process.env.AGUJA_QA_APP_ROOT||path.resolve(__dirname,'..');let app;
 fs.writeFileSync(image,'synthetic image');
 fs.writeFileSync(bootstrap,`
 const fs=require('node:fs'),{EventEmitter}=require('node:events'),electron=require('electron');
 const nativeMessageBox=electron.dialog.showMessageBox.bind(electron.dialog);
 const state=globalThis.flashResultFixture={answer:0,error:null,unverified:false,preparationError:false,writes:0,prepares:0,dialogs:[]};
 const root=${JSON.stringify(root)};
 const result=()=>state.error?{ok:false,error:state.error}:{ok:true,verified:!state.unverified};
 require(root+'/core.cjs').getHTTPS=async()=>{throw Error('Synthetic offline fixture');};
 require(root+'/provisioning.cjs').prepareWindows=async d=>{state.prepares++;if(state.preparationError)throw Error('La imagen no se pudo preparar: espacio insuficiente.');fs.writeFileSync(d.output,'private synthetic image');};
 require(root+'/windows-flash.cjs').flashWindows=async()=>{state.writes++;return JSON.stringify(result());};
 require(root+'/bitlocker.cjs').getBitLockerStatus=async()=>({available:false,volumes:[]});
 require('node:child_process').spawn=(command,args)=>{const p=new EventEmitter();p.stdout=new EventEmitter();p.stderr=new EventEmitter();p.stdin=new EventEmitter();p.kill=()=>{};p.stdin.end=input=>setImmediate(()=>{try{
 let out='',code=0;
 if(command==='/usr/bin/lsblk')out=JSON.stringify({blockdevices:[{path:'/dev/fixture-usb',type:'disk',tran:'usb',rm:true,serial:'FIXTURE',size:1024**3,model:'Synthetic USB',mountpoints:[]}]});
 else if(command==='/usr/bin/python3'&&input){const d=JSON.parse(input);state.prepares++;if(state.preparationError){out=JSON.stringify({ok:false,error:'La imagen no se pudo preparar: espacio insuficiente.'});code=1;}else{fs.writeFileSync(d.output_path,'private synthetic image');out=JSON.stringify({ok:true});}}
 else if(command==='/usr/bin/python3')out='';
 else if(command==='/usr/bin/pkexec'){state.writes++;out=JSON.stringify(result());if(state.error)code=1;}
 else if(/powershell/i.test(command))out=JSON.stringify([{device:${JSON.stringify('\\\\.\\PhysicalDrive99')},serial:'FIXTURE',size:1024**3,model:'Synthetic USB',eligible:true}]);
 else throw Error('Fixture: unrelated helper blocked');
 state.lastCommand={command,out,code};p.stdout.emit('data',Buffer.from(out));p.emit('close',code);
 }catch(e){p.emit('error',e);}});return p;};
 electron.dialog.showOpenDialog=async()=>({canceled:false,filePaths:[${JSON.stringify(image)}]});
 electron.dialog.showSaveDialog=async()=>{throw Error('Unexpected Save As');};
 electron.dialog.showMessageBox=async(w,o)=>{if(o.type==='warning')return {response:state.answer};state.dialogs.push(o);return ${process.env.AGUJA_QA_NATIVE_DIALOGS==='1'?'nativeMessageBox(w,o)':'{response:0}'};};
 require(root+'/main.cjs');
 `);
 try{
 const env={...process.env,ELECTRON_DISABLE_SECURITY_WARNINGS:'1'};delete env.ELECTRON_RUN_AS_NODE;
 app=await electron.launch({executablePath:process.env.AGUJA_QA_ELECTRON||undefined,args:[bootstrap,'--lang=es','--no-sandbox','--user-data-dir='+path.join(temp,'state')],env,timeout:60000});
 const w=await app.firstWindow();await w.waitForLoadState('domcontentloaded');await w.locator('#app-language').selectOption('es');await w.locator('#image-import').click();await w.locator('#image-status').waitFor({state:'visible'});
 await w.locator('.step').nth(7).click();await w.locator('input[name="protection"][value="plain"]').check();await w.locator('#disks-refresh').click();await w.locator('#usb-disks option[value="0"]').waitFor({state:'attached'});await w.locator('#usb-disks').selectOption('0');
 const idle=()=>w.waitForFunction(()=>!document.getElementById('flash').disabled,null,{timeout:30000});
 const state=()=>app.evaluate(()=>globalThis.flashResultFixture);
 await w.locator('#flash').click();await idle();let s=await state();assert.equal(s.writes,0);assert.equal(s.dialogs.length,0);
 await app.evaluate(()=>{globalThis.flashResultFixture.answer=1;});await w.locator('#flash').click();await w.locator('#notification.success').waitFor();s=await state();assert.equal(s.dialogs.length,1);assert.equal(s.dialogs[0].title,'USB listo');assert.equal(s.dialogs[0].type,'info');assert.equal(s.writes,1);assert.equal(s.prepares,1);
 for(const error of ['No se autorizó la grabación. Permiso denegado para el USB.','USB: error de escritura; dispositivo desconectado.','USB: la lectura de comprobación no coincide con la imagen.']){
  await app.evaluate((_,e)=>{globalThis.flashResultFixture.error=e;},error);await w.locator('#flash').click();await idle();s=await state();assert.equal(s.dialogs.at(-1).type,'error');assert(s.dialogs.at(-1).detail.startsWith(error),JSON.stringify({dialog:s.dialogs.at(-1),command:s.lastCommand}));assert(!(await w.locator('#notification').getAttribute('class')).includes('success'));
 }
 await app.evaluate(()=>{globalThis.flashResultFixture.error=null;globalThis.flashResultFixture.unverified=true;});await w.locator('#flash').click();await idle();s=await state();assert.equal(s.dialogs.at(-1).type,'error');assert(s.dialogs.at(-1).detail.includes('lectura verificada'));
 await app.evaluate(()=>{globalThis.flashResultFixture.unverified=false;globalThis.flashResultFixture.preparationError=true;});await w.locator('.step').nth(1).click();await w.locator('#hostname').fill('aguja-fixture-changed');await w.locator('.step').nth(7).click();const writes=s.writes;await w.locator('#flash').click();await idle();s=await state();assert.equal(s.writes,writes);assert(s.dialogs.at(-1).detail.includes('espacio insuficiente'));
 const report={ok:true,platform:process.platform,realElectron:true,nativeDialogs:process.env.AGUJA_QA_NATIVE_DIALOGS==='1',cases:['canceled-no-dialog','verified-success','permissions','disconnected-write','readback-mismatch','unverified-receipt','preparation-no-space'],dialogs:s.dialogs.map(({title,type,detail})=>({title,type,detail})),physicalUsbWritten:false,writerMocked:true};
 if(process.env.AGUJA_QA_RESULT)fs.writeFileSync(process.env.AGUJA_QA_RESULT,JSON.stringify(report,null,2));console.log(JSON.stringify(report));
 }finally{if(app)await app.close();fs.rmSync(temp,{recursive:true,force:true});}
})().catch(e=>{console.error(e.stack);process.exitCode=1;});
