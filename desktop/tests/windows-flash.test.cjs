'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const {flashWindows,requestFor,LAUNCHER}=require('../windows-flash.cjs');
const disk={device:'\\\\.\\PhysicalDrive12',serial:'SYNTHETIC-SERIAL',size:128*1024**3,model:"USB á ' & $(literal)"};
const image={path:"C:\\Users\\fixture\\private á ' & $(literal).img",sha256:'a'.repeat(64)};
test('Windows elevated request pins exact disk number, serial, size and model',()=>{
 assert.deepEqual(requestFor(image,disk),{ImagePath:image.path,DiskNumber:12,ExpectedSerial:disk.serial,ExpectedSha256:image.sha256,ExpectedSize:disk.size,ExpectedModel:disk.model});
 for(const change of [{device:'xPhysicalDrive12'},{device:'\\\\.\\PhysicalDrive-1'},{device:'\\\\.\\PhysicalDrive12extra'},{serial:''},{size:0},{model:''}])assert.throws(()=>requestFor(image,{...disk,...change}),/identidad/);
 assert.throws(()=>requestFor({...image,sha256:'wrong'},disk),/identidad/);
});
test('Windows UAC bridge keeps request out of arguments, preserves literal paths and removes ephemeral files',async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),"aguja uac á ' & "));
 let stage;
 try{
  const output=await flashWindows({image,disk,directory:dir,writer:path.resolve(__dirname,'../flash-windows.ps1'),run:async(command,args,input,options)=>{
   assert.match(command,/WindowsPowerShell\\v1\.0\\powershell\.exe$/);
   assert.equal(input,null);assert.equal(options.phase,'flash');
   const launcher=args[args.indexOf('-File')+1];stage=path.dirname(launcher);
   for(const value of [image.path,image.sha256,disk.serial,disk.model])assert(!args.join(' ').includes(value));
   const request=JSON.parse(fs.readFileSync(path.join(stage,'request.json'),'utf8'));assert.deepEqual(request,{...requestFor(image,disk),ApplicationPID:process.pid});
   assert.equal(fs.readFileSync(launcher,'utf8'),'\ufeff'+LAUNCHER);
   assert(fs.readFileSync(path.join(stage,'writer.ps1'),'utf8').startsWith('\ufeff'));
   assert.equal(fs.readFileSync(path.join(stage,'progress.jsonl'),'utf8'),'');
   return '{"ok":true,"verified":true}\n';
  }});
  assert.equal(JSON.parse(output).verified,true);assert(!fs.existsSync(stage));
 }finally{fs.rmSync(dir,{recursive:true,force:true});}
});
test('Windows UAC bridge cleans its request after canceled elevation without suppressing error',async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'aguja-uac-cancel-'));let stage;
 try{await assert.rejects(()=>flashWindows({image,disk,directory:dir,writer:path.resolve(__dirname,'../flash-windows.ps1'),run:async(command,args)=>{stage=path.dirname(args.at(-1));throw new Error('No se autorizó la grabación de Windows.');}}),/No se autorizó/);assert(!fs.existsSync(stage));}finally{fs.rmSync(dir,{recursive:true,force:true});}
});
