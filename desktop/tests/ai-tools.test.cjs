'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const {AITools,provider,psQuote,powershellArgs,invocation,networkError}=require('../ai-tools.cjs'),core=require('../core.cjs'),provisioning=require('../provisioning.cjs');
test('unknown/prototype providers cannot select an installer or execute a CLI',()=>{for(const id of ['__proto__','constructor','toString','codex; touch /tmp/no',''])assert.throws(()=>provider(id));});
test('PowerShell literal paths preserve spaces, accents, apostrophes and metacharacters',()=>{
 const filename="C:\\Users\\Mar lón's & tools\\codex.exe",script='& '+psQuote(filename)+" 'login'";const args=powershellArgs(script,{visible:true});assert(args.includes('-NoExit'));assert(!args.includes('-NonInteractive'));assert.equal(Buffer.from(args.at(-1),'base64').toString('utf16le'),script);assert(script.includes("lón''s & tools"));assert(!args.includes('-ExecutionPolicy'));const hidden=powershellArgs(script);assert.deepEqual(hidden,['-NoProfile','-NonInteractive','-Command',script]);
});
test('CLI lookup includes desktop-specific user bins and does not search relative PATH entries',()=>{const dir=fs.mkdtempSync(path.join(os.tmpdir(),'aguja-cli-path-'));try{
 const bin=path.join(dir,'.local','bin');fs.mkdirSync(bin,{recursive:true});const cli=path.join(bin,'agy');fs.writeFileSync(cli,'fixture',{mode:0o700});assert.equal(core.resolveProviderBinary('agy',{home:dir,env:{PATH:'.'}}),cli);assert.throws(()=>core.resolveProviderBinary('../agy'));assert.equal(core.resolveProviderBinary('codex',{home:dir,env:{PATH:''}}),null);
 }finally{fs.rmSync(dir,{recursive:true,force:true});}});
test('already-installed CLI is never reinstalled, authenticated or mutated',async()=>{const dir=fs.mkdtempSync(path.join(os.tmpdir(),'aguja-ai-existing-'));try{fs.mkdirSync(path.join(dir,'.local','bin'),{recursive:true});fs.writeFileSync(path.join(dir,'.local','bin','codex'),'fixture',{mode:0o700});const manager=new AITools({directory:dir,home:dir,env:{PATH:''},run:()=>{throw Error('must not execute');}});assert.deepEqual(await manager.install('codex'),{installed:true,alreadyInstalled:true});assert.equal(manager.status().codex.installed,true);}finally{fs.rmSync(dir,{recursive:true,force:true});}});
test('Windows npm entry points support JS and native packages without invoking shims in special paths',()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),"aguja npm á ' & "));try{
  for(const [name,pkg,bin]of [['codex','@openai/codex','bin/codex.js'],['claude','@anthropic-ai/claude-code','bin/claude.exe'],['opencode','opencode-ai','./bin/opencode.exe']]){
   const root=path.join(dir,'node_modules',pkg),entry=path.resolve(root,bin);fs.mkdirSync(path.dirname(entry),{recursive:true});fs.writeFileSync(entry,'fixture');fs.writeFileSync(path.join(root,'package.json'),JSON.stringify({bin:{[name]:bin}}));
   const call=invocation(path.join(dir,name+'.cmd'),['--version'],{platform:'win32',node:path.join(dir,'node.exe')});
   assert.equal(call.command,name==='codex'?path.join(dir,'node.exe'):entry);assert.deepEqual(call.args,name==='codex'?[entry,'--version']:['--version']);
  }
 }finally{fs.rmSync(dir,{recursive:true,force:true});}
});
test('native import maps custom host paths to canonical Linux paths and never copies hooks/MCP',()=>{const home=fs.mkdtempSync(path.join(os.tmpdir(),"aguja-config-space-'"));try{
 const config=path.join(home,'custom codex');fs.mkdirSync(config);fs.writeFileSync(path.join(config,'auth.json'),JSON.stringify({tokens:{access_token:'SYNTHETIC',refresh_token:'SYNTHETIC'}}));fs.writeFileSync(path.join(config,'config.toml'),'model="fixture"\n[mcp_servers.evil]\ncommand="C:\\\\private\\\\bad.exe"\n');
 const result=provisioning.discover('codex',{home,env:{CODEX_HOME:config}});assert.equal(result.portable,true);assert.deepEqual(result.paths.map(p=>p.target),['.codex/auth.json','.codex/config.toml']);const out=provisioning.materialize({providers:{codex:{mode:'import'}}},{codex:result.paths});assert(!JSON.stringify(out).includes(home));const text=Buffer.from(out.providers.codex.files['.codex/config.toml'],'base64url').toString();assert(text.includes('cli_auth_credentials_store = "file"'));assert(!text.includes('mcp_servers'));assert(!text.includes('private'));
 // Re-read approval at image creation: replacing a native file with a symlink fails.
 fs.renameSync(path.join(config,'auth.json'),path.join(home,'old-auth'));fs.symlinkSync(path.join(home,'old-auth'),path.join(config,'auth.json'));assert.throws(()=>provisioning.materialize({providers:{codex:{mode:'import'}}},{codex:result.paths}));
 }finally{fs.rmSync(home,{recursive:true,force:true});}});
