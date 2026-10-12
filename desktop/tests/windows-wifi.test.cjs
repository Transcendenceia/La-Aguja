'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {importActiveWifi}=require('../windows-wifi.cjs');
const wifi={ssid:'Fixture " ñ',password:'fixture-password',security:'wpa-psk',country:'ES',hidden:false};
test('active Windows network import always requests scoped UAC and only returns validated network',async()=>{
 let options;
 const result=await importActiveWifi({platform:'win32',query:async(script,o)=>{options=o;return JSON.stringify({ok:true,wifi,other:'SECRET-METADATA'});}});
 assert.deepEqual(options,{elevated:true,operation:'wifi'});assert.deepEqual(result,{wifi});
});
test('cancelled permissions and malformed/unsupported credentials cannot look like successful import',async()=>{
 for(const response of ['', '{}','invalid',JSON.stringify({ok:false,code:'key-unavailable'}),JSON.stringify({ok:true,wifi:{...wifi,password:''}}),JSON.stringify({ok:true,wifi:{...wifi,security:'enterprise'}}),JSON.stringify({ok:true,wifi:{...wifi,ssid:'x'.repeat(33)}})]){
  await assert.rejects(importActiveWifi({platform:'win32',query:async()=>response}),/Wi-Fi/);
 }
 await assert.rejects(importActiveWifi({platform:'win32',query:async()=>JSON.stringify({ok:false,canceled:true})}),/No se autorizó/);
 await assert.rejects(importActiveWifi({platform:'win32',query:async()=>{throw Error('PRIVATE-NATIVE-DETAIL');}}),e=>!e.message.includes('PRIVATE'));
});
test('open and WPA3 active networks preserve their security mode',async()=>{
 for(const w of [{...wifi,password:'',security:'open'},{...wifi,security:'sae',hidden:true}]){
  assert.deepEqual(await importActiveWifi({platform:'win32',query:async()=>JSON.stringify({ok:true,wifi:w})}),{wifi:w});
 }
});
