import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createSite} from '../app.mjs';
const {chromium}=await import(process.env.AGUJA_PLAYWRIGHT||'playwright');
const output=process.env.AGUJA_QA_ROOT||'/tmp/aguja-launch-ui';fs.mkdirSync(output,{recursive:true});
const languages=(process.env.AGUJA_QA_LANGS||'en,es,fr,de,pt,it,nl,zh').split(',');
const site=process.env.AGUJA_QA_BASE?null:createSite();if(site)await new Promise(r=>site.server.listen(0,'127.0.0.1',r));const base=process.env.AGUJA_QA_BASE||'http://127.0.0.1:'+site.server.address().port;
const browser=await chromium.launch({headless:true,executablePath:'/usr/bin/chromium',args:['--no-sandbox']});const errors=[],failures=[],external=[];let count=0;
try{
 for(const width of [1440,375,320])for(const lang of languages){
  const context=await browser.newContext({viewport:{width,height:960}});const page=await context.newPage();
  page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.status()>=400)failures.push(r.url());});page.on('request',r=>{if(!r.url().startsWith(base)&&!r.url().startsWith('data:'))external.push(r.url());});
  for(const suffix of ['','/docs']){
   await page.goto(base+'/'+lang+suffix);await page.evaluate(async()=>{for(const i of document.images){i.loading='eager';await i.decode();}});
   assert.equal(await page.locator('h1').count(),1);
   assert.equal(await page.locator('.language-nav a').count(),8);
   assert.equal(await page.locator('.language-nav [aria-current=page]').getAttribute('lang'),lang);
   if(!suffix){const faq=page.locator('#questions details').first();await faq.locator('summary').focus();await page.keyboard.press('Enter');assert(await faq.evaluate(x=>x.open));await page.keyboard.press('Enter');assert.equal(await faq.evaluate(x=>x.open),false);}

   const overflow=await page.evaluate(()=>{document.documentElement.style.overflow='visible';document.body.style.overflow='visible';return document.documentElement.scrollWidth>innerWidth;});assert.equal(overflow,false,lang+suffix+' '+width);
   for(const a of await page.locator('.actions a,.installer-links a').all()){const box=await a.boundingBox();assert(box&&box.x>=0&&box.x+box.width<=width+1,lang+' clipped action');}
   await page.selectOption('#situation','plan-1');assert.equal(await page.locator('[data-plan]:visible').count(),1);await page.selectOption('#situation','all');assert.equal(await page.locator('[data-plan]:visible').count(),3);
   if(suffix){
    assert.equal(await page.locator('.doc-section').count(),26);await page.locator('.checklist input').first().check();assert((await page.locator('.check-status').innerText()).includes('1 / 6'));
    await page.fill('#doc-search','ENOSPC');assert(await page.locator('[data-doc-link]:visible').count()>0);assert(await page.locator('[data-doc-link]:visible').count()<26);await page.locator('#doc-search').press('Escape');assert.equal(await page.locator('[data-doc-link]:visible').count(),26);
    const link=page.locator('.zoom-image').first();await link.click();assert(await page.locator('dialog').isVisible());await page.keyboard.press('Escape');assert.equal(await page.locator('dialog').isVisible(),false);assert(await link.evaluate(x=>x===document.activeElement));
    await page.evaluate(()=>Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async()=>{throw Error('QA denial');}}}));await page.locator('.prompt .copy-text').first().click();assert((await page.evaluate(()=>getSelection().toString())).length>50);
    await page.evaluate(()=>Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async text=>{window.qaClipboard=text;}}}));await page.locator('.prompt .copy-text').first().click();assert((await page.evaluate(()=>window.qaClipboard)).length>50);
    await page.reload();assert.equal(await page.locator('.checklist input:checked').count(),0);
    const other=lang==='en'?'es':'en';await page.evaluate(()=>location.hash='trabajo-ia');await page.locator('.language-nav a[lang='+other+']').click();assert(page.url().endsWith('/'+other+'/docs#trabajo-ia'));await page.goto(base+'/'+lang+'/docs');
    await page.evaluate(()=>dispatchEvent(new Event('beforeprint')));assert.equal(await page.locator('details:not([open])').count(),0);await page.evaluate(()=>dispatchEvent(new Event('afterprint')));
   }
   assert.equal((await context.cookies()).length,0);assert.equal(await page.evaluate(()=>localStorage.length+sessionStorage.length),0);
   if(lang==='en'||lang==='es'){await page.screenshot({path:output+'/'+lang+(suffix?'-docs':'-home')+'-'+width+'.png',fullPage:false});}
   count++;
  }
  await context.close();
 }
 const nojs=await browser.newContext({javaScriptEnabled:false,viewport:{width:320,height:960}});const page=await nojs.newPage();for(const lang of languages){await page.goto(base+'/'+lang+'/docs');assert.equal(await page.locator('.doc-section').count(),26);assert.equal(await page.locator('[data-plan]:visible').count(),3);assert.equal(await page.locator('.zoom-image').count(),5);}await nojs.close();
 assert.deepEqual(errors,[]);assert.deepEqual(failures,[]);assert.deepEqual(external,[]);
 const result={ok:true,languages,widths:[1440,375,320],pages:count,nojs:true,copySuccess:'mock clipboard',copyFallback:true,modalEscapeAndFocus:true,externalRequests:external,errors,failures};fs.writeFileSync(output+'/result.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result));
}finally{await browser.close();if(site)await site.close();}
