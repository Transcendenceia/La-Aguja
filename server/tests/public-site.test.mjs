import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const imagerVersion=JSON.parse(fs.readFileSync(new URL('../../desktop/package.json',import.meta.url),'utf8')).version;
const currentVersion=fs.readFileSync(new URL('../../VERSION',import.meta.url),'utf8').trim();
import {createSite} from '../app.mjs';
async function fixture(run,options={}){const site=createSite(options);await new Promise(r=>site.server.listen(0,'127.0.0.1',r));try{await run('http://127.0.0.1:'+site.server.address().port);}finally{await site.close();}}
test('opening the informational site does not require unpublished GitHub assets or accounts',()=>fixture(async base=>{
 const r=await fetch(base+'/');assert.equal(r.status,200);assert.equal(r.headers.get('cache-control'),'no-store');assert.equal(r.headers.get('set-cookie'),null);
 const html=await r.text();assert(html.includes('Web pública, sin cuenta.'));assert(html.includes('aria-disabled="true"'));assert(!/href="https:\/\/github.com\/Transcendenceia\/La-Aguja/.test(html));
 assert.equal((await fetch(base+'/docs')).status,200);assert.equal((await fetch(base+'/v1/catalog',{redirect:'manual'})).status,503);assert.equal((await fetch(base+'/releases/SHA256SUMS',{redirect:'manual'})).status,503);
}, {downloadsPublished:false}));
test('homepage/manual/assets/health are anonymous and never set account cookies',()=>fixture(async base=>{for(const route of ['/','/docs','/privacy','/assets/docs.css','/assets/docs/agujita.png','/health']){const r=await fetch(base+route);assert.equal(r.status,200,route);assert.equal(r.headers.get('set-cookie'),null);assert(!r.headers.has('www-authenticate'));await r.arrayBuffer();}}));
test('retired account, relay and console endpoints cannot establish sessions',()=>fixture(async base=>{for(const route of ['/account','/auth/login','/connect/fixture','/v1/devices','/v1/account/tunnels']){const r=await fetch(base+route);assert.equal(r.status,410);assert.equal(r.headers.get('set-cookie'),null);}assert.equal((await fetch(base+'/v1/devices',{method:'POST'})).status,405);}));
test('legacy downloads redirect to GitHub, not a local private release store',()=>fixture(async base=>{for(const [route,end] of [['/releases/SHA256SUMS','SHA256SUMS'],['/v1/catalog','catalog.json']]){const r=await fetch(base+route,{redirect:'manual'});assert.equal(r.status,302);assert.equal(r.headers.get('location'),'https://github.com/Transcendenceia/La-Aguja/releases/latest/download/'+end);}}));
test('sensitive files, traversal and old account assets are not served',()=>fixture(async base=>{for(const route of ['/assets/../accounts.mjs','/assets/%2e%2e%2findex.mjs','/assets/account.js','/assets/../.env','/devices.json'])assert.equal((await fetch(base+route)).status,404,route);}));
test('all localized download cards use existing 1.0 release asset names and the independent skill tag',()=>fixture(async base=>{
 const repo='https://github.com/Transcendenceia/La-Aguja/releases/';
 const skillVersion=fs.readFileSync(new URL('../../skills/flash-imager/SKILL.md',import.meta.url),'utf8').match(/^  version: "([^"]+)"$/m)[1];
 const productAssets=[`aguja-flash-imager-${imagerVersion}-win-x64.exe`,`aguja-flash-imager-${imagerVersion}-x86_64.AppImage`,`aguja-flash-imager-${imagerVersion}-amd64.deb`,`aguja-flash-imager-${imagerVersion}-linux-x64.tar.gz`,`SHA256SUMS-imager-${imagerVersion}-windows`,`SHA256SUMS-imager-${imagerVersion}-linux`,`aguja-${currentVersion}-amd64.img.zst`,`aguja-${currentVersion}-amd64.iso`,'SHA256SUMS'];
 const skillAssets=[`aguja-flash-imager-skill-${skillVersion}.zip`,`aguja-flash-imager-skill-${skillVersion}.tar.gz`,`SHA256SUMS-flash-imager-skill-${skillVersion}`];
 const expected=new Set([...productAssets.map(n=>repo+`download/v${n.includes('imager')?imagerVersion:currentVersion}/`+n),...skillAssets.map(n=>repo+`download/flash-imager-skill-v${skillVersion}/`+n),repo+`tag/v${currentVersion}`]);
 for(const lang of ['en','es','fr','de','pt','it','nl','zh']){
  const html=await(await fetch(base+'/'+lang)).text();
  const links=[...html.matchAll(/href="([^"]*\/releases\/[^"]+)"/g)].map(m=>m[1]);
  assert.deepEqual(new Set(links),expected,lang+' download contract');
  assert(!/href="\/releases\//.test(html),'No legacy proxy or nonexistent rescue checksum asset');
  assert(html.includes('id="version-1"'));assert(html.includes('.aguja'));assert(html.includes('1.0.0'));
 }
}));
test('social crawlers receive the matching localized banner without JavaScript',()=>fixture(async base=>{
 const rCrawler=await fetch(base+'/',{headers:{'User-Agent':'WhatsApp/2.23.23.77 i'}});
 assert.equal(rCrawler.status,200);
 const htmlCrawler=await rCrawler.text();
 assert(htmlCrawler.includes('property="og:site_name" content="LA AGUJA"'));
 assert(htmlCrawler.includes('property="og:image" content="https://aguja.transcendenceia.net/assets/og-possibilities-es-20261010-v2.png"'));
 assert(htmlCrawler.includes('name="twitter:card" content="summary_large_image"'));
 assert(htmlCrawler.includes('<html lang="es">'));
 const rAsset=await fetch(base+'/assets/og-banner.png');
 assert.equal(rAsset.status,200);
 assert.equal(rAsset.headers.get('content-type'),'image/png');
 assert(Number(rAsset.headers.get('content-length'))>50000);
 for(const lang of ['en','es','fr','de','pt','it','nl','zh']){
  const image='/assets/og-possibilities-'+lang+'-20261010-v2.png';
  const asset=await fetch(base+image);assert.equal(asset.status,200);assert.equal(asset.headers.get('content-type'),'image/png');
  const png=Buffer.from(await asset.arrayBuffer());assert(png.length>50000);assert.equal(png.subarray(1,4).toString(),'PNG');
  const width=png.readUInt32BE(16),height=png.readUInt32BE(20);assert(width/height>1.89&&width/height<1.92);
  for(const suffix of ['','/docs','/privacy'])for(const ua of ['WhatsApp/2.23.23.77 i','facebookexternalhit/1.1','Twitterbot/1.0','LinkedInBot/1.0','Discordbot/2.0']){
   const page=await fetch(base+'/'+lang+suffix,{headers:{'User-Agent':ua,'Accept-Language':'es'}});assert.equal(page.status,200);
   const html=await page.text();assert(html.includes('<html lang="'+lang+'">'));
   assert(html.includes('property="og:image" content="https://aguja.transcendenceia.net'+image+'"'));
   assert(html.includes('name="twitter:image" content="https://aguja.transcendenceia.net'+image+'"'));
   assert(html.includes('property="og:image:width" content="'+width+'"'));assert(html.includes('property="og:image:height" content="'+height+'"'));
  }
 }
}));
