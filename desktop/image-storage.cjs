'use strict';
const fs=require('node:fs'),path=require('node:path');
const MARGIN=64*1024**2;
const gib=bytes=>(Number(bytes)/1024**3).toFixed(2);
function storageError(error){
 if(error?.code==='ENOSPC')return new Error('No hay espacio suficiente para preparar la imagen privada. Elige una carpeta en otra unidad o libera espacio; el USB no se ha grabado.');
 if(error?.code==='EEXIST')return new Error('Ya existe un archivo en el destino de la imagen privada. Elige otro nombre; no se ha sobrescrito.');
 if(['EACCES','EPERM'].includes(error?.code))return new Error('No hay permiso para guardar la imagen privada en esa carpeta. Elige otra carpeta; el USB no se ha grabado.');
 if(error?.code==='EFBIG')return new Error('La unidad de destino no admite un archivo de este tamaño. Elige una carpeta en una unidad NTFS o exFAT.');
 return error;
}
async function checkSpace(directory,bytes,{statfs=fs.promises.statfs}={}){
 let stats;
 try{stats=await statfs(directory,{bigint:true});}catch(e){if(['ENOSYS','ENOTSUP'].includes(e.code))return;throw storageError(e);}
 const available=stats.bavail*stats.bsize,needed=BigInt(bytes)+BigInt(MARGIN);
 if(available<needed)throw new Error(`No hay espacio suficiente para la imagen privada: se necesitan ${gib(needed)} GiB libres y hay ${gib(available)} GiB. Elige una carpeta en otra unidad o libera espacio; el USB no se ha grabado.`);
}
async function checkDestination(source,output){
 if(path.resolve(source)===path.resolve(output))throw new Error('La imagen privada debe tener otro nombre.');
 try{await fs.promises.lstat(output);throw Object.assign(new Error(),{code:'EEXIST'});}catch(e){if(e.code!=='ENOENT')throw storageError(e);}
 const sourceStat=await fs.promises.stat(source);
 await checkSpace(path.dirname(output),sourceStat.size);
}
module.exports={MARGIN,storageError,checkSpace,checkDestination};
