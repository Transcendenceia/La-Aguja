import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createSite} from '../app.mjs';
const languages=['en','es','fr','de','pt','it','nl','zh'];
test('locale routes preserve anonymous access, content structure and localised navigation',async()=>{
 const site=createSite();await new Promise(r=>site.server.listen(0,'127.0.0.1',r));
 const base='http://127.0.0.1:'+site.server.address().port;
 try{
  for(const lang of languages){
   for(const route of ['', '/docs','/privacy']){
    const response=await fetch(base+'/'+lang+route);assert.equal(response.status,200);assert.equal(response.headers.get('set-cookie'),null);
    const html=await response.text();assert(html.includes(`<html lang="${lang}">`));
    assert.equal((html.match(/hreflang="(?:en|es|fr|de|pt|it|nl|zh)"/g)||[]).length,16);
    assert(html.includes(`href="/${lang}/docs"`)||lang==='es');
    if(route==='/docs'){
     assert.equal((html.match(/class="doc-section"/g)||[]).length,26);
     assert(html.includes('aguja profile unlock'));assert(html.includes('Ctrl+Shift+V'));
     assert(html.includes('0.9.2'));assert(html.includes('0.9.0'));
    }else if(route===''){
     assert(html.includes('v0.9.4/aguja-flash-imager-0.9.4-win-x64.exe'));
     assert(html.includes('/releases/aguja-0.9.0-amd64.img.zst'));assert(!html.includes('Tu LA AGUJA'));
    }
   }
  }
  for(const route of ['/xx/docs','/en/account','/en/../../.env','/assets/%2e%2e%2fen/index.html'])assert.equal((await fetch(base+route)).status,404,route);
  assert.equal((await fetch(base+'/en/docs',{method:'POST'})).status,405);
  const sitemap=await(await fetch(base+'/sitemap.xml')).text();assert.equal((sitemap.match(/<url>/g)||[]).length,24);
 }finally{await site.close();}
});
test('repository language guides are present without translating runnable command blocks',()=>{
 for(const lang of languages){
  const guide=fs.readFileSync(new URL(`../../docs/${lang}/USER-GUIDE.md`,import.meta.url),'utf8');
  assert.equal((guide.match(/^## /gm)||[]).length,26,lang);assert(guide.includes('aguja profile unlock'));assert(guide.includes('aguja doctor'));
 }
 const readme=fs.readFileSync(new URL('../../README.md',import.meta.url),'utf8');assert(readme.includes('English is the primary repository language'));assert(readme.includes('README.es.md'));
});
