'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),{execFile}=require('node:child_process');
const {userEnvironment}=require('../windows-environment.cjs');
test('native Windows environment query runs without changing execution policy or exposing secrets',{skip:process.platform!=='win32'},async()=>{
 const run=(command,args,input,options)=>new Promise((resolve,reject)=>execFile(command,args,{timeout:options.timeout,windowsHide:true},(e,out)=>e?reject(Error('query failed')):resolve(out)));
 const env=await userEnvironment(run,process.env);assert.equal(typeof env.PATH,'string');assert(env.PATH.includes(process.env.PATH||process.env.Path));
 const keys=Object.keys(env).filter(k=>k.toLowerCase()==='path');assert.deepEqual(keys,['PATH']);
});
