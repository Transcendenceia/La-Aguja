'use strict';
const fs=require('node:fs'),path=require('node:path'),os=require('node:os');
// An AppImage FUSE mount belongs to the desktop user, not root. Polkit can
// authenticate successfully and Python still cannot open a helper on it.
// Stage only the bundled, standalone helper (never credentials) off FUSE.
async function withPrivilegedHelper(source,operation,{directory=os.tmpdir()}={}){
 const stat=await fs.promises.lstat(source);
 if(!stat.isFile()||stat.isSymbolicLink()||stat.size>1024*1024)throw new Error('El ayudante de permisos de Linux no es válido.');
 const stage=await fs.promises.mkdtemp(path.join(directory,'aguja-helper-'));
 try{
  await fs.promises.chmod(stage,0o700);
  const target=path.join(stage,path.basename(source));
  await fs.promises.copyFile(source,target,fs.constants.COPYFILE_EXCL);
  await fs.promises.chmod(target,0o600);
  return await operation(target);
 }finally{await fs.promises.rm(stage,{recursive:true,force:true});}
}
module.exports={withPrivilegedHelper};
