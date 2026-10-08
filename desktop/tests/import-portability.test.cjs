'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const core=require('../core.cjs'),p=require('../provisioning.cjs'),{userEnvironment}=require('../windows-environment.cjs');
test('Windows editor encodings import credentials and normalize portable files to UTF-8',()=>{
 for(const [id,target,data]of [['codex','.codex/auth.json',{tokens:{access_token:'SYNTHETIC',refresh_token:'SYNTHETIC'}}],['claude','.claude/.credentials.json',{claudeAiOauth:{accessToken:'SYNTHETIC',refreshToken:'SYNTHETIC'}}]]){
  const json=JSON.stringify(data),le=Buffer.from(json,'utf16le'),be=Buffer.from(le).swap16();
  for(const raw of [Buffer.from('\ufeff'+json),Buffer.concat([Buffer.from([255,254]),le]),Buffer.concat([Buffer.from([254,255]),be])])assert.deepEqual(JSON.parse(p.sanitize(id,target,raw)),data);
 }
 assert.match(p.sanitize('codex','.codex/config.toml',Buffer.from('\ufeffmodel="synthetic"')).toString(),/model = "synthetic"/);
});
test('explicit profile folders import all providers into canonical Linux files without copying executable configuration',()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),"aguja import á ' & "));
 try{
  const fixtures={codex:{'auth.json':{tokens:{access_token:'SYNTHETIC'}},'config.toml':'model="fixture"\n[mcp_servers.bad]\ncommand="bad.exe"'},claude:{'.credentials.json':{claudeAiOauth:{accessToken:'SYNTHETIC'}},'settings.json':{model:'fixture',hooks:{evil:'bad'}}},antigravity:{'antigravity-oauth-token':{token:{access_token:'SYNTHETIC',refresh_token:'SYNTHETIC',token_type:'Bearer',expiry:'2025-01-01T00:00:00Z'},auth_method:'oauth',id_token:'SYNTHETIC'},'settings.json':{model:'fixture',modelProvider:'gemini'}},opencode:{'auth.json':{openai:{type:'oauth',access:'SYNTHETIC',refresh:'SYNTHETIC'}},'opencode.jsonc':'{ // comment\n"model":"fixture/model","plugin":["evil"],"mcp":{"evil":{}},\n}'}};
  for(const [id,files]of Object.entries(fixtures)){
   const folder=path.join(root,id);fs.mkdirSync(folder);
   for(const [name,data]of Object.entries(files))fs.writeFileSync(path.join(folder,name),typeof data==='string'?data:JSON.stringify(data),{mode:0o600});
   const result=p.discover(id,{home:root,env:{},configDirectory:folder});assert.equal(result.portable,true,id);assert.equal(result.paths.length,2,id);
   const out=p.materialize({providers:{[id]:{mode:'import'}}},{[id]:result.paths});assert(!JSON.stringify(out).includes(root));
   for(const value of Object.values(out.providers[id].files)){const raw=Buffer.from(value,'base64url').toString();assert(!/evil|bad.exe|modelProvider|hooks|plugin/.test(raw));}
  }
  const folder=path.join(root,'opencode');fs.writeFileSync(path.join(folder,'opencode.jsonc'),'{"model":broken}');const result=p.discover('opencode',{home:root,env:{},configDirectory:folder});assert.equal(result.portable,true);assert.equal(result.paths.length,1);
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});
test('Windows recheck refreshes persisted tool locations without querying secret variables or shell profiles',async()=>{
 let query;
 const env=await userEnvironment(async(command,args)=>{query=args.at(-1);return JSON.stringify({Path:'C:\\new tools;C:\\machine tools',CODEX_HOME:'C:\\custom codex',PNPM_HOME:'C:\\pnpm',OPENAI_API_KEY:'SYNTHETIC-MUST-NOT-IMPORT'});},{Path:'C:\\old tools',CLAUDE_CONFIG_DIR:'C:\\explicit claude'});
 assert.equal(env.PATH,'C:\\old tools;C:\\new tools;C:\\machine tools');assert.equal(env.CODEX_HOME,'C:\\custom codex');assert.equal(env.CLAUDE_CONFIG_DIR,'C:\\explicit claude');assert.equal(env.OPENAI_API_KEY,undefined);assert(!Object.hasOwn(env,'Path'));assert(!query.includes('OPENAI_API_KEY'));assert(!query.includes('$PROFILE'));
 assert.deepEqual(await userEnvironment(async()=>{throw Error('SYNTHETIC-PRIVATE');},{Path:'old'}),{Path:'old'});
});
test('native Windows detection finds pnpm, npm custom prefixes, Bun and Scoop outside stale PATH',{skip:process.platform!=='win32'},()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'aguja-native-windows-lookup-'));
 try{
  for(const [folder,env,name]of [['.bun/bin',{},'codex'],['scoop/shims',{},'claude'],['pnpm',{PNPM_HOME:path.join(root,'pnpm')},'opencode'],['custom npm',{NPM_CONFIG_PREFIX:path.join(root,'custom npm')},'agy']]){
   const bin=path.join(root,...folder.split('/'));fs.mkdirSync(bin,{recursive:true});const file=path.join(bin,name+'.exe');fs.writeFileSync(file,'fixture');assert.equal(core.resolveProviderBinary(name,{home:root,env:{PATH:'.',...env},platform:'win32'}),file);
  }
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});
