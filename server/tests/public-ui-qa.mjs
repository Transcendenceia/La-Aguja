import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {chromium} from 'playwright';
import {createSite} from '../app.mjs';

const output=process.env.AGUJA_QA_ROOT||fs.mkdtempSync(path.join(os.tmpdir(),'aguja-public-web-'));
fs.mkdirSync(output,{recursive:true});
const site=process.env.AGUJA_QA_BASE_URL?null:createSite({downloadsPublished:process.env.AGUJA_QA_PENDING_RELEASE!=='1'});
if(site)await new Promise(resolve=>site.server.listen(0,'127.0.0.1',resolve));
const base=process.env.AGUJA_QA_BASE_URL||'http://127.0.0.1:'+site.server.address().port;
let browser;const errors=[],failed=[];let images=0;
try{
 browser=await chromium.launch({headless:true,executablePath:process.env.AGUJA_QA_BROWSER||'/usr/bin/chromium'});
 for(const width of [1440,375,320]){
  const context=await browser.newContext({viewport:{width,height:980}}),page=await context.newPage();
  page.on('pageerror',error=>errors.push(error.message));
  page.on('response',response=>{if(response.url().startsWith(base)&&response.status()>=400)failed.push(response.status()+' '+new URL(response.url()).pathname);});
  for(const route of ['/','/docs','/privacy']){
   const response=await page.goto(base+route);assert.equal(response.status(),200);
   assert.equal(response.headers()['set-cookie'],undefined);
   if(route==='/'){
    assert(await page.locator('h1').isVisible());
    for(const link of await page.locator('#application .installer-links a, #application .installer-links [aria-disabled="true"]').all()){
     await link.scrollIntoViewIfNeeded();const box=await link.boundingBox();
     assert(box&&box.width>0&&box.height>0);assert(box.x>=0&&box.x+box.width<=width+1);
    }
   }
   await page.evaluate(async()=>{for(const image of document.images){image.loading='eager';await image.decode();}});
   images+=await page.locator('img').count();
   const horizontal=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
   assert.equal(horizontal,false,`${route} ${width}px overflow`);
   assert.equal(await page.locator('input[type=password], form[action*=auth], a[href="/account"]').count(),0);
   assert.equal((await context.cookies()).length,0);
   await page.screenshot({path:path.join(output,(route==='/'?'home':route.slice(1))+'-'+width+'.png'),fullPage:true});
  }
  await context.close();
 }
 assert.deepEqual(errors,[]);assert.deepEqual(failed,[]);
 const result={ok:true,widths:[1440,375,320],routes:3,decodedImages:images,accountForms:0,cookies:0,jsErrors:errors,failedLocalResponses:failed,githubDownloadsNotClicked:true};
 fs.writeFileSync(path.join(output,'public-ui-result.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
}finally{await browser?.close();if(site)await site.close();}
