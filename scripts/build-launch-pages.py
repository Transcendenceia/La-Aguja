#!/usr/bin/env python3
"""Build reviewed launch overlay from locale sources, without modifying repository guides.
Run after build-site-locales.py. No routing changes; no third-party dependencies.
"""
import html,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PUBLIC=ROOT/'server/public'
LANGS=['en','es','fr','de','pt','it','nl','zh']
IDS=['que-es','primer-usb','glosario','preparacion','descargas','imagen','red','ssh','ia-preparacion','tailnet','politicas','secretos','bitlocker','grabar','arranque','reinicios','ia-login','primer-diagnostico','trabajo-ia','herramientas','casos','profesional','problemas','terminar','validacion','referencias']
GH='https://github.com/Transcendenceia/La-Aguja'
ORIGIN='https://aguja.transcendenceia.net'
E=html.escape
BASE={l:json.loads((ROOT/f'server/locales/{l}.json').read_text()) for l in LANGS}
# The historic Spanish guide has richer structured content than its locale JSON.
spanish=(PUBLIC/'docs.html').read_text()
ES_BODIES={}
BASE['es']['sections']=[]
for identifier in IDS:
 match=re.search(r'<section id="'+identifier+r'".*?(?=<section id=|<footer|</main>)',spanish,re.S)
 if not match:raise ValueError('Missing Spanish chapter '+identifier)
 chunk=match.group();title=re.search(r'<h2[^>]*>(.*?)</h2>',chunk,re.S).group(1)
 BASE['es']['sections'].append([html.unescape(re.sub('<[^>]+>','',title))])
 chunk=re.sub(r'^.*?</h2>','',chunk,count=1,flags=re.S)
 chunk=re.sub(r'<figure.*?</figure>','',chunk,flags=re.S)
 chunk=re.sub(r'<p[^>]*>[^<]*[^<]*0\.8\.[01].*?</p>','',chunk,flags=re.S)
 chunk=re.sub(r'</section>\s*$','',chunk)
 chunk=chunk.replace('Las capturas anteriores indican expresamente su versión histórica. ','')
 ES_BODIES[identifier]=chunk

COMMANDS={1:'aguja status\naguja doctor\nlsblk -o NAME,SIZE,MODEL,SERIAL,FSTYPE,LABEL,MOUNTPOINTS',7:'ssh aguja@IP',14:'aguja profile unlock\naguja status',16:'aguja login codex\naguja login claude\naguja login antigravity\nopencode auth login',17:'aguja doctor\nlsblk -o NAME,SIZE,MODEL,SERIAL,FSTYPE,LABEL,MOUNTPOINTS\nfindmnt',19:'aguja tools\naguja status --disks\naguja status --json\naguja context\naguja help'}
FIGURES={4:['imager'],14:['rescue-dashboard'],16:['rescue-console'],18:['rescue-safe-mode','rescue-wheel']}
def paras(items):return ''.join('<p>'+E(x)+'</p>' for x in items)
def current(s):return s.replace('0.9.2','0.9.9').replace('0.9.1','0.9.9').replace('0.9.0','0.9.9').replace('Flash Imager Linux 0.8.2','Flash Imager Linux 0.9.9').replace('Flash Imager Windows 0.8.2','Flash Imager Windows 0.9.9')
def head(l,c,b,suffix):
 title=('LA AGUJA · '+c['hero'][0]) if not suffix else current(b['docTitle'])+' · 0.9.9'
 desc=c['lead'] if not suffix else current(b['docDescription']);canonical=ORIGIN+'/'+l+suffix
 return f'<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="dark"><title>{E(title)}</title><meta name="description" content="{E(desc)}"><link rel="canonical" href="{canonical}">'+''.join(f'<link rel="alternate" hreflang="{x}" href="{ORIGIN}/{x}{suffix}">' for x in LANGS)+f'<link rel="alternate" hreflang="x-default" href="{ORIGIN}/en{suffix}"><meta property="og:type" content="website"><meta property="og:site_name" content="LA AGUJA Rescue Disk"><meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{canonical}"><meta property="og:image" content="{ORIGIN}/assets/og-banner.png"><meta property="og:image:secure_url" content="{ORIGIN}/assets/og-banner.png"><meta property="og:image:type" content="image/png"><meta property="og:image:width" content="1600"><meta property="og:image:height" content="900"><meta property="og:image:alt" content="Agujita · LA AGUJA Rescue Disk"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{E(title)}"><meta name="twitter:description" content="{E(desc)}"><meta name="twitter:image" content="{ORIGIN}/assets/og-banner.png"><meta name="twitter:image:alt" content="Agujita · LA AGUJA Rescue Disk"><link rel="icon" href="/assets/docs/agujita.png"><link rel="stylesheet" href="/assets/launch-20261009-v1.css"><script src="/assets/launch-20261009-v1.js" defer></script>'
