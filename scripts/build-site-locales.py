#!/usr/bin/env python3
"""Build anonymous, server-rendered locale pages from reviewed project content."""
import html
import json
import re
from pathlib import Path
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'server/public'
LANGS = ['en', 'es', 'fr', 'de', 'pt', 'it', 'nl', 'zh']
CONTENT = {lang: json.loads((ROOT / f'server/locales/{lang}.json').read_text()) for lang in LANGS}
IDS = ['que-es','primer-usb','glosario','preparacion','descargas','imagen','red','ssh','ia-preparacion','tailnet','politicas','secretos','bitlocker','grabar','arranque','reinicios','ia-login','primer-diagnostico','trabajo-ia','herramientas','casos','profesional','problemas','terminar','validacion','referencias']
GH = 'https://github.com/Transcendenceia/La-Aguja'
IMAGER_VERSION = json.loads((ROOT / 'desktop/package.json').read_text())['version']
IMAGER_TAG = 'v' + IMAGER_VERSION
ORIGIN = 'https://aguja.transcendenceia.net'
esc = html.escape

def language_nav(lang, suffix=''):
    return '<nav class="language-nav" aria-label="Language / Idioma">' + ''.join(
        f'<a href="/{code}{suffix}" lang="{code}" hreflang="{code}"'+ (' aria-current="page"' if code==lang else '') + f'>{CONTENT[code]["name"]}</a>' for code in LANGS) + '</nav>'

def metadata(lang, suffix, title, description=''):
    return f'<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="dark"><title>{esc(title)}</title><meta name="description" content="{esc(description)}"><link rel="canonical" href="{ORIGIN}/{lang}{suffix}">' + ''.join(f'<link rel="alternate" hreflang="{code}" href="{ORIGIN}/{code}{suffix}">' for code in LANGS) + f'<link rel="alternate" hreflang="x-default" href="{ORIGIN}/en{suffix}"><link rel="stylesheet" href="/assets/locales-20261008.css">'

# Use fixed original artwork and preserve the long Spanish reference separately.
original = (PUBLIC / 'index.html').read_text()
icon = re.search(r'<link rel="icon"[^>]+>', original).group()
images = re.findall(r'<img[^>]+>', original)
spanish = (PUBLIC / 'docs.html').read_text()
spanish = spanish.replace('Imager 0.9.1', 'Imager 0.9.2').replace('/assets/docs.js\"', '/assets/docs.js?v=multilingual-20261008\"')
spanish = spanish.replace('href="/"', 'href="/es"').replace('href="/#application"', 'href="/es#application"').replace('href="/privacy"','href="/es/privacy"')
# Keep the historical PDF clearly Spanish and distinct from current print-to-PDF.
spanish = spanish.replace('Descargar manual PDF', 'PDF histórico · español (0.9.0)')

figures = {}
for identifier in IDS:
    match = re.search(r'<section\b[^>]*id="'+identifier+r'"[\s\S]*?(?=<section\b|<footer>)',spanish)
    if not match:
        raise ValueError('Missing Spanish section: '+identifier)
    figures[identifier] = re.findall(r'<figure[\s\S]*?</figure>',match.group())

commands = {
 'primer-usb': 'aguja status\naguja doctor\nlsblk -o NAME,SIZE,MODEL,FSTYPE,LABEL,MOUNTPOINTS',
 'ssh': 'ssh aguja@IP',
 'arranque': 'aguja profile unlock\naguja status',
 'ia-login': 'aguja login codex\naguja login claude\naguja login antigravity\nopencode auth login',
 'primer-diagnostico': 'aguja doctor\nlsblk -o NAME,SIZE,MODEL,SERIAL,FSTYPE,LABEL,MOUNTPOINTS\nfindmnt',
 'herramientas': 'aguja tools\naguja status --disks\naguja status --json\naguja context\naguja help',
}
versions = {'windows-bitlocker.png':'Windows · 0.8.1','linux-06-imagen-preparada.png':'Linux · 0.8.0','rescue-panel.png':'VM · 0.8.0','rescue-browser.png':'VM · 0.8.0','rescue-console.png':'VM · 0.8.0'}
synthetic = {'en':'Historical QA capture; example data. No real provider sign-in or inference is demonstrated.', 'fr':'Capture historique de test ; données d’exemple. Aucun vrai login fournisseur ni inférence démontrés.', 'de':'Historische QA-Aufnahme mit Beispieldaten; kein echter Anbieterlogin oder Inferenznachweis.', 'pt':'Captura histórica de teste com dados de exemplo; não prova login real ou inferência.', 'it':'Schermata storica di test con dati di esempio; non dimostra login reale o inferenza.', 'zh':'历史测试截图，使用示例数据；不代表真实提供商登录或推理。', 'nl':'Historische testopname met voorbeeldgegevens; geen bewijs van echte providerlogin of inferentie.'}

