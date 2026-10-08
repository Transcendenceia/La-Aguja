import {createSite} from './app.mjs';
const port=Number(process.env.AGUJA_PORT||8787);
if(!Number.isInteger(port)||port<1024||port>65535)throw Error('Invalid AGUJA_PORT');
const site=createSite({repository:process.env.AGUJA_GITHUB_REPOSITORY||'Transcendenceia/La-Aguja'});
site.server.listen(port,'127.0.0.1',()=>console.log('LA AGUJA public information site on loopback:'+port));
for(const signal of ['SIGTERM','SIGINT'])process.once(signal,async()=>{await site.close();process.exit(0);});
