'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {LOCALE_CATALOG:catalog,validateLocale,importedLocale}=require('../core.cjs');
const {language,translation}=require('../ui/i18n.js');
test('catalog drives every allowed language, keyboard and variant without execution',()=>{
 for(const l of catalog.languages)for(const k of catalog.keyboards)for(const variant of k.variants)assert.deepEqual(validateLocale({language:l.value,keyboard:k.value,variant}),{language:l.value,keyboard:k.value,variant});
 for(const attack of ['cn; touch /tmp/should-not-exist','$(id)','us\nXKBOPTIONS=evil',''])assert.throws(()=>validateLocale({language:'zh_CN.UTF-8',keyboard:attack,variant:''}));
 assert.throws(()=>validateLocale({language:'zh_CN.UTF-8',keyboard:'cn',variant:'intl'}));
 assert.deepEqual(importedLocale({language:'zh_CN.utf8',keyboard:'cn',variant:''}).locale,{language:'zh_CN.UTF-8',keyboard:'cn',variant:''});
});
test('complete translation catalogs preserve placeholders and exact LA AGUJA brand',()=>{
 assert.equal(catalog.brand,'LA AGUJA');const sources=Object.keys(catalog.translations.en).sort();
 for(const [locale,entries]of Object.entries(catalog.translations)){
  assert.deepEqual(Object.keys(entries).sort(),sources,`${locale} missing keys`);
  for(const source of sources){const translated=entries[source];assert.equal(typeof translated,'string');assert(translated.trim());assert.deepEqual((translated.match(/\{\w+\}/g)||[]).sort(),(source.match(/\{\w+\}/g)||[]).sort(),`${locale}: ${source}`);if(source.includes('LA AGUJA'))assert(translated.includes('LA AGUJA'),`${locale} changed brand`);}
 }
 for(const locale of ['es-CO','en-US','zh-CN'])assert.equal(translation(catalog,locale,'LA AGUJA'),'LA AGUJA');
 assert.equal(language(catalog,'zh_CN.UTF-8'),'zh');assert.equal(language(catalog,'es-CO'),'es');assert.equal(language(catalog,'xx-ZZ'),'en');
 assert.equal(translation(catalog,'zh-CN','Acceso remoto'),'远程访问');
});
test('desktop locale selectors are populated only from catalog; translation never writes input values',()=>{
 const html=fs.readFileSync(path.join(__dirname,'../ui/index.html'),'utf8'),translator=fs.readFileSync(path.join(__dirname,'../ui/i18n.js'),'utf8');
 for(const name of ['language','keyboard','variant'])assert(html.includes(`<select id="locale-${name}"></select>`));
 assert(!translator.includes('innerHTML'));assert(!translator.includes('.value='));assert(!translator.includes('input.value'));
 assert(!html.includes('id="agent-access"'));assert(!html.includes('id="account-login"'));assert(!html.includes('id="remote-enabled" type="checkbox" checked'));
});

test('native dialog templates translate while preserving destination identity literally',()=>{
 const source='Modelo: Public key / port \nCapacidad: 16.00 GiB\nDispositivo: /dev/sdz\nSerie: SYNTHETIC-SERIAL\n\nTu imagen privada está lista. Se borrará el contenido anterior SIN RESPALDO. Después se verificará la grabación. Ningún disco interno es elegible.';
 for(const locale of Object.keys(catalog.translations)){
  const output=translation(catalog,locale,source);assert(output.includes('/dev/sdz'));assert(output.includes('SYNTHETIC-SERIAL'));assert(output.includes('Public key / port '));assert(output.includes('16.00 GiB'));if(locale!=='es')assert(!output.includes('Ningún disco interno es elegible.'));
 }
 assert.equal(translation(catalog,'zh','Falta la clave API de Codex'),'缺少 Codex 的 API 密钥');
});