def header(l,c,b,suffix):
 return f'<a class="skip-link" href="#main">{E(c["ui"]["skip"])}</a><header class="site-header"><a class="brand" href="/{l}"><img src="/assets/docs/agujita.png" width="48" height="48" alt="Agujita"><span>LA AGUJA<small>TRANSCENDENCEIA / RESCUE DISK</small></span></a><nav class="site-nav" aria-label="{E(b["nav"][1])}"><a href="/{l}#application">{E(b["nav"][0])}</a><a href="/{l}/docs">{E(b["nav"][1])}</a><a href="{GH}">GitHub ↗</a><a href="/{l}#donate">{E(b["donation"]["title"])}</a></nav></header><nav class="language-nav" aria-label="Language / Idioma">'+''.join(f'<a href="/{x}{suffix}" lang="{x}" hreflang="{x}"'+(' aria-current="page"' if x==l else '')+f'>{BASE[x]["name"]}</a>' for x in LANGS)+'</nav>'
def page(l,c,b,body,suffix=''):
 ui=' '.join(f'data-{k}="{E(c[k])}"' for k in ['copy','copied','close','zoom'])+' '+ ' '.join(f'data-{key}="{E(c[value])}"' for key,value in [('copy-fallback','copyFallback'),('search-matches','searchMatches'),('no-matches','noMatches'),('check-progress','checkProgress')])
 return f'<!doctype html><html lang="{l}"><head>{head(l,c,b,suffix)}</head><body {ui}>{header(l,c,b,suffix)}<main><div id="main">{body}</div></main><footer><a href="https://www.transcendenceia.net">LA AGUJA / TRANSCENDENCEIA ↗</a><a href="/{l}/privacy">{E(b["privacy"])}</a><span>{E(b["footer"])}</span></footer></body></html>\n'
def planner(c):
 return f'<section class="planner" id="plan"><h2>{E(c["plannerTitle"])}</h2><p>{E(c["plannerNote"])}</p><div class="planner-controls" hidden><label for="situation">{E(c["choose"])}</label><select id="situation"><option value="all">{E(c["allPlans"])}</option>'+''.join(f'<option value="plan-{i}">{E(p["title"])}</option>' for i,p in enumerate(c['plans']))+'</select></div><div class="plan-grid">'+''.join(f'<article class="plan-card" id="plan-{i}" data-plan><span class="number">0{i+1}</span><h3>{E(p["title"])}</h3><p>{E(p["intro"])}</p><ol>'+''.join('<li>'+E(s)+'</li>' for s in p['steps'])+f'</ol><p class="stop"><strong>{E(c["stop"])}</strong> {E(p["stop"])}</p></article>' for i,p in enumerate(c['plans']))+'</div></section>'
