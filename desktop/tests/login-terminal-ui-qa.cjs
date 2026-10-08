'use strict';
// Packaged Windows button -> native console -> synthetic keyboard input.
// Only provider command resolution is replaced; IPC and the launcher are real.
const {_electron:electron}=require('playwright'),fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),{execFile}=require('node:child_process');
const root=process.env.AGUJA_QA_ROOT,exe=process.env.AGUJA_QA_EXECUTABLE;
if(process.platform!=='win32'||!root||!exe)throw Error('Windows QA paths required');
const ps='C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe',quote=s=>"'"+s.replace(/'/g,"''")+"'",args=s=>['-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-EncodedCommand',Buffer.from(s,'utf16le').toString('base64')];
const run=s=>new Promise((resolve,reject)=>execFile(ps,args(s),{windowsHide:true,timeout:15000},(e,out)=>e?reject(e):resolve(out)));
const wait=async file=>{for(let i=0;i<150;i++){if(fs.existsSync(file))return JSON.parse(fs.readFileSync(file,'utf8').replace(/^\ufeff/,''));await new Promise(r=>setTimeout(r,100));}throw Error('Console fixture did not report');};
(async()=>{let app;const consoles=[],results={};try{
 fs.mkdirSync(root,{recursive:true});const env={...process.env};delete env.ELECTRON_RUN_AS_NODE;
 app=await electron.launch({executablePath:exe,chromiumSandbox:true,args:['--lang=es','--user-data-dir='+path.join(root,'ui-state')],env});
 const w=await app.firstWindow();await w.waitForLoadState('domcontentloaded');await w.locator('.step').nth(3).click();
 await app.evaluate(({app},root)=>{const req=process.getBuiltinModule('node:module').createRequire(app.getAppPath()+'/main.cjs'),{AITools,powershellArgs,windowsPowerShell,psQuote}=req('./ai-tools.cjs'),path=req('node:path');
 AITools.prototype.resolve=function(){return windowsPowerShell();};
 AITools.prototype.loginCommand=function(id){const ready=path.join(root,id+'-ready.json'),done=path.join(root,id+'-done.json');
 const script='$ErrorActionPreference="Stop";$Host.UI.RawUI.WindowTitle='+psQuote('LA AGUJA LOGIN QA '+id)+';@{pid=$PID;inputRedirected=[Console]::IsInputRedirected;outputRedirected=[Console]::IsOutputRedirected;errorRedirected=[Console]::IsErrorRedirected}|ConvertTo-Json|Set-Content -LiteralPath '+psQuote(ready)+' -Encoding UTF8;[Console]::WriteLine("LA AGUJA - QA sin cuentas: escribe AGUJA-LOGIN-QA");$answer=[Console]::ReadLine();@{inputReceived=($answer -ceq "AGUJA-LOGIN-QA")}|ConvertTo-Json|Set-Content -LiteralPath '+psQuote(done)+' -Encoding UTF8';
 return {command:windowsPowerShell(),args:powershellArgs(script)};};},root);
 await w.locator('#check-codex').click();await w.waitForFunction(()=>!document.getElementById('login-codex').disabled);
 for(const id of ['codex','antigravity','claude','opencode']){
 await w.locator('#mode-'+id).selectOption('import');await w.locator('#login-'+id).click();
 await w.locator('#notification.success').filter({hasText:'Se abrió el CLI oficial'}).waitFor();
 const before=await wait(path.join(root,id+'-ready.json'));assert.equal(before.inputRedirected,false);assert.equal(before.outputRedirected,false);assert.equal(before.errorRedirected,false);
 const title='LA AGUJA LOGIN QA '+id;
 const windows=await run(`Add-Type -AssemblyName UIAutomationClient;$w=@([Windows.Automation.AutomationElement]::RootElement.FindAll([Windows.Automation.TreeScope]::Children,[Windows.Automation.Condition]::TrueCondition)|Where-Object {$_.Current.Name -eq ${quote(title)}});if($w.Count -ne 1){throw 'Expected one QA console'};@{handle=$w[0].Current.NativeWindowHandle}|ConvertTo-Json -Compress`);const {handle}=JSON.parse(windows);consoles.push(handle);
 await run(`Add-Type -AssemblyName System.Windows.Forms;Add-Type -TypeDefinition 'using System;using System.Runtime.InteropServices;public class LoginQAInput{[DllImport("user32.dll")]public static extern bool SetForegroundWindow(IntPtr h);}';if(-not [LoginQAInput]::SetForegroundWindow([IntPtr]${handle})){throw 'Could not focus QA console'};Start-Sleep -Milliseconds 200;[Windows.Forms.SendKeys]::SendWait('AGUJA-LOGIN-QA{ENTER}')`);
 assert.equal((await wait(path.join(root,id+'-done.json'))).inputReceived,true);
 assert.match(await w.locator('#import-state-'+id).innerText(),/Aún no se ha importado/);
 results[id]={buttonLaunchesConsole:true,inputRedirected:false,outputRedirected:false,syntheticInputReceived:true,doesNotClaimImported:true};
 await run(`Add-Type -TypeDefinition 'using System;using System.Runtime.InteropServices;public class LoginQAClose{[DllImport("user32.dll")]public static extern bool PostMessage(IntPtr h,uint m,IntPtr w,IntPtr l);}';[LoginQAClose]::PostMessage([IntPtr]${handle},0x0010,[IntPtr]::Zero,[IntPtr]::Zero)|Out-Null`);consoles.pop();
 }
 await w.screenshot({path:path.join(root,'login-buttons.png'),fullPage:true});
 fs.writeFileSync(path.join(root,'ui-result.json'),JSON.stringify({ok:true,providers:results,packaged:true,realAccountsAuthorized:false},null,2));
 }catch(e){fs.writeFileSync(path.join(root,'ui-result.json'),JSON.stringify({ok:false,error:e.message,providers:results},null,2));if(app)try{await (await app.firstWindow()).screenshot({path:path.join(root,'failure.png'),fullPage:true});}catch{}throw e;}finally{
 for(const handle of consoles)try{await run(`Add-Type -TypeDefinition 'using System;using System.Runtime.InteropServices;public class LoginQAClose{[DllImport("user32.dll")]public static extern bool PostMessage(IntPtr h,uint m,IntPtr w,IntPtr l);}';[LoginQAClose]::PostMessage([IntPtr]${handle},0x0010,[IntPtr]::Zero,[IntPtr]::Zero)|Out-Null`);}catch{}
 if(app)await app.close();}})().catch(e=>{console.error(e.message);process.exitCode=1;});
