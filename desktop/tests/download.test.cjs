'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const {downloadImage}=require('../core.cjs');

test('stalled streaming aborts the request, cancels its body and removes unpublished private data',{timeout:2000},async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'aguja-stalled-download-'));
 const previousFetch=global.fetch;let requestSignal,canceled=false;
 try{
  global.fetch=async(_url,options)=>{
   requestSignal=options.signal;
   return new Response(new ReadableStream({start(controller){controller.enqueue(Buffer.from('incomplete-image'));},cancel(){canceled=true;}}));
  };
  const destination=path.join(dir,'rescue.img');
  const release={url:'https://example.invalid/rescue.img',bytes:4096,sha256:'a'.repeat(64)};
  await assert.rejects(downloadImage(release,destination,()=>{},undefined,{}, {idleTimeoutMs:40}),/no avanzó a tiempo/);
  assert.equal(requestSignal.aborted,true);
  assert.equal(canceled,true);
  assert.deepEqual(fs.readdirSync(dir),[]);
 }finally{global.fetch=previousFetch;fs.rmSync(dir,{recursive:true});}
});

test('caller cancellation also closes a stalled body without publishing an image',{timeout:2000},async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'aguja-canceled-download-'));
 const previousFetch=global.fetch;const controller=new AbortController();let canceled=false;
 try{
  global.fetch=async()=>new Response(new ReadableStream({start(stream){stream.enqueue(Buffer.from('partial'));},cancel(){canceled=true;}}));
  const result=downloadImage({url:'https://example.invalid/rescue.img',bytes:4096,sha256:'b'.repeat(64)},path.join(dir,'rescue.img'),()=>controller.abort(),controller.signal);
  await assert.rejects(result,{name:'AbortError'});
  assert.equal(canceled,true);
  assert.deepEqual(fs.readdirSync(dir),[]);
 }finally{global.fetch=previousFetch;fs.rmSync(dir,{recursive:true});}
});
