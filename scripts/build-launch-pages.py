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
VERSION=(ROOT/'VERSION').read_text().strip()
IMAGER_VERSION=json.loads((ROOT/'desktop/package.json').read_text())['version']
SKILL_VERSION=re.search(r'^  version: "([^"]+)"$',(ROOT/'skills/flash-imager/SKILL.md').read_text(),re.M).group(1)
SKILL_TAG='flash-imager-skill-v'+SKILL_VERSION
ORIGIN='https://aguja.transcendenceia.net'
E=html.escape
BASE={l:json.loads((ROOT/f'server/locales/{l}.json').read_text()) for l in LANGS}
SOCIAL=json.loads((ROOT/'server/locales/social-images.json').read_text())
RELEASE=json.loads((ROOT/'server/locales/release-1.0.json').read_text())
IOT_SECTION={
 'en':{'title':'LA AGUJA IoT · ESP32 family in Flash Imager 1.2.0','text':'Flash supported ESP32 microcontrollers directly from Flash Imager (Linux and Windows, zero Python on Windows) into remote Tailscale/Headscale proxy nodes controllable by AI agents.','cards':[('11 ESP32 boards · auto-detect','ESP32-C6, ESP32-S3 (Octal/Std), ESP32-C3, ESP32 and ESP32-S2 with real USB chip detection and 6 prebuilt v1.4.0 firmwares.'),('Multi-Wi-Fi · SoftAP off by default','Up to 8 prioritized Wi-Fi networks, pure-JS ESP-IDF NVS v2 injection, serial boot check and 1-click flash erase.'),('Tailnet proxy & agent REST CLI','Exit node, dynamic upstream subnet router, DNS relay, dual-OTA rollback and remote hardware control via aguja-iot.py.')],'download':'Download Flash Imager 1.2.0','docs':'IoT architecture & boards','skillDocs':'Agent Skill IoT reference'},
 'es':{'title':'LA AGUJA IoT · Familia ESP32 en Flash Imager 1.2.0','text':'Flashea microcontroladores ESP32 compatibles desde Flash Imager (Linux y Windows, sin Python en Windows) para desplegar nodos proxy Tailscale/Headscale controlables por agentes IA.','cards':[('11 placas ESP32 · autodetección','ESP32-C6, ESP32-S3 (Octal/Std), ESP32-C3, ESP32 y ESP32-S2 con detección real del chip por USB y 6 firmwares v1.4.0 precompilados.'),('Multi-Wi-Fi · SoftAP desactivado','Hasta 8 redes Wi-Fi con prioridad, generador NVS v2 en JS puro, verificación serie al arrancar y borrado de flash en 1 clic.'),('Proxy tailnet y CLI para agentes','Exit node, subnet router dinámico, DNS relay, doble partición OTA y control remoto de hardware con aguja-iot.py.')],'download':'Descargar Flash Imager 1.2.0','docs':'Arquitectura IoT y placas','skillDocs':'Referencia IoT de la Agent Skill'},
 'fr':{'title':'LA AGUJA IoT · Famille ESP32 dans Flash Imager 1.2.0','text':'Flashez des microcontrôleurs ESP32 depuis Flash Imager (Linux et Windows, sans Python sous Windows) en nœuds proxy Tailscale/Headscale contrôlables par vos agents IA.','cards':[('11 cartes ESP32 · détection auto','ESP32-C6, ESP32-S3, ESP32-C3, ESP32 et ESP32-S2 avec détection USB réelle de la puce et 6 firmwares v1.4.0 précompilés.'),('Multi-Wi-Fi · SoftAP désactivé','Jusqu’à 8 réseaux Wi-Fi prioritaires, génération NVS v2 en JS pur, vérification série au démarrage et effacement flash en 1 clic.'),('Proxy tailnet et CLI agent','Exit node, routeur de sous-réseau dynamique, relais DNS, double OTA et contrôle matériel distant via aguja-iot.py.')],'download':'Télécharger Flash Imager 1.2.0','docs':'Architecture IoT et cartes','skillDocs':'Référence IoT Agent Skill'},
 'de':{'title':'LA AGUJA IoT · ESP32-Familie in Flash Imager 1.2.0','text':'Flashe unterstützte ESP32-Mikrocontroller direkt mit Flash Imager (Linux und Windows, ohne Python unter Windows) zu Tailscale/Headscale-Proxy-Knoten für KI-Agenten.','cards':[('11 ESP32-Boards · Auto-Erkennung','ESP32-C6, ESP32-S3, ESP32-C3, ESP32 und ESP32-S2 mit echter USB-Chip-Erkennung und 6 fertigen v1.4.0-Firmwares.'),('Multi-WLAN · SoftAP standardmäßig aus','Bis zu 8 priorisierte WLANs, reiner JS-NVS-v2-Generator, serielle Boot-Prüfung und Flash-Löschen per Klick.'),('Tailnet-Proxy & Agent-CLI','Exit-Node, dynamischer Subnetz-Router, DNS-Relay, Dual-OTA und Fernsteuerung per aguja-iot.py.')],'download':'Flash Imager 1.2.0 herunterladen','docs':'IoT-Architektur & Boards','skillDocs':'Agent-Skill IoT-Referenz'},
 'pt':{'title':'LA AGUJA IoT · Família ESP32 no Flash Imager 1.2.0','text':'Grave microcontroladores ESP32 diretamente no Flash Imager (Linux e Windows, sem Python no Windows) como nós proxy Tailscale/Headscale controláveis por agentes IA.','cards':[('11 placas ESP32 · deteção automática','ESP32-C6, ESP32-S3, ESP32-C3, ESP32 e ESP32-S2 com deteção real por USB e 6 firmwares v1.4.0 pré-compilados.'),('Multi-Wi-Fi · SoftAP desativado','Até 8 redes Wi-Fi prioritárias, gerador NVS v2 em JS puro, verificação série no arranque e limpeza de flash num clique.'),('Proxy tailnet e CLI para agentes','Exit node, subnet router dinâmico, DNS relay, duplo OTA e controlo remoto de hardware via aguja-iot.py.')],'download':'Descarregar Flash Imager 1.2.0','docs':'Arquitetura IoT e placas','skillDocs':'Referência IoT da Agent Skill'},
 'it':{'title':'LA AGUJA IoT · Famiglia ESP32 in Flash Imager 1.2.0','text':'Scrivi il firmware su microcontrollori ESP32 direttamente da Flash Imager (Linux e Windows, senza Python su Windows) per creare nodi proxy Tailscale/Headscale controllabili da agenti IA.','cards':[('11 schede ESP32 · rilevamento auto','ESP32-C6, ESP32-S3, ESP32-C3, ESP32 ed ESP32-S2 con rilevamento USB del chip e 6 firmware v1.4.0 precompilati.'),('Multi-Wi-Fi · SoftAP disattivato','Fino a 8 reti Wi-Fi in ordine di priorità, generatore NVS v2 in JS puro, verifica seriale all’avvio e cancellazione flash in 1 clic.'),('Proxy tailnet e CLI per agenti','Exit node, subnet router dinamico, DNS relay, doppio OTA e controllo remoto hardware con aguja-iot.py.')],'download':'Scarica Flash Imager 1.2.0','docs':'Architettura IoT e schede','skillDocs':'Riferimento IoT Agent Skill'},
 'nl':{'title':'LA AGUJA IoT · ESP32-familie in Flash Imager 1.2.0','text':'Flash ondersteunde ESP32-microcontrollers rechtstreeks met Flash Imager (Linux en Windows, zonder Python op Windows) naar Tailscale/Headscale-proxynodes voor AI-agents.','cards':[('11 ESP32-boards · auto-detectie','ESP32-C6, ESP32-S3, ESP32-C3, ESP32 en ESP32-S2 met echte USB-chipherkenning en 6 voorgebouwde v1.4.0-firmwares.'),('Multi-Wi-Fi · SoftAP standaard uit','Tot 8 geprioriteerde wifi-netwerken, pure JS NVS v2-generator, seriële opstartcheck en flash wissen met 1 klik.'),('Tailnet-proxy en agent-CLI','Exit node, dynamische subnetrouter, DNS-relay, dubbele OTA en afstandsbediening via aguja-iot.py.')],'download':'Flash Imager 1.2.0 downloaden','docs':'IoT-architectuur & boards','skillDocs':'Agent Skill IoT-referentie'},
 'zh':{'title':'LA AGUJA IoT · Flash Imager 1.2.0 中的 ESP32 系列','text':'直接使用 Flash Imager（Linux 与 Windows，Windows 无需 Python）烧录 ESP32 微控制器，将其变为可由 AI 代理控制的 Tailscale/Headscale 代理节点。','cards':[('11 款 ESP32 开发板 · 自动识别','支持 ESP32-C6、ESP32-S3、ESP32-C3、ESP32 与 ESP32-S2，支持真实 USB 芯片探测及 6 套预编译 v1.4.0 固件。'),('多 Wi-Fi · 默认关闭 SoftAP','最多 8 个按优先级排序的 Wi-Fi、纯 JS NVS v2 生成器、串口启动校验与一键清空闪存。'),('Tailnet 代理与代理 REST CLI','出口节点、动态上游子网路由、DNS 中继、双分区 OTA 回滚与 aguja-iot.py 远程硬件控制。')],'download':'下载 Flash Imager 1.2.0','docs':'IoT 架构与开发板','skillDocs':'Agent Skill IoT 参考'}
}
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
def current(s):
 s=re.sub(r'(?<!\d)0\.9\.(?:0|1|2|9|10)(?!\d)',VERSION,s)
 return re.sub(r'(Flash Imager(?: Linux| Windows)? )'+re.escape(VERSION),r'\g<1>'+IMAGER_VERSION,s).replace('Flash Imager Linux 0.8.2','Flash Imager Linux '+IMAGER_VERSION).replace('Flash Imager Windows 0.8.2','Flash Imager Windows '+IMAGER_VERSION)
