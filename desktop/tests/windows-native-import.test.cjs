'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os'),crypto=require('node:crypto');
const n=require('../windows-native-import.cjs'),p=require('../provisioning.cjs');
const agy={token:{access_token:'SYNTHETIC-AGY',refresh_token:'SYNTHETIC-AGY',token_type:'Bearer',expiry:'2020-01-01T00:00:00Z'},auth_method:'consumer',id_token:'SYNTHETIC-AGY'};
function fixture(t){const home=fs.mkdtempSync(path.join(os.tmpdir(),'aguja-native-'));t.after(()=>fs.rmSync(home,{recursive:true,force:true}));fs.mkdirSync(path.join(home,'.codex'));return {home,env:{}};}
function file(options,relative,data){const f=path.join(options.home,...relative.split('/'));fs.mkdirSync(path.dirname(f),{recursive:true});fs.writeFileSync(f,typeof data==='string'?data:JSON.stringify(data),{mode:0o600});return f;}
test('Codex Win32 keyring identifier matches Rust canonical path, including UNC and missing profile',()=>{
 const hash=s=>crypto.createHash('sha256').update(s).digest('hex').slice(0,16);
 assert.equal(n.codexStoreKey('C:\\Users\\Me\\.codex',()=> 'C:\\Users\\Me\\.codex'),hash('\\\\?\\C:\\Users\\Me\\.codex'));
 assert.equal(n.codexStoreKey('C:\\Users\\Me\\.codex',()=> '\\\\?\\C:\\Users\\Me\\.codex'),hash('\\\\?\\C:\\Users\\Me\\.codex'));
 assert.equal(n.codexStoreKey('\\\\srv\\profile',()=> '\\\\srv\\profile'),hash('\\\\?\\UNC\\srv\\profile'));
 assert.equal(n.codexStoreKey('C:\\missing',()=>{throw Error();}),hash('C:\\missing'));
});
test('Antigravity native session uses memory only and exports just portable OAuth',async t=>{
 const options=fixture(t);let calls=0;const blob=Buffer.from(JSON.stringify({...agy,project:'not-portable',region:'not-portable'}));
 const r=await n.discover('antigravity',options,{platform:'win32',readCredential:async request=>{calls++;assert.deepEqual(request,{provider:'antigravity'});return blob;}});
 assert(r.portable);assert.equal(calls,1);assert(blob.every(x=>x===0));assert.equal(r.paths[0].source,undefined);
 const c=p.materialize({providers:{antigravity:{mode:'import'}}},{antigravity:r.paths});assert.deepEqual(JSON.parse(Buffer.from(c.providers.antigravity.files[r.paths[0].target],'base64url')),agy);
 n.clear(r.paths);assert(r.paths[0].credential.every(x=>x===0));assert.throws(()=>p.materialize({providers:{antigravity:{mode:'import'}}},{antigravity:r.paths}));
});
test('Codex keyring beats stale file, UTF16 no BOM, config export forces portable file store',async t=>{
 const options=fixture(t);file(options,'.codex/config.toml','cli_auth_credentials_store="keyring"\nmodel="gpt-5"');file(options,'.codex/auth.json',{OPENAI_API_KEY:'SYNTHETIC-STALE'});
 const auth={tokens:{access_token:'SYNTHETIC-ACTIVE',refresh_token:'SYNTHETIC-REFRESH',id_token:'SYNTHETIC-ID'},last_refresh:'2026-10-08T00:00:00Z'};
 const blob=Buffer.from(JSON.stringify(auth),'utf16le');const r=await n.discover('codex',options,{platform:'win32',realpath:()=> 'C:\\Users\\Test\\.codex',readCredential:async request=>{assert.match(request.target,/^cli\|[a-f0-9]{16}\.Codex Auth$/);return blob;}});
 const c=p.materialize({providers:{codex:{mode:'import'}}},{codex:r.paths});assert.deepEqual(JSON.parse(Buffer.from(c.providers.codex.files['.codex/auth.json'],'base64url')),auth);assert.match(Buffer.from(c.providers.codex.files['.codex/config.toml'],'base64url').toString(),/cli_auth_credentials_store = "file"/);
});
test('Codex file mode never consults vault, keyring missing does not import stale auth, auto does',async t=>{
 const options=fixture(t);file(options,'.codex/auth.json',{OPENAI_API_KEY:'SYNTHETIC'});
 const reader=async()=>{throw Error('must not read vault');};assert((await n.discover('codex',options,{platform:'win32',readCredential:reader})).portable);
 file(options,'.codex/config.toml','cli_auth_credentials_store="keyring"');assert.equal((await n.discover('codex',options,{platform:'win32',readCredential:async()=>null})).portable,false);
 file(options,'.codex/config.toml','cli_auth_credentials_store="auto"');assert((await n.discover('codex',options,{platform:'win32',readCredential:async()=>null})).portable);
});
test('Codex encrypted age store decrypts native global/CODEX_AUTH only; tamper/wrong key rejected',async t=>{
 const options=fixture(t);const {Encrypter}=await import('age-encryption');const e=new Encrypter();e.setScryptWorkFactor(10);e.setPassphrase('SYNTHETIC-PASSPHRASE');const auth={tokens:{access_token:'SYNTHETIC-CODEX',refresh_token:'SYNTHETIC-CODEX'}};
 const bytes=await e.encrypt(JSON.stringify({version:1,secrets:{'global/CODEX_AUTH':JSON.stringify(auth),'global/UNRELATED':'SYNTHETIC-UNRELATED'}}));
 file(options,'.codex/config.toml','cli_auth_credentials_store="keyring"\n[features]\nsecret_auth_storage=true');const encrypted=path.join(options.home,'.codex','secrets','codex_auth.age');fs.mkdirSync(path.dirname(encrypted));fs.writeFileSync(encrypted,bytes);
 const r=await n.discover('codex',options,{platform:'win32',readCredential:async request=>{assert.match(request.target,/^secrets\|[a-f0-9]{16}\.codex$/);return Buffer.from('SYNTHETIC-PASSPHRASE','utf16le');}});assert.deepEqual(JSON.parse(r.paths[0].credential),auth);
 await assert.rejects(n.decryptCodexAge(Buffer.from(bytes),'wrong'),/No se pudo descifrar/);const tampered=Buffer.from(bytes);tampered[tampered.length-1]^=1;await assert.rejects(n.decryptCodexAge(tampered,'SYNTHETIC-PASSPHRASE'),/No se pudo descifrar/);
});
test('Claude/OpenCode Windows native files and configured directories remain usable without vault',async t=>{
 const options=fixture(t);file(options,'.claude/.credentials.json',{claudeAiOauth:{accessToken:'SYNTHETIC',refreshToken:'SYNTHETIC'}});file(options,'.local/share/opencode/auth.json',{openai:{type:'oauth',access:'SYNTHETIC',refresh:'SYNTHETIC',expires:0}});
 for(const provider of ['claude','opencode'])assert((await n.discover(provider,options,{platform:'win32',readCredential:async()=>{throw Error('must not query vault');}})).portable);
});
test('Linux does not change stores and explicit Antigravity folder uses its file',async t=>{
 const options=fixture(t);file(options,'.gemini/antigravity-cli/antigravity-oauth-token',agy);
 const deps={readCredential:async()=>{throw Error('vault must not be read');}};
 assert((await n.discover('antigravity',options,{...deps,platform:'linux'})).portable);
 options.configDirectory=path.join(options.home,'.gemini','antigravity-cli');assert((await n.discover('antigravity',options,{...deps,platform:'win32'})).portable);
});
test('Credential bridge validates output, redacts private exceptions and does not execute shell profiles',async()=>{
 const raw=Buffer.from('SYNTHETIC');const value=await n.readCredential(async(cmd,args,request)=>{assert(args.includes('-NoProfile'));assert(!args.includes('-ExecutionPolicy'));assert.deepEqual(request,{provider:'antigravity'});return JSON.stringify({status:'found',blob:raw.toString('base64')});},{provider:'antigravity'});assert(value.equals(raw));
 assert.equal(await n.readCredential(async()=>'{"status":"missing"}',{provider:'antigravity'}),null);
 await assert.rejects(n.readCredential(async()=>{throw Error('SYNTHETIC-PRIVATE');},{provider:'antigravity'}),e=>!e.message.includes('SYNTHETIC')&&/Administrador/.test(e.message));
});
// Real Credential Manager roundtrip, under a unique synthetic USERPROFILE and
// CODEX_HOME. Never overwrite an existing entry; remove only our own fixture.
test('native Windows Credential Manager: agy UTF8 and Codex UTF16 roundtrip',{skip:process.platform!=='win32'},async t=>{
 const {spawn}=require('node:child_process'),{powershellArgs,windowsPowerShell}=require('../ai-tools.cjs');
 const options=fixture(t);options.env={...process.env,USERPROFILE:options.home};
 const run=(command,args,input,settings)=>new Promise((resolve,reject)=>{
  const child=spawn(command,args,{env:{...process.env,...settings.env},windowsHide:true,stdio:['pipe','pipe','pipe']});let out='';child.stdout.on('data',b=>out+=b);child.stderr.resume();child.on('error',()=>reject(Error('native bridge failed')));child.on('close',code=>code?reject(Error('native bridge failed')):resolve(out));child.stdin.end(input===null?'':JSON.stringify(input));
 });
 const declaration=fs.readFileSync(path.resolve(__dirname,'../windows-credentials.ps1'),'utf8').replace(/\r\n/g,'\n').split("@'\n")[1].split("\n'@")[0].replace('[DllImport("advapi32.dll")] public static extern void CredFree', '[DllImport("advapi32.dll", EntryPoint="CredWriteW", CharSet=CharSet.Unicode, SetLastError=true)] public static extern bool Write(ref Credential credential,uint flags);\n [DllImport("advapi32.dll", EntryPoint="CredDeleteW", CharSet=CharSet.Unicode)] public static extern bool Delete(string target,uint type,uint flags);\n [DllImport("advapi32.dll")] public static extern void CredFree');
 const fixtureScript=`$ErrorActionPreference='Stop';[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false);Add-Type -TypeDefinition @'\n${declaration}\n'@\n$r=[Console]::In.ReadToEnd()|ConvertFrom-Json;if($r.op -eq 'delete'){[AgujaWinCred]::Delete($r.target,1,0)|Out-Null;exit};$p=[IntPtr]::Zero;if([AgujaWinCred]::Read($r.target,1,0,[ref]$p)){[AgujaWinCred]::CredFree($p);throw 'Fixture collision'};$b=[Convert]::FromBase64String($r.blob);$pin=[Runtime.InteropServices.GCHandle]::Alloc($b,[Runtime.InteropServices.GCHandleType]::Pinned);try{$c=New-Object AgujaWinCred+Credential;$c.Type=1;$c.TargetName=$r.target;$c.UserName='Aguja synthetic fixture';$c.Persist=1;$c.BlobSize=$b.Length;$c.Blob=$pin.AddrOfPinnedObject();if(-not [AgujaWinCred]::Write([ref]$c,0)){throw 'Fixture write failed'}}finally{$pin.Free();[Array]::Clear($b,0,$b.Length)}`;
 const bridge=request=>run(windowsPowerShell(options.env),powershellArgs(fixtureScript),request,{env:options.env});
 const targets=[['antigravity','gemini:'+path.join(options.home,'.gemini','jetski-standalone-oauth-token'),Buffer.from(JSON.stringify(agy))],['codex','cli|'+n.codexStoreKey(path.join(options.home,'.codex'))+'.Codex Auth',Buffer.from(JSON.stringify({OPENAI_API_KEY:'SYNTHETIC-ONLY'}),'utf16le')]];
 file(options,'.codex/config.toml','cli_auth_credentials_store="keyring"');
 for(const [provider,target,blob]of targets){let written=false;try{
  await bridge({target,op:'write',blob:blob.toString('base64')});written=true;
  const result=await n.discover(provider,options,{run});assert.equal(result.portable,true);assert(Buffer.isBuffer(result.paths[0].credential));
  const c=p.materialize({providers:{[provider]:{mode:'import'}}},{[provider]:result.paths});assert(Buffer.from(c.providers[provider].files[result.paths[0].target],'base64url').length>10);n.clear(result.paths);
 }finally{if(written)await bridge({target,op:'delete'});}}
});
