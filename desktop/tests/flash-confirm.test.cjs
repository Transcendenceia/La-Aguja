'use strict';
const test=require('node:test'),assert=require('node:assert/strict');const {flashConfirmDialog}=require('../flash-confirm.cjs'),{LOCALE_CATALOG:catalog}=require('../core.cjs'),{translation}=require('../ui/i18n.js');
test('native confirmation translates each app clause, preserves hardware identity, and limits release promise to Windows',()=>{
 const disk={model:'Tu tailnet, tu control.',size:16*1024**3,device:'\\\\.\\PhysicalDrive99',serial:'SYNTHETIC-SERIAL'};
 for(const language of ['es',...Object.keys(catalog.translations)]){
  const t=s=>translation(catalog,language,s),win=flashConfirmDialog(disk,{windows:true},t),linux=flashConfirmDialog(disk,{},t);
  assert(win.detail.includes(disk.device));assert(win.detail.includes(disk.serial));assert(win.detail.includes(disk.model));assert(win.detail.includes('16.00 GiB'));
  assert(win.detail.includes(t('Se cerrarán ordenadamente las aplicaciones que usan este USB y se desmontarán sus volúmenes para uso exclusivo.')));
  assert(!linux.detail.includes(t('Se cerrarán ordenadamente las aplicaciones que usan este USB y se desmontarán sus volúmenes para uso exclusivo.')));
  if(language!=='es')assert(!win.detail.includes('Se borrará el contenido anterior SIN RESPALDO.'));
 }
});