def head(l,c,b,suffix):
 image=SOCIAL[l];image_url=ORIGIN+'/assets/'+image['file']
 title=('LA AGUJA · '+c['hero'][0]) if not suffix else current(b['docTitle'])+f' · {VERSION}'
 desc=c['lead'] if not suffix else current(b['docDescription']);canonical=ORIGIN+'/'+l+suffix
 return f'<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="dark"><title>{E(title)}</title><meta name="description" content="{E(desc)}"><link rel="canonical" href="{canonical}">'+''.join(f'<link rel="alternate" hreflang="{x}" href="{ORIGIN}/{x}{suffix}">' for x in LANGS)+f'<link rel="alternate" hreflang="x-default" href="{ORIGIN}/en{suffix}"><meta property="og:type" content="website"><meta property="og:site_name" content="LA AGUJA"><meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{canonical}"><meta property="og:image" content="{image_url}"><meta property="og:image:secure_url" content="{image_url}"><meta property="og:image:type" content="image/png"><meta property="og:image:width" content="{image["width"]}"><meta property="og:image:height" content="{image["height"]}"><meta property="og:image:alt" content="{E(image["alt"])}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{E(title)}"><meta name="twitter:description" content="{E(desc)}"><meta name="twitter:image" content="{image_url}"><meta name="twitter:image:alt" content="{E(image["alt"])}"><link rel="icon" href="/assets/docs/agujita.png"><link rel="stylesheet" href="/assets/launch-20261009-v1.css"><script src="/assets/launch-20261009-v1.js" defer></script>'
