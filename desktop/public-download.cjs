'use strict';
// GitHub release assets redirect to GitHub's CDN. No account, cookies or
// authorization headers are accepted or forwarded at any hop.
const HOSTS=new Set(['github.com','raw.githubusercontent.com','release-assets.githubusercontent.com','objects.githubusercontent.com']);
function trusted(url){const u=new URL(url);if(u.protocol!=='https:'||u.username||u.password||u.hash||u.port&&u.port!=='443')throw Error('Dirección de descarga no válida.');return u;}
async function publicResponse(url,{signal,accept='application/octet-stream'}={}){
 let current=trusted(url);const github=HOSTS.has(current.hostname);
 for(let hop=0;hop<6;hop++){
  const response=await fetch(current.href,{redirect:github?'manual':'error',signal,credentials:'omit',headers:{Accept:accept}});
  if(![301,302,303,307,308].includes(response.status))return response;
  const next=trusted(new URL(response.headers.get('location'),current).href);
  await response.body?.cancel();
  if(!github||!HOSTS.has(next.hostname))throw Error('Redirección de descarga no autorizada.');
  current=next;
 }
 throw Error('Demasiadas redirecciones de descarga.');
}
module.exports={publicResponse};