def translated_figures(identifier, lang, title):
    out=''
    for fig in figures[identifier]:
        img = re.search(r'<img[^>]+>',fig).group()
        img = re.sub(r'alt="[^"]*"',f'alt="{esc(title)}"',img)
        name = re.search(r'src="[^"]*/([^/"]+)"',img)[1]
        version = versions.get(name,'Linux · 0.9.0')
        out += f'<figure>{img}<figcaption>{version} · {esc(synthetic[lang])} {esc(CONTENT[lang]["docUI"][15])}</figcaption></figure>'
    return out

def common_header(lang, doc=False):
    c=CONTENT[lang]
    return f'<header'+(' class="doc-header"' if doc else '')+f'><a class="brand" href="/{lang}">{images[0]}<span>LA AGUJA<small>TRANSCENDENCEIA / RESCUE DISK</small></span></a><nav class="site-nav" aria-label="{esc(c["nav"][1])}"><a href="/{lang}#application">{esc(c["nav"][0])}</a><a href="/{lang}/docs">{esc(c["nav"][1])}</a><a href="{GH}">{esc(c["nav"][2])}</a></nav></header>'

def home_sections(lang):
    c = CONTENT[lang]
    body = ''
    for section in c['homeSections']:
        identifier = section['id']
        if not re.fullmatch(r'[a-z][a-z-]*', identifier):
            raise ValueError('Invalid home section ID: ' + identifier)
        body += f'<section class="meaning-section" id="{identifier}" aria-labelledby="heading-{identifier}"><h2 id="heading-{identifier}">{esc(section["title"])}</h2>'
        body += ''.join(f'<p class="meaning-copy">{esc(text)}</p>' for text in section['paragraphs'])
        if 'cards' in section:
            body += '<div class="meaning-grid">' + ''.join(
                f'<article><h3>{esc(title)}</h3><p>{esc(text)}</p></article>'
                for title, text in section['cards']) + '</div>'
        body += '</section>'
    body += f'<section class="meaning-section home-faq" id="questions" aria-labelledby="heading-questions"><h2 id="heading-questions">{esc(c["faqTitle"])}</h2>'
    body += ''.join(f'<details><summary>{esc(question)}</summary><p>{esc(answer)}</p></details>' for question, answer in c['faq'])
    return body + '</section>'

def skill_section(lang):
    s = CONTENT[lang]['imagerSkill']
    urls = [GH+'/releases/download/v0.9.2/aguja-flash-imager-skill-1.0.0.zip',
            GH+'/releases/download/v0.9.2/aguja-flash-imager-skill-1.0.0.tar.gz',
            GH+'/blob/main/skills/flash-imager/references/harnesses.md',
            GH+'/releases/download/v0.9.2/SHA256SUMS-flash-imager-skill-1.0.0']
    links = ''.join(f'<a href="{url}">{esc(label)} ↗</a>' for url,label in zip(urls,s['links']))
    return f'<section class="downloads" id="agent-skill"><span class="step">02 / AGENT SKILL · 1.0.0</span><h2>{esc(s["title"])}</h2><p>{esc(s["text"])}</p><div class="installer-links">{links}</div><p>{esc(s["note"])}</p></section>'