def cases(c):return '<div class="case-grid">'+''.join('<article><span class="eyebrow">'+E(tag)+'</span><h3>'+E(title)+'</h3><p>'+E(body)+'</p></article>' for tag,title,body in c['cases'])+'</div>'
def checklist(c):return '<fieldset class="checklist"><legend>'+E(c['checkTitle'])+'</legend><p>'+E(c['checkNote'])+'</p>'+''.join(f'<label><input type="checkbox" name="check-{i}"><span>{E(s)}</span></label>' for i,s in enumerate(c['checks']))+'<p class="check-status" role="status" aria-live="polite"></p></fieldset>'
def figure(c,name):return f'<figure><a class="zoom-image" href="/assets/docs/099/{name}.png" aria-label="{E(c["zoom"]+": "+c["figures"][name])}"><img src="/assets/docs/099/{name}.png" loading="lazy" decoding="async" alt="{E(c["figures"][name])}"></a><figcaption><strong>{E(c["figures"][name])}</strong> · {E(c["captureNote"])} <span>{E(c["zoom"])}</span></figcaption></figure>'
def home(l,c,b):
 body=f'<section class="hero"><div><span class="eyebrow">{E(c["eyebrow"])}</span><h1>{E(c["hero"][0])}<br><span>{E(c["hero"][1])}</span></h1><p class="lead">{E(c["lead"])}</p><div class="actions"><a class="button" href="#application">{E(b["actions"][0])} ↘</a><a class="button secondary" href="/{l}/docs">{E(c["ui"]["readGuide"])} →</a></div><p class="micro">{E(c["ui"]["heroNote"])}</p></div><figure class="hero-art"><img src="/assets/hero-recovery-20261009-v1.webp" width="1200" height="800" alt="{E(b["recoveryAlt"])}" fetchpriority="high"><figcaption>{E(b["caption"][1])}</figcaption></figure></section><div class="trust-strip"><span>Rescue Disk <strong>0.9.9</strong></span><span>Flash Imager <strong>0.9.9</strong></span><span>Agent Skill <strong>1.0.1</strong></span></div><section class="intro"><h2>{E(c["introTitle"])}</h2>'+paras(c['intro'])+'</section><div class="feature-grid">'+''.join(f'<article><span class="number">0{i+1}</span><h3>{E(title)}</h3><p>{E(text)}</p></article>' for i,(title,text) in enumerate(b['steps']))+'</div>'+planner(c)+f'<section id="possibilities"><span class="eyebrow">{E(c["ui"]["possibilities"])}</span><h2>{E(c["casesTitle"])}</h2><p>{E(c["casesNote"])}</p>'+cases(c)+f'</section><section class="boundary"><h2>{E(c["boundaryTitle"])}</h2>'+paras(c['boundaries'])+f'</section><section id="application"><span class="eyebrow">01 / FLASH IMAGER · 0.9.9</span><h2>{E(b["imagerTitle"])}</h2><p>{E(c["downloadText"])}</p><div class="installer-links">'
 files=[('win-x64.exe','Windows 10 / 11 · EXE'),('x86_64.AppImage','Linux · AppImage'),('amd64.deb','Debian / Ubuntu · DEB'),('x64.tar.gz',b['portable'])]
 body+=''.join(f'<a href="{GH}/releases/download/v0.9.9/aguja-flash-imager-0.9.9-{file}">{E(label)} ↗</a>' for file,label in files)+f'</div><p><a href="{GH}/releases/download/v0.9.9/SHA256SUMS-imager-0.9.9-windows">SHA-256 · Windows</a> · <a href="{GH}/releases/download/v0.9.9/SHA256SUMS-imager-0.9.9-linux">SHA-256 · Linux</a></p><a href="/{l}/docs#primer-usb">{E(c["ui"]["firstUsb"])} →</a></section>'
 s=b['imagerSkill'];d=b['donation']
 urls=[GH+'/releases/download/v0.9.9/aguja-flash-imager-skill-1.0.1.zip',GH+'/releases/download/v0.9.9/aguja-flash-imager-skill-1.0.1.tar.gz',GH+'/blob/main/skills/flash-imager/references/harnesses.md',GH+'/releases/download/v0.9.9/SHA256SUMS-flash-imager-skill-1.0.1']
 body+=f'<section id="agent-skill"><span class="eyebrow">02 / AGENT SKILL · 1.0.1</span><h2>{E(s["title"])}</h2><p>{E(s["text"])}</p><div class="installer-links">'+''.join(f'<a href="{u}">{E(label)} ↗</a>' for u,label in zip(urls,s['links']))+f'</div><p>{E(s["note"])}</p></section><section id="images"><span class="eyebrow">03 / RESCUE DISK · 0.9.9</span><h2>{E(b["imagesTitle"])}</h2><p>{E(c["imageText"])}</p><div class="installer-links">'
 urls=['/releases/aguja-0.9.9-amd64.img.zst','/releases/aguja-0.9.9-amd64.iso','/releases/SHA256SUMS-rescue-0.9.9.txt',GH+'/releases/tag/v0.9.9']
 body+=''.join(f'<a href="{u}">{E(label)}</a>' for u,label in zip(urls,b['imageLinks']))+f'</div></section><section id="questions"><h2>{E(b["faqTitle"])}</h2>'+''.join('<details><summary>'+E(q)+'</summary><p>'+E(a)+'</p></details>' for q,a in b['faq'])+f'</section><section id="donate"><div class="support-heading"><img src="/assets/support-icon.svg" width="48" height="48" alt=""><h2>{E(d["title"])}</h2></div><p>{E(d["message"])}</p><details><summary>Ko-fi · {E(d["title"])}</summary><img class="support-qr" src="/assets/donation-qr.png" width="260" height="260" alt="Ko-fi QR"><p><a href="https://ko-fi.com/transcendenceia" target="_blank" rel="noopener noreferrer">Ko-fi · Transcendence IA ↗</a></p><p>{E(d["optional"])}</p></details></section>'
 return page(l,c,b,body)
