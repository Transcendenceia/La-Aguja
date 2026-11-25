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
CSS_HREF='/assets/launch-20261125-v2.css'
E=html.escape
BASE={l:json.loads((ROOT/f'server/locales/{l}.json').read_text()) for l in LANGS}
SOCIAL=json.loads((ROOT/'server/locales/social-images.json').read_text())
RELEASE=json.loads((ROOT/'server/locales/release-1.0.json').read_text())

ICONS={
 'usb':'<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="6" y="7" width="12" height="13" rx="2"/><path d="M9 7V3h6v4"/><path d="M10 12h4"/><path d="M10 15h4"/></svg>',
 'chip':'<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="7" y="7" width="10" height="10" rx="2"/><path d="M9 1v3M15 1v3M9 20v3M15 20v3M1 9h3M1 15h3M20 9h3M20 15h3"/></svg>',
 'imager':'<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="4" width="18" height="13" rx="2"/><path d="M8 21h8M12 17v4"/><path d="M9 10.5l2 2 4-4"/></svg>',
 'agent':'<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8 9l3 3-3 3"/><path d="M13 15h4"/><rect x="3" y="4" width="18" height="16" rx="2.5"/></svg>',
}

BRAND_SUB={
 'en':'TRANSCENDENCEIA / PORTABLE COMMAND POST',
 'es':'TRANSCENDENCEIA / PUESTO DE MANDO PORTÁTIL',
 'fr':'TRANSCENDENCEIA / POSTE DE COMMANDE PORTABLE',
 'de':'TRANSCENDENCEIA / TRAGBARER LEITSTAND',
 'pt':'TRANSCENDENCEIA / POSTO DE COMANDO PORTÁTIL',
 'it':'TRANSCENDENCEIA / POSTO DI COMANDO PORTATILE',
 'nl':'TRANSCENDENCEIA / DRAAGBARE COMMANDOPOST',
 'zh':'TRANSCENDENCEIA / 便携移动指挥站',
}

