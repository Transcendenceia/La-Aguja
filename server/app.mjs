import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const HERE=path.dirname(fileURLToPath(import.meta.url));
const types={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8','.png':'image/png','.svg':'image/svg+xml','.json':'application/json; charset=utf-8','.ico':'image/x-icon','.xml':'application/xml; charset=utf-8','.txt':'text/plain; charset=utf-8'};
export function createSite({publicDir=path.join(HERE,'public'),repository='Transcendenceia/La-Aguja',downloadsPublished=true}={}){
 if(!/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(repository))throw Error('Invalid GitHub repository');
 const github='https://github.com/'+repository;
 const server=http.createServer(async(req,res)=>{
  res.setHeader('X-Content-Type-Options','nosniff');res.setHeader('Referrer-Policy','strict-origin-when-cross-origin');res.setHeader('X-Frame-Options','DENY');res.setHeader('Permissions-Policy','camera=(), microphone=(), geolocation=()');
  res.setHeader('Content-Security-Policy',"default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'");
  if(!['GET','HEAD'].includes(req.method)){res.writeHead(405,{'Allow':'GET, HEAD'});return res.end();}
  let pathname;try{pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname);}catch{res.writeHead(400);return res.end();}
  if(pathname==='/health'){res.writeHead(200,{'Content-Type':types['.json']});return res.end(req.method==='HEAD'?undefined:JSON.stringify({ok:true,service:'aguja-public-site',accounts:false,relay:false,downloadsPublished}));}
  if(!downloadsPublished&&(pathname==='/v1/catalog'||pathname.startsWith('/releases/'))){res.writeHead(503,{'Content-Type':types['.json'],'Cache-Control':'no-store','Retry-After':'3600'});return res.end(req.method==='HEAD'?undefined:JSON.stringify({error:'La publicación de archivos en GitHub está pendiente. La web y el manual ya son públicos, sin cuenta.'}));}
  if(pathname==='/v1/catalog'){res.writeHead(302,{Location:github+'/releases/latest/download/catalog.json','Cache-Control':'no-store'});return res.end();}
  if(pathname.startsWith('/releases/')){
   const name=pathname.slice(10);if(!/^[A-Za-z0-9_.-]+$/.test(name)){res.writeHead(400);return res.end();}
   res.writeHead(302,{Location:github+'/releases/latest/download/'+encodeURIComponent(name),'Cache-Control':'no-store'});return res.end();
  }
  if(/^\/(account|auth|api|connect|v1)(\/|$)/.test(pathname)){res.writeHead(410,{'Content-Type':types['.json'],'Cache-Control':'no-store'});return res.end(req.method==='HEAD'?undefined:JSON.stringify({error:'LA AGUJA no usa cuentas ni relay propio. Usa tu Tailscale/Headscale y SSH.'}));}
  const fixed={'/':'en/index.html','/docs':'en/docs.html','/privacy':'en/privacy.html','/robots.txt':'robots.txt','/sitemap.xml':'sitemap.xml'};
  let file=fixed[pathname];
  const localeRoute=pathname.match(/^\/(en|es|fr|de|pt|it|nl|zh)(?:\/(docs|privacy))?\/?$/);
  if(localeRoute)file=localeRoute[1]+'/'+(localeRoute[2]||'index')+'.html';
  if(!file&&pathname.startsWith('/assets/')){
   const name=pathname.slice(8);if(name.startsWith('docs/'))file='docs-images/'+name.slice(5);else file=name;
  }
  if(!file||file.split(/[\\/]/).some(x=>x==='..'||x.startsWith('.'))){res.writeHead(404);return res.end();}
  const target=path.resolve(publicDir,file);
  if(!target.startsWith(path.resolve(publicDir)+path.sep)){res.writeHead(404);return res.end();}
  try{
   const stat=await fs.promises.lstat(target);if(!stat.isFile()||stat.isSymbolicLink())throw Error();
   if(path.extname(target)==='.html'){
    let html=await fs.promises.readFile(target,'utf8');
    if(!downloadsPublished){
     html=html.replace(/<a\b[^>]*href="([^"]+)"[^>]*>([\s\S]*?)<\/a>/g,(link,href,label)=>href===github||href.startsWith(github+'/')||href.startsWith('/releases/')?'<span class="download-pending" role="link" aria-disabled="true" title="Publicación en GitHub pendiente">'+label+'</span>':link);
     html=html.replace('<main>','<main><section role="status" class="release-notice"><strong>Web pública, sin cuenta.</strong> El código y los archivos de descarga se están preparando para GitHub. Las descargas estarán disponibles cuando se publique la release; el manual ya puede consultarse aquí.</section>');
     html=html.replace('Las descargas se realizan directamente en GitHub Releases.','Cuando estén publicadas, las descargas se realizarán directamente en GitHub Releases.');
    }
    html=html.replace(/(\/assets\/(?:app|theme|docs)\.(?:css|js))(?=")/g,'$1?v=public-20261008');
    res.writeHead(200,{'Content-Type':types['.html'],'Content-Length':Buffer.byteLength(html),'Cache-Control':'no-store'});
    return res.end(req.method==='HEAD'?undefined:html);
   }
   res.writeHead(200,{'Content-Type':types[path.extname(target)]||'application/octet-stream','Content-Length':stat.size,'Cache-Control':'public, max-age=300'});
   if(req.method==='HEAD')return res.end();fs.createReadStream(target).on('error',()=>res.destroy()).pipe(res);
  }catch{res.writeHead(404);res.end();}
 });
 return {server,ready:Promise.resolve(),close:()=>new Promise((resolve,reject)=>{server.close(e=>e?reject(e):resolve());server.closeIdleConnections();})};
}
