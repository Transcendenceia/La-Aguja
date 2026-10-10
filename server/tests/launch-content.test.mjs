import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const languages=['en','es','fr','de','pt','it','nl','zh'];
const read=p=>fs.readFileSync(new URL(p,import.meta.url),'utf8');
function shape(x){if(Array.isArray(x))return x.map(shape);if(x&&typeof x==='object')return Object.fromEntries(Object.entries(x).map(([k,v])=>[k,shape(v)]));return typeof x;}
test('all launch locales have equivalent plans, cases, safety additions and interaction labels',()=>{
 const source=JSON.parse(read('../locales/launch-en.json'));
 for(const lang of languages){const c=JSON.parse(read('../locales/launch-'+lang+'.json'));assert.deepEqual(shape(c),shape(source),lang);assert.equal(c.cases.length,20);assert.equal(c.plans.length,4);assert.equal(c.checks.length,6);
  for(const suffix of ['index','docs']){const h=read('../public/'+lang+'/'+suffix+'.html');if(suffix==='index')assert(h.includes('hero-recovery-20261009-v1.webp'));assert(h.includes('/assets/og-possibilities-'+lang+'-20261010-v2.png'));assert(h.includes('property="og:image"'));assert(h.includes('name="twitter:card"'));assert(h.includes('launch-20261009-v1.js'));assert.equal((h.match(/data-plan>/g)||[]).length,4);assert(!h.includes('<script>'));const ids=[...h.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);assert.equal(new Set(ids).size,ids.length,lang+' duplicate ids');for(const m of h.matchAll(/href="#([^"]+)"/g))assert(ids.includes(m[1]),lang+' broken '+m[1]);}
  const docs=read('../public/'+lang+'/docs.html');for(const name of ['rescue-dashboard','rescue-console','rescue-wheel','rescue-safe-mode','imager'])assert(docs.includes('/assets/docs/099/'+name+'.png'));for(const text of ['ENOSPC','YOLO','RAM','BitLocker','aguja profile unlock','SHA-256'])assert(docs.includes(text),lang+' '+text);assert(!docs.includes('0.9.2'));assert(!docs.includes('0.9.0'));
 }
});
test('interactive layer has no persistence or network APIs',()=>{const js=read('../public/launch-20261009-v1.js');assert(!/fetch\s*\(|XMLHttpRequest|sendBeacon|localStorage|sessionStorage|WebSocket/.test(js));assert(js.includes('navigator.clipboard.writeText'));assert(js.includes('range.selectNodeContents'));assert(js.includes('dialog.showModal'));});
