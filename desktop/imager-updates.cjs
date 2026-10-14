'use strict';
const crypto=require('node:crypto'),fs=require('node:fs'),path=require('node:path');
const core=require('./core.cjs');
function version(value){if(!/^\d+\.\d+\.\d+$/.test(value))throw Error('Versión de actualización no válida.');const nums=value.split('.').map(Number);if(nums.some(n=>!Number.isSafeInteger(n)))throw Error('Versión de actualización no válida.');return nums;}
function newer(a,b){const x=version(a),y=version(b);for(let i=0;i<3;i++){if(x[i]!==y[i])return x[i]>y[i];}return false;}
function document(envelope,pin,now=Date.now()){
 if(envelope?.key_id!==pin.key_id||typeof envelope.payload!=='string'||typeof envelope.signature!=='string')throw Error('La firma del catálogo no coincide con esta aplicación.');
 const raw=Buffer.from(envelope.payload,'base64');if(!raw.length||raw.length>65536||!crypto.verify(null,raw,pin.public_key_pem,Buffer.from(envelope.signature,'base64')))throw Error('Catálogo sin firma válida. No se descarga.');
 const data=JSON.parse(raw.toString('utf8'));if(data.schema!==1||!Number.isFinite(Date.parse(data.expires_at))||Date.parse(data.expires_at)<now)throw Error('El catálogo ha caducado.');return data;
}
function releases(envelope,pin,platform,now){
 if(!['win32','linux'].includes(platform))throw Error('Esta actualización no corresponde al sistema.');const data=document(envelope,pin,now);
 if(!Array.isArray(data.imagers)||data.imagers.length>20)throw Error('El catálogo aún no incluye actualizaciones del Imager.');
 return data.imagers.map(r=>{version(r.version);if(!Array.isArray(r.assets)||r.assets.length>8)throw Error('Información de versión no válida.');
 const assets=r.assets.filter(a=>a.platform===platform).map(a=>{const u=new URL(a.url);if(u.protocol!=='https:'||u.hostname!=='github.com'||u.username||u.password||u.search||u.hash||u.port||!u.pathname.startsWith('/'+pin.repository+'/releases/download/v'+r.version+'/')||!Number.isSafeInteger(a.bytes)||a.bytes<1048576||a.bytes>=2*1024**3||!/^\w[\w.-]+$/.test(a.name)||decodeURIComponent(u.pathname.split('/').at(-1))!==a.name)throw Error('Información de versión no válida.');core.sha(a.sha256);if(platform==='win32'&&!a.name.endsWith('.exe')||platform==='linux'&&!/\.(AppImage|deb|tar\.gz)$/.test(a.name))throw Error('Esta actualización no corresponde al sistema.');return {...a,url:u.href};});return {version:r.version,assets};}).filter(r=>r.assets.length).sort((a,b)=>newer(a.version,b.version)?-1:newer(b.version,a.version)?1:0);
}
async function check(pin,current,platform,{get=core.getHTTPS}={}){const all=releases(await get(pin.update_catalog_url||pin.catalog_url),pin,platform);const latest=all[0];return {current,latest:latest?.version||current,available:Boolean(latest&&newer(latest.version,current)),assets:latest?.assets||[]};}
async function download(asset,destination,progress,{download=core.downloadImage}={}){
 const out=await download({url:asset.url,bytes:asset.bytes,sha256:asset.sha256},destination,progress);
 if(asset.name.endsWith('.AppImage'))await fs.promises.chmod(destination,0o755);return {...out,name:path.basename(destination),version:asset.version};
}
module.exports={version,newer,document,releases,check,download};
