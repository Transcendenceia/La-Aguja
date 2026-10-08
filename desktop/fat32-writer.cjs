'use strict';
const fs = require('node:fs');
const path = require('node:path');

/**
 * Lector y escritor FAT32 autónomo en JavaScript para particiones GPT de LA AGUJA.
 * Permite inyectar archivos (como bitlocker.json o aguja-profile.json) sin depender
 * de herramientas del sistema operativo como mtools o controladores de kernel.
 */

function findGptPartition(fd, targetLabel = 'AGUJA_CFG') {
  const headerBuf = Buffer.alloc(512);
  fs.readSync(fd, headerBuf, 0, 512, 512); // LBA 1

  if (headerBuf.subarray(0, 8).toString('ascii') !== 'EFI PART') {
    throw new Error('La imagen no tiene una tabla de particiones GPT válida.');
  }

  const tableLba = headerBuf.readBigUInt64LE(72);
  const numEntries = headerBuf.readUInt32LE(80);
  const entrySize = headerBuf.readUInt32LE(84);

  if (entrySize !== 128 || numEntries === 0 || numEntries > 4096) {
    throw new Error('Estructura GPT incompatible.');
  }

  const tableBuf = Buffer.alloc(numEntries * entrySize);
  fs.readSync(fd, tableBuf, 0, tableBuf.length, Number(tableLba * 512n));

  for (let i = 0; i < numEntries; i++) {
    const offset = i * entrySize;
    // Comprobar si el partition type GUID es nulo
    let isNull = true;
    for (let j = 0; j < 16; j++) {
      if (tableBuf[offset + j] !== 0) { isNull = false; break; }
    }
    if (isNull) continue;

    const startLba = tableBuf.readBigUInt64LE(offset + 32);
    const endLba = tableBuf.readBigUInt64LE(offset + 40);
    const nameRaw = tableBuf.subarray(offset + 56, offset + 128);
    const label = nameRaw.toString('utf16le').replace(/\0.*$/, '').trim();

    if (label === targetLabel) {
      if (startLba < 34n || endLba < startLba || (endLba + 1n) * 512n > BigInt(fs.fstatSync(fd).size)) throw new Error('Límites GPT de configuración no válidos.');
      return {
        label,
        startLba,
        endLba,
        offset: startLba * 512n,
        length: (endLba - startLba + 1n) * 512n
      };
    }
  }

  throw new Error(`Partición '${targetLabel}' no encontrada en la imagen.`);
}

function parseFat32Params(fd, partitionOffset) {
  const boot = Buffer.alloc(512);
  fs.readSync(fd, boot, 0, 512, Number(partitionOffset));

  const bytesPerSector = boot.readUInt16LE(11);
  const sectorsPerCluster = boot.readUInt8(13);
  const reservedSectors = boot.readUInt16LE(14);
  const numFats = boot.readUInt8(16);
  const sectorsPerFat = boot.readUInt32LE(36);
  const rootCluster = boot.readUInt32LE(44);

  if (bytesPerSector !== 512 || !sectorsPerCluster || sectorsPerCluster > 128 || (sectorsPerCluster & (sectorsPerCluster - 1)) || numFats !== 2 || sectorsPerFat === 0 || rootCluster < 2) {
    throw new Error('Parámetros de partición FAT32 no compatibles.');
  }

  const clusterSize = bytesPerSector * sectorsPerCluster;
  const totalSectors = boot.readUInt32LE(32) || Math.floor((fs.fstatSync(fd).size - Number(partitionOffset)) / bytesPerSector);
  const totalClusters = Math.floor((totalSectors - reservedSectors - numFats * sectorsPerFat) / sectorsPerCluster);
  if (totalClusters < 1 || rootCluster >= totalClusters + 2) throw new Error('Límites FAT32 de configuración no válidos.');
  const fat1Offset = partitionOffset + BigInt(reservedSectors * bytesPerSector);
  const fat2Offset = fat1Offset + BigInt(sectorsPerFat * bytesPerSector);
  const dataStartOffset = partitionOffset + BigInt((reservedSectors + numFats * sectorsPerFat) * bytesPerSector);

  return {
    totalClusters,
    bytesPerSector,
    sectorsPerCluster,
    reservedSectors,
    numFats,
    sectorsPerFat,
    rootCluster,
    clusterSize,
    fat1Offset,
    fat2Offset,
    dataStartOffset
  };
}

function clusterToOffset(params, cluster) {
  return params.dataStartOffset + BigInt((cluster - 2) * params.clusterSize);
}

function readFatEntry(fd, params, cluster) {
  const buf = Buffer.alloc(4);
  fs.readSync(fd, buf, 0, 4, Number(params.fat1Offset + BigInt(cluster * 4)));
  return buf.readUInt32LE(0) & 0x0fffffff;
}

function writeFatEntry(fd, params, cluster, value) {
  const buf = Buffer.alloc(4);
  buf.writeUInt32LE(value & 0x0fffffff, 0);
  // Escribir en FAT1 y FAT2
  fs.writeSync(fd, buf, 0, 4, Number(params.fat1Offset + BigInt(cluster * 4)));
  fs.writeSync(fd, buf, 0, 4, Number(params.fat2Offset + BigInt(cluster * 4)));
}