def header(l,c,b,suffix):
 return f'<a class="skip-link" href="#main">{E(c["ui"]["skip"])}</a><header class="site-header"><a class="brand" href="/{l}"><img src="/assets/docs/agujita.png" width="48" height="48" alt="Agujita"><span>LA AGUJA<small>TRANSCENDENCEIA / LIVE LINUX + AI</small></span></a><nav class="site-nav" aria-label="{E(b["nav"][1])}"><a href="/{l}#application">{E(b["nav"][0])}</a><a href="/{l}/docs">{E(b["nav"][1])}</a><a href="{GH}">GitHub ↗</a><a href="/{l}#donate">{E(b["donation"]["title"])}</a></nav></header><nav class="language-nav" aria-label="Language / Idioma">'+''.join(f'<a href="/{x}{suffix}" lang="{x}" hreflang="{x}"'+(' aria-current="page"' if x==l else '')+f'>{BASE[x]["name"]}</a>' for x in LANGS)+'</nav>'
def page(l,c,b,body,suffix=''):
 ui=' '.join(f'data-{k}="{E(c[k])}"' for k in ['copy','copied','close','zoom'])+' '+ ' '.join(f'data-{key}="{E(c[value])}"' for key,value in [('copy-fallback','copyFallback'),('search-matches','searchMatches'),('no-matches','noMatches'),('check-progress','checkProgress')])
 return f'<!doctype html><html lang="{l}"><head>{head(l,c,b,suffix)}</head><body {ui}>{header(l,c,b,suffix)}<main><div id="main">{body}</div></main><footer><a href="https://www.transcendenceia.net">LA AGUJA / TRANSCENDENCEIA ↗</a><a href="/{l}/privacy">{E(b["privacy"])}</a><span>{E(b["footer"])}</span></footer></body></html>\n'
