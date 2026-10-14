'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {flashResultDialog}=require('../flash-result.cjs');
const {LOCALE_CATALOG}=require('../core.cjs');
const {translation}=require('../ui/i18n.js');
test('only a successful verified receipt declares the USB ready',()=>{
 const good=flashResultDialog({ok:true,verified:true});
 assert.equal(good.type,'info');assert.equal(good.title,'USB listo');
 assert(good.detail.includes('Expulsa'));assert(!good.detail.includes('respaldo'));
 assert(flashResultDialog({ok:true,verified:true,backupVerified:true}).detail.includes('respaldo'));
 for(const result of [undefined,{ok:true},{ok:true,verified:false},{ok:false,verified:true,error:'USB: fallo de lectura'}]){
  const dialog=flashResultDialog(result);assert.equal(dialog.type,'error');assert(dialog.detail.includes('El USB no está listo.'));
 }
});
test('canceling produces no completion dialog; errors retain their public cause',()=>{
 assert.equal(flashResultDialog({ok:true,canceled:true}),null);
 const error='No se autorizó la grabación. Acepta el diálogo de permisos de Linux o vuelve a intentarlo.';
 const dialog=flashResultDialog({ok:false,error,privateImage:{password:'NEVER-SHOW'},rawOutput:'NEVER-SHOW'});
 assert(dialog.detail.startsWith(error));assert(!JSON.stringify(dialog).includes('NEVER-SHOW'));
});
test('every supported UI language translates completion text without translating the error twice',()=>{
 for(const locale of Object.keys(LOCALE_CATALOG.translations)){
  const t=s=>translation(LOCALE_CATALOG,locale,s);
  for(const result of [{ok:true,verified:true,backupVerified:true},{ok:false,error:'PUBLIC CAUSE /device/identity'}]){
   const dialog=flashResultDialog(result,t);
   if(locale!=='es'){assert(!dialog.message.includes('Tu pendrive'));assert(!dialog.detail.includes('El USB no está listo.'));}
   if(!result.ok)assert(dialog.detail.startsWith(result.error));
  }
 }
});