def reviewed(s,c):
 for old,new in c.get("replacements",[]):s=s.replace(old,new)
 return current(s)
def docs(l,c,b):
 body=f'<section class="guide-intro"><span class="eyebrow">RESCUE DISK + FLASH IMAGER · 0.9.9</span><h1>{E(b["docUI"][2])}</h1><p class="lead">{E(current(b["docDescription"]))}</p><p>{E(c["docNote"])}</p><div class="actions"><a class="button" href="#primer-usb">{E(c["ui"]["firstUsb"])} ↓</a><button class="secondary print-guide" type="button" hidden>{E(c["ui"]["print"])}</button></div></section><div class="guide-layout"><aside class="contents"><details open><summary>{E(c["ui"]["contents"])}</summary><div class="search-controls" hidden><label for="doc-search">{E(c["ui"]["search"])}</label><input type="search" id="doc-search" placeholder="SSH, BitLocker, ENOSPC…"><p id="search-status" role="status" aria-live="polite"></p></div><nav aria-label="{E(c["ui"]["contents"])}">'+''.join(f'<a data-doc-link href="#{i}">{n+1:02} · {E(s[0])}</a>' for n,(i,s) in enumerate(zip(IDS,b['sections'])))+'</nav></details></aside><div class="chapters">'
 assert len(b['sections'])==26
 for n,(i,s) in enumerate(zip(IDS,b['sections'])):
  ps=[reviewed(p,c) for p in s[1:] if not re.search(r'0\.8\.[01]',p)]
  body+=f'<section class="doc-section" id="{i}"><span class="eyebrow">{n+1:02} / 26</span><h2>{E(s[0])}</h2>'+(reviewed(ES_BODIES[i],c) if l=='es' else paras(ps))+paras(c['additions'].get(str(n),[]))
  if n in COMMANDS and (l!='es' or '<pre' not in ES_BODIES[i]):body+='<pre><code>'+E(COMMANDS[n])+'</code></pre>'
  if str(n) in c['prompts']:body+='<div class="prompt"><h3>'+E(c['promptLabel'])+'</h3><pre><code>'+E(c['prompts'][str(n)])+'</code></pre></div>'
  for image in FIGURES.get(n,[]):body+=figure(c,image)
  if n==1:body+=checklist(c)
  if n==20:body+=planner(c)+f'<h3>{E(c["casesTitle"])}</h3><p>{E(c["casesNote"])}</p>'+cases(c)
  body+='</section>'
 return page(l,c,b,body+'</div></div>','/docs')
if __name__=='__main__':
 for l in (sys.argv[1:] or LANGS):
  c=json.loads((ROOT/f'server/locales/launch-{l}.json').read_text());b=BASE[l]
  (PUBLIC/l/'index.html').write_text(home(l,c,b));(PUBLIC/l/'docs.html').write_text(docs(l,c,b))
 print('Built launch home + guide pages; routing and other files untouched.')
