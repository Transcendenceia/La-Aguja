'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),{execFile}=require('node:child_process');
const {userEnvironment}=require('../windows-environment.cjs');
test('failed or slow Windows queries preserve caller locations with one canonical PATH',async()=>{
 const base={Path:'C:\\Existing;C:\\Owner',HOME:'C:\\Owner'};
 const env=await userEnvironment(async()=>{throw Error('query unavailable');},base);
 assert.equal(env.PATH,base.Path);assert.equal(env.HOME,base.HOME);
 assert.deepEqual(Object.keys(env).filter(k=>k.toLowerCase()==='path'),['PATH']);
 assert.equal(base.Path,'C:\\Existing;C:\\Owner');assert(!Object.hasOwn(base,'PATH'));
});
test('native Windows environment query runs without changing execution policy or exposing secrets',{skip:process.platform!=='win32'},async()=>{
 const run=(command,args,input,options)=>new Promise((resolve,reject)=>execFile(command,args,{timeout:options.timeout,windowsHide:true},(e,out)=>e?reject(Error('query failed')):resolve(out)));
 const env=await userEnvironment(run,process.env);assert.equal(typeof env.PATH,'string');assert(env.PATH.includes(process.env.PATH||process.env.Path));
 const keys=Object.keys(env).filter(k=>k.toLowerCase()==='path');assert.deepEqual(keys,['PATH']);
});
