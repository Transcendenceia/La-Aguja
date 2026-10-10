import test from 'node:test';
import assert from 'node:assert/strict';
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
test('homepage images use the official web and other downloads use the intended GitHub repository',()=>fixture(async base=>{const text=await(await fetch(base+'/')).text();assert(!text.includes('href="/account'));assert(!text.includes('id="connection"'));const links=[...text.matchAll(/href="([^"]*\/releases\/[^\"]+)"/g)].map(m=>m[1]);assert(links.length>=8);const images=new Set(['/releases/aguja-0.9.9-amd64.iso','/releases/aguja-0.9.9-amd64.img.zst']);assert.equal(links.filter(link=>images.has(link)).length,2);for(const link of links)assert(images.has(link)||link==='/releases/SHA256SUMS-rescue-0.9.9.txt'||link.startsWith('https://github.com/Transcendenceia/La-Aguja/releases/'));}));
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