def home(lang):
    c=CONTENT[lang]
    hero=''.join(esc(x)+'<br>' for x in c['hero'][:2])+f'<span>{esc(c["hero"][2])}</span>'
    mascot = re.sub(r'alt="[^"]*"',f'alt="{esc(c["mascotAlt"])}"',images[1])
    installers=[(f'aguja-flash-imager-{IMAGER_VERSION}-win-x64.exe','Windows 10 / 11 (.exe)'),(f'aguja-flash-imager-{IMAGER_VERSION}-x86_64.AppImage','Linux AppImage'),(f'aguja-flash-imager-{IMAGER_VERSION}-amd64.deb','Debian / Ubuntu'),(f'aguja-flash-imager-{IMAGER_VERSION}-linux-x64.tar.gz',c['portable'])]
    links=''.join(f'<a href="{GH}/releases/download/{IMAGER_TAG}/{name}">{esc(label)} ↗</a>' for name,label in installers)
    imageurls=['/releases/aguja-0.9.0-amd64.img.zst','/releases/aguja-0.9.0-amd64.iso',GH+'/releases/download/v0.9.1/SHA256SUMS',GH+'/releases/tag/v0.9.1']
    return f'<!doctype html><html lang="{lang}"><head>{metadata(lang,"",c["siteTitle"],c["lead"])}<link rel="stylesheet" href="/assets/app.css"><link rel="stylesheet" href="/assets/meaning-20261008-v1.css">{icon}</head><body>{common_header(lang)}{language_nav(lang)}<main><section id="landing"><div class="landing-hero"><div class="hero-copy"><div class="eyebrow">{esc(c["eyebrow"])}</div><h1>{hero}</h1><p class="lead">{esc(c["lead"])}</p><div class="hero-actions"><a class="button-link" href="#application">{esc(c["actions"][0])} ↘</a><a class="button-link button-ghost" href="/{lang}/docs">{esc(c["actions"][1])} ↗</a></div><p class="hero-note">{esc(c["note"])}</p></div><aside class="needle-lab"><div class="panel-topline"><span>LA AGUJA / RESCUE DISK</span><i aria-hidden="true"></i></div><div class="needle-stage">{mascot}</div><div class="lab-caption"><span class="section-code">{esc(c["caption"][0])}</span><strong>{esc(c["caption"][1])}</strong><p>{esc(c["caption"][2])}</p></div></aside></div><div class="cards">'+''.join(f'<article><span class="step">{i+1:02}</span><h2>{esc(title)}</h2><p>{esc(text)}</p></article>' for i,(title,text) in enumerate(c['steps']))+f'</div>{home_sections(lang)}<section class="downloads" id="application"><span class="step">01 / FLASH IMAGER</span><h2>{esc(c["imagerTitle"])}</h2><p>{esc(c["imagerText"])}</p><div class="installer-links">{links}</div><p><a href="{GH}/releases/download/{IMAGER_TAG}/SHA256SUMS-imager-{IMAGER_VERSION}-windows">SHA-256 · Windows {IMAGER_VERSION}</a> · <a href="{GH}/releases/download/{IMAGER_TAG}/SHA256SUMS-imager-{IMAGER_VERSION}-linux">SHA-256 · Linux {IMAGER_VERSION}</a></p></section>{skill_section(lang)}<section class="downloads" id="images"><span class="step">03 / RESCUE DISK</span><h2>{esc(c["imagesTitle"])}</h2><p>{esc(c["imagesText"])}</p><div class="installer-links">'+''.join(f'<a href="{url}">{esc(label)}</a>' for url,label in zip(imageurls,c['imageLinks']))+f'</div><p>{esc(c["imageNote"])}</p></section>{donation_section(lang)}</section></main><footer><a href="https://www.transcendenceia.net">LA AGUJA / TRANSCENDENCEIA ↗</a><a href="/{lang}/privacy">{esc(c["privacy"])}</a><span>{esc(c["footer"])}</span></footer></body></html>'

def donation_section(lang):
    c=CONTENT[lang]['donation']
    return f'<section class="downloads" id="donate"><h2>{esc(c["title"])}</h2><p>{esc(c["message"])}</p><details><summary>{esc(c["title"])} · Ko-fi ↗</summary><img src="/assets/donation-qr.png" width="260" height="260" alt="Ko-fi QR"><p><a class="button-link" href="https://ko-fi.com/transcendenceia" target="_blank" rel="noopener noreferrer">Ko-fi · Transcendence IA ↗</a></p><p>{esc(c["optional"])}</p></details></section>'

