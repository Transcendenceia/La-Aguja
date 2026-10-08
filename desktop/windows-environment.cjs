'use strict';
const {powershellArgs,windowsPowerShell}=require('./ai-tools.cjs');
const KEYS=Object.freeze(['CODEX_HOME','CLAUDE_CONFIG_DIR','XDG_CONFIG_HOME','XDG_DATA_HOME','OPENCODE_CONFIG','OPENCODE_CONFIG_DIR','NPM_CONFIG_PREFIX','PNPM_HOME','NVM_HOME','NVM_SYMLINK']);
async function userEnvironment(run,base=process.env){
 // Explorer and an already-running Imager retain old PATH after a CLI install.
 // Query only known non-secret location variables; never run shell profiles or
 // enumerate environment values (which may contain provider keys).
 const script='$ErrorActionPreference="Stop";[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false);$result=@{};foreach($key in @('+['Path',...KEYS].map(k=>"'"+k+"'").join(',')+')){$u=[Environment]::GetEnvironmentVariable($key,"User");$m=[Environment]::GetEnvironmentVariable($key,"Machine");if($key -eq "Path"){$result[$key]=@($u,$m)-join ";"}elseif($u){$result[$key]=$u}elseif($m){$result[$key]=$m}};$result|ConvertTo-Json -Compress';
 let values;try{values=JSON.parse((await run(windowsPowerShell(base),powershellArgs(script),null,{timeout:10000})).replace(/^\ufeff/,''));}catch{return {...base};}
 const env={...base};
 for(const key of KEYS)if(!env[key]&&typeof values?.[key]==='string'&&values[key].length<32768)env[key]=values[key];
 const current=Object.entries(base).find(([k])=>k.toLowerCase()==='path')?.[1]||'';
 for(const key of Object.keys(env))if(key.toLowerCase()==='path')delete env[key];
 env.PATH=[current,typeof values?.Path==='string'&&values.Path.length<32768?values.Path:''].filter(Boolean).join(';');
 return env;
}
module.exports={userEnvironment,KEYS};