DECK={
 'en':{
  'title':'Four surfaces, one portable operations command',
  'lead':'LA AGUJA brings together bootable x86-64 Linux, pocket ESP32 tailnet bridges, a cross-platform desktop flasher and a headless agent skill—all running on your own hardware and private network.',
  'pillars':[
   ('usb','Rescue Disk · '+VERSION,'Bootable Linux + AI workbench','Start any x86-64 PC from clean hardware with Codex, Claude Code, Antigravity, OpenCode, QEMU/KVM, LUKS/BitLocker recovery and encrypted persistence.','Explore Rescue Disk','#images'),
   ('chip','IoT · ESP32 · v1.4.0','Pocket ESP32 tailnet nodes','Flash 11 ESP32-family boards into remote Tailscale/Headscale exit nodes, dynamic subnet routers and DNS relays with dual-OTA and REST/CLI hardware control.','Explore IoT ESP32','#iot-mcu'),
   ('imager','Flash Imager · '+IMAGER_VERSION,'One preparer for USB & MCU','Linux and Windows app with signed catalogue verification, reusable .aguja profiles, USB auto-detection for ESP32 chips and bundled esptool.exe (zero Python on Windows).','Download Flash Imager','#application'),
   ('agent','Agent Skill · '+SKILL_VERSION,'Headless automation for AI agents','Open Agent Skills package (Node 22+, no Electron) so Codex, Claude Code, OpenCode, Gemini CLI, Cursor or OpenClaw prepare .img or 48 KiB ESP32 NVS binaries.','Get Agent Skill','#agent-skill'),
  ],
  'topology':[
   ('1. Your workstation','Flash Imager 1.2.0 or Agent Skill 1.3.0 prepares verified media locally.'),
   ('2. Bootable USB (x86-64)','Boots independent Linux + AI tools directly on target hardware.'),
   ('3. ESP32 IoT node','Plugs into any USB power + Wi-Fi to bridge local networks remotely.'),
   ('4. Your Tailscale / Headscale','Direct private coordination under your own policies—zero LA AGUJA relay.'),
  ],
 },
 'es':{
  'title':'Cuatro piezas, un solo puesto de mando portátil',
  'lead':'LA AGUJA reúne un Linux arrancable para cualquier PC, nodos ESP32 de bolsillo para tu red privada, un grabador multiplataforma y una skill para agentes IA: todo sobre tu hardware y tu propia tailnet.',
  'pillars':[
   ('usb','Rescue Disk · '+VERSION,'Linux live + taller IA en USB','Arranca cualquier equipo x86-64 desde hardware limpio con Codex, Claude Code, Antigravity, OpenCode, QEMU/KVM, recuperación LUKS/BitLocker y persistencia cifrada.','Ver Rescue Disk','#images'),
   ('chip','IoT · ESP32 · v1.4.0','Nodos ESP32 en tu tailnet','Flashea 11 placas de la familia ESP32 como exit node, subnet router dinámico y DNS relay en tu Tailscale/Headscale, con doble OTA y control remoto por REST/CLI.','Ver IoT ESP32','#iot-mcu'),
   ('imager','Flash Imager · '+IMAGER_VERSION,'Un preparador para USB y MCU','App para Linux y Windows con catálogo firmado, perfiles .aguja reutilizables, detección real del chip ESP32 por USB y esptool.exe integrado (cero Python en Windows).','Descargar Flash Imager','#application'),
   ('agent','Agent Skill · '+SKILL_VERSION,'Automatización headless para agentes','Paquete abierto Agent Skills (Node 22+, sin Electron) para que Codex, Claude Code, OpenCode, Gemini CLI, Cursor u OpenClaw preparen imágenes .img o NVS v2 de 48 KiB.','Descargar Agent Skill','#agent-skill'),
  ],
  'topology':[
   ('1. Tu equipo','Flash Imager 1.2.0 o Agent Skill 1.3.0 preparan medios verificados en local.'),
   ('2. USB live (x86-64)','Arranca Linux independiente con agentes IA directo sobre el hardware.'),
   ('3. Nodo ESP32 IoT','Se conecta por Wi-Fi donde lo enchufes y abre puente a tu red privada.'),
   ('4. Tu Tailscale / Headscale','Control y tráfico bajo tus propias políticas, sin cuentas ni relay de LA AGUJA.'),
  ],
 },
 'fr':{
  'title':'Quatre surfaces, un poste de commande portable',
  'lead':'LA AGUJA réunit un Linux amorçable x86-64, des ponts ESP32 de poche pour votre tailnet, un préparateur multiplateforme et une skill pour agents IA, sur votre propre matériel et réseau privé.',
  'pillars':[
   ('usb','Rescue Disk · '+VERSION,'Linux live + atelier IA sur USB','Démarrez tout PC x86-64 avec Codex, Claude Code, Antigravity, OpenCode, QEMU/KVM, récupération LUKS/BitLocker et persistance chiffrée.','Voir Rescue Disk','#images'),
   ('chip','IoT · ESP32 · v1.4.0','Nœuds ESP32 dans votre tailnet','Flashez 11 cartes ESP32 en exit node, routeur de sous-réseau dynamique et relais DNS Tailscale/Headscale avec double OTA et CLI distante.','Voir IoT ESP32','#iot-mcu'),
   ('imager','Flash Imager · '+IMAGER_VERSION,'Un préparateur USB et MCU','Application Linux/Windows avec catalogue signé, profils .aguja réutilisables, détection USB ESP32 et esptool.exe intégré sans Python sous Windows.','Télécharger Flash Imager','#application'),
   ('agent','Agent Skill · '+SKILL_VERSION,'Préparation headless pour agents','Paquet Agent Skills (Node 22+, sans Electron) pour préparer des images .img ou des partitions NVS v2 48 Kio ESP32 depuis votre agent IA.','Télécharger Agent Skill','#agent-skill'),
  ],
  'topology':[
   ('1. Votre poste','Flash Imager 1.2.0 ou Agent Skill 1.3.0 prépare vos médias en local.'),
   ('2. Clé USB live (x86-64)','Démarre un Linux indépendant et ses agents IA sur le matériel cible.'),
   ('3. Nœud ESP32 IoT','Se branche sur alimentation USB + Wi-Fi pour relier le réseau local.'),
   ('4. Votre Tailscale / Headscale','Accès privé selon vos propres règles, sans compte ni relais LA AGUJA.'),
  ],
 },
 'de':{
  'title':'Vier Bausteine, ein tragbarer Leitstand',
  'lead':'LA AGUJA vereint bootfähiges x86-64-Linux, kompakte ESP32-Tailnet-Knoten, eine plattformübergreifende Imager-App und einen Agent-Skill — vollständig auf eigener Hardware und im eigenen Netz.',
  'pillars':[
   ('usb','Rescue Disk · '+VERSION,'Live-Linux + KI-Werkbank auf USB','Starte jeden x86-64-PC mit Codex, Claude Code, Antigravity, OpenCode, QEMU/KVM, LUKS/BitLocker-Werkzeugen und verschlüsselter Persistenz.','Rescue Disk ansehen','#images'),
   ('chip','IoT · ESP32 · v1.4.0','ESP32-Knoten für dein Tailnet','Flashe 11 ESP32-Boards als Exit-Node, dynamischen Subnetz-Router und DNS-Relay in deinem Tailscale/Headscale mit Dual-OTA und Fern-CLI.','IoT ESP32 ansehen','#iot-mcu'),
   ('imager','Flash Imager · '+IMAGER_VERSION,'Ein Werkzeug für USB und MCU','Linux- und Windows-App mit signiertem Katalog, .aguja-Profilen, USB-Chip-Erkennung und integriertem esptool.exe (ohne Python unter Windows).','Flash Imager laden','#application'),
   ('agent','Agent Skill · '+SKILL_VERSION,'Headless-Automatisierung für Agenten','Offenes Agent-Skills-Paket (Node 22+, ohne Electron) für personalisierte .img-Dateien und 48-KiB-ESP32-NVS-Partitionen.','Agent Skill laden','#agent-skill'),
  ],
  'topology':[
   ('1. Dein Arbeitsrechner','Flash Imager 1.2.0 oder Agent Skill 1.3.0 bereitet Medien lokal vor.'),
   ('2. Live-USB (x86-64)','Startet unabhängiges Linux mit KI-Agenten direkt auf der Hardware.'),
   ('3. ESP32-IoT-Knoten','Verbindet sich per WLAN und stellt einen Fernzugang im Zielnetz bereit.'),
   ('4. Dein Tailscale / Headscale','Direkte private Steuerung nach eigenen Regeln — ohne LA-AGUJA-Relay.'),
  ],
 },
 'pt':{
  'title':'Quatro peças, um posto de comando portátil',
  'lead':'LA AGUJA combina Linux arrancável x86-64 em USB, nós ESP32 de bolso para a tua rede privada, gravador multiplataforma e skill para agentes IA — tudo no teu hardware e tailnet própria.',
  'pillars':[
   ('usb','Rescue Disk · '+VERSION,'Linux live + oficina IA em USB','Arranca qualquer PC x86-64 com Codex, Claude Code, Antigravity, OpenCode, QEMU/KVM, recuperação LUKS/BitLocker e persistência cifrada.','Ver Rescue Disk','#images'),
   ('chip','IoT · ESP32 · v1.4.0','Nós ESP32 na tua tailnet','Grava 11 placas ESP32 como exit node, subnet router dinâmico e DNS relay no teu Tailscale/Headscale com duplo OTA e CLI remota.','Ver IoT ESP32','#iot-mcu'),
   ('imager','Flash Imager · '+IMAGER_VERSION,'Um preparador para USB e MCU','App Linux e Windows com catálogo assinado, perfis .aguja reutilizáveis, deteção USB de chips ESP32 e esptool.exe incluído sem Python no Windows.','Descarregar Flash Imager','#application'),
   ('agent','Agent Skill · '+SKILL_VERSION,'Automatização headless para agentes','Pacote aberto Agent Skills (Node 22+, sem Electron) para preparar imagens .img ou partições NVS v2 de 48 KiB para ESP32.','Descarregar Agent Skill','#agent-skill'),
  ],
  'topology':[
   ('1. O teu computador','Flash Imager 1.2.0 ou Agent Skill 1.3.0 prepara ficheiros verificados localmente.'),
   ('2. USB live (x86-64)','Inicia Linux independente com agentes IA diretamente no hardware.'),
   ('3. Nó ESP32 IoT','Liga-se por Wi-Fi onde for conectado e cria ponte para a tua rede privada.'),
   ('4. O teu Tailscale / Headscale','Coordenação privada sob as tuas políticas, sem contas nem relay LA AGUJA.'),
  ],
 },
 'it':{
  'title':'Quattro superfici, un posto di comando portatile',
  'lead':'LA AGUJA unisce Linux avviabile x86-64 su USB, nodi ESP32 tascabili per la tua tailnet, un preparatore multipiattaforma e una skill per agenti IA: tutto sul tuo hardware e sulla tua rete privata.',
  'pillars':[
   ('usb','Rescue Disk · '+VERSION,'Linux live + banco IA su USB','Avvia qualsiasi PC x86-64 con Codex, Claude Code, Antigravity, OpenCode, QEMU/KVM, recupero LUKS/BitLocker e persistenza cifrata.','Vedi Rescue Disk','#images'),
   ('chip','IoT · ESP32 · v1.4.0','Nodi ESP32 nella tua tailnet','Scrivi 11 schede ESP32 come exit node, subnet router dinamico e DNS relay su Tailscale/Headscale con doppio OTA e CLI remota.','Vedi IoT ESP32','#iot-mcu'),
   ('imager','Flash Imager · '+IMAGER_VERSION,'Un solo strumento per USB e MCU','App Linux e Windows con catalogo firmato, profili .aguja riutilizzabili, rilevamento USB del chip ESP32 ed esptool.exe integrato senza Python su Windows.','Scarica Flash Imager','#application'),
   ('agent','Agent Skill · '+SKILL_VERSION,'Automazione headless per agenti','Pacchetto aperto Agent Skills (Node 22+, senza Electron) per creare immagini .img o partizioni NVS v2 da 48 KiB per ESP32.','Scarica Agent Skill','#agent-skill'),
  ],
  'topology':[
   ('1. La tua postazione','Flash Imager 1.2.0 o Agent Skill 1.3.0 prepara i file verificati in locale.'),
   ('2. USB live (x86-64)','Avvia Linux indipendente con agenti IA direttamente sull’hardware.'),
   ('3. Nodo ESP32 IoT','Si collega al Wi-Fi dove lo alimenti e apre un ponte verso la tua rete.'),
   ('4. Il tuo Tailscale / Headscale','Accesso privato secondo le tue regole, senza account né relay LA AGUJA.'),
  ],
 },
 'nl':{
  'title':'Vier bouwstenen, één draagbare commandopost',
  'lead':'LA AGUJA combineert bootbare x86-64 Linux op USB, ESP32-tailnetnodes in zakformaat, een desktop-preparer en een headless agent-skill — volledig op je eigen hardware en privénetwerk.',
  'pillars':[
   ('usb','Rescue Disk · '+VERSION,'Live Linux + AI-werkbank op USB','Start elke x86-64 pc met Codex, Claude Code, Antigravity, OpenCode, QEMU/KVM, LUKS/BitLocker-herstel en versleutelde persistentie.','Bekijk Rescue Disk','#images'),
   ('chip','IoT · ESP32 · v1.4.0','ESP32-nodes in je tailnet','Flash 11 ESP32-boards als exit node, dynamische subnetrouter en DNS-relay voor Tailscale/Headscale met dubbele OTA en remote CLI.','Bekijk IoT ESP32','#iot-mcu'),
   ('imager','Flash Imager · '+IMAGER_VERSION,'Eén app voor USB en MCU','Linux- en Windows-app met gesigneerde catalogus, herbruikbare .aguja-profielen, USB-chipherkenning en ingebouwde esptool.exe (geen Python op Windows).','Download Flash Imager','#application'),
   ('agent','Agent Skill · '+SKILL_VERSION,'Headless voorbereiding voor agents','Open Agent Skills-pakket (Node 22+, zonder Electron) om .img-bestanden of 48 KiB ESP32 NVS-partities voor te bereiden.','Download Agent Skill','#agent-skill'),
  ],
  'topology':[
   ('1. Je werkstation','Flash Imager 1.2.0 of Agent Skill 1.3.0 bereidt bestanden lokaal voor.'),
   ('2. Live USB (x86-64)','Start onafhankelijke Linux met AI-agents rechtstreeks op de hardware.'),
   ('3. ESP32 IoT-node','Verbindt via wifi op locatie en overbrugt het lokale netwerk privé.'),
   ('4. Je eigen Tailscale / Headscale','Directe toegang onder jouw beleid — zonder LA AGUJA-relay of account.'),
  ],
 },
 'zh':{
  'title':'四大模块，构成一座随身移动指挥站',
  'lead':'LA AGUJA 将可启动的 x86-64 Linux、口袋级 ESP32 Tailnet 节点、跨平台烧录器与无界面 Agent Skill 融为一体——全部运行在你自己的硬件与私有网络中。',
  'pillars':[
   ('usb','Rescue Disk · '+VERSION,'可启动 Linux + AI 工作台','在任意 x86-64 电脑上独立启动，内置 Codex、Claude Code、Antigravity、OpenCode、QEMU/KVM、LUKS/BitLocker 工具与加密持久化。','查看 Rescue Disk','#images'),
   ('chip','IoT · ESP32 · v1.4.0','口袋级 ESP32 代理节点','将 11 款 ESP32 开发板烧录为 Tailscale/Headscale 出口节点、动态子网路由与 DNS 中继，支持双分区 OTA 与远程 REST/CLI 控制。','查看 IoT ESP32','#iot-mcu'),
   ('imager','Flash Imager · '+IMAGER_VERSION,'USB 与微控制器二合一准备工具','支持 Linux 与 Windows，提供签名目录校验、可复用 .aguja 配置、ESP32 USB 芯片自动探测及内置 esptool.exe（Windows 无需 Python）。','下载 Flash Imager','#application'),
   ('agent','Agent Skill · '+SKILL_VERSION,'AI 代理无界面自动化','开放 Agent Skills 格式（Node 22+，无需 Electron），让代理直接生成个性化 .img 或 48 KiB ESP32 NVS 分区文件。','获取 Agent Skill','#agent-skill'),
  ],
  'topology':[
   ('1. 你的工作机','Flash Imager 1.2.0 或 Agent Skill 1.3.0 在本地准备并校验文件。'),
   ('2. Live USB (x86-64)','直接从目标硬件启动独立 Linux 与 AI 代理工具。'),
   ('3. ESP32 IoT 节点','通电连入 Wi-Fi 即成为你私有网络中的远程边缘节点。'),
   ('4. 你的 Tailscale / Headscale','完全遵循你自己的访问策略，无 LA AGUJA 账户与中继。'),
  ],
 },
}