def planner(c):
 return f'<section class="planner" id="plan"><h2>{E(c["plannerTitle"])}</h2><p>{E(c["plannerNote"])}</p><div class="planner-controls" hidden><label for="situation">{E(c["choose"])}</label><select id="situation"><option value="all">{E(c["allPlans"])}</option>'+''.join(f'<option value="plan-{i}">{E(p["title"])}</option>' for i,p in enumerate(c['plans']))+'</select></div><div class="plan-grid">'+''.join(f'<article class="plan-card" id="plan-{i}" data-plan><span class="number">0{i+1}</span><h3>{E(p["title"])}</h3><p>{E(p["intro"])}</p><ol>'+''.join('<li>'+E(s)+'</li>' for s in p['steps'])+f'</ol><p class="stop"><strong>{E(c["stop"])}</strong> {E(p["stop"])}</p></article>' for i,p in enumerate(c['plans']))+'</div></section>'
def cases(c):return '<div class="case-grid">'+''.join('<article><span class="eyebrow">'+E(tag)+'</span><h3>'+E(title)+'</h3><p>'+E(body)+'</p></article>' for tag,title,body in c['cases'])+'</div>'
def checklist(c):return '<fieldset class="checklist"><legend>'+E(c['checkTitle'])+'</legend><p>'+E(c['checkNote'])+'</p>'+''.join(f'<label><input type="checkbox" name="check-{i}"><span>{E(s)}</span></label>' for i,s in enumerate(c['checks']))+'<p class="check-status" role="status" aria-live="polite"></p></fieldset>'
def figure(c,name):return f'<figure><a class="zoom-image" href="/assets/docs/099/{name}.png" aria-label="{E(c["zoom"]+": "+c["figures"][name])}"><img src="/assets/docs/099/{name}.png" loading="lazy" decoding="async" alt="{E(c["figures"][name])}"></a><figcaption><strong>{E(c["figures"][name])}</strong> · {E(c["captureNote"])} <span>{E(c["zoom"])}</span></figcaption></figure>'
def home(l,c,b):
 c["imageText"]=RELEASE[l]["image"]
 body=f'<section class="hero"><div><span class="eyebrow">{E(c["eyebrow"])}</span><h1>{E(c["hero"][0])}<br><span>{E(c["hero"][1])}</span></h1><p class="lead">{E(c["lead"])}</p><div class="actions"><a class="button" href="#application">{E(b["actions"][0])} ↘</a><a class="button secondary" href="/{l}/docs">{E(c["ui"]["readGuide"])} →</a></div><p class="micro">{E(c["ui"]["heroNote"])}</p></div><figure class="hero-art"><img src="/assets/hero-recovery-20261009-v1.webp" width="1200" height="800" alt="{E(b["recoveryAlt"])}" fetchpriority="high"><figcaption>{E(b["caption"][1])}</figcaption></figure></section><div class="trust-strip"><span>Rescue Disk <strong>{VERSION}</strong></span><span>Flash Imager <strong>{IMAGER_VERSION}</strong></span><span>Agent Skill <strong>{SKILL_VERSION}</strong></span></div><section class="intro"><h2>{E(c["introTitle"])}</h2>'+paras(c['intro'])+'</section><div class="feature-grid">'+''.join(f'<article><span class="number">0{i+1}</span><h3>{E(title)}</h3><p>{E(text)}</p></article>' for i,(title,text) in enumerate(b['steps']))+'</div>'+planner(c)+f'<section id="possibilities"><span class="eyebrow">{E(c["ui"]["possibilities"])}</span><h2>{E(c["casesTitle"])}</h2><p>{E(c["casesNote"])}</p>'+cases(c)+f'</section><section class="boundary"><h2>{E(c["boundaryTitle"])}</h2>'+paras(c['boundaries'])+f'</section><section id="application"><span class="eyebrow">01 / FLASH IMAGER · {IMAGER_VERSION}</span><h2>{E(b["imagerTitle"])}</h2><p>{E(c["downloadText"])}</p><div class="installer-links">'
 files=[('win-x64.exe','Windows 10 / 11 · EXE'),('x86_64.AppImage','Linux · AppImage'),('amd64.deb','Debian / Ubuntu · DEB'),('linux-x64.tar.gz',b['portable'])]
 body+=''.join(f'<a href="{GH}/releases/download/v{IMAGER_VERSION}/aguja-flash-imager-{IMAGER_VERSION}-{file}">{E(label)} ↗</a>' for file,label in files)+f'</div><p><a href="{GH}/releases/download/v{IMAGER_VERSION}/SHA256SUMS-imager-{IMAGER_VERSION}-windows">SHA-256 · Windows</a> · <a href="{GH}/releases/download/v{IMAGER_VERSION}/SHA256SUMS-imager-{IMAGER_VERSION}-linux">SHA-256 · Linux</a></p><a href="/{l}/docs#primer-usb">{E(c["ui"]["firstUsb"])} →</a></section>'
 s=b['imagerSkill'];d=b['donation']
 urls=[GH+f'/releases/download/{SKILL_TAG}/aguja-flash-imager-skill-{SKILL_VERSION}.zip',GH+f'/releases/download/{SKILL_TAG}/aguja-flash-imager-skill-{SKILL_VERSION}.tar.gz',GH+f'/blob/main/skills/flash-imager/references/harnesses.md',GH+f'/releases/download/{SKILL_TAG}/SHA256SUMS-flash-imager-skill-{SKILL_VERSION}']
 body+=f'<section id="agent-skill"><span class="eyebrow">02 / AGENT SKILL · {SKILL_VERSION}</span><h2>{E(s["title"])}</h2><p>{E(s["text"])}</p><div class="installer-links">'+''.join(f'<a href="{u}">{E(label)} ↗</a>' for u,label in zip(urls,s['links']))+f'</div><p>{E(s["note"])}</p></section>'
 iot=IOT_SECTION[l]
 body+=f'<section id="iot-mcu"><span class="eyebrow">03 / LA AGUJA IoT · ESP32 · v1.4.0</span><h2>{E(iot["title"])}</h2><p>{E(iot["text"])}</p><div class="feature-grid">'+''.join('<article><h3>'+E(t)+'</h3><p>'+E(p)+'</p></article>' for t,p in iot['cards'])+f'</div><div class="installer-links"><a href="#application">{E(iot["download"])} ↑</a><a href="{GH}/blob/main/iot/README.md">{E(iot["docs"])} ↗</a><a href="{GH}/blob/main/skills/flash-imager/references/iot.md">{E(iot["skillDocs"])} ↗</a></div></section>'
 body+=f'<section id="images"><span class="eyebrow">04 / RESCUE DISK · {VERSION}</span><h2>{E(b["imagesTitle"])}</h2><p>{E(c["imageText"])}</p><div class="installer-links">'
 image_base=json.loads((ROOT/'config/image-hosting.json').read_text()).get(VERSION,GH+f'/releases/download/v{VERSION}/')
 if image_base not in ('https://aguja.transcendenceia.net/releases/',GH+f'/releases/download/v{VERSION}/'):raise ValueError('Unexpected image download origin')
 urls=[image_base+f'aguja-{VERSION}-amd64.img.zst',image_base+f'aguja-{VERSION}-amd64.iso',GH+f'/releases/download/v{VERSION}/SHA256SUMS',GH+f'/releases/tag/v{VERSION}']
 body+=''.join(f'<a href="{u}">{E(label)}</a>' for u,label in zip(urls,b['imageLinks']))+f'</div></section><section id="questions"><h2>{E(b["faqTitle"])}</h2>'+''.join('<details><summary>'+E(q)+'</summary><p>'+E(a)+'</p></details>' for q,a in b['faq'])+f'</section><section id="donate"><div class="support-heading"><img src="/assets/support-icon.svg" width="48" height="48" alt=""><h2>{E(d["title"])}</h2></div><p>{E(d["message"])}</p><details><summary>Ko-fi · {E(d["title"])}</summary><img class="support-qr" src="/assets/donation-qr.png" width="260" height="260" alt="Ko-fi QR"><p><a href="https://ko-fi.com/transcendenceia" target="_blank" rel="noopener noreferrer">Ko-fi · Transcendence IA ↗</a></p><p>{E(d["optional"])}</p></details></section>'
 release=RELEASE[l]
 release_label={'en':'Complete release notes','es':'Lista completa de cambios','fr':'Notes de version complètes','de':'Vollständige Versionshinweise','pt':'Lista completa de alterações','it':'Note di rilascio complete','nl':'Volledige versieopmerkingen','zh':'完整版本说明'}[l]
 news=f'<section id="version-1"><span class="eyebrow">LA AGUJA · {VERSION}</span><h2>{E(release["title"])}</h2>'+paras(release['intro'])+'<div class="feature-grid">'+''.join('<article><h3>'+E(t)+'</h3><p>'+E(p)+'</p></article>' for t,p in release['features'])+f'</div><p><a href="{GH}/releases/tag/v{VERSION}">{E(release_label)} · {VERSION} ↗</a></p><a href="/{l}/docs#reinicios">{E(c["ui"]["readGuide"])} →</a></section>'
 body=body.replace('<section class="intro">',news+'<section class="intro">',1)
 return page(l,c,b,body)
