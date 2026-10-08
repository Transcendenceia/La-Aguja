'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),{execFileSync}=require('node:child_process');
const modules=process.env.AGUJA_QA_MODULES||path.resolve(__dirname,'..');
const {windowsPowerShell,powershellArgs}=require(path.join(modules,'ai-tools.cjs'));

// Exercise the actual writer/readback expressions in PS 5.1. Its overload
// binder otherwise selects Int32 and refuses remaining sizes above 2 GiB.
test('Windows writer and readback handle images above 2 GiB',{skip:process.platform!=='win32'},()=>{
 const source=fs.readFileSync(path.join(modules,'flash-windows.ps1'),'utf8');
 const expressions=[...source.matchAll(/^\s*\$toRead = (.+)$/gm)].map(m=>m[1]);
 assert.equal(expressions.length,2);
 const cases=[2147483648,3882876928,8589934592,4194304,4194303,1];
 const script="$ErrorActionPreference='Stop';$chunkSize=4*1024*1024;[long]$written=0;[long]$verifiedBytes=0;$values=@();"+expressions.map(e=>cases.map(n=>`[long]$imageBytes=${n};$values+=(${e});`).join('')).join('')+'ConvertTo-Json -Compress -InputObject @($values)';
 const result=JSON.parse(execFileSync(windowsPowerShell(),powershellArgs(script),{encoding:'utf8',windowsHide:true,timeout:30000}).trim());
 const expected=cases.map(n=>Math.min(4194304,n));assert.deepEqual(result,[...expected,...expected]);
});
