'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os'),{spawn,execFile}=require('node:child_process');
const modules=process.env.AGUJA_QA_MODULES||path.resolve(__dirname,'..');
const {openWindowsLoginTerminal,windowsPowerShell,powershellArgs}=require(path.join(modules,'ai-tools.cjs'));
const run=(command,args,input,options)=>new Promise((resolve,reject)=>execFile(command,args,{env:options.env,timeout:options.timeout,windowsHide:true},(e,out)=>e?reject(e):resolve(out)));
const wait=async file=>{for(let i=0;i<100;i++){if(fs.existsSync(file))return JSON.parse(fs.readFileSync(file,'utf8').replace(/^\ufeff/,''));await new Promise(r=>setTimeout(r,100));}throw Error('Console fixture did not report');};
const quote=s=>"'"+s.replace(/'/g,"''")+"'";

test('Windows login broker provides interactive console handles while old discarded stdio does not',{skip:process.platform!=='win32'},async()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),"aguja login á ' & ")),old=path.join(root,'old.json'),fixed=path.join(root,'fixed.json'),ready=path.join(root,'ready.json');
 const fixture=file=>`$ErrorActionPreference='Stop';@{inputRedirected=[Console]::IsInputRedirected;outputRedirected=[Console]::IsOutputRedirected;errorRedirected=[Console]::IsErrorRedirected;pid=$PID}|ConvertTo-Json|Set-Content -LiteralPath ${quote(file)} -Encoding UTF8`;
 let oldChild,loginPid;
 try{
  oldChild=spawn(windowsPowerShell(),powershellArgs(fixture(old),{visible:true}),{stdio:'ignore',detached:true,windowsHide:false});const oldExit=new Promise(resolve=>oldChild.once('exit',(code,signal)=>resolve({exited:true,code,signal})));await new Promise((resolve,reject)=>{oldChild.once('spawn',resolve);oldChild.once('error',reject);});
  const before=await Promise.race([wait(old),oldExit]);assert(before.exited||(before.inputRedirected&&before.outputRedirected),'Old launcher must not provide an interactive console');
  console.log(JSON.stringify({oldLauncher:before}));
  oldChild.kill();
  const fixtureScript=fixture(ready)+`;[Console]::WriteLine('LA AGUJA QA - escribe AGUJA-LOGIN-QA y pulsa Enter');$answer=[Console]::ReadLine();@{inputReceived=($answer -ceq 'AGUJA-LOGIN-QA');pid=$PID}|ConvertTo-Json|Set-Content -LiteralPath ${quote(fixed)} -Encoding UTF8`;
  const result=await openWindowsLoginTerminal({command:windowsPowerShell(),args:powershellArgs(fixtureScript)},{cwd:root,name:'QA interactiva',run});loginPid=result.pid;assert.equal(result.launched,true);
  const after=await wait(ready);assert.equal(after.inputRedirected,false);assert.equal(after.outputRedirected,false);assert.equal(after.errorRedirected,false);
  console.log(JSON.stringify({newConsole:after}));
  // Real input, routed only to this fixture's exact process/window. No account login.
  const inputScript=`$ErrorActionPreference='Stop';Add-Type -AssemblyName System.Windows.Forms;Add-Type -AssemblyName UIAutomationClient;Add-Type -TypeDefinition 'using System;using System.Runtime.InteropServices;public class LoginQAInput{[DllImport("user32.dll")]public static extern bool SetForegroundWindow(IntPtr h);}';$windows=@([Windows.Automation.AutomationElement]::RootElement.FindAll([Windows.Automation.TreeScope]::Children,[Windows.Automation.Condition]::TrueCondition)|Where-Object {$_.Current.Name -like '*QA interactiva*'});if($windows.Count -ne 1){throw 'Expected exactly one QA console'};if(-not [LoginQAInput]::SetForegroundWindow([IntPtr]$windows[0].Current.NativeWindowHandle)){throw 'Could not focus QA console'};Start-Sleep -Milliseconds 200;[Windows.Forms.SendKeys]::SendWait('AGUJA-LOGIN-QA{ENTER}')`;
  await run(windowsPowerShell(),powershellArgs(inputScript),null,{env:process.env,timeout:15000});assert.equal((await wait(fixed)).inputReceived,true);
  console.log(JSON.stringify({syntheticInputReceived:true}));
 }finally{if(oldChild)try{oldChild.kill();}catch{}if(loginPid)await run(windowsPowerShell(),powershellArgs(`Stop-Process -Id ${loginPid} -Force -ErrorAction SilentlyContinue;exit 0`),null,{env:process.env,timeout:15000});fs.rmSync(root,{recursive:true,force:true});}
});

test('Windows terminal start errors are not reported as a successful login launch',async()=>{
 await assert.rejects(()=>openWindowsLoginTerminal({command:'fixture',args:['login']},{run:async()=>{throw Error('SYNTHETIC-PRIVATE-ERROR');}}),e=>/abrir el terminal/.test(e.message)&&!e.message.includes('SYNTHETIC'));
 await assert.rejects(()=>openWindowsLoginTerminal({command:'fixture',args:['login']},{run:async()=>'{}'}),/abrir el terminal/);
});