test('OpenCode XDG and explicit config paths are resolved without leaking host paths',()=>{const items=provisioning.locations('opencode',{home:'/fixture',env:{XDG_DATA_HOME:'/native data',OPENCODE_CONFIG:'/config space/opencode.json'}});assert.equal(items[0].source,'/native data/opencode/auth.json');assert.equal(items[0].target,'.local/share/opencode/auth.json');assert.equal(items[1].source,'/config space/opencode.json');});
test('invalid or empty auth and malformed Antigravity tokens never become portable sessions',()=>{for(const raw of ['{}','[]','broken'])assert.throws(()=>provisioning.sanitize('codex','.codex/auth.json',Buffer.from(raw)));assert.throws(()=>provisioning.sanitize('antigravity','.gemini/antigravity-cli/antigravity-oauth-token',Buffer.from(JSON.stringify({token:{refresh_token:[]}}))));});

test('network diagnostics classify bounded AggregateError causes without exposing URLs, secrets or causes',()=>{
 const privateText='https://private.invalid/?key=SYNTHETIC-NEVER-PUBLIC';
 const blocked=new TypeError('fetch failed',{cause:new AggregateError([Object.assign(new Error(privateText),{code:'EACCES'}),Object.assign(new Error(privateText),{code:'ETIMEDOUT'})],privateText)});
 const safe=networkError(blocked);assert.match(safe.message,/denegado la conexión HTTPS/);assert.match(safe.message,/imagen local/);assert(!safe.message.includes(privateText));assert.equal(safe.cause,undefined);
 for(const [code,pattern]of [['ENOTFOUND',/DNS/],['ETIMEDOUT',/tardó demasiado/],['ECONNREFUSED',/establecer la conexión HTTPS/],['CERT_HAS_EXPIRED',/certificado HTTPS/]]){
  const original=Object.assign(new Error(privateText),{code});const result=networkError(new TypeError('fetch failed',{cause:original}));assert.match(result.message,pattern);assert(!result.message.includes('SYNTHETIC'));assert.equal(result.cause,undefined);
 }
 const diskError=Object.assign(new Error('Local fixture error'),{code:'ENOENT'});assert.equal(networkError(diskError),diskError);
 const cyclic={message:'fetch failed'};cyclic.cause=cyclic;assert.match(networkError(cyclic).message,/HTTPS/);
});
test('blocked official downloads give useful diagnostics for all installers without executing a CLI',async()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'aguja-network-blocked-')),savedFetch=globalThis.fetch;
 globalThis.fetch=async()=>{throw new TypeError('fetch failed',{cause:new AggregateError([Object.assign(new Error('SYNTHETIC-URL-TOKEN-NEVER-PUBLIC'),{code:'EACCES'})])});};
 try{
  for(const id of ['codex','claude','opencode','antigravity']){
   const manager=new AITools({directory:path.join(root,id),home:root,env:{PATH:''},run:()=>{throw Error('Must not execute a CLI after failed download');}});
   await assert.rejects(()=>manager.install(id),error=>/denegado la conexión HTTPS/.test(error.message)&&!error.message.includes('SYNTHETIC')&&error.cause===undefined);
   assert.equal(manager.status()[id].installed,false);
  }
 }finally{globalThis.fetch=savedFetch;fs.rmSync(root,{recursive:true,force:true});}
});
test('streaming download errors are classified while local destination errors remain local',async()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'aguja-network-stream-')),savedFetch=globalThis.fetch;
 try{
  const manager=new AITools({directory:root,run:()=>{throw Error('unused');}});
  globalThis.fetch=async()=>({ok:true,body:(async function*(){yield Buffer.from('fixture');throw Object.assign(new Error('SYNTHETIC-PRIVATE-NETWORK-URL'),{code:'ECONNRESET'});})()});
  const dest=path.join(root,'partial');await assert.rejects(()=>manager.download('https://fixture.invalid/file',dest),error=>/conexión HTTPS/.test(error.message)&&!error.message.includes('SYNTHETIC'));
  fs.rmSync(dest);
  globalThis.fetch=async()=>({ok:true,body:(async function*(){yield Buffer.from('fixture');})()});fs.writeFileSync(dest,'existing');
  await assert.rejects(()=>manager.download('https://fixture.invalid/file',dest),error=>error.code==='EEXIST'&&!/conexión HTTPS/.test(error.message));assert.equal(fs.readFileSync(dest,'utf8'),'existing');
 }finally{globalThis.fetch=savedFetch;fs.rmSync(root,{recursive:true,force:true});}
});