def reviewed(s,c):
 for old,new in c.get("replacements",[]):s=s.replace(old,new)
 return current(s)
def docs(l,c,b):
 release=RELEASE[l]
 for n,section in release['sections'].items(): b['sections'][int(n)]=section
 b['sections'][13][0]=release['create']
 body=f'<section class="guide-intro"><span class="eyebrow">RESCUE DISK · {VERSION} / FLASH IMAGER · {IMAGER_VERSION}</span><h1>{E(b["docUI"][2])}</h1><p class="lead">{E(current(b["docDescription"]))}</p><p>{E(c["docNote"])}</p><div class="actions"><a class="button" href="#primer-usb">{E(c["ui"]["firstUsb"])} ↓</a><button class="secondary print-guide" type="button" hidden>{E(c["ui"]["print"])}</button></div></section><div class="guide-layout"><aside class="contents"><details open><summary>{E(c["ui"]["contents"])}</summary><div class="search-controls" hidden><label for="doc-search">{E(c["ui"]["search"])}</label><input type="search" id="doc-search" placeholder="SSH, BitLocker, ENOSPC…"><p id="search-status" role="status" aria-live="polite"></p></div><nav aria-label="{E(c["ui"]["contents"])}">'+''.join(f'<a data-doc-link href="#{i}">{n+1:02} · {E(s[0])}</a>' for n,(i,s) in enumerate(zip(IDS,b['sections'])))+'</nav></details></aside><div class="chapters">'
 assert len(b['sections'])==26
 for n,(i,s) in enumerate(zip(IDS,b['sections'])):
  ps=[reviewed(p,c) for p in s[1:] if not re.search(r'0\.8\.[01]',p)]
  content=paras(s[1:]) if str(n) in release['sections'] else (reviewed(ES_BODIES[i],c) if l=='es' else paras(ps))
  if n==0:content=paras(c['intro'])
  body+=f'<section class="doc-section" id="{i}"><span class="eyebrow">{n+1:02} / 26</span><h2>{E(s[0])}</h2>'+content+paras(c['additions'].get(str(n),[]))
  if n==1:body+=paras(release['wizard'])
  if n==15:
   for name,title in release['updateCaptions'].items():
    url='/assets/docs/101/'+name+'.png'
    body+=f'<figure><a class="zoom-image" href="{url}" aria-label="{E(title)}"><img src="{url}" loading="lazy" decoding="async" width="1280" height="800" alt="{E(title)}"></a><figcaption>{E(title)} · {E(release["captureProvenance"])}</figcaption></figure>'
  if n==15:body+='<pre><code>aguja update menu\naguja update status --json\naguja update check --json\naguja update rollback</code></pre>'
  if n==12:body+='<pre><code>aguja secrets --json\nsudo aguja recovery status --json\nsudo aguja recovery list --json</code></pre>'
  if n==24:body+=f'<p><a href="{GH}/releases/download/v{VERSION}/VALIDATION-{VERSION}.md">GitHub · {VERSION} · Validation ↗</a> · <a href="{GH}/releases/download/v{VERSION}/UPDATES.md">aguja update · README ↗</a></p>'
  if n in COMMANDS and (l!='es' or '<pre' not in ES_BODIES[i]):body+='<pre><code>'+E(COMMANDS[n])+'</code></pre>'
  if str(n) in c['prompts']:body+='<div class="prompt"><h3>'+E(c['promptLabel'])+'</h3><pre><code>'+E(c['prompts'][str(n)])+'</code></pre></div>'
  for image in FIGURES.get(n,[]):body+=figure(c,image)
  if n==1:body+=checklist(c)
  if n==20:body+=planner(c)+f'<h3>{E(c["casesTitle"])}</h3><p>{E(c["casesNote"])}</p>'+cases(c)
  body+='</section>'
 # SSH user@IP examples are commands, not mail addresses. Preserve them at the edge.
 body=body.replace('<pre>','<!--email_off--><pre>').replace('</pre>','</pre><!--/email_off-->')
 return page(l,c,b,body+'</div></div>','/docs')
if __name__=='__main__':
 for l in (sys.argv[1:] or LANGS):
  c=json.loads((ROOT/f'server/locales/launch-{l}.json').read_text());b=BASE[l]
  (PUBLIC/l/'index.html').write_text(home(l,c,b));(PUBLIC/l/'docs.html').write_text(docs(l,c,b))
  guide=ROOT/f'docs/{l}/USER-GUIDE.md'
  text=guide.read_text();chapters=list(re.finditer(r'^## .*$',text,re.M));assert len(chapters)==26
  section=RELEASE[l]['sections']['15'];block='## '+section[0]+'\n\n'+'\n\n'.join(section[1:])+'\n\n```sh\naguja update menu\naguja update status --json\naguja update check --json\naguja update rollback\n```\n\n'
  block+='\n\n'.join('!['+title+'](../../server/public/docs-images/101/'+name+'.png)' for name,title in RELEASE[l]['updateCaptions'].items())+'\n\n'+RELEASE[l]['captureProvenance']+'\n\n'
  guide.write_text(text[:chapters[15].start()]+block+text[chapters[16].start():])
 print('Built launch home + guide pages; routing and other files untouched.')
