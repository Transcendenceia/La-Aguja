'use strict';
// Private signing key stays outside the source/release directories.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
async function digest(file){const hash=crypto.createHash('sha256');for await(const chunk of fs.createReadStream(file))hash.update(chunk);return hash.digest('hex');}
async function main(){
 const [image,assetDir,keyfile]=process.argv.slice(2);
 if(!image||!assetDir||!keyfile)throw Error('Uso: node scripts/release-catalog.cjs IMAGEN DIRECTORIO_ASSETS CLAVE_PRIVADA');
 const root=path.resolve(__dirname,'..'),version=fs.readFileSync(path.join(root,'VERSION'),'utf8').trim(),pin=JSON.parse(fs.readFileSync(path.join(root,'desktop/resources/release-key.json')));
 const folder=path.resolve(assetDir),keypath=path.resolve(keyfile);
 if(keypath.startsWith(root+path.sep)||keypath.startsWith(folder+path.sep))throw Error('La clave de firma debe permanecer fuera del código y assets.');
 const stat=fs.statSync(keypath);if((stat.mode&0o077)!==0)throw Error('La clave necesita permisos 0600.');
 const privateKey=crypto.createPrivateKey(fs.readFileSync(keypath));
 if(crypto.createPublicKey(privateKey).export({type:'spki',format:'pem'})!==pin.public_key_pem)throw Error('Clave distinta del pin del Imager.');
 fs.mkdirSync(folder,{recursive:true});const base='aguja-'+version+'-amd64.img',size=fs.statSync(image).size,parts=[],max=1792*1024**2;
 const file=await fs.promises.open(image,'r');try{
  for(let start=0,index=1;start<size;index++,start+=max){
   const name=base+'.part'+String(index).padStart(2,'0'),bytes=Math.min(max,size-start),destination=path.join(folder,name);
   const output=await fs.promises.open(destination,'wx',0o644),hash=crypto.createHash('sha256');
   try{let copied=0;const buffer=Buffer.alloc(4*1024**2);while(copied<bytes){const read=await file.read(buffer,0,Math.min(buffer.length,bytes-copied),start+copied);if(!read.bytesRead)throw Error('Imagen incompleta');const data=buffer.subarray(0,read.bytesRead);hash.update(data);let written=0;while(written<data.length){written+=(await output.write(data,written,data.length-written)).bytesWritten;}copied+=read.bytesRead;}await output.sync();}finally{await output.close();}
   parts.push({url:`https://github.com/${pin.repository}/releases/download/v${version}/${name}`,bytes,sha256:hash.digest('hex')});
  }
 }finally{await file.close();}
 const payload=Buffer.from(JSON.stringify({schema:1,expires_at:new Date(Date.now()+365*86400000).toISOString(),releases:[{version,bytes:size,sha256:await digest(image),parts,notes:'Versión pública sin cuentas de LA AGUJA. SSH por tu LAN/Tailscale/Headscale.'}]}));
 const envelope={key_id:pin.key_id,payload:payload.toString('base64'),signature:crypto.sign(null,payload,privateKey).toString('base64')};
 const result=require('../desktop/core.cjs').verifyManifest(envelope,pin);if(result[0].bytes!==size)throw Error('Catálogo no verificable');
 fs.writeFileSync(path.join(folder,'catalog.json'),JSON.stringify(envelope,null,2)+'\n',{flag:'wx'});
 console.log(JSON.stringify({ok:true,version,parts:parts.length,bytes:size,key_id:pin.key_id}));
}
main().catch(()=>{console.error('No se generó el catálogo. Revisa rutas, permisos, pin y assets existentes.');process.exitCode=1;});
