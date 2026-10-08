'use strict';
// Real Linux package, actual kitty PTY, synthetic keyboard input; no account login.
const {_electron:electron}=require('playwright'),fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),{spawn,execFileSync}=require('node:child_process');
const root=process.env.AGUJA_QA_ROOT,exe=process.env.AGUJA_QA_EXECUTABLE;
if(process.platform!=='linux'||!root||!exe)throw Error('Linux QA paths required');
const wait=async file=>{for(let i=0;i<150;i++){if(fs.existsSync(file))return JSON.parse(fs.readFileSync(file,'utf8'));await new Promise(r=>setTimeout(r,100));}throw Error('PTY fixture did not report');};
(async()=>{let app,keyboard;const results={};try{
 fs.mkdirSync(root,{recursive:true});const socket=path.join(root,'keyboard.sock');
 keyboard=spawn('/usr/bin/ydotoold',['--socket-path='+socket,'--socket-perm=0600','--mouse-off'],{stdio:'ignore'});
 for(let i=0;!fs.existsSync(socket)&&i<100;i++)await new Promise(r=>setTimeout(r,100));assert(fs.existsSync(socket),'Keyboard fixture not ready');
 const fixture=path.join(root,'console-fixture.py');fs.writeFileSync(fixture,`import sys,json,pathlib\np,r=sys.argv[1:];root=pathlib.Path(r)\nsys.stdout.write('\\033]0;LA AGUJA LOGIN QA '+p+'\\007');sys.stdout.flush()\n(root/(p+'-ready.json')).write_text(json.dumps({'stdinTTY':sys.stdin.isatty(),'stdoutTTY':sys.stdout.isatty(),'stderrTTY':sys.stderr.isatty()}))\nprint('LA AGUJA - QA sin cuentas: escribe AGUJALOGINQA',flush=True)\nanswer=input()\n(root/(p+'-done.json')).write_text(json.dumps({'inputReceived':answer=='AGUJALOGINQA'}))\n`);
 const env={...process.env};delete env.ELECTRON_RUN_AS_NODE;
 app=await electron.launch({executablePath:exe,chromiumSandbox:true,args:['--disable-gpu','--lang=es','--user-data-dir='+path.join(root,'isolated-state')],env});
 const w=await app.firstWindow();await w.waitForLoadState('domcontentloaded');await w.locator('#app-language').selectOption('es');await w.locator('.step').nth(3).click();
 await app.evaluate(({app},{root,fixture})=>{const req=process.getBuiltinModule('node:module').createRequire(app.getAppPath()+'/main.cjs'),{AITools}=req('./ai-tools.cjs');AITools.prototype.resolve=()=>'/usr/bin/python3';AITools.prototype.loginCommand=id=>({command:'/usr/bin/python3',args:[fixture,id,root]});},{root,fixture});
 await w.locator('#check-codex').click();await w.waitForFunction(()=>!document.getElementById('login-codex').disabled);
 for(const id of ['codex','antigravity','claude','opencode']){
  await w.locator('#mode-'+id).selectOption('import');await w.locator('#login-'+id).click();await w.locator('#notification.success').filter({hasText:'Se abrió el CLI oficial'}).waitFor();
  const ready=await wait(path.join(root,id+'-ready.json'));assert.deepEqual(ready,{stdinTTY:true,stdoutTTY:true,stderrTTY:true});
  const title='LA AGUJA LOGIN QA '+id;const windows=JSON.parse(execFileSync('/usr/bin/hyprctl',['-j','clients'],{encoding:'utf8'})).filter(p=>p.title===title);assert.equal(windows.length,1);
  execFileSync('/usr/bin/hyprctl',['dispatch','focuswindow','address:'+windows[0].address]);
  assert.equal(JSON.parse(execFileSync('/usr/bin/hyprctl',['-j','activewindow'],{encoding:'utf8'})).title,title,'Do not type into another application');
  const keyEnv={...process.env,YDOTOOL_SOCKET:socket};execFileSync('/usr/bin/ydotool',['type','AGUJALOGINQA'],{env:keyEnv,stdio:'pipe'});execFileSync('/usr/bin/ydotool',['key','28:1','28:0'],{env:keyEnv,stdio:'pipe'});
  assert.equal((await wait(path.join(root,id+'-done.json'))).inputReceived,true);assert.match(await w.locator('#import-state-'+id).innerText(),/Aún no se ha importado/);
  results[id]={buttonLaunchesPTY:true,syntheticInputReceived:true,doesNotClaimImported:true};
 }
 const security=await app.evaluate(({BrowserWindow})=>{const p=BrowserWindow.getAllWindows()[0].webContents.getLastWebPreferences();return {sandbox:p.sandbox,contextIsolation:p.contextIsolation,nodeIntegration:p.nodeIntegration};});assert.deepEqual(security,{sandbox:true,contextIsolation:true,nodeIntegration:false});
 assert.equal(await w.locator('#bitlocker-card').isVisible(),false);await w.screenshot({path:path.join(root,'linux-login-buttons.png'),fullPage:true});
 fs.writeFileSync(path.join(root,'result.json'),JSON.stringify({ok:true,packaged:true,providers:results,security,bitlockerWindowsOnly:true,realAccountsAuthorized:false},null,2));
 }catch(e){fs.writeFileSync(path.join(root,'result.json'),JSON.stringify({ok:false,error:e.message,providers:results}));throw e;}finally{if(app)await app.close();if(keyboard)keyboard.kill();}})().catch(e=>{console.error(e.message);process.exitCode=1;});