def manual(lang):
    c=CONTENT[lang];ui=c['docUI']
    if lang=='es':
        head=metadata(lang,'/docs',c['docTitle'],c['docDescription']); head=head[head.index('<link rel=\"canonical\"'):]
        return spanish.replace('</head>',head+'</head>').replace('</header>','</header>'+language_nav(lang,'/docs'),1)
    sections=c['sections']
    if len(sections)!=26: raise ValueError(lang+' requires 26 sections')
    body=''
    for i,(identifier,section) in enumerate(zip(IDS,sections)):
        title,*paragraphs=section
        body+=f'<section id="{identifier}" class="doc-section"><span class="section-number">{i+1:02} / {esc(ui[7])}</span><h2 id="title-{identifier}">{esc(title)}</h2>'+''.join(f'<p>{esc(text)}</p>' for text in paragraphs)
        if identifier in commands: body+='<pre><code>'+esc(commands[identifier])+'</code></pre>'
        body+=translated_figures(identifier,lang,title)+'</section>'
    links=''.join(f'<a href="#{identifier}" data-doc-link>{esc(section[0])}</a>' for identifier,section in zip(IDS,sections))
    return f'<!doctype html><html lang="{lang}"><head>{metadata(lang,"/docs",c["docTitle"],c["docDescription"])}<link rel="icon" href="/assets/docs/agujita.png"><link rel="stylesheet" href="/assets/docs.css"><script src="/assets/docs.js?v=multilingual-20261008" defer></script></head><body><a class="skip-link" href="#manual">{esc(ui[0])}</a>{common_header(lang,True)}{language_nav(lang,"/docs")}<div class="doc-layout"><aside class="doc-sidebar"><button id="index-toggle" aria-expanded="false" aria-controls="doc-index">{esc(ui[1])} ↘</button><div id="doc-index"><span class="eyebrow">LA AGUJA / {IMAGER_VERSION} + 0.9.0</span><h1>{esc(ui[2])}</h1><label for="doc-search">{esc(ui[3])}</label><input id="doc-search" type="search" placeholder="SSH, BitLocker…" autocomplete="off"><p id="search-status" role="status" aria-live="polite">{esc(ui[4])}</p><nav aria-label="{esc(ui[1])}">{links}</nav></div></aside><main id="manual"><p class="locale-reference"><a href="/es/docs">{esc(ui[14])}</a></p>{body}<footer><a href="/{lang}#application">{esc(c["nav"][0])}</a> · <a href="{GH}">GitHub</a> · <a href="/{lang}/privacy">{esc(c["privacy"])}</a></footer></main></div><button id="print-guide" class="print-guide" type="button">{esc(ui[5])}</button><button id="back-top" class="back-top" aria-label="{esc(ui[6])}">↑</button></body></html>'

class MarkdownText(HTMLParser):
    def __init__(self): super().__init__();self.text=[];self.incode=False
    def handle_data(self,data): self.text.append(data)
    def handle_starttag(self,tag,attrs):
        if tag in ('p','h2','li'): self.text.append('\n\n')

for lang in LANGS:
    folder=PUBLIC / lang
    folder.mkdir(exist_ok=True)
    (folder/'index.html').write_text(home(lang))
    (folder/'docs.html').write_text(manual(lang))
    c=CONTENT[lang]
    (folder/'privacy.html').write_text(f'<!doctype html><html lang="{lang}"><head>{metadata(lang,"/privacy",c["privacy"]+" · LA AGUJA")}<link rel="stylesheet" href="/assets/theme.css"></head><body>{common_header(lang)}{language_nav(lang,"/privacy")}<main><h1>{esc(c["privacyTitle"])}</h1>'+''.join(f'<p>{esc(text)}</p>' for text in c['privacyParagraphs'])+f'<p><a href="{GH}/blob/main/NOTICE.md">GPL-3.0-or-later / NOTICE</a></p></main></body></html>')
    (ROOT/f'docs/{lang}').mkdir(exist_ok=True)
    if lang=='es':
        source=(ROOT/'docs/USER-GUIDE.es.md').read_text().replace('Imager 0.9.1','Imager 0.9.2').replace('https://aguja.transcendenceia.net/docs','https://aguja.transcendenceia.net/es/docs')
        (ROOT/'docs/es/USER-GUIDE.md').write_text(source)
    else:
        lines=[f'# {c["docTitle"]}',f'[Website]({ORIGIN}/{lang}/docs) · [English](../en/USER-GUIDE.md) · [Español](../es/USER-GUIDE.md)\n']
        for identifier,section in zip(IDS,c['sections']):
            lines += ['## '+section[0],*section[1:]]
            if identifier in commands: lines += ['```sh\n'+commands[identifier]+'\n```']
            lines += [f'[↗]({ORIGIN}/{lang}/docs#{identifier})']
        (ROOT/f'docs/{lang}/USER-GUIDE.md').write_text('\n\n'.join(lines)+'\n')

(PUBLIC/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{ORIGIN}/{lang}{suffix}</loc></url>' for lang in LANGS for suffix in ('','/docs','/privacy'))+'</urlset>')
print('Built 24 locale pages and 8 repository guides.')
