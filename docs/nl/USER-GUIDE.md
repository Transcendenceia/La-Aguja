# Gebruikershandleiding · LA AGUJA

[Website](https://aguja.transcendenceia.net/nl/docs) · [English](../en/USER-GUIDE.md) · [Español](../es/USER-GUIDE.md)


## Een lanceerplatform, niet alleen een reddingsboei.

Geef een geavanceerde agent een doel, niet alleen een reparatiecommando. Hij kan hardware analyseren, tools kiezen, scripts maken en uitvoeren binnen je toestemming en resultaten controleren. Het geïnstalleerde systeem hoeft niet te starten of zelfs te bestaan.

De live-sessie gebruikt een schrijfbare RAM-laag boven het alleen-lezen USB-image. Dit is Linux, geen firmware; niet de hele USB wordt naar RAM gekopieerd. Interne schijven blijven bij het starten onaangeroerd; jij kiest wanneer je erop schrijft.

Inbegrepen: AI-clients met root-toegang, SSH, Python, Git, schijfhulpmiddelen, debootstrap en arch-install-scripts. Breid uit met geschikte pakketten: QEMU/KVM, container-engines en build-tools vereisen extra installatie, genoeg RAM/opslag en geschikte hardware. Sla belangrijke resultaten bewust op; RAM is tijdelijk. Cloud-AI vereist netwerk en je eigen account; er is geen lokaal model inbegrepen.

[↗](https://aguja.transcendenceia.net/nl/docs#que-es)

## Je eerste USB

Maak een kopie van een voldoende grote USB. Download Imager en kies het image uit de ondertekende catalogus. Laat Ethernet op DHCP, stel taal/toetsenbord/naam en eigen SSH-wachtwoord of publieke sleutel in. AI en privénetwerk mogen uit blijven. Versleutel profielen met geheimen en bewaar de ontgrendelzin buiten USB. Vergelijk model, capaciteit en serienummer vóór schrijven. Wacht op terugleescontrole, start USB en ontgrendel indien nodig. Het paneel zien en schijven herkennen volstaat voor deze eerste test.

```sh
aguja status
aguja doctor
lsblk -o NAME,SIZE,MODEL,FSTYPE,LABEL,MOUNTPOINTS
```

[↗](https://aguja.transcendenceia.net/nl/docs#primer-usb)

## Belangrijke begrippen

Live betekent starten zonder installatie. Configureerbare IMG en boot-ISO zijn in de Imager niet uitwisselbaar. Schijf, partitie en aankoppelen zijn verschillend; /dev/sda kan veranderen. DHCP deelt adressen uit; SSH geeft een versleutelde console met servervingerafdruk. Root/sudo is beheer, geen alleen-lezen-sandbox. Registratiesleutel, API-sleutel, SSH-wachtwoord en profielzin hebben andere rollen. SHA-256 controleert bytes, niet opstartbaarheid. De profielzin opent geen BitLocker/LUKS.

[↗](https://aguja.transcendenceia.net/nl/docs#glosario)

## Vooraf: hardware, toestemming en kopie

Controleer x86-64, USB-boot en firmware. BIOS/UEFI zijn voorzien; ARM, alle wifi-chips en universeel ondertekend Secure Boot niet gegarandeerd. Verkrijg toestemming voor computer en gegevens. Kies een ander hersteldoel; overweeg bij onstabiele schijven eerst een image. Schrijven vervangt USB-inhoud. Windows heeft nog geen ingebouwde USB-back-up: gebruik extern gereedschap. Linux heeft een optionele gecontroleerde volledige kopie, standaard uit, met benodigde ruimte/rechten. Dit kopieert niet de interne schijf. BitLocker/LUKS vereisen de sleutel van de eigenaar.

[↗](https://aguja.transcendenceia.net/nl/docs#preparacion)

## Imager downloaden en openen

Kies officiële Windows-10/11-EXE, AppImage, Debian/Ubuntu-DEB of draagbaar Linux-archief. Controleer SHA-256 en open op de voorbereidings-pc. EXE/AppImage zijn geen USB-herstelimages. Geen LA AGUJA-account. De EXE heeft geen erkende Authenticode-handtekening; AppImage kan uitvoerrechten nodig hebben. Schrijven vereist lokale rechtenverhoging. Een geopende toepassing bewijst geen voorbereide of opstartbare USB.

[↗](https://aguja.transcendenceia.net/nl/docs#descargas)

## Stap 1 · Image kiezen

Gebruik ondertekende catalogus of lokale .img. Ed25519 en hashes worden gecontroleerd en delen samengevoegd. Pak .img.zst uit voor handmatige import. Private voorbereiding maakt een nieuw bestand, niet een wijziging van het openbare image. Imager 0.9.2, herstelimage 0.9.0. Opties hangen af van imagefuncties; zonder tailscale-profile-v1 wordt voorbereiding met privénetwerk geweigerd. Controleer echte capaciteit, niet alleen het etiket.

[↗](https://aguja.transcendenceia.net/nl/docs#imagen)

## Stap 2 · Netwerk, taal, naam

Kies live-taal, toetsenbord en variant; de Imager-taal is onafhankelijk. Gebruik een herkenbare hostnaam. Ethernet DHCP maakt de eerste start eenvoudiger. Opgeslagen wifi wordt gebruikt; zonder netwerk is er interactieve selectie. Wifi-import kan lokale toestemming vragen. Bedrijfswifi/captive portals vereisen soms handmatige NetworkManager-instelling. Controleer verbinding, DNS, HTTPS en tijd afzonderlijk. Lokale diagnose kan offline.

[↗](https://aguja.transcendenceia.net/nl/docs#red)

## Stap 3 · SSH

Gebruik een uniek wachtwoord of toegestane publieke sleutel, nooit een privésleutel. Standaardpoort 22; gebruik echte IP en vergelijk vingerafdruk. Andere poort vervangt geen authenticatie. Fabrieksgebruiker en openbaar wachtwoord: aguja. Eigen wachtwoord gaat voor; leeg met publieke sleutel geeft alleen sleuteltoegang, zonder sleutel blijft fabriekslogin. Onbeperkt sudo. aguja password bewaart op USB; sudo passwd aguja wijzigt alleen de sessie.

```sh
ssh aguja@IP
```

[↗](https://aguja.transcendenceia.net/nl/docs#ssh)

## Stap 4 · AI voorbereiden

Codex CLI, OpenCode, Claude Code en Antigravity: API-sleutel, selectieve import van compatibele draagbare sessie of login na starten. Installatiecontrole bewijst geen login of inferentie. Geen volledige sleutelbos, geschiedenis, hooks of MCP gekopieerd. Sessies kunnen verlopen zijn. Kosten, quota en gegevens hangen van aanbieder af. USB kan zonder AI-gegevens voorbereid worden; cloud-AI wordt niet offline beloofd.

[↗](https://aguja.transcendenceia.net/nl/docs#ia-preparacion)

## Stap 5 · Eigen Tailscale/Headscale

Optioneel: schakel privénetwerk in, geef toegestane auth/pre-auth-sleutel en optionele nodenaam. Lege Headscale-URL gebruikt officieel Tailscale; anders eigen HTTPS-server. Het live meldt aan na netwerk/ontgrendeling, niet de voorbereidings-pc. Client moet in het toegestane netwerk zitten en beleid volgen. Registratiesleutel is geen SSH-wachtwoord. Aanmelding bewijst geen ACL: test echt SSH. Identiteit in RAM, nieuwe aanmelding na herstart.

[↗](https://aguja.transcendenceia.net/nl/docs#tailnet)

## OpenSSH versus Tailscale SSH

Standaard is OpenSSH over het privénetwerk: wachtwoorden/sleutels, vingerafdruk en netwerk-ACLs blijven nodig. Tailscale SSH is geavanceerd, met serverondersteuning en expliciet SSH-beleid. Scheid registratie, bereikbaarheid, TCP-poort en authenticatie. Open geen publieke poorten en verruim ACLs niet om loginproblemen te verbergen. Raadpleeg documentatie van werkelijk gebruikte versies.

[↗](https://aguja.transcendenceia.net/nl/docs#politicas)

## Geheimen en versleuteling

Profielen kunnen wifi-, SSH-, AI- en registratiesleutels bevatten. Versleutel de capsule, bewaar de zin apart en ontgrendel lokaal voor laden. .aguja-sjablonen en kopieën zijn ook gevoelig. Niet heel AGUJA_DATA versleuteld, geen bescherming tegen root na ontgrendelen. persistent_home=no verliest HOME/tokens na herstart; yes bewaart ongecodeerd. Platte aguja.conf is fysiek leesbaar. Publiceer geen private images of sleutels.

[↗](https://aguja.transcendenceia.net/nl/docs#secretos)

## Windows · BitLocker

Linux starten verwijdert BitLocker niet. Vraag de juiste volumesleutel aan de eigenaar. Profielzin en SSH-wachtwoord zijn geen BitLocker-sleutels. LA AGUJA omzeilt versleuteling niet. Windows Imager kan beschikbare sleutels bekijken en expliciet gekozen sleutels in private image opnemen. Bescherm profiel en bewaar andere kopie. Een sleutel zien bewijst geen ontgrendeld volume. Windows-screenshot is historische 0.8.1, geen nieuwe native 0.9.2-test.

[↗](https://aguja.transcendenceia.net/nl/docs#bitlocker)

## Stap 6 · Voorbereiden, schrijven, controleren

Controleer image, bescherming en overzicht. Private image maken produceert bestand; USB voorbereiden/schrijven beschrijft ook apparaat. Vergelijk model, serie en echte capaciteit in native bevestiging; annuleer bij twijfel. Geef UAC/Polkit alleen voor gewenste actie. Wacht zonder loskoppelen op schrijven en volledige terugleescontrole, controleer resultaat. Correcte bytes garanderen geen firmware: test hardwareboot. Externe Windows-USB-back-up moet vooraf gedaan zijn.

[↗](https://aguja.transcendenceia.net/nl/docs#grabar)

## Starten, ontgrendelen, verbinden

Kies USB in fabrikantmenu. Paneel toont netwerk/SSH. Versleuteld profiel: aguja profile unlock lokaal. Grafisch paneel kan terugvallen op tekstconsole. Gebruik echte IP; .local vereist mDNS/multicast en kan bij naamconflict veranderen. SSH werkt ook via LAN zonder tailnet. Vergelijk vingerafdruk, controleer status/schijven. Paneel betekent geen automatische interne koppeling of reparatie.

```sh
aguja profile unlock
aguja status
```

[↗](https://aguja.transcendenceia.net/nl/docs#arranque)

## Herstart: tijdelijke identiteit

Tailnet-status staat in RAM. Na herstart zijn netwerk, ontgrendeling en nieuwe registratie nodig. Een eenmalige sleutel kan verbruikt zijn. Gebruik voor meerdere starts een geldige beperkte herbruikbare sleutel. Identiteit staat los van USB-SSH-hostsleutel en HOME-persistentie. Verwijder oude nodes en trek onnodige sleutels in. Oude verbinding bewijst geen huidige status.

[↗](https://aguja.transcendenceia.net/nl/docs#reinicios)

## AI-login in lokale browser

aguja login codex, claude of antigravity opent sandboxed Chromium met officiële login en console in dezelfde PTY. Kopiëren focust console; plak bewust met Ctrl+Shift+V. Sluiten keert terug. Geen QR of automatische toestemming. OpenCode houdt opencode auth login. SSH/serie/zonder scherm gebruiken native methode; externe localhost-callback niet automatisch doorgestuurd. API en sessie-import zijn aparte routes. Synthetische screenshots bewijzen geen echte login/inferentie.

```sh
aguja login codex
aguja login claude
aguja login antigravity
opencode auth login
```

[↗](https://aguja.transcendenceia.net/nl/docs#ia-login)

## Eerste diagnose

Stel een concrete vraag, verzamel status, apparaatidentiteit, bestandssystemen en mounts. Gebruik aguja doctor en inventaris hieronder. Herken USB, bron en doel via model/grootte/ID, niet aangenomen letters. Controleer alleen-lezen-opties en bestandssysteemjournalgedrag voor bestandstoegang. Bewaar observaties. Instabiele schijf vraagt mogelijk ddrescue-image met mapbestand, niet herhaalde reparatie op origineel.

```sh
aguja doctor
lsblk -o NAME,SIZE,MODEL,SERIAL,FSTYPE,LABEL,MOUNTPOINTS
findmnt
```

[↗](https://aguja.transcendenceia.net/nl/docs#primer-diagnostico)

## Met een agent werken

Definieer doel, exact apparaat/schijf, toegestane acties, back-up en stopcriteria. Vraag actuele status en bewijs vóór wijzigen. Controleer bestanden/boot onafhankelijk. Codex Safe in 0.9.10 gebruikt een workspace-write-sandbox zonder netwerk. Elk hulpmiddel vereist een nieuwe menselijke bevestiging; de sandbox verlaten vereist menselijke goedkeuring. Het account behoudt sudo buiten de sandbox. Andere clients behouden hun bevestigingen; YOLO blijft onbeperkt. Kies met aguja agent NAME; Escape annuleert. Geen modus staat acties buiten je verzoek toe.

[↗](https://aguja.transcendenceia.net/nl/docs#trabajo-ia)

## Gereedschappen en opdrachten

aguja tools geeft inventaris. ddrescue voor images met map, TestDisk/PhotoRec voor herstel, rsync voor kopiëren, smartctl/nvme-cli voor hardware. Volume/versleuteling vereist juiste doelen en sleutels. Opdrachten hieronder geven oriëntatie. Geen format, bootloaderinstallatie of partitiewrites naar geraden apparaat. Lees handleidingen, werk zo nodig op kopie. Traditionele tools zonder cloud; geen universele herstelgarantie.

```sh
aguja tools
aguja status --disks
aguja status --json
aguja context
aguja help
```

[↗](https://aguja.transcendenceia.net/nl/docs#herramientas)

## Wat zou je vanaf het opstarten kunnen bouwen?

Gebruik de aanwezige Linux-tools of voeg projectafhankelijkheden toe. Dit zijn aanpasbare missies, geen éénklikfuncties of allemaal al geteste scenario’s.

[↗](https://aguja.transcendenceia.net/nl/docs#casos)

## Professioneel werken

Leg toestemming, hardware, versie/hash, beginstatus, schijven en plan vast. Werk op kopie, label bewijs en relatie met origineel. Bewaar map en stopcriteria bij instabiele media. Kleine wijzigingen met doel/resultaat. Controleer gegevens/boot, niet alleen exitcode. Versleutel herbruikbare .aguja-profielen en controleer verlopen gegevens. Geen klantgegevens/sleutels in openbare tickets.

[↗](https://aguja.transcendenceia.net/nl/docs#profesional)

## Problemen per laag

Geen boot: architectuur, integriteit, firmware, tekstconsole. Geen netwerk: link/wifi, DHCP, DNS, HTTPS, tijd. Geen SSH: IP/poort, dienst, beleid, login. Geen tailnet: sleutel, URL, geldigheid, gebruikte eenmalige sleutel. Geen AI: methode, account, internet, callback. Geen profiel: functies/ontgrendeling. Geen schijf: controller/inventaris vóór writes. Gezonde doctor bewijst geen ACL, OAuth of alle hardware.

[↗](https://aguja.transcendenceia.net/nl/docs#problemas)

## Afronden zonder vergeten toegang

Vat observaties, wijzigingen en controles samen. Sluit sessies, rond writes af, sluit veilig af en controleer doelbestanden. Bewaar originelen/kopieën tot acceptatie. Verwijder tijdelijke nodes en onnodige sleutels; controleer persistente USB-tokens. Behandel private images/profielen volgens goedgekeurd herstelbaar proces. Trek geen ongerelateerde toegang in en vernietig geen bewijs. Meld resterende grenzen.

[↗](https://aguja.transcendenceia.net/nl/docs#terminar)

## Wat is gecontroleerd

Publieke editie zonder LA AGUJA-accounts/eigen relay. Voorbereidings-, pakket- en VM-tests dekken bepaalde routes, niet elke pc. Imager 0.9.2 corrigeert titel in zeven talen; image blijft 0.9.0. Screenshots behouden echte versies. Teruglezen is geen universele boot; paneel/CLI/sessie is geen AI-login; lokale registratie bewijst geen SSH. Windows zonder ingebouwde USB-back-up of erkende Authenticode. Geen universeel ondertekend Secure Boot.

[↗](https://aguja.transcendenceia.net/nl/docs#validacion)

## Referenties en vervolg

Bovenste links voor downloads en broncode. Uitgebreide Spaanse referentie bewaart 26 oorspronkelijke hoofdstukken; deze gids dekt dezelfde fasen in Nederlands. Screenshots behouden herkomst/versie. Druk af als Nederlands PDF; losse historische PDF is Spaans. Lees officiële OpenSSH, Tailscale/Headscale, ddrescue, TestDisk en Microsoft BitLocker voor je versies. Eigen code GPL-3.0-or-later, derden eigen licenties. Tickets met versie en geschoonde symptomen, nooit wachtwoorden, tokens, privésleutels of images.

[↗](https://aguja.transcendenceia.net/nl/docs#referencias)
