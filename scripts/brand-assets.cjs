#!/usr/bin/env node
// Package the unchanged AI-generated sheet into reusable poses, frames and marks.
const sharp = require('sharp');
const fs = require('node:fs/promises');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const base = path.resolve(__dirname, '../branding');
const names = ['idle', 'blink', 'wink', 'surprise', 'laugh', 'look-left', 'look-right', 'mischief'];
const fps = 12, count = 96;
function poseAt(n) {
  if (n >= 14 && n <= 15 || n >= 58 && n <= 59) return 1;
  if (n >= 23 && n <= 31) return 5;
  if (n >= 34 && n <= 42) return 6;
  if (n >= 46 && n <= 53) return 3;
  if (n >= 62 && n <= 69) return 4;
  if (n >= 73 && n <= 82) return 2;
  if (n >= 85 && n <= 91) return 7;
  return 0;
}
const svg = (w,h,body) => Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">${body}</svg>`);
async function canvas(w,h,layers,bg='#0b1220') {
  return sharp({create:{width:w,height:h,channels:4,background:bg}}).composite(layers).png().toBuffer();
}
async function main() {
  for (const folder of ['mascot', 'plymouth', 'grub']) await fs.mkdir(path.join(base,folder), {recursive:true});
  const source=path.join(base,'source/aguja-expressions.png');
  const meta=await sharp(source).metadata();
  if (meta.width % 4 || meta.height % 2 || !meta.hasAlpha) throw new Error('Expected 4×2 RGBA sheet');
  const cw=meta.width/4, ch=meta.height/2, poses=[];
  for(let i=0;i<8;i++) {
    const cell=await sharp(source).extract({left:i%4*cw,top:Math.floor(i/4)*ch,width:cw,height:ch}).png().toBuffer();
    const pose=await sharp(cell).trim({background:'#00000000',threshold:8}).resize({height:360}).png().toBuffer();
    const pm=await sharp(pose).metadata();
    const output=await canvas(320,440,[{input:pose,left:Math.round((320-pm.width)/2),top:36}],'#00000000');
    poses.push(output);
    await fs.writeFile(path.join(base,'mascot',`${names[i]}.png`),output);
  }
  const manifest={name:'Agujita',fps,frameCount:count,durationSeconds:count/fps,width:320,height:440,expressions:names,frames:[]};
  for(let n=0;n<count;n++) {
    const phase=n/count*Math.PI*2;
    const angle=2.4*Math.sin(phase*2)+0.9*Math.sin(phase*3);
    const bounce=Math.round(6*Math.sin(phase*4));
    const padded=await sharp(poses[poseAt(n)]).extend({top:24,bottom:24,left:24,right:24,background:'#00000000'}).png().toBuffer();
    const rotated=await sharp(padded).rotate(angle,{background:'#00000000'}).png().toBuffer();
    const rm=await sharp(rotated).metadata();
    const frame=await sharp(rotated).extract({left:Math.floor((rm.width-320)/2),top:Math.floor((rm.height-440)/2)-bounce,width:320,height:440}).png().toBuffer();
    const file=`frame-${String(n).padStart(3,'0')}.png`;
    await fs.writeFile(path.join(base,'plymouth',file),frame);
    manifest.frames.push({file,expression:names[poseAt(n)]});
  }
  await fs.writeFile(path.join(base,'mascot/animation.json'),JSON.stringify(manifest,null,2)+'\n');
  await fs.copyFile(path.join(base,'mascot/idle.png'),path.join(base,'mascot/aguja-mascot.png'));
  const face=await sharp(source).extract({left:48,top:0,width:300,height:340}).resize({height:224}).png().toBuffer();
  const fm=await sharp(face).metadata();
  const icon=await canvas(256,256,[{input:face,left:Math.round((256-fm.width)/2),top:16}],'#00000000');
  await fs.writeFile(path.join(base,'mascot/icon-256.png'),icon);
  for(const size of [32,64,128]) await sharp(icon).resize(size,size).png().toFile(path.join(base,'mascot',`icon-${size}.png`));
  const mark=svg(800,200,`<text x="0" y="96" font-family="DejaVu Sans" font-size="88" font-weight="bold" letter-spacing="-4" fill="#f5f7fb">LA AGUJA<tspan fill="#35e3c0">.</tspan></text><text x="6" y="148" font-family="DejaVu Sans" font-size="36" font-weight="bold" letter-spacing="9" fill="#35e3c0">RESCUE DISK</text><text x="6" y="188" font-family="DejaVu Sans" font-size="18" letter-spacing="5" fill="#92a4bb">AI-FIRST RESCUE LINUX</text>`);
  await fs.writeFile(path.join(base,'wordmark.svg'),mark);
  await fs.writeFile(path.join(base,'logo.svg'),mark);
  const word=await sharp(mark).png().toBuffer();
  const lockup=await canvas(1000,440,[{input:poses[0],left:0,top:0},{input:await sharp(word).resize({width:640}).png().toBuffer(),left:330,top:140}]);
  await fs.writeFile(path.join(base,'brand-lockup.png'),lockup);
  const wordBoot=await sharp(svg(680,78,`<text x="0" y="60" font-family="DejaVu Sans" font-weight="bold" font-size="46" letter-spacing="-3" fill="#f5f7fb">LA AGUJA<tspan dx="18" fill="#35e3c0">RESCUE DISK</tspan></text>`)).trim().png().toBuffer();
  await fs.writeFile(path.join(base,'plymouth/wordmark.png'),wordBoot);
  const tagline=await sharp(svg(640,40,`<text x="0" y="26" font-family="DejaVu Sans" font-size="21" fill="#92a4bb">Una entrada pequeña. Control completo.</text>`)).trim().png().toBuffer();
  await fs.writeFile(path.join(base,'plymouth/tagline.png'),tagline);
  await sharp(svg(8,8,'<circle cx="4" cy="4" r="3" fill="#35e3c0"/>')).png().toFile(path.join(base,'plymouth/dot.png'));
  const hero=svg(1600,900,`<defs><radialGradient id="g"><stop stop-color="#143733"/><stop offset="1" stop-color="#0b1220"/></radialGradient></defs><rect width="1600" height="900" fill="#0b1220"/><circle cx="1150" cy="450" r="520" fill="url(#g)"/><text x="100" y="155" font-family="DejaVu Sans" font-size="18" letter-spacing="5" fill="#35e3c0">AI-FIRST RESCUE LINUX</text><text x="95" y="330" font-family="DejaVu Sans" font-size="110" font-weight="bold" letter-spacing="-5" fill="#f5f7fb">LA AGUJA<tspan fill="#35e3c0">.</tspan></text><text x="103" y="405" font-family="DejaVu Sans" font-size="46" font-weight="bold" letter-spacing="10" fill="#35e3c0">RESCUE DISK</text><text x="103" y="490" font-family="DejaVu Sans" font-size="32" fill="#92a4bb">Una entrada pequeña.</text><text x="103" y="539" font-family="DejaVu Sans" font-size="32" fill="#f5f7fb">Control completo.</text><path d="M105 680h620" stroke="#254542"/><text x="103" y="727" font-family="DejaVu Sans" font-size="20" fill="#35e3c0">LIVE USB · SSH · CUATRO AGENTES · SUDO</text><text x="103" y="815" font-family="DejaVu Sans" font-size="17" fill="#92a4bb">Precisa por naturaleza. Curiosa por vocación.</text>`);
  const heroMascot=await sharp(poses[2]).resize({height:700}).png().toBuffer();
  await sharp(hero).composite([{input:heroMascot,left:900,top:105}]).png().toFile(path.join(base,'product-banner.png'));
  const grubBg=svg(1024,768,`<rect width="1024" height="768" fill="#0b1220"/><text x="420" y="170" font-family="DejaVu Sans" font-size="56" font-weight="bold" letter-spacing="-5" fill="#f5f7fb">LA AGUJA<tspan fill="#35e3c0">.</tspan></text><text x="425" y="212" font-family="DejaVu Sans" font-size="26" font-weight="bold" letter-spacing="7" fill="#35e3c0">RESCUE DISK</text><text x="427" y="250" font-family="DejaVu Sans" font-size="18" fill="#92a4bb">Una entrada pequeña. Control completo.</text><path d="M428 280h480" stroke="#254542"/><text x="50" y="718" font-family="DejaVu Sans" font-size="16" fill="#92a4bb">↑ ↓ Elegir    Enter Arrancar    E Editar</text><text x="720" y="718" font-family="DejaVu Sans" font-size="15" fill="#35e3c0">AI-FIRST RESCUE LINUX</text>`);
  await sharp(grubBg).composite([{input:poses[0],left:65,top:140}]).png().toFile(path.join(base,'grub/background.png'));
  execFileSync('ffmpeg',['-v','error','-y','-framerate',String(fps),'-i',path.join(base,'plymouth/frame-%03d.png'),'-filter_complex','[0:v]split[a][b];[a]palettegen=reserve_transparent=1:stats_mode=diff[p];[b][p]paletteuse=dither=sierra2_4a','-loop','0',path.join(base,'mascot/aguja-animated.gif')]);
  await sharp(path.join(base,'mascot/aguja-animated.gif'),{animated:true}).webp({quality:88,loop:0}).toFile(path.join(base,'mascot/aguja-animated.webp'));
  console.log(`Agujita: ${names.length} poses, ${count} frames, alpha, WebP/GIF, GRUB and product artwork.`);
}
main().catch(e=>{console.error(e.message);process.exitCode=1;});
