'use strict';
const fs=require('node:fs');const path=require('node:path');const {execFileSync}=require('node:child_process');
const root=path.resolve(__dirname,'..'),pkg=require('../package.json'),out=path.join(root,'dist');
const archive=path.join(out,`aguja-flash-imager-${pkg.version}-x64.tar.gz`),temp=archive+'.building';
execFileSync('/usr/bin/tar',['-I','gzip -1','-cf',temp,'-C',out,'linux-unpacked'],{stdio:'inherit'});
execFileSync('/usr/bin/tar',['-tf',temp],{stdio:'pipe'});fs.renameSync(temp,archive);
console.log('Portable Linux archive created and listing verified.');
