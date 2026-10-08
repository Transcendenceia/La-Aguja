#!/usr/bin/env node
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
const path=require('node:path');
const sharp=require('sharp');
const {chromium}=require('playwright');
const {pathToFileURL}=require('node:url');
const root=path.resolve(__dirname,'..');
async function main(){
  const release=(await fs.readFile(path.join(root,'VERSION'),'utf8')).trim();
  const output=path.join(root,'operations',`branding-${release}`);await fs.mkdir(output,{recursive:true});
  const manifest=JSON.parse(await fs.readFile(path.join(root,'branding/mascot/animation.json')));
  assert.equal(manifest.frameCount,96);assert.equal(manifest.expressions.length,8);
  for(let n=0;n<96;n++){
    const f=path.join(root,'branding/plymouth',manifest.frames[n].file);
    const {data,info}=await sharp(f).ensureAlpha().raw().toBuffer({resolveWithObject:true});
    assert.equal(info.width,320);assert.equal(info.height,440);
    assert.equal(data[3],0,'Frame corner must be genuinely transparent');
    let visible=0,transparent=0;for(let i=3;i<data.length;i+=4){if(data[i])visible++;else transparent++;}
    assert(visible>10000 && transparent>50000,'A full visible mascot on transparent background');
  }
  for(const type of ['gif','webp']){
    const m=await sharp(path.join(root,`branding/mascot/aguja-animated.${type}`),{animated:true}).metadata();
    assert.equal(m.pages,96);assert.equal(m.loop,0);assert(m.hasAlpha);
  }
  assert((await fs.readFile(path.join(root,'branding/wordmark.svg'),'utf8')).includes('LA AGUJA'));
  const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
  const failures=[];
  try{
    for(const width of [1280,360]){
      const page=await browser.newPage({viewport:{width,height:900}});
      page.on('pageerror',e=>failures.push(e.message));
      await page.goto(pathToFileURL(path.join(root,'branding/preview/index.html')).href);
      await page.locator('#mascot').evaluate(i=>i.decode());
      assert.equal(await page.title(),'LA AGUJA Rescue Disk · Agujita, nuestra mascota');
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'No horizontal overflow');
      await page.screenshot({path:path.join(output,`preview-${width}.png`),fullPage:true});
      await page.getByRole('button',{name:'Splash de arranque',exact:true}).click();
      await page.locator('#mascot').evaluate(i=>i.decode());
      assert.equal(await page.locator('.boot-title').innerText(),'LA AGUJA RESCUE DISK');
      await page.screenshot({path:path.join(output,`splash-preview-${width}.png`),fullPage:true});
      await page.getByRole('button',{name:'Pausar animación',exact:true}).click();
      assert((await page.locator('#mascot').getAttribute('src')).endsWith('/idle.png'));
      await page.getByRole('button',{name:'Reanudar animación',exact:true}).click();
      assert((await page.locator('#mascot').getAttribute('src')).endsWith('.webp'));
      await page.getByRole('button',{name:'Ocho expresiones',exact:true}).click();
      for(const label of ['Curiosa','Parpadeo','Guiño','Sorpresa','Risa','Mira izquierda','Mira derecha','Travesura']){
        await page.getByRole('button',{name:label,exact:true}).click();
        await page.locator('#mascot').evaluate(i=>i.decode());
      }
      await page.close();
    }
    const reduced=await browser.newPage({reducedMotion:'reduce'});
    await reduced.goto(pathToFileURL(path.join(root,'branding/preview/index.html')).href);
    assert((await reduced.locator('#mascot').getAttribute('src')).endsWith('/idle.png'));
    await reduced.close();assert.deepEqual(failures,[]);
  }finally{await browser.close();}
  const report={brand:'LA AGUJA Rescue Disk',mascot:'Agujita',rgbaFrames:96,expressions:8,animatedExports:['GIF','WebP'],browserWidths:[1280,360],pauseResume:true,expressionControls:true,reducedMotion:true,browserErrors:failures};
  await fs.writeFile(path.join(output,'asset-and-preview-checks.json'),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(report));
}
main().catch(e=>{console.error(e.message);process.exitCode=1;});
