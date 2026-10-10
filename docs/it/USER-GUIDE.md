# Guida utente · LA AGUJA

[Website](https://aguja.transcendenceia.net/it/docs) · [English](../en/USER-GUIDE.md) · [Español](../es/USER-GUIDE.md)


## Una piattaforma di lancio, non solo un salvagente.

LA AGUJA trasforma un PC compatibile in un’officina Linux prima dell’avvio del sistema installato, anche con il disco vuoto. Dai una missione all’agente: costruire, configurare, sperimentare, migrare o recuperare.

La sessione live usa uno strato scrivibile in RAM sopra l’immagine USB di sola lettura. È Linux, non firmware; l’intera USB non viene copiata in RAM. I dischi interni restano intatti all’avvio; decidi tu quando scriverci.

Include client IA con accesso root, SSH, Python, Git, strumenti per dischi, debootstrap e arch-install-scripts. Aggiungi pacchetti compatibili: QEMU/KVM, motori di container e strumenti di compilazione richiedono installazione aggiuntiva, RAM/spazio sufficienti e hardware compatibile. Salva esplicitamente i risultati importanti; la RAM è temporanea. L’IA cloud richiede rete e il tuo account; nessun modello locale è incluso.

[↗](https://aguja.transcendenceia.net/it/docs#que-es)

## La prima USB

Salva i dati di una USB abbastanza capiente. Scarica Imager e immagine dal catalogo firmato. Lascia Ethernet DHCP, imposta lingua/tastiera/nome e password SSH personale o chiave pubblica. IA e rete privata possono restare disattivate. Cifra i profili con segreti e conserva la frase fuori dalla USB. Conferma modello, capacità e seriale prima della scrittura. Attendi la rilettura verificata, avvia dalla USB e sblocca il profilo se necessario. Vedere il pannello e identificare i dischi completa il primo test.

```sh
aguja status
aguja doctor
lsblk -o NAME,SIZE,MODEL,FSTYPE,LABEL,MOUNTPOINTS
```

[↗](https://aguja.transcendenceia.net/it/docs#primer-usb)

## Termini utili

Live significa avvio senza installazione. IMG configurabile e ISO non sono intercambiabili nell’Imager. Disco, partizione e montaggio sono distinti; /dev/sda può cambiare. DHCP assegna indirizzi; SSH offre console cifrata e impronta del server. Root/sudo è amministrazione, non sandbox in sola lettura. Chiave d’iscrizione, chiave API, password SSH e frase del profilo hanno ruoli diversi. SHA-256 verifica byte, non avvio universale. La frase del profilo non apre BitLocker/LUKS.

[↗](https://aguja.transcendenceia.net/it/docs#glosario)

## Prima: hardware, autorizzazione e backup

Verifica x86-64, USB e firmware. BIOS/UEFI sono previsti; ARM, tutti i chip Wi-Fi e Secure Boot firmato universale non sono garantiti. Ottieni autorizzazione per macchina e dati. Scegli una destinazione separata; per dischi instabili valuta prima un’immagine. La scrittura sostituisce la USB. Windows non offre ancora backup USB integrato: eseguilo esternamente. Linux offre backup completo verificato facoltativo, disattivato per impostazione iniziale, con spazio e permessi necessari. Non è backup del disco interno. BitLocker/LUKS richiedono la chiave del proprietario.

[↗](https://aguja.transcendenceia.net/it/docs#preparacion)

## Scaricare e aprire Imager

Scegli EXE Windows 10/11, AppImage, DEB Debian/Ubuntu o archivio Linux portatile dal sito ufficiale. Verifica SHA-256 e apri sul PC preparatore. Non scrivere EXE/AppImage come immagine USB. Nessun account LA AGUJA. L’EXE non ha firma Authenticode riconosciuta; AppImage può richiedere permessi di esecuzione. La scrittura richiede elevazione locale. Aprire l’applicazione non prova preparazione o avvio della USB.

[↗](https://aguja.transcendenceia.net/it/docs#descargas)

## Passo 1 · Scegliere l’immagine

Usa catalogo firmato o .img locale. Si verificano Ed25519 e hash; le parti vengono unite. Decomprimi .img.zst prima dell’importazione manuale. La preparazione privata crea un nuovo file senza cambiare l’immagine pubblica. Imager 0.9.2, immagine 0.9.0. Le opzioni dipendono dalle capacità dell’immagine; senza tailscale-profile-v1 viene rifiutata la preparazione con iscrizione alla rete privata. Controlla capacità reale, non solo l’etichetta.

[↗](https://aguja.transcendenceia.net/it/docs#imagen)

## Passo 2 · Rete, lingua e nome

Scegli lingua live, tastiera e variante; lingua Imager indipendente. Usa un nome riconoscibile. Ethernet DHCP facilita l’avvio. Wi-Fi salvato viene attivato; senza rete c’è selezione interattiva. Importare password Wi-Fi può richiedere permesso locale. Reti aziendali e portali captive possono richiedere NetworkManager manuale. Verifica separatamente rete, DNS, HTTPS e ora. Diagnostica locale possibile offline.

[↗](https://aguja.transcendenceia.net/it/docs#red)

## Passo 3 · SSH

Imposta password unica o chiave pubblica autorizzata, mai privata. Porta predefinita 22; usa IP reale e confronta l’impronta. Cambiare porta non sostituisce autenticazione. Utente e password pubblici di fabbrica: aguja. Password personale prevale; vuota con chiave pubblica permette solo chiave, senza chiave conserva accesso di fabbrica. Sudo illimitato. aguja password conserva sul USB; sudo passwd aguja cambia solo la sessione.

```sh
ssh aguja@IP
```

[↗](https://aguja.transcendenceia.net/it/docs#ssh)

## Passo 4 · Preparare IA

Codex CLI, OpenCode, Claude Code e Antigravity: chiave API, importazione selettiva di sessione portatile compatibile o login dopo l’avvio. Verifica d’installazione non significa login o inferenza riuscita. Nessuna copia dell’intero portachiavi, cronologia, hook o MCP. Le sessioni possono essere scadute. Costi, quote e dati dipendono dal fornitore. Puoi preparare senza credenziali IA; non si promette IA cloud offline.

[↗](https://aguja.transcendenceia.net/it/docs#ia-preparacion)

## Passo 5 · Tailscale/Headscale proprio

Accesso facoltativo: abilita rete privata, chiave auth/pre-auth autorizzata e nome opzionale. URL Headscale vuota usa Tailscale ufficiale; altrimenti server HTTPS proprio. Si iscrive il live dopo rete e sblocco, non il PC preparatore. Client nella rete autorizzata e politiche compatibili. Chiave d’iscrizione non è password SSH. Iscrizione non prova ACL: verifica SSH reale. Identità in RAM, nuova iscrizione dopo riavvio.

[↗](https://aguja.transcendenceia.net/it/docs#tailnet)

## OpenSSH e Tailscale SSH

Il percorso standard è OpenSSH sulla rete privata: password/chiavi, impronta e ACL di rete restano necessari. Tailscale SSH è avanzato, con server compatibile e politiche SSH esplicite. Distingui iscrizione, raggiungibilità, porta TCP e autenticazione. Non aprire porte pubbliche né ampliare ACL per nascondere errori. Consulta documentazione delle versioni effettivamente utilizzate.

[↗](https://aguja.transcendenceia.net/it/docs#politicas)

## Segreti e limiti della cifratura

Profili privati possono contenere Wi-Fi, SSH, IA e chiavi d’iscrizione. Cifra la capsula, conserva la frase separata, sblocca localmente prima di caricare. Modelli .aguja e backup sono sensibili. Non cifra tutto AGUJA_DATA né protegge da root dopo sblocco. persistent_home=no perde HOME/token al riavvio; yes li salva non cifrati. aguja.conf in chiaro è fisicamente leggibile. Non pubblicare immagini private o chiavi.

[↗](https://aguja.transcendenceia.net/it/docs#secretos)

## Windows · BitLocker

Avviare Linux non rimuove BitLocker. Ottieni dal proprietario la chiave corretta per il volume. Frase del profilo e password SSH non sono chiavi BitLocker. LA AGUJA non aggira la cifratura. Imager Windows può consultare chiavi disponibili e includere solo quelle selezionate esplicitamente nell’immagine privata. Proteggi il profilo e tieni altra copia. Vedere la chiave non prova sblocco. La schermata Windows è storica 0.8.1, non nuovo test nativo 0.9.2.

[↗](https://aguja.transcendenceia.net/it/docs#bitlocker)

## Passo 6 · Preparare, scrivere, verificare

Rivedi immagine, protezione e riepilogo. Creare immagine privata genera file; preparare e scrivere USB scrive anche il dispositivo. Conferma modello, seriale e capacità reale nel dialogo nativo; annulla nel dubbio. Autorizza UAC/Polkit per l’azione voluta. Attendi scrittura e rilettura completa senza scollegare. Verifica risultato. Byte corretti non garantiscono firmware: prova avvio reale. Backup USB Windows già eseguito esternamente.

[↗](https://aguja.transcendenceia.net/it/docs#grabar)

## Avviare, sbloccare, collegarsi

Scegli USB nel menu del produttore. Pannello con rete/SSH. Profilo cifrato: aguja profile unlock in console locale. La grafica può ripiegare sulla console testo. Usa IP reale; .local dipende da mDNS/multicast e conflitti. SSH funziona anche in LAN senza tailnet. Confronta impronta, verifica stato/dischi. Pannello visibile non implica montaggio o riparazione interna.

```sh
aguja profile unlock
aguja status
```

[↗](https://aguja.transcendenceia.net/it/docs#arranque)

## Riavvii: identità temporanea

Stato tailnet in RAM: dopo riavvio servono rete, profilo sbloccato e nuova iscrizione. Chiave monouso può essere già consumata. Per più avvii usa chiave riutilizzabile valida e limitata. Identità distinta dalla chiave host SSH USB e dalla persistenza HOME. Rimuovi nodi obsoleti e revoca chiavi inutili. Una vecchia connessione non prova lo stato attuale.

[↗](https://aguja.transcendenceia.net/it/docs#reinicios)

## Login IA nel browser locale

aguja login codex, claude o antigravity apre Chromium con sandbox, accesso ufficiale e console nella stessa PTY. Copiare focalizza la console; incolla con Ctrl+Shift+V. Chiudere torna al terminale. Nessun QR o consenso automatico. OpenCode mantiene opencode auth login. SSH/seriale/senza schermo usano metodo nativo; callback localhost remoto non automaticamente inoltrato. API e importazione sessione sono separati. Schermate sintetiche non provano login o inferenza reali.

```sh
aguja login codex
aguja login claude
aguja login antigravity
opencode auth login
```

[↗](https://aguja.transcendenceia.net/it/docs#ia-login)

## Prima diagnosi

Formula domanda precisa, raccogli stato, identità, filesystem e montaggi. Usa aguja doctor e inventario seguente. Identifica USB, origine e destinazione con modello/dimensioni/ID, non lettere supposte. Verifica montaggio sola lettura e comportamento del journal prima di leggere file. Salva osservazioni. Un disco instabile può richiedere immagine ddrescue con mappa, non riparazioni ripetute sull’originale.

```sh
aguja doctor
lsblk -o NAME,SIZE,MODEL,SERIAL,FSTYPE,LABEL,MOUNTPOINTS
findmnt
```

[↗](https://aguja.transcendenceia.net/it/docs#primer-diagnostico)

## Lavorare con un agente

Definisci obiettivo, computer/disco esatto, azioni autorizzate, backup e criteri di arresto. Chiedi stato reale e prove prima delle modifiche. Verifica dati/avvio indipendentemente dall’agente. aguja ha root/sudo completo; modalità standard a pieno accesso, richiesta di sola lettura non è sandbox. agent_mode=ask mantiene approvazioni senza togliere root. Controlla azioni distruttive e conserva rollback.

[↗](https://aguja.transcendenceia.net/it/docs#trabajo-ia)

## Strumenti e comandi

aguja tools elenca strumenti. ddrescue per immagini con mappa, TestDisk/PhotoRec per recupero, rsync per copia, smartctl/nvme-cli per hardware. Volumi/cifratura richiedono dispositivo e chiavi corretti. Comandi sotto per orientamento. Non formattare, installare bootloader o scrivere partizioni su dispositivi indovinati. Consulta manuali e lavora su copia se necessario. Strumenti tradizionali senza cloud, nessun recupero universale garantito.

```sh
aguja tools
aguja status --disks
aguja status --json
aguja context
aguja help
```

[↗](https://aguja.transcendenceia.net/it/docs#herramientas)

## Otto missioni. Il recupero è solo una.

Usa gli strumenti Linux inclusi o aggiungi le dipendenze del progetto. Sono missioni adattabili, non funzioni con un clic né scenari tutti già collaudati.

[↗](https://aguja.transcendenceia.net/it/docs#casos)

## Percorso professionale

Registra autorizzazione, hardware, versione/hash, stato, dischi e piano. Lavora su copia, etichetta prove e collegamento all’originale. Conserva mappa e criteri di arresto per media instabili. Modifiche limitate con scopo e risultato. Verifica dati/avvio, non solo exit code. Cifra .aguja riutilizzabili e rivedi credenziali obsolete. Nessun dato o chiave cliente nei ticket pubblici.

[↗](https://aguja.transcendenceia.net/it/docs#profesional)

## Problemi per livelli

Nessun avvio: architettura, integrità, firmware, console testo. Nessuna rete: link/Wi-Fi, DHCP, DNS, HTTPS, ora. Nessun SSH: IP/porta, servizio, politica, autenticazione. Nessuna tailnet: chiave, URL, scadenza, monouso consumata. Nessuna IA: metodo, account, Internet, callback. Profilo assente: capacità/sblocco. Disco assente: controller e inventario prima delle scritture. doctor sano non prova ACL, OAuth o compatibilità totale.

[↗](https://aguja.transcendenceia.net/it/docs#problemas)

## Chiudere senza accessi dimenticati

Riassumi osservazioni, cambiamenti e verifiche. Chiudi sessioni, completa scritture, spegni correttamente e controlla i file sul destinatario. Conserva originali/backup fino all’accettazione. Rimuovi nodi temporanei e revoca chiavi inutili; verifica token persistenti sul USB. Gestisci immagini/profili con procedura approvata e recuperabile. Non togliere accessi estranei né distruggere prove. Segnala limiti residui.

[↗](https://aguja.transcendenceia.net/it/docs#terminar)

## Cosa è verificato

Edizione pubblica senza account LA AGUJA o relay proprietario. Test di preparazione, pacchetti e VM coprono percorsi specifici, non ogni PC. Imager 0.9.2 corregge il titolo in sette lingue; immagine 0.9.0 invariata. Schermate conservano versioni reali. Rilettura non è avvio universale; pannello/CLI/sessione non è login IA; iscrizione locale non prova SSH. Windows senza backup USB integrato o Authenticode riconosciuto. Nessun Secure Boot firmato universale.

[↗](https://aguja.transcendenceia.net/it/docs#validacion)

## Riferimenti e prossimi passi

Link superiori per download e codice. Riferimento spagnolo esteso conserva i 26 capitoli originali; questa guida copre le stesse fasi in italiano. Schermate mantengono origine/versione. Stampa per PDF italiano; PDF storico separato in spagnolo. Consulta OpenSSH, Tailscale/Headscale, ddrescue, TestDisk e Microsoft BitLocker per le tue versioni. Codice GPL-3.0-or-later, terzi con proprie licenze. Ticket con versione e sintomi ripuliti, mai password, token, chiavi o immagini private.

[↗](https://aguja.transcendenceia.net/it/docs#referencias)
