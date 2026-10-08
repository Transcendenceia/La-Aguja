'use strict';
if(process.env.AGUJA_QA_PROXY)require('./proxy-fetch.cjs');
// Opt-in integration test: official downloads into an isolated disposable user home.
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),{execFile}=require('node:child_process');
const {AITools}=require(process.env.AGUJA_QA_MODULES?path.join(process.env.AGUJA_QA_MODULES,'ai-tools.cjs'):'../ai-tools.cjs');
const root=process.env.AGUJA_QA_ROOT||fs.mkdtempSync(path.join(os.tmpdir(),"aguja CLI á ' & "));
const home=path.join(root,'home'),state=path.join(root,'state');fs.mkdirSync(home,{recursive:true});fs.mkdirSync(state,{recursive:true});
const env={...process.env,HOME:home,USERPROFILE:home,LOCALAPPDATA:path.join(home,'AppData','Local'),APPDATA:path.join(home,'AppData','Roaming'),XDG_CONFIG_HOME:path.join(home,'.config'),XDG_DATA_HOME:path.join(home,'.local','share')};
// Exercise clean-host Node bootstrap, not this machine's global npm.
const systemRoot=process.env.SystemRoot||'C:\\Windows';env.PATH=process.platform==='win32'?path.join(systemRoot,'System32')+'/;'+path.join(systemRoot,'System32','WindowsPowerShell','v1.0'):'/usr/bin:/bin';delete env.Path;
function run(command,args,input,options={}){return new Promise((resolve,reject)=>{execFile(command,args,{env:{...env,...options.env},timeout:options.timeout||120000,windowsHide:true,maxBuffer:8*1024**2},(error,out,err)=>{if(error){fs.writeFileSync(path.join(root,'execute-failure.json'),JSON.stringify({exitCode:error.code,stderr:String(err).slice(-12000)},null,2));reject(new Error('CLI download/install/version verification failed.'));}else resolve(out);});});}
const manager=new AITools({directory:state,home,env,run,progress:()=>{}});
(async()=>{const report={platform:process.platform,isolated:true,accountsAuthorized:false,providers:{}};for(const id of ['codex','antigravity','claude','opencode']){try{await manager.install(id);const found=manager.resolve(id);if(!found||!manager.status()[id].installed)throw new Error('CLI executable not found.');await manager.execute(found,['--version'],{timeout:60000});report.providers[id]={installed:true,versionCommand:true};}catch(e){report.providers[id]={installed:false,error:e.message};}fs.writeFileSync(path.join(root,'install-result.json'),JSON.stringify(report,null,2));}
 report.ok=Object.values(report.providers).every(p=>p.installed);fs.writeFileSync(path.join(root,'install-result.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));if(!report.ok)process.exitCode=1;})().catch(()=>{process.exitCode=1;});