IOT_SECTION={
 'en':{'title':'LA AGUJA IoT · ESP32 family','text':'Flash supported ESP32 microcontrollers directly from Flash Imager (Linux and Windows, zero Python on Windows) into remote Tailscale/Headscale proxy nodes controllable by AI agents.','cards':[('11 ESP32 boards · auto-detect','ESP32-C6, ESP32-S3 (Octal/Std), ESP32-C3, ESP32 and ESP32-S2 with real USB chip detection and 6 prebuilt v1.4.0 firmwares.'),('Multi-Wi-Fi · SoftAP off by default','Up to 8 prioritized Wi-Fi networks, pure-JS ESP-IDF NVS v2 injection, serial boot check and 1-click flash erase.'),('Tailnet proxy & agent REST CLI','Exit node, dynamic upstream subnet router, DNS relay, dual-OTA rollback and remote hardware control via aguja-iot.py.')],'download':'Download Flash Imager 1.2.0','docs':'IoT architecture & boards','skillDocs':'Agent Skill IoT reference'},
 'es':{'title':'LA AGUJA IoT · Familia ESP32','text':'Flashea microcontroladores ESP32 compatibles desde Flash Imager (Linux y Windows, sin Python en Windows) para desplegar nodos proxy Tailscale/Headscale controlables por agentes IA.','cards':[('11 placas ESP32 · autodetección','ESP32-C6, ESP32-S3 (Octal/Std), ESP32-C3, ESP32 y ESP32-S2 con detección real del chip por USB y 6 firmwares v1.4.0 precompilados.'),('Multi-Wi-Fi · SoftAP desactivado','Hasta 8 redes Wi-Fi con prioridad, generador NVS v2 en JS puro, verificación serie al arrancar y borrado de flash en 1 clic.'),('Proxy tailnet y CLI para agentes','Exit node, subnet router dinámico, DNS relay, doble partición OTA y control remoto de hardware con aguja-iot.py.')],'download':'Descargar Flash Imager 1.2.0','docs':'Arquitectura IoT y placas','skillDocs':'Referencia IoT de la Agent Skill'},
 'fr':{'title':'LA AGUJA IoT · Famille ESP32','text':'Flashez des microcontrôleurs ESP32 depuis Flash Imager (Linux et Windows, sans Python sous Windows) en nœuds proxy Tailscale/Headscale contrôlables par vos agents IA.','cards':[('11 cartes ESP32 · détection auto','ESP32-C6, ESP32-S3, ESP32-C3, ESP32 et ESP32-S2 avec détection USB réelle de la puce et 6 firmwares v1.4.0 précompilés.'),('Multi-Wi-Fi · SoftAP désactivé','Jusqu’à 8 réseaux Wi-Fi prioritaires, génération NVS v2 en JS pur, vérification série au démarrage et effacement flash en 1 clic.'),('Proxy tailnet et CLI agent','Exit node, routeur de sous-réseau dynamique, relais DNS, double OTA et contrôle matériel distant via aguja-iot.py.')],'download':'Télécharger Flash Imager 1.2.0','docs':'Architecture IoT et cartes','skillDocs':'Référence IoT Agent Skill'},
 'de':{'title':'LA AGUJA IoT · ESP32-Familie','text':'Flashe unterstützte ESP32-Mikrocontroller direkt mit Flash Imager (Linux und Windows, ohne Python unter Windows) zu Tailscale/Headscale-Proxy-Knoten für KI-Agenten.','cards':[('11 ESP32-Boards · Auto-Erkennung','ESP32-C6, ESP32-S3, ESP32-C3, ESP32 und ESP32-S2 mit echter USB-Chip-Erkennung und 6 fertigen v1.4.0-Firmwares.'),('Multi-WLAN · SoftAP standardmäßig aus','Bis zu 8 priorisierte WLANs, reiner JS-NVS-v2-Generator, serielle Boot-Prüfung und Flash-Löschen per Klick.'),('Tailnet-Proxy & Agent-CLI','Exit-Node, dynamischer Subnetz-Router, DNS-Relay, Dual-OTA und Fernsteuerung per aguja-iot.py.')],'download':'Flash Imager 1.2.0 herunterladen','docs':'IoT-Architektur & Boards','skillDocs':'Agent-Skill IoT-Referenz'},
 'pt':{'title':'LA AGUJA IoT · Família ESP32','text':'Grave microcontroladores ESP32 diretamente no Flash Imager (Linux e Windows, sem Python no Windows) como nós proxy Tailscale/Headscale controláveis por agentes IA.','cards':[('11 placas ESP32 · deteção automática','ESP32-C6, ESP32-S3, ESP32-C3, ESP32 e ESP32-S2 com deteção real por USB e 6 firmwares v1.4.0 pré-compilados.'),('Multi-Wi-Fi · SoftAP desativado','Até 8 redes Wi-Fi prioritárias, gerador NVS v2 em JS puro, verificação série no arranque e limpeza de flash num clique.'),('Proxy tailnet e CLI para agentes','Exit node, subnet router dinâmico, DNS relay, duplo OTA e controlo remoto de hardware via aguja-iot.py.')],'download':'Descarregar Flash Imager 1.2.0','docs':'Arquitetura IoT e placas','skillDocs':'Referência IoT da Agent Skill'},
 'it':{'title':'LA AGUJA IoT · Famiglia ESP32','text':'Scrivi il firmware su microcontrollori ESP32 direttamente da Flash Imager (Linux e Windows, senza Python su Windows) per creare nodi proxy Tailscale/Headscale controllabili da agenti IA.','cards':[('11 schede ESP32 · rilevamento auto','ESP32-C6, ESP32-S3, ESP32-C3, ESP32 ed ESP32-S2 con rilevamento USB del chip e 6 firmware v1.4.0 precompilati.'),('Multi-Wi-Fi · SoftAP disattivato','Fino a 8 reti Wi-Fi in ordine di priorità, generatore NVS v2 in JS puro, verifica seriale all’avvio e cancellazione flash in 1 clic.'),('Proxy tailnet e CLI per agenti','Exit node, subnet router dinamico, DNS relay, doppio OTA e controllo remoto hardware con aguja-iot.py.')],'download':'Scarica Flash Imager 1.2.0','docs':'Architettura IoT e schede','skillDocs':'Riferimento IoT Agent Skill'},
 'nl':{'title':'LA AGUJA IoT · ESP32-familie','text':'Flash ondersteunde ESP32-microcontrollers rechtstreeks met Flash Imager (Linux en Windows, zonder Python op Windows) naar Tailscale/Headscale-proxynodes voor AI-agents.','cards':[('11 ESP32-boards · auto-detectie','ESP32-C6, ESP32-S3, ESP32-C3, ESP32 en ESP32-S2 met echte USB-chipherkenning en 6 voorgebouwde v1.4.0-firmwares.'),('Multi-Wi-Fi · SoftAP standaard uit','Tot 8 geprioriteerde wifi-netwerken, pure JS NVS v2-generator, seriële opstartcheck en flash wissen met 1 klik.'),('Tailnet-proxy en agent-CLI','Exit node, dynamische subnetrouter, DNS-relay, dubbele OTA en afstandsbediening via aguja-iot.py.')],'download':'Flash Imager 1.2.0 downloaden','docs':'IoT-architectuur & boards','skillDocs':'Agent Skill IoT-referentie'},
 'zh':{'title':'LA AGUJA IoT · ESP32 系列','text':'直接使用 Flash Imager（Linux 与 Windows，Windows 无需 Python）烧录 ESP32 微控制器，将其变为可由 AI 代理控制的 Tailscale/Headscale 代理节点。','cards':[('11 款 ESP32 开发板 · 自动识别','支持 ESP32-C6、ESP32-S3、ESP32-C3、ESP32 与 ESP32-S2，支持真实 USB 芯片探测及 6 套预编译 v1.4.0 固件。'),('多 Wi-Fi · 默认关闭 SoftAP','最多 8 个按优先级排序的 Wi-Fi、纯 JS NVS v2 生成器、串口启动校验与一键清空闪存。'),('Tailnet 代理与代理 REST CLI','出口节点、动态上游子网路由、DNS 中继、双分区 OTA 回滚与 aguja-iot.py 远程硬件控制。')],'download':'下载 Flash Imager 1.2.0','docs':'IoT 架构与开发板','skillDocs':'Agent Skill IoT 参考'},
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
 title=('LA AGUJA · '+c['hero'][0]+' '+c['hero'][1]) if not suffix else current(b['docTitle'])+f' · {VERSION}'
 desc=c['lead'] if not suffix else current(b['docDescription']);canonical=ORIGIN+'/'+l+suffix
 return f'<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="dark"><title>{E(title)}</title><meta name="description" content="{E(desc)}"><link rel="canonical" href="{canonical}">'+''.join(f'<link rel="alternate" hreflang="{x}" href="{ORIGIN}/{x}{suffix}">' for x in LANGS)+f'<link rel="alternate" hreflang="x-default" href="{ORIGIN}/en{suffix}"><meta property="og:type" content="website"><meta property="og:site_name" content="LA AGUJA"><meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{canonical}"><meta property="og:image" content="{image_url}"><meta property="og:image:secure_url" content="{image_url}"><meta property="og:image:type" content="image/png"><meta property="og:image:width" content="{image["width"]}"><meta property="og:image:height" content="{image["height"]}"><meta property="og:image:alt" content="{E(image["alt"])}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{E(title)}"><meta name="twitter:description" content="{E(desc)}"><meta name="twitter:image" content="{image_url}"><meta name="twitter:image:alt" content="{E(image["alt"])}"><link rel="icon" href="/assets/docs/agujita.png"><link rel="stylesheet" href="{CSS_HREF}"><script src="/assets/launch-20261009-v1.js" defer></script>'
def header(l,c,b,suffix):
 return f'<a class="skip-link" href="#main">{E(c["ui"]["skip"])}</a><div class="site-shell-top"><header class="site-header"><a class="brand" href="/{l}"><img src="/assets/docs/agujita.png" width="42" height="42" alt="Agujita"><span>LA AGUJA<small>{E(BRAND_SUB[l])}</small></span></a><nav class="site-nav" aria-label="{E(b["nav"][1])}"><a href="/{l}#iot-mcu">IoT ESP32</a><a href="/{l}/docs">{E(b["nav"][1])}</a><a href="{GH}">GitHub ↗</a><a href="/{l}#donate">{E(b["donation"]["title"])}</a><a class="nav-cta" href="/{l}#application">{E(b["nav"][0])}</a></nav></header><nav class="language-nav" aria-label="Language / Idioma">'+''.join(f'<a href="/{x}{suffix}" lang="{x}" hreflang="{x}"'+(' aria-current="page"' if x==l else '')+f'>{BASE[x]["name"]}</a>' for x in LANGS)+'</nav></div>'
def page(l,c,b,body,suffix=''):
 ui=' '.join(f'data-{k}="{E(c[k])}"' for k in ['copy','copied','close','zoom'])+' '+ ' '.join(f'data-{key}="{E(c[value])}"' for key,value in [('copy-fallback','copyFallback'),('search-matches','searchMatches'),('no-matches','noMatches'),('check-progress','checkProgress')])
 return f'<!doctype html><html lang="{l}"><head>{head(l,c,b,suffix)}</head><body {ui}>{header(l,c,b,suffix)}<main><div id="main">{body}</div></main><footer><a href="https://www.transcendenceia.net">LA AGUJA / TRANSCENDENCEIA ↗</a><a href="/{l}/privacy">{E(b["privacy"])}</a><span>{E(b["footer"])}</span></footer></body></html>\n'
def planner(c):
 return f'<section class="planner" id="plan"><h2>{E(c["plannerTitle"])}</h2><p>{E(c["plannerNote"])}</p><div class="planner-controls" hidden><label for="situation">{E(c["choose"])}</label><select id="situation"><option value="all">{E(c["allPlans"])}</option>'+''.join(f'<option value="plan-{i}">{E(p["title"])}</option>' for i,p in enumerate(c['plans']))+'</select></div><div class="plan-grid">'+''.join(f'<article class="plan-card" id="plan-{i}" data-plan><span class="number">0{i+1}</span><h3>{E(p["title"])}</h3><p>{E(p["intro"])}</p><ol>'+''.join('<li>'+E(s)+'</li>' for s in p['steps'])+f'</ol><p class="stop"><strong>{E(c["stop"])}</strong> {E(p["stop"])}</p></article>' for i,p in enumerate(c['plans']))+'</div></section>'
def cases(c):return '<div class="case-grid">'+''.join('<article><span class="case-tag">'+E(tag)+'</span><h3>'+E(title)+'</h3><p>'+E(body)+'</p></article>' for tag,title,body in c['cases'])+'</div>'
def checklist(c):return '<fieldset class="checklist"><legend>'+E(c['checkTitle'])+'</legend><p>'+E(c['checkNote'])+'</p>'+''.join(f'<label><input type="checkbox" name="check-{i}"><span>{E(s)}</span></label>' for i,s in enumerate(c['checks']))+'<p class="check-status" role="status" aria-live="polite"></p></fieldset>'
def figure(c,name):return f'<figure><a class="zoom-image" href="/assets/docs/099/{name}.png" aria-label="{E(c["zoom"]+": "+c["figures"][name])}"><img src="/assets/docs/099/{name}.png" loading="lazy" decoding="async" alt="{E(c["figures"][name])}"></a><figcaption><strong>{E(c["figures"][name])}</strong> · {E(c["captureNote"])} <span>{E(c["zoom"])}</span></figcaption></figure>'
def deck_section(l):
 d=DECK[l]
 cards=''.join(f'<article class="pillar-card"><div class="pillar-top"><span class="pillar-icon">{ICONS[icon]}</span><span class="pillar-meta">{E(meta)}</span></div><h3>{E(title)}</h3><p>{E(text)}</p><a class="pillar-link" href="{href}">{E(cta)} →</a></article>' for icon,meta,title,text,cta,href in d['pillars'])
 topo=''.join(f'<div class="topology-node"><strong>{E(t)}</strong><span>{E(desc)}</span></div>' for t,desc in d['topology'])
 return f'<section class="command-deck" id="command-deck"><h2>{E(d["title"])}</h2><p class="lead">{E(d["lead"])}</p><div class="pillar-grid">{cards}</div><div class="topology" aria-label="{E(d["title"])}">{topo}</div></section>'
def home(l,c,b):
 c["imageText"]=RELEASE[l]["image"]
 release=RELEASE[l]
 release_label={'en':'Complete release notes','es':'Lista completa de cambios','fr':'Notes de version complètes','de':'Vollständige Versionshinweise','pt':'Lista completa de alterações','it':'Note di rilascio complete','nl':'Volledige versieopmerkingen','zh':'完整版本说明'}[l]
 body=f'<section class="hero"><div><h1>{E(c["hero"][0])}<br><span>{E(c["hero"][1])}</span></h1><p class="lead">{E(c["lead"])}</p><div class="actions"><a class="button" href="#application">{E(b["actions"][0])} ↘</a><a class="button secondary" href="/{l}/docs">{E(c["ui"]["readGuide"])} →</a></div><p class="micro">{E(c["ui"]["heroNote"])}</p></div><figure class="hero-art"><img src="/assets/hero-recovery-20261009-v1.webp" width="1200" height="800" alt="{E(b["recoveryAlt"])}" fetchpriority="high"><figcaption>{E(b["caption"][1])}</figcaption></figure></section>'
 body+=f'<div class="trust-strip"><span>Flash Imager <strong>{IMAGER_VERSION}</strong></span><span>Rescue Disk <strong>{VERSION}</strong></span><span>IoT ESP32 <strong>v1.4.0</strong></span><span>Agent Skill <strong>{SKILL_VERSION}</strong></span></div>'
 body+=deck_section(l)
 body+=f'<section id="version-1"><div class="section-head"><h2>{E(release["title"])}</h2><span class="version-tag">Rescue Disk {VERSION}</span></div>'+paras(release['intro'])+'<div class="feature-grid">'+''.join('<article><h3>'+E(t)+'</h3><p>'+E(p)+'</p></article>' for t,p in release['features'])+f'</div><p class="meta-links"><a href="{GH}/releases/tag/v{VERSION}">{E(release_label)} · {VERSION} ↗</a> · <a href="/{l}/docs#reinicios">{E(c["ui"]["readGuide"])} →</a></p></section>'
 body+=f'<section class="intro"><h2>{E(c["introTitle"])}</h2>'+paras(c['intro'])+'</section><div class="feature-grid">'+''.join(f'<article><span class="number">0{i+1}</span><h3>{E(title)}</h3><p>{E(text)}</p></article>' for i,(title,text) in enumerate(b['steps']))+'</div>'+planner(c)+f'<section id="possibilities"><h2>{E(c["casesTitle"])}</h2><p>{E(c["casesNote"])}</p>'+cases(c)+f'</section><section class="boundary"><h2>{E(c["boundaryTitle"])}</h2>'+paras(c['boundaries'])+f'</section>'
 files=[('win-x64.exe','Windows 10 / 11 · EXE'),('x86_64.AppImage','Linux · AppImage'),('amd64.deb','Debian / Ubuntu · DEB'),('linux-x64.tar.gz',b['portable'])]
 body+=f'<section class="download-band" id="application"><div class="section-head"><h2>{E(b["imagerTitle"])}</h2><span class="version-tag">Flash Imager {IMAGER_VERSION}</span></div><p>{E(c["downloadText"])}</p><div class="installer-links">'+''.join(f'<a href="{GH}/releases/download/v{IMAGER_VERSION}/aguja-flash-imager-{IMAGER_VERSION}-{file}"><span>{E(label)}</span><span aria-hidden="true">↗</span></a>' for file,label in files)+f'</div><p class="meta-links"><a href="{GH}/releases/download/v{IMAGER_VERSION}/SHA256SUMS-imager-{IMAGER_VERSION}-windows">SHA-256 · Windows</a> · <a href="{GH}/releases/download/v{IMAGER_VERSION}/SHA256SUMS-imager-{IMAGER_VERSION}-linux">SHA-256 · Linux</a> · <a href="/{l}/docs#primer-usb">{E(c["ui"]["firstUsb"])} →</a></p></section>'
 s=b['imagerSkill'];d=b['donation']
 urls=[GH+f'/releases/download/{SKILL_TAG}/aguja-flash-imager-skill-{SKILL_VERSION}.zip',GH+f'/releases/download/{SKILL_TAG}/aguja-flash-imager-skill-{SKILL_VERSION}.tar.gz',GH+f'/blob/main/skills/flash-imager/references/harnesses.md',GH+f'/releases/download/{SKILL_TAG}/SHA256SUMS-flash-imager-skill-{SKILL_VERSION}']
 body+=f'<section class="download-band" id="agent-skill"><div class="section-head"><h2>{E(s["title"])}</h2><span class="version-tag">Agent Skill {SKILL_VERSION}</span></div><p>{E(s["text"])}</p><div class="installer-links">'+''.join(f'<a href="{u}"><span>{E(label)}</span><span aria-hidden="true">↗</span></a>' for u,label in zip(urls,s['links']))+f'</div><p class="meta-links">{E(s["note"])}</p></section>'
 iot=IOT_SECTION[l]
 body+=f'<section id="iot-mcu"><div class="iot-panel"><div class="section-head"><h2>{E(iot["title"])}</h2><span class="version-tag">ESP32 · v1.4.0</span></div><p>{E(iot["text"])}</p><div class="feature-grid">'+''.join('<article><h3>'+E(t)+'</h3><p>'+E(p)+'</p></article>' for t,p in iot['cards'])+f'</div><div class="installer-links"><a href="#application"><span>{E(iot["download"])}</span><span aria-hidden="true">↑</span></a><a href="{GH}/blob/main/iot/README.md"><span>{E(iot["docs"])}</span><span aria-hidden="true">↗</span></a><a href="{GH}/blob/main/skills/flash-imager/references/iot.md"><span>{E(iot["skillDocs"])}</span><span aria-hidden="true">↗</span></a></div></div></section>'
 body+=f'<section class="download-band" id="images"><div class="section-head"><h2>{E(b["imagesTitle"])}</h2><span class="version-tag">Rescue Disk {VERSION}</span></div><p>{E(c["imageText"])}</p><div class="installer-links">'
 image_base=json.loads((ROOT/'config/image-hosting.json').read_text()).get(VERSION,GH+f'/releases/download/v{VERSION}/')
 if image_base not in ('https://aguja.transcendenceia.net/releases/',GH+f'/releases/download/v{VERSION}/'):raise ValueError('Unexpected image download origin')
 urls=[image_base+f'aguja-{VERSION}-amd64.img.zst',image_base+f'aguja-{VERSION}-amd64.iso',GH+f'/releases/download/v{VERSION}/SHA256SUMS',GH+f'/releases/tag/v{VERSION}']
 body+=''.join(f'<a href="{u}"><span>{E(label)}</span></a>' for u,label in zip(urls,b['imageLinks']))+f'</div></section><section id="questions"><h2>{E(b["faqTitle"])}</h2>'+''.join('<details><summary>'+E(q)+'</summary><p>'+E(a)+'</p></details>' for q,a in b['faq'])+f'</section><section id="donate"><div class="support-heading"><img src="/assets/support-icon.svg" width="48" height="48" alt=""><h2>{E(d["title"])}</h2></div><p>{E(d["message"])}</p><details><summary>Ko-fi · {E(d["title"])}</summary><img class="support-qr" src="/assets/donation-qr.png" width="260" height="260" alt="Ko-fi QR"><p><a href="https://ko-fi.com/transcendenceia" target="_blank" rel="noopener noreferrer">Ko-fi · Transcendence IA ↗</a></p><p>{E(d["optional"])}</p></details></section>'
 return page(l,c,b,body)
def reviewed(s,c):
 for old,new in c.get("replacements",[]):s=s.replace(old,new)
 return current(s)
def docs(l,c,b):
 release=RELEASE[l]
 for n,section in release['sections'].items(): b['sections'][int(n)]=section
 b['sections'][13][0]=release['create']
 body=f'<section class="guide-intro"><div class="section-head"><h1>{E(b["docUI"][2])}</h1><span class="version-tag">Rescue {VERSION} · Imager {IMAGER_VERSION}</span></div><p class="lead">{E(current(b["docDescription"]))}</p><p>{E(c["docNote"])}</p><div class="actions"><a class="button" href="#primer-usb">{E(c["ui"]["firstUsb"])} ↓</a><button class="secondary print-guide" type="button" hidden>{E(c["ui"]["print"])}</button></div></section><div class="guide-layout"><aside class="contents"><details open><summary>{E(c["ui"]["contents"])}</summary><div class="search-controls" hidden><label for="doc-search">{E(c["ui"]["search"])}</label><input type="search" id="doc-search" placeholder="SSH, BitLocker, ENOSPC…"><p id="search-status" role="status" aria-live="polite"></p></div><nav aria-label="{E(c["ui"]["contents"])}">'+''.join(f'<a data-doc-link href="#{i}">{n+1:02} · {E(s[0])}</a>' for n,(i,s) in enumerate(zip(IDS,b['sections'])))+'</nav></details></aside><div class="chapters">'
 assert len(b['sections'])==26
 for n,(i,s) in enumerate(zip(IDS,b['sections'])):
  ps=[reviewed(p,c) for p in s[1:] if not re.search(r'0\.8\.[01]',p)]
  content=paras(s[1:]) if str(n) in release['sections'] else (reviewed(ES_BODIES[i],c) if l=='es' else paras(ps))
  if n==0:content=paras(c['intro'])
  body+=f'<section class="doc-section" id="{i}"><span class="chapter-index">{n+1:02} / 26</span><h2>{E(s[0])}</h2>'+content+paras(c['additions'].get(str(n),[]))
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