function findFreeClusters(fd, params, count) {
  const freeClusters = [];
  // Escanear tabla FAT a partir del cluster 3
  const maxScan = Math.min(params.sectorsPerFat * 128, params.totalClusters + 2);
  for (let c = 3; c < maxScan; c++) {
    const val = readFatEntry(fd, params, c);
    if (val === 0) {
      freeClusters.push(c);
      if (freeClusters.length === count) break;
    }
  }
  if (freeClusters.length < count) {
    throw new Error('No hay suficiente espacio libre en la partición de configuración.');
  }
  return freeClusters;
}

function formatShortName(fullName) {
  const parts = fullName.toUpperCase().split('.');
  let base = (parts[0] || '').replace(/[^A-Z0-9]/g, '');
  let ext = (parts[1] || '').replace(/[^A-Z0-9]/g, '');
  base = base.slice(0, 8).padEnd(8, ' ');
  ext = ext.slice(0, 3).padEnd(3, ' ');
  return base + ext;
}

function clusterChain(fd,params,first) {
  const out=[],seen=new Set();let current=first;
  const max=Math.min(params.sectorsPerFat*128,params.totalClusters+2);
  while(current>=2&&current<0x0ffffff8){
    if(current>=max||seen.has(current))throw new Error('Cadena FAT32 de configuración no válida.');
    seen.add(current);out.push(current);current=readFatEntry(fd,params,current);
  }
  if(current<0x0ffffff8)throw new Error('Cadena FAT32 de configuración incompleta.');
  return out;
}
function directory(fd,params) {
  const clusters=clusterChain(fd,params,params.rootCluster);
  const buffers=clusters.map(c=>{const b=Buffer.alloc(params.clusterSize);fs.readSync(fd,b,0,b.length,Number(clusterToOffset(params,c)));return b;});
  return {clusters,buffer:Buffer.concat(buffers)};
}
function checksum(name){let sum=0;for(const b of Buffer.from(name,'ascii'))sum=((sum&1)?128:0)+(sum>>1)+b&255;return sum;}
const LFN_OFFSETS=[1,3,5,7,9,14,16,18,20,22,24,28,30];
function entries(buffer) {
  const out=[];let fragments=[],lfnStart=0;
  for(let i=0;i<buffer.length;i+=32){const e=buffer.subarray(i,i+32);if(e[0]===0)break;if(e[0]===0xe5){fragments=[];continue;}
    if(e[11]===0x0f){if(e[0]&0x40){fragments=[];lfnStart=i;}fragments.push({order:e[0]&31,check:e[13],value:LFN_OFFSETS.map(o=>e.readUInt16LE(o))});continue;}
    const short=e.subarray(0,11).toString('ascii'),shortText=short.slice(0,8).trim()+ (short.slice(8).trim()?'.'+short.slice(8).trim():'');
    let name=shortText,start=i;
    if(fragments.length&&fragments.every(f=>f.check===checksum(short))){const units=fragments.sort((a,b)=>a.order-b.order).flatMap(f=>f.value);const end=units.indexOf(0);name=String.fromCharCode(...units.slice(0,end<0?units.length:end).filter(c=>c!==65535));start=lfnStart;}
    if(!(e[11]&0x18))out.push({name,short,index:i,start,cluster:e.readUInt16LE(20)*65536+e.readUInt16LE(26),size:e.readUInt32LE(28)});
    fragments=[];
  }return out;
}
function lfnEntries(filename,short) {
  const units=Array.from({length:filename.length},(_,i)=>filename.charCodeAt(i));units.push(0);const count=Math.ceil(units.length/13),out=[];
  for(let ordinal=count;ordinal>=1;ordinal--){const e=Buffer.alloc(32,255);e[0]=ordinal|(ordinal===count?0x40:0);e[11]=15;e[12]=0;e[13]=checksum(short);e.writeUInt16LE(0,26);for(let j=0;j<13;j++)e.writeUInt16LE(units[(ordinal-1)*13+j]??65535,LFN_OFFSETS[j]);out.push(e);}return out;
}
function readFat32File(fd,params,filename) {
  const entry=entries(directory(fd,params).buffer).find(e=>e.name.toLowerCase()===filename.toLowerCase()||e.short===formatShortName(filename));
  if(!entry)return null;if(entry.size>8*1024*1024)throw new Error('Archivo de configuración demasiado grande.');if(!entry.size)return Buffer.alloc(0);
  const chain=clusterChain(fd,params,entry.cluster);if(chain.length*params.clusterSize<entry.size)throw new Error('Archivo de configuración incompleto.');
  const result=Buffer.alloc(entry.size);let done=0;for(const c of chain){const n=Math.min(params.clusterSize,entry.size-done);if(!n)break;fs.readSync(fd,result,done,n,Number(clusterToOffset(params,c)));done+=n;}return result;
}
function writeFat32File(imagePath,targetLabel,filename,contentBuffer) {
  if(!/^[a-zA-Z0-9_.-]{1,128}$/.test(filename)||filename==='.'||filename==='..')throw new Error('Nombre de configuración no válido.');
  contentBuffer=Buffer.from(contentBuffer);if(contentBuffer.length>8*1024*1024)throw new Error('Archivo de configuración demasiado grande.');
  const fd=fs.openSync(imagePath,'r+');try{
    const partition=findGptPartition(fd,targetLabel),params=parseFat32Params(fd,partition.offset),dir=directory(fd,params);
    const list=entries(dir.buffer),old=list.find(e=>e.name.toLowerCase()===filename.toLowerCase());
    let short=old?.short||formatShortName(filename);
    const needsLFN=!/^[A-Z0-9]{1,8}(\.[A-Z0-9]{1,3})?$/.test(filename);
    if(!old&&needsLFN){let n=1;const parts=filename.toUpperCase().split('.'),base=parts[0].replace(/[^A-Z0-9]/g,''),ext=(parts.at(-1)||'').replace(/[^A-Z0-9]/g,'').slice(0,3);do{short=(base.slice(0,Math.max(1,7-String(n).length))+'~'+n).padEnd(8,' ')+ext.padEnd(3,' ');n++;}while(list.some(e=>e.short===short));}
    if(old)for(let i=old.start;i<=old.index;i+=32)dir.buffer[i]=0xe5;
    const long=needsLFN?lfnEntries(filename,short):[],slots=long.length+1;
    let start=-1,count=0,end=false;
    for(let i=0;i<dir.buffer.length;i+=32){if(dir.buffer[i]===0)end=true;if(end||dir.buffer[i]===0xe5){count++;if(count===slots){start=i-(slots-1)*32;break;}}else count=0;}
    if(start<0){const extra=findFreeClusters(fd,params,1)[0];writeFatEntry(fd,params,dir.clusters.at(-1),extra);writeFatEntry(fd,params,extra,0x0fffffff);start=dir.buffer.length-count*32;dir.clusters.push(extra);dir.buffer=Buffer.concat([dir.buffer,Buffer.alloc(params.clusterSize)]);}
    if(start+slots*32>dir.buffer.length)throw new Error('No hay espacio de directorio para esta configuración.');
    const allocated=findFreeClusters(fd,params,Math.max(1,Math.ceil(contentBuffer.length/params.clusterSize)));
    for(let i=0;i<allocated.length;i++){const b=Buffer.alloc(params.clusterSize);contentBuffer.copy(b,0,i*params.clusterSize,(i+1)*params.clusterSize);fs.writeSync(fd,b,0,b.length,Number(clusterToOffset(params,allocated[i])));writeFatEntry(fd,params,allocated[i],allocated[i+1]||0x0fffffff);}
    const e=Buffer.alloc(32);e.write(short,0,11,'ascii');e[11]=32;const now=new Date(),time=now.getHours()<<11|now.getMinutes()<<5|now.getSeconds()>>1,date=(now.getFullYear()-1980)<<9|(now.getMonth()+1)<<5|now.getDate();e.writeUInt16LE(time,14);e.writeUInt16LE(date,16);e.writeUInt16LE(date,18);e.writeUInt16LE(time,22);e.writeUInt16LE(date,24);e.writeUInt16LE(allocated[0]>>>16,20);e.writeUInt16LE(allocated[0]&65535,26);e.writeUInt32LE(contentBuffer.length,28);
    Buffer.concat([...long,e]).copy(dir.buffer,start);
    for(let i=0;i<dir.clusters.length;i++)fs.writeSync(fd,dir.buffer,i*params.clusterSize,params.clusterSize,Number(clusterToOffset(params,dir.clusters[i])));
    if(old&&old.cluster>=2)for(const c of clusterChain(fd,params,old.cluster))writeFatEntry(fd,params,c,0);
    // FAT FSInfo counts are now unknown; let OS recompute rather than retain stale values.
    const boot=Buffer.alloc(512);fs.readSync(fd,boot,0,512,Number(partition.offset));const infoSector=boot.readUInt16LE(48),backup=boot.readUInt16LE(50);
    for(const sector of [infoSector,backup+infoSector])if(infoSector>0&&sector<params.reservedSectors){const b=Buffer.alloc(512),offset=Number(partition.offset)+sector*512;fs.readSync(fd,b,0,512,offset);if(b.readUInt32LE(0)===0x41615252&&b.readUInt32LE(484)===0x61417272){b.writeUInt32LE(0xffffffff,488);b.writeUInt32LE(0xffffffff,492);fs.writeSync(fd,b,0,512,offset);}}
    fs.fsyncSync(fd);if(!readFat32File(fd,params,filename)?.equals(contentBuffer))throw new Error('No coincide la lectura de la configuración escrita.');return {ok:true,filename,shortName:short,bytes:contentBuffer.length,clusters:allocated};
  }finally{fs.closeSync(fd);}
}
module.exports={findGptPartition,parseFat32Params,writeFat32File,readFat32File,formatShortName};
