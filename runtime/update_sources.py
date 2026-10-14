"""Public upstream discovery and bounded, verified downloads. No login/session use."""
import base64,hashlib,json,re,ssl,urllib.request
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlsplit
ALLOWED={'github.com','api.github.com','raw.githubusercontent.com','release-assets.githubusercontent.com','objects.githubusercontent.com','registry.npmjs.org','storage.googleapis.com','antigravity-cli-auto-updater-974169037036.us-central1.run.app'}
def url(value):
 u=urlsplit(value)
 if u.scheme!='https' or u.hostname not in ALLOWED or u.username or u.password or u.fragment or u.port not in (None,443):raise ValueError('Origen de actualización no permitido')
 return value
class Redirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):return super().redirect_request(req,fp,code,msg,headers,url(newurl))
OPENER=urllib.request.build_opener(Redirect())
def stream(value):return OPENER.open(urllib.request.Request(url(value),headers={'User-Agent':'LA-AGUJA-update/1.0','Accept':'application/json, application/octet-stream'}),timeout=30)
def get(value,limit=2*1024**2):
 with stream(value) as f:
  raw=f.read(limit+1)
  if len(raw)>limit:raise ValueError('Metadatos demasiado grandes')
  return json.loads(raw)
def semver(v):
 if not isinstance(v,str) or not re.fullmatch(r'\d+\.\d+\.\d+',v):raise ValueError('Versión no válida')
 return tuple(map(int,v.split('.')))
def catalog(pin):
 from cryptography.hazmat.primitives.serialization import load_pem_public_key
 e=get(pin['update_catalog_url'],131072)
 if e.get('key_id')!=pin['key_id']:raise ValueError('Clave de publicación no válida')
 raw=base64.b64decode(e['payload'],validate=True)
 if len(raw)>65536:raise ValueError('Catálogo demasiado grande')
 load_pem_public_key(pin['public_key_pem'].encode()).verify(base64.b64decode(e['signature'],validate=True),raw)
 data=json.loads(raw)
 if data.get('schema')!=1 or datetime.fromisoformat(data['expires_at'].replace('Z','+00:00'))<datetime.now(timezone.utc):raise ValueError('Catálogo caducado')
 result=[]
 for r in data['releases']:
  semver(r['version']);parts=r.get('parts') or [{'url':r['url'],'bytes':r['bytes'],'sha256':r['sha256']}]
  if not 1048576<=r['bytes']<=64*1024**3 or not re.fullmatch('[a-f0-9]{64}',r['sha256']) or len(parts)>64:raise ValueError('Imagen no válida')
  for p in parts:
   parsed=urlsplit(url(p['url']))
   if parsed.hostname!='github.com' or not parsed.path.startswith('/'+pin['repository']+'/releases/download/v'+r['version']+'/') or not 0<p['bytes']<2*1024**3 or not re.fullmatch('[a-f0-9]{64}',p['sha256']):raise ValueError('Parte no válida')
  if sum(p['bytes'] for p in parts)!=r['bytes']:raise ValueError('Tamaño de imagen no válido')
  result.append({**r,'parts':parts})
 return sorted(result,key=lambda r:semver(r['version']),reverse=True)
def fetch(value,target,algorithm,expected,size=None,limit=512*1024**2):
 h=hashlib.new(algorithm);count=0
 with stream(value) as source,open(target,'xb') as dest:
  while b:=source.read(1024**2):
   count+=len(b)
   if count>limit or size is not None and count>size:raise ValueError('Descarga demasiado grande')
   h.update(b);dest.write(b)
  dest.flush();import os;os.fsync(dest.fileno())
 if h.hexdigest()!=expected or size is not None and count!=size:raise ValueError('Hash de descarga incorrecto')
 return count
def harnesses():
 result={};r=get('https://api.github.com/repos/openai/codex/releases/latest');v=r['tag_name'].removeprefix('rust-v');semver(v)
 a=next(x for x in r['assets'] if x['name']=='codex-x86_64-unknown-linux-musl.tar.gz');digest=a.get('digest','')
 if not re.fullmatch('sha256:[a-f0-9]{64}',digest):raise ValueError('Codex no publica un hash verificable')
 result['codex']={'version':v,'url':url(a['browser_download_url']),'algorithm':'sha256','digest':digest[7:],'bytes':a['size'],'member':'codex-x86_64-unknown-linux-musl'}
 for name,pkg,member in [('claude','@anthropic-ai/claude-code-linux-x64','package/claude'),('opencode','opencode-linux-x64-baseline','package/bin/opencode')]:
  r=get('https://registry.npmjs.org/'+pkg+'/latest');semver(r['version']);dist=r['dist'];integrity=dist['integrity']
  if not integrity.startswith('sha512-'):raise ValueError('Integridad nativa no válida')
  result[name]={'version':r['version'],'url':url(dist['tarball']),'algorithm':'sha512','digest':base64.b64decode(integrity[7:],validate=True).hex(),'member':member}
 r=get('https://antigravity-cli-auto-updater-974169037036.us-central1.run.app/manifests/linux_amd64.json');semver(r['version'])
 if not re.fullmatch('[a-f0-9]{128}',r['sha512']):raise ValueError('Integridad Antigravity no válida')
 result['antigravity']={'version':r['version'],'url':url(r['url']),'algorithm':'sha512','digest':r['sha512'],'member':'antigravity'}
 return result
