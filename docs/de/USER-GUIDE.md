# Benutzerhandbuch · LA AGUJA Rescue Disk

[Website](https://aguja.transcendenceia.net/de/docs) · [English](../en/USER-GUIDE.md) · [Español](../es/USER-GUIDE.md)


## Kleiner Einstieg. Volle Kontrolle.

LA AGUJA ist ein x86-64 Rettungs-Linux, das vor dem installierten Betriebssystem vom USB-Stick startet. Flash Imager bereitet den Stick auf einem funktionierenden Windows-/Linux-PC vor; Rescue Disk läuft auf dem untersuchten Computer. Beim Start werden interne Datenträger nicht automatisch eingebunden, repariert oder beschrieben.

Arbeite lokal oder per SSH, optional über dein Tailscale/Headscale-Netz. Cloud-KI benötigt Internet und dein eigenes Anbieterkonto; klassische Werkzeuge können offline arbeiten. Es gibt kein LA AGUJA Konto oder zentrales Relay. Das Produkt ist experimentell und garantiert nicht jede Hardware.

[↗](https://aguja.transcendenceia.net/de/docs#que-es)

## Dein erster USB-Stick

Sichere einen ausreichend großen Stick. Lade den Imager, wähle das öffentliche Abbild aus dem signierten Katalog und lasse Ethernet auf DHCP. Stelle Sprache, Tastatur, Hostname und eigenes SSH-Passwort oder öffentlichen Schlüssel ein. KI und privates Netz können beim ersten Versuch ausgeschaltet bleiben.

Verschlüssele ein Profil mit Geheimnissen und bewahre die Entsperrphrase außerhalb des Sticks auf. Vergleiche Modell, Größe und Seriennummer vor der Schreibbestätigung. Warte auf die Rückleseprüfung, starte vom Stick und entsperre das Profil bei Bedarf. Panel sehen und Datenträger identifizieren reicht für diesen ersten Durchlauf.

```sh
aguja status
aguja doctor
lsblk -o NAME,SIZE,MODEL,FSTYPE,LABEL,MOUNTPOINTS
```

[↗](https://aguja.transcendenceia.net/de/docs#primer-usb)

## Wichtige Begriffe

Live bedeutet Start ohne Installation. Das konfigurierbare IMG und die Boot-ISO sind im Imager nicht austauschbar. Ein Datenträger ist das gesamte Gerät, eine Partition ein Teil und ein Mount macht Dateien erreichbar. Namen wie /dev/sda können wechseln.

DHCP vergibt Adressen; SSH bietet eine verschlüsselte Konsole mit Host-Fingerabdruck. Root/sudo bedeutet Administration, kein Nur-Lese-Sandbox. Registrierungsschlüssel, KI-API-Schlüssel, SSH-Passwort und Profilphrase erfüllen unterschiedliche Aufgaben. SHA-256 prüft Bytes, nicht das Booten. Die Profilphrase entsperrt keine BitLocker-/LUKS-Volumes.

[↗](https://aguja.transcendenceia.net/de/docs#glosario)

## Vorher: Hardware, Erlaubnis, Sicherung

Prüfe x86-64 Hardware, USB-Boot und Firmware. BIOS/UEFI sind vorgesehen; ARM, alle WLAN-Chips und eine universelle signierte Secure-Boot-Kette werden nicht zugesichert. Hole die Erlaubnis für Gerät und Daten ein. Wähle ein separates Wiederherstellungsziel. Bei instabilen Datenträgern kann zuerst ein Abbild sinnvoll sein.

Das Schreiben ersetzt den Stickinhalt. Windows hat noch keine integrierte USB-Sicherung: sichere extern. Linux bietet eine optionale geprüfte Vollsicherung, standardmäßig aus, mit Platz- und Rechtebedarf. Das ist keine Sicherung des internen Datenträgers. BitLocker/LUKS benötigen den passenden Schlüssel des Eigentümers.

[↗](https://aguja.transcendenceia.net/de/docs#preparacion)

## Flash Imager herunterladen und öffnen

Wähle auf der offiziellen Seite Windows-10/11-EXE, Linux-AppImage, Debian/Ubuntu-DEB oder portables Archiv. Prüfe SHA-256 und öffne die Anwendung auf dem Vorbereitung-PC. EXE und AppImage gehören nicht als Rettungsabbild auf den Stick. Kein LA AGUJA Konto nötig.

Die EXE hat derzeit keine anerkannte Authenticode-Signatur. AppImages benötigen gegebenenfalls Ausführungsrechte; das portable Archiv ist eine Alternative. Geräteschreiben braucht lokale Rechteerhöhung. Eine gestartete App beweist keine vorbereitete oder bootfähige Rettung.

[↗](https://aguja.transcendenceia.net/de/docs#descargas)

## Schritt 1 · Passendes Abbild wählen

Nutze den signierten Katalog oder eine lokale .img-Datei. Ed25519 und Hashwerte werden geprüft, Downloadteile zusammengefügt. Eine manuell importierte .img.zst muss vorher entpackt werden. Private Vorbereitung erstellt eine neue Datei und verändert nicht das öffentliche Abbild.

Aktuell: Imager 0.9.2, Rettungsabbild 0.9.0. Optionen hängen von unterstützten Abbildfunktionen ab: Ohne tailscale-profile-v1 wird die Vorbereitung mit privater Netzregistrierung abgelehnt. Prüfe die reale Größe statt der Werbeangabe des Sticks.

[↗](https://aguja.transcendenceia.net/de/docs#imagen)

## Schritt 2 · Netzwerk, Sprache, Hostname

Wähle Live-Sprache, Tastaturlayout und Variante; die Imager-Oberflächensprache ist unabhängig. Verwende einen erkennbaren Hostnamen. Ethernet DHCP vereinfacht den Einstieg. Gespeichertes WLAN wird beim Start verwendet; ohne Netz bietet das Panel eine interaktive Auswahl.

WLAN-Passwortimport kann lokale Berechtigung erfordern. Unternehmensnetze und Captive Portals brauchen eventuell manuelles NetworkManager-Setup. Prüfe für Onlinedienste Verbindung, DNS, HTTPS und Uhrzeit getrennt. Lokale Diagnose kann ohne Internet funktionieren.

[↗](https://aguja.transcendenceia.net/de/docs#red)

## Schritt 3 · SSH-Zugang

Verwende ein eigenes Passwort oder den öffentlichen Schlüssel des autorisierten Operators, nie einen privaten Schlüssel. Standardport ist 22. Nutze die echte Live-IP und vergleiche den Host-Fingerabdruck. Ein anderer Port ersetzt keine Authentifizierung.

Werkseitiger Benutzer und öffentliches Passwort sind aguja. Ein eigenes Passwort hat Vorrang. Leeres Passwort mit öffentlichem Schlüssel erlaubt nur Schlüsselzugriff; ohne Schlüssel bleibt der Werkszugang erhalten. Der Benutzer hat unbegrenztes sudo. aguja password speichert auf USB, sudo passwd aguja ändert nur die laufende Sitzung.

```sh
ssh aguja@IP
```

[↗](https://aguja.transcendenceia.net/de/docs#ssh)

## Schritt 4 · KI vorbereiten

Flash Imager integriert Codex CLI, OpenCode, Claude Code und Antigravity. Wähle API-Schlüssel, selektiven Import einer kompatiblen portablen Sitzung oder Anmeldung nach dem Start. Eine CLI-Installationsprüfung belegt weder erfolgreiche Anmeldung noch Inferenz.

Der gesamte Schlüsselbund, Verlauf, Hooks und MCP-Konfiguration werden nicht kopiert. Portable Sitzungen können abgelaufen sein. Kosten, Kontingente und Datenübertragung richten sich nach deinem Anbieter. Du kannst den Stick ohne KI-Zugangsdaten vorbereiten; Cloud-KI wird nicht offline zugesichert.

[↗](https://aguja.transcendenceia.net/de/docs#ia-preparacion)

## Schritt 5 · Eigenes Tailscale/Headscale

Fernzugriff ist optional. Aktiviere das private Netz, gib einen autorisierten Auth-/Pre-Auth-Schlüssel und optional einen Knotennamen an. Leere Headscale-URL verwendet offizielles Tailscale; sonst deinen HTTPS-Server. Das Live registriert sich nach Netzwerk und Profilentsperrung, nicht der Vorbereitung-PC.

Der Client muss zum autorisierten Netz gehören und dessen Richtlinien erfüllen. Registrierungsschlüssel sind keine SSH-Passwörter. Anmeldung belegt keine erlaubenden ACLs: teste echtes SSH vom autorisierten Client. Die Live-Identität liegt im RAM und registriert sich nach Neustart erneut.

[↗](https://aguja.transcendenceia.net/de/docs#tailnet)

## OpenSSH ist nicht Tailscale SSH

Standard ist normales OpenSSH über das private Netz: Schlüssel/Passwort und Fingerabdruck gelten weiter, passende Netzwerk-ACLs sind nötig. Tailscale SSH ist eine erweiterte Option mit kompatiblem Server und ausdrücklichen SSH-Richtlinien.

Trenne Registrierung, Erreichbarkeit, TCP-Port und SSH-Authentifizierung. Öffne nicht öffentliche Ports oder breite ACLs, um einen Anmeldefehler zu verdecken. Prüfe die Dokumentation deiner tatsächlich eingesetzten Tailscale-/Headscale-Version.

[↗](https://aguja.transcendenceia.net/de/docs#politicas)

## Geheimnisse und Verschlüsselungsgrenzen

Private Profile können WLAN-Passwörter, SSH-Einstellungen, KI- und Registrierungsschlüssel enthalten. Verschlüssele die Kapsel, bewahre die Phrase separat auf und entsperre lokal vor dem Laden. Eine .aguja-Vorlage und ihre Sicherungen sind ebenfalls sensibel.

Die Kapsel verschlüsselt nicht ganz AGUJA_DATA und schützt geladene Geheimnisse nicht vor root. persistent_home=no verliert HOME/Tokens nach Neustart; yes speichert sie unverschlüsselt auf USB. Klartext-aguja.conf ist bei physischem Zugriff lesbar. Keine privaten Abbilder oder Schlüssel öffentlich hochladen.

[↗](https://aguja.transcendenceia.net/de/docs#secretos)

## Windows · BitLocker verstehen

BitLocker schützt Windows-Volumes; Linux-Boot entfernt die Verschlüsselung nicht. Beschaffe vom Eigentümer den zum Volume passenden Wiederherstellungsschlüssel. Profilphrase und SSH-Passwort sind keine BitLocker-Schlüssel. LA AGUJA umgeht die Verschlüsselung nicht.

Unter Windows kann der Imager verfügbare Schlüssel prüfen und ausdrücklich ausgewählte Schlüssel in ein privates Abbild aufnehmen. Verschlüssele das Profil und behalte eine weitere Kopie. Ein angezeigter Schlüssel beweist kein entsperrtes Volume. Der Windows-Screenshot stammt aus 0.8.1, nicht aus einem neuen nativen 0.9.2-Test.

[↗](https://aguja.transcendenceia.net/de/docs#bitlocker)

## Schritt 6 · Vorbereiten, schreiben, prüfen

Prüfe Abbild, Schutzmodus und Zusammenfassung. Privates Abbild erstellen erzeugt eine Datei; USB vorbereiten und schreiben beschreibt zusätzlich das gewählte Gerät. Vergleiche Modell, Seriennummer und echte Größe in der nativen Bestätigung. Bei Unsicherheit abbrechen. UAC/Polkit nur für die beabsichtigte Aktion zulassen.

Warte ohne Abziehen auf die vollständige Rückleseprüfung und prüfe deren Ergebnis. Korrekte Bytes garantieren nicht jeden Firmware-Start: teste auf deiner Hardware. Die externe Windows-USB-Sicherung muss vorher erfolgt sein.

[↗](https://aguja.transcendenceia.net/de/docs#grabar)

## Starten, entsperren, verbinden

Wähle den Stick im Hersteller-Bootmenü. Das Panel zeigt Netzwerk und SSH. Ein verschlüsseltes Profil wird lokal mit aguja profile unlock entsperrt. Bei Bedarf fällt die grafische Ansicht auf eine Textkonsole zurück.

Nutze die tatsächliche IP. .local erfordert funktionierendes mDNS/Multicast und kann bei Kollision wechseln. SSH geht auch im LAN ohne Tailnet. Vergleiche den Fingerabdruck, prüfe Status und Datenträger. Das sichtbare Panel bindet oder repariert keine internen Laufwerke automatisch.

```sh
aguja profile unlock
aguja status
```

[↗](https://aguja.transcendenceia.net/de/docs#arranque)

## Neustart: vorübergehende Netzidentität

Die Tailnet-Identität lebt im RAM. Nach Neustart sind Netzwerk, Profilentsperrung und neue Registrierung nötig. Ein Einmalschlüssel kann bereits nach dem ersten Boot verbraucht sein. Für wiederholte Starts verwende einen gültigen, begrenzten wiederverwendbaren Schlüssel in deiner Verwaltung.

Das ist unabhängig vom SSH-Hostschlüssel des USB und von HOME-Persistenz. Entferne veraltete Knoten und widerrufe unbenötigte Schlüssel. Eine frühere Verbindung beweist keine aktuelle Registrierung oder Richtlinie.

[↗](https://aguja.transcendenceia.net/de/docs#reinicios)

## KI-Anmeldung im lokalen Browser

aguja login codex, claude oder antigravity öffnet lokal sandboxed Chromium mit offiziellem Login und Konsole an derselben PTY. Kopieren fokussiert nur die Konsole; füge mit Ctrl+Shift+V ein. Schließen kehrt zum ursprünglichen Terminal zurück. Kein QR und keine automatische Zustimmung.

OpenCode behält opencode auth login. Über SSH, seriell oder ohne Bildschirm gilt die native Methode; entfernte localhost-Callbacks werden nicht automatisch zugesichert. API und Sitzungsimport sind andere Wege. Synthetische Screenshots belegen die Oberfläche, nicht echte Anbieteranmeldung oder Inferenz.

```sh
aguja login codex
aguja login claude
aguja login antigravity
opencode auth login
```

[↗](https://aguja.transcendenceia.net/de/docs#ia-login)

## Erste Diagnose: verstehen vor reparieren

Formuliere eine konkrete Frage, sammle Status, Geräteidentität, Dateisysteme und Mounts. Starte aguja doctor und das Inventar unten. Identifiziere USB, Quelle und Ziel nach Modell, Größe und Kennung, nicht nach vermuteten Gerätebuchstaben.

Prüfe für Dateizugriff Nur-Lese-Mount und Dateisystem-Journalverhalten. Sichere Beobachtungen vor Änderungen. Instabile Medien brauchen möglicherweise ddrescue-Abbild und Map-Datei statt wiederholter Reparaturversuche.

```sh
aguja doctor
lsblk -o NAME,SIZE,MODEL,SERIAL,FSTYPE,LABEL,MOUNTPOINTS
findmnt
```

[↗](https://aguja.transcendenceia.net/de/docs#primer-diagnostico)

## Mit einem Agenten arbeiten

Definiere Ziel, Computer, exakten Datenträger, erlaubte Aktionen, Sicherungsziel und Abbruchbedingungen. Verlange aktuellen Zustand und Belege vor Änderungen. Prüfe wiederhergestellte Dateien oder Bootverhalten unabhängig von der Antwort des Agenten.

aguja hat volle root-/sudo-Rechte. Standardstarter nutzen die Vollzugriffsmechanismen der Werkzeuge; eine Nur-Lese-Anweisung ist keine Sandbox. agent_mode=ask erhält deren Freigabeverhalten ohne root zu entfernen. Prüfe destruktive Aktionen und behalte eine Rückfallkopie.

[↗](https://aguja.transcendenceia.net/de/docs#trabajo-ia)

## Rettungswerkzeuge und Orientierung

aguja tools zeigt die Werkzeuge. ddrescue erstellt Abbilder instabiler Medien; TestDisk/PhotoRec unterstützen Wiederherstellung; rsync kopiert; smartctl/nvme-cli prüfen Hardware. Volume-/Verschlüsselungswerkzeuge brauchen passende Geräte und Schlüssel.

Die Befehle unten dienen der Bestandsaufnahme. Keine Formatierung, Bootloaderinstallation oder Partitionstabellen-Schreibaktion auf einem geratenen Gerät. Lies die jeweiligen Handbücher und arbeite gegebenenfalls auf Kopien. Klassische Werkzeuge brauchen keine Cloud-KI; universelle Wiederherstellung wird nicht versprochen.

```sh
aguja tools
aguja status --disks
aguja status --json
aguja context
aguja help
```

[↗](https://aguja.transcendenceia.net/de/docs#herramientas)

## Zehn praktische Abläufe

1. Nicht bootenden PC inventarisieren. 2. Erlaubte Dateien auf ein anderes Ziel kopieren. 3. Defektes Laufwerk mit ddrescue und Map abbilden. 4. Partitionen vor TestDisk-Schreibzugriff prüfen. 5. PhotoRec auf ein separates Ziel anwenden. 6. SMART/NVMe untersuchen. 7. UEFI/Bootloader nach Sicherung diagnostizieren. 8. BitLocker/LUKS mit richtigem Schlüssel öffnen. 9. Autorisierten SSH-Support leisten. 10. OS-Installation nur auf ausdrücklich freigegebenem Ziel begleiten.

Anpassbare Verfahren, keine automatischen Reparaturen oder garantierten Ergebnisse. Bestimme Quelle, Ziel und Rückweg, prüfe das beobachtbare Ergebnis. Keine geretteten Daten auf die Quelle schreiben.

[↗](https://aguja.transcendenceia.net/de/docs#casos)

## Professionell: Belege und Wiederholbarkeit

Dokumentiere Erlaubnis, Hardware, Version/Hash, Anfangszustand, Datenträger und Rettungsplan. Arbeite möglichst auf einer Kopie, kennzeichne Belege und die Zuordnung zum Original. Bei instabilen Medien Map-Datei und Abbruchkriterien erhalten.

Ändere schrittweise mit Zweck und Ergebnis. Prüfe Daten/Boot statt nur Exitcodes. Wiederverwendbare .aguja-Profile verschlüsseln und auf veraltete Schlüssel prüfen. Keine Kundendaten oder Schlüssel in öffentlichen Tickets oder Vorführungen.

[↗](https://aguja.transcendenceia.net/de/docs#profesional)

## Fehler nach Ebenen eingrenzen

Kein Boot: Architektur, Integrität, Firmware, Textkonsole. Kein Netz: Verbindung/WLAN, DHCP, DNS, HTTPS, Zeit. Kein SSH: IP/Port, Dienst, Richtlinie, Authentifizierung. Kein Tailnet: Schlüssel, URL, Ablauf oder bereits verbrauchter Einmalschlüssel.

Kein KI-Login: Methode, Konto, Internet, Callback. Profil fehlt: Abbildfähigkeit und Entsperrung. Laufwerk fehlt: Controller/Inventar vor Schreibaktionen. Ein gesundes doctor-Ergebnis beweist weder ACLs noch OAuth noch universelle Hardware-Kompatibilität.

[↗](https://aguja.transcendenceia.net/de/docs#problemas)

## Abschließen ohne vergessene Zugänge

Fasse Beobachtungen, Änderungen und Prüfungen zusammen. Beende Sitzungen und Schreibvorgänge, fahre sauber herunter. Prüfe Dateien am Ziel und behalte Original/Sicherung bis zur Abnahme.

Entferne temporäre Knoten, widerrufe unnötige Schlüssel und prüfe persistente USB-Tokens. Private Profile/Abbilder nur nach freigegebenem, wiederherstellbarem Verfahren behandeln. Keine fremden Eigentümerzugänge entziehen oder Belege vernichten. Verbleibende Grenzen benennen.

[↗](https://aguja.transcendenceia.net/de/docs#terminar)

## Was getestet ist und was daraus nicht folgt

Die öffentliche Ausgabe entfernt LA AGUJA Konten und proprietäres Relay. Paket-, Vorbereitungs- und VM-Tests belegen bestimmte Abläufe, nicht jeden PC. Imager 0.9.2 korrigiert den Titel in sieben Sprachen; das Rettungsabbild bleibt 0.9.0. Ältere Screenshots behalten ihre echten Versionen.

Rücklesen ist keine universelle Bootprüfung; Panel/CLI/portable Sitzung ist keine KI-Anmeldung. Lokale Registrierung belegt keinen erlaubten SSH-Zugriff. Windows hat weder integrierte USB-Sicherung noch anerkannte Authenticode-Signatur. Keine universelle signierte Secure-Boot-Kette.

[↗](https://aguja.transcendenceia.net/de/docs#validacion)

## Referenzen und nächste Schritte

Links oben führen zu Downloads und Quellcode. Die ausführliche spanische Referenz enthält das ursprüngliche Handbuch mit 26 Kapiteln. Diese Anleitung deckt dieselben Betriebsschritte auf Deutsch ab. Bilder behalten Version und Herkunft. Drucke diese Seite als deutsches PDF; das separat veröffentlichte historische PDF ist spanisch.

Nutze offizielle Dokumentation von OpenSSH, Tailscale/Headscale, ddrescue, TestDisk und Microsoft BitLocker für deine Versionen. Eigener Code: GPL-3.0-or-later, Fremdkomponenten: eigene Lizenzen. Tickets enthalten Versionen und bereinigte Symptome, keine Passwörter, Tokens, privaten Schlüssel oder Abbilder.

[↗](https://aguja.transcendenceia.net/de/docs#referencias)
