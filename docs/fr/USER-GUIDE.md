# Guide d’utilisation · LA AGUJA Rescue Disk

[Website](https://aguja.transcendenceia.net/fr/docs) · [English](../en/USER-GUIDE.md) · [Español](../es/USER-GUIDE.md)


## Une petite entrée. Un contrôle complet.

LA AGUJA est un Linux de secours x86-64 démarré depuis une clé USB avant le système installé. Flash Imager prépare la clé sur un ordinateur Windows ou Linux fonctionnel ; le Rescue Disk s’exécute sur l’ordinateur à examiner. Le démarrage ne monte, ne répare et ne modifie pas automatiquement les disques internes.

Travaillez localement ou par SSH, avec un réseau Tailscale/Headscale facultatif. L’IA distante nécessite Internet et votre propre compte fournisseur ; les outils classiques peuvent fonctionner hors ligne. Aucun compte LA AGUJA ni relais central. Le produit est expérimental, sans garantie de compatibilité universelle.

[↗](https://aguja.transcendenceia.net/fr/docs#que-es)

## Votre première clé USB

Sauvegardez une clé assez grande, téléchargez l’Imager et choisissez l’image publique dans le catalogue signé. Gardez Ethernet en DHCP, définissez langue, clavier, nom d’hôte et mot de passe SSH personnel ou clé publique. L’IA et le réseau privé peuvent rester désactivés pour ce premier essai.

Si le profil contient des secrets, chiffrez-le et conservez la phrase de déverrouillage hors de la clé. Vérifiez modèle, capacité et numéro de série avant de confirmer l’écriture. Attendez la vérification de relecture, démarrez sur la clé puis déverrouillez le profil si nécessaire. Afficher le panneau et identifier les disques suffit pour ce premier parcours.

```sh
aguja status
aguja doctor
lsblk -o NAME,SIZE,MODEL,FSTYPE,LABEL,MOUNTPOINTS
```

[↗](https://aguja.transcendenceia.net/fr/docs#primer-usb)

## Le vocabulaire utile

Un système live démarre sans installation. L’IMG configurable et l’ISO de démarrage ne sont pas interchangeables dans l’Imager. Un disque est le périphérique complet, une partition en est une partie et un montage rend ses fichiers accessibles. Les noms comme /dev/sda peuvent changer.

DHCP attribue une adresse ; SSH fournit une console chiffrée et une empreinte d’identité. Root/sudo signifie administration, pas lecture seule. Un réseau privé, une clé d’inscription, une clé API, un mot de passe SSH et une phrase de profil remplissent des rôles différents. SHA-256 contrôle les octets, pas le démarrage. La phrase du profil ne déchiffre pas BitLocker/LUKS.

[↗](https://aguja.transcendenceia.net/fr/docs#glosario)

## Avant de commencer : matériel, autorisation, sauvegarde

Vérifiez le matériel x86-64, le démarrage USB et le firmware. BIOS/UEFI sont prévus ; ARM, tous les contrôleurs Wi-Fi et une chaîne Secure Boot signée universelle ne sont pas garantis. Obtenez l’autorisation pour la machine et les données. Choisissez une destination de récupération distincte ; face à un disque instable, envisagez une image avant la réparation.

L’écriture remplace le contenu de la clé. Windows n’a pas de sauvegarde USB intégrée : utilisez un outil externe avant. Linux propose une sauvegarde complète vérifiée, facultative, désactivée par défaut et exigeant de l’espace. Ce n’est pas une sauvegarde du disque interne. Les volumes BitLocker/LUKS nécessitent la bonne clé du propriétaire.

[↗](https://aguja.transcendenceia.net/fr/docs#preparacion)

## Télécharger et ouvrir Flash Imager

Choisissez l’EXE Windows 10/11, l’AppImage Linux, le DEB Debian/Ubuntu ou l’archive portable sur la page officielle. Vérifiez la somme SHA-256 et ouvrez l’application sur le PC préparateur. Ne gravez pas l’EXE ou l’AppImage sur la clé. Aucun compte LA AGUJA n’est nécessaire.

L’EXE n’a actuellement pas de signature Authenticode reconnue. Une AppImage peut nécessiter le droit d’exécution ; l’archive portable est une alternative. L’écriture du périphérique requiert une élévation locale. Ouvrir l’application ne prouve pas qu’une clé a été préparée ni qu’elle démarre.

[↗](https://aguja.transcendenceia.net/fr/docs#descargas)

## Étape 1 · Choisir une image compatible

Utilisez le catalogue signé ou une image .img locale. Le catalogue vérifie Ed25519 et les empreintes ; les parties téléchargées sont assemblées. Une .img.zst importée manuellement doit d’abord être décompressée. Préparer une image privée crée un nouveau fichier sans modifier l’image publique.

Version actuelle : Imager 0.9.2, image de secours 0.9.0. Les options dépendent des capacités de l’image : sans tailscale-profile-v1, la préparation avec inscription au réseau privé est refusée. Contrôlez la capacité réelle, pas seulement l’étiquette commerciale de la clé.

[↗](https://aguja.transcendenceia.net/fr/docs#imagen)

## Étape 2 · Réseau, langue et nom d’hôte

Choisissez la langue du live, la disposition et la variante du clavier ; la langue de l’interface Imager est distincte. Donnez un nom reconnaissable au système. Ethernet DHCP simplifie le premier démarrage. Le Wi-Fi enregistré est activé ; sans réseau, le panneau permet une sélection interactive.

L’import d’un mot de passe Wi-Fi peut demander une autorisation locale. Les réseaux d’entreprise ou portails captifs peuvent exiger NetworkManager manuel. Pour une connexion en ligne, vérifiez séparément réseau, DNS, HTTPS et heure. Le diagnostic local reste possible sans Internet.

[↗](https://aguja.transcendenceia.net/fr/docs#red)

## Étape 3 · Accès SSH

Utilisez un mot de passe unique ou la clé publique de l’opérateur autorisé, jamais sa clé privée. Le port par défaut est 22. Comparez l’empreinte du serveur et utilisez l’IP réelle du live. Un changement de port ne remplace pas l’authentification.

Le compte d’usine est aguja et le mot de passe public est aguja. Un mot de passe personnel prévaut. Un mot de passe vide avec clé publique donne un accès par clé seule ; sans clé il conserve l’accès d’usine. Le compte dispose de sudo illimité. aguja password conserve le changement sur USB ; sudo passwd aguja ne change que la session.

```sh
ssh aguja@IP
```

[↗](https://aguja.transcendenceia.net/fr/docs#ssh)

## Étape 4 · Préparer l’IA

L’Imager intègre Codex CLI, OpenCode, Claude Code et Antigravity. Choisissez clé API, import sélectif d’une session portable compatible ou connexion après démarrage. La vérification d’installation d’un CLI n’atteste pas une authentification ni une inférence réussie.

Le trousseau complet, l’historique, les hooks et la configuration MCP ne sont pas copiés. Une session portable peut être expirée. Coûts, quotas et données envoyées dépendent de votre fournisseur. Vous pouvez préparer la clé sans identifiants IA ; l’IA distante n’est pas promise hors ligne.

[↗](https://aguja.transcendenceia.net/fr/docs#ia-preparacion)

## Étape 5 · Votre Tailscale ou Headscale

L’accès distant est facultatif. Activez le réseau privé, fournissez une clé auth/pre-auth autorisée et éventuellement un nom de nœud. Une URL Headscale vide utilise Tailscale officiel ; sinon indiquez votre serveur HTTPS. Le live s’inscrit au démarrage après réseau et déverrouillage, pas le PC préparateur.

Le client doit appartenir au réseau privé autorisé et respecter ses politiques. La clé d’inscription ne remplace pas le mot de passe SSH. Une inscription ne prouve pas les ACL : testez SSH depuis le client autorisé. L’identité du live est conservée en RAM et doit se réinscrire après redémarrage.

[↗](https://aguja.transcendenceia.net/fr/docs#tailnet)

## OpenSSH et Tailscale SSH sont différents

OpenSSH sur le réseau privé est le parcours par défaut : mots de passe/clés et empreintes restent applicables, avec des ACL réseau compatibles. Tailscale SSH est une option avancée nécessitant un support serveur et des politiques SSH explicites.

Distinguez inscription, joignabilité, port TCP et authentification SSH. N’ouvrez pas de ports publics et n’élargissez pas les ACL pour masquer un problème d’identification. Consultez la documentation de vos versions Tailscale/Headscale.

[↗](https://aguja.transcendenceia.net/fr/docs#politicas)

## Secrets : portée du chiffrement

Le profil privé peut contenir mots de passe Wi-Fi, paramètres SSH, clés IA et d’inscription. Chiffrez la capsule, gardez sa phrase séparément et déverrouillez localement avant de charger les paramètres. Un modèle .aguja et ses sauvegardes sont également sensibles.

La capsule ne chiffre pas tout AGUJA_DATA et ne protège pas les secrets déverrouillés face à root. persistent_home=no perd HOME et jetons au redémarrage ; yes les conserve sans chiffrement sur USB. aguja.conf en clair est lisible physiquement. Ne publiez ni profils privés, ni clés, ni images personnalisées.

[↗](https://aguja.transcendenceia.net/fr/docs#secretos)

## Windows · Comprendre BitLocker

BitLocker protège les volumes Windows ; démarrer Linux ne supprime pas ce chiffrement. Obtenez du propriétaire la clé correspondant au volume. La phrase du profil et le mot de passe SSH ne sont pas des clés BitLocker. LA AGUJA ne casse pas le chiffrement.

Sous Windows, l’Imager peut examiner les clés disponibles et inclure explicitement celles choisies dans une image privée. Chiffrez le profil et gardez une autre copie. Voir une clé ne prouve pas le déverrouillage du volume. La capture Windows publiée date de 0.8.1, pas d’un nouveau test natif 0.9.2.

[↗](https://aguja.transcendenceia.net/fr/docs#bitlocker)

## Étape 6 · Préparer, écrire, vérifier

Relisez image, protection et résumé. Créer une image privée produit un fichier ; préparer et écrire la clé écrit aussi le périphérique choisi. Comparez modèle, série et capacité dans la confirmation native. En cas de doute, annulez. Accordez UAC/Polkit uniquement pour l’opération voulue.

Attendez la relecture complète sans débrancher. Vérifiez le résultat annoncé. Une relecture correcte contrôle les octets, pas tous les firmwares : testez le démarrage sur votre matériel. La sauvegarde USB Windows doit avoir été faite séparément.

[↗](https://aguja.transcendenceia.net/fr/docs#grabar)

## Démarrer, déverrouiller, se connecter

Sélectionnez la clé dans le menu de démarrage du fabricant. Le panneau affiche réseau et SSH. Un profil chiffré se déverrouille avec aguja profile unlock dans la console locale. Selon le matériel, la vue graphique peut laisser place à une console texte.

Utilisez l’IP réelle. Le nom .local nécessite mDNS/multicast et peut changer en cas de conflit. SSH fonctionne aussi en LAN sans réseau privé. Comparez l’empreinte puis vérifiez état et disques. Afficher le panneau ne monte ni ne répare les disques internes.

```sh
aguja profile unlock
aguja status
```

[↗](https://aguja.transcendenceia.net/fr/docs#arranque)

## Redémarrage : une identité temporaire

L’état du réseau privé est en RAM : après redémarrage, il faut se réinscrire avec réseau et profil déverrouillé. Une clé à usage unique peut être consommée au premier démarrage. Pour plusieurs démarrages, utilisez une clé réutilisable valide et limitée selon votre administration.

Cette identité est distincte de la clé d’hôte SSH du USB et de la persistance HOME. Supprimez les nœuds obsolètes et révoquez les clés devenues inutiles. Une connexion précédente ne prouve pas l’état ou la politique actuelle.

[↗](https://aguja.transcendenceia.net/fr/docs#reinicios)

## Connexion IA dans le navigateur local

aguja login codex, claude ou antigravity ouvre localement un Chromium avec bac à sable et la connexion officielle, lié à la même PTY. Copier le code donne le focus à la console ; collez avec Ctrl+Shift+V. Fermer revient au terminal initial. Pas de QR ni de consentement automatique.

OpenCode conserve opencode auth login. En SSH, série ou sans écran, utilisez la méthode native ; aucun callback localhost distant n’est automatiquement garanti. Clé API et import de session sont d’autres parcours. Les captures synthétiques démontrent l’interface, pas un vrai consentement fournisseur ou une inférence.

```sh
aguja login codex
aguja login claude
aguja login antigravity
opencode auth login
```

[↗](https://aguja.transcendenceia.net/fr/docs#ia-login)

## Premier diagnostic : comprendre avant de réparer

Posez une question précise et recueillez état, identité des périphériques, systèmes de fichiers et montages. Lancez aguja doctor et l’inventaire ci-dessous. Identifiez clé, disque source et destination par modèle/taille/identifiants, jamais par une lettre supposée.

Pour consulter des fichiers, contrôlez le montage en lecture seule et les particularités du journal du système de fichiers. Conservez les observations avant changement. Un disque instable peut nécessiter une image ddrescue et son fichier de suivi plutôt que des réparations répétées.

```sh
aguja doctor
lsblk -o NAME,SIZE,MODEL,SERIAL,FSTYPE,LABEL,MOUNTPOINTS
findmnt
```

[↗](https://aguja.transcendenceia.net/fr/docs#primer-diagnostico)

## Travailler avec un agent

Définissez objectif, machine, disque exact, actions autorisées, destination de sauvegarde et conditions d’arrêt. Demandez l’état vivant et les preuves avant modification. Validez les fichiers récupérés ou le démarrage indépendamment du discours de l’agent.

aguja dispose de root/sudo complet. Le mode par défaut utilise les mécanismes de pleine puissance des outils ; demander une lecture seule ne crée pas un bac à sable. agent_mode=ask conserve leurs approbations sans retirer root. Contrôlez les actions destructives et gardez une copie de retour arrière.

[↗](https://aguja.transcendenceia.net/fr/docs#trabajo-ia)

## Outils de secours et commandes d’orientation

aguja tools liste les outils. ddrescue aide à imager un support instable ; TestDisk/PhotoRec à récupérer ; rsync à copier ; smartctl/nvme-cli à examiner le matériel. Les outils de volumes et chiffrement nécessitent les bonnes cibles et clés.

Les commandes ci-dessous servent à l’inventaire. Ne formatez pas, ne réinstallez pas de chargeur et n’écrivez pas une table de partitions sur un périphérique deviné. Consultez les manuels et travaillez sur copie si nécessaire. Les outils traditionnels fonctionnent sans IA distante ; aucune récupération universelle n’est promise.

```sh
aguja tools
aguja status --disks
aguja status --json
aguja context
aguja help
```

[↗](https://aguja.transcendenceia.net/fr/docs#herramientas)

## Dix parcours pratiques

1. Inventorier un PC qui ne démarre plus. 2. Copier des fichiers autorisés ailleurs. 3. Imager un disque défaillant avec ddrescue et son suivi. 4. Examiner les partitions avant TestDisk. 5. Récupérer avec PhotoRec vers un autre support. 6. Inspecter SMART/NVMe. 7. Diagnostiquer UEFI/chargeur après sauvegarde. 8. Ouvrir BitLocker/LUKS avec la bonne clé. 9. Assister en SSH autorisé. 10. Aider à installer un OS sur une cible explicitement approuvée.

Ce sont des procédures adaptables, pas des réparations automatiques ni des résultats garantis. Identifiez source, destination et retour arrière, puis vérifiez le résultat observable. N’enregistrez pas les fichiers récupérés sur la source.

[↗](https://aguja.transcendenceia.net/fr/docs#casos)

## Parcours professionnel : preuve et répétabilité

Consignez autorisation, matériel, version/empreinte, état initial, disques et plan de récupération. Travaillez sur copie si possible, étiquetez les preuves et gardez le lien avec l’original. Pour un disque instable, conservez le suivi ddrescue et les conditions d’arrêt.

Avancez par changements limités, avec motif et résultat. Vérifiez données et démarrage plutôt que les seuls codes de sortie. Un profil .aguja réutilisable doit être chiffré et ses clés revues. Aucune donnée ou clé client dans un ticket public ou une démonstration.

[↗](https://aguja.transcendenceia.net/fr/docs#profesional)

## Dépannage : séparer les couches

Pas de démarrage : architecture, intégrité, firmware, console texte. Pas de réseau : lien/Wi-Fi, DHCP, DNS, HTTPS, heure. Pas de SSH : IP/port, service, politiques, authentification. Pas de réseau privé : clé, URL, expiration ou clé à usage unique déjà consommée.

Pas de connexion IA : méthode, compte, Internet et callback. Profil absent : capacités de l’image et déverrouillage. Disque invisible : contrôleur et inventaire avant toute écriture. Un doctor sain ne prouve ni ACL, ni OAuth, ni compatibilité universelle.

[↗](https://aguja.transcendenceia.net/fr/docs#problemas)

## Terminer sans accès oublié

Résumez observations, modifications et vérifications. Fermez les sessions, terminez les écritures et arrêtez proprement. Vérifiez les fichiers sur la destination et conservez originaux/sauvegardes jusqu’à acceptation du propriétaire.

Retirez les nœuds temporaires et révoquez les clés inutiles. Vérifiez les jetons persistants sur USB et traitez profils/images privés par une procédure approuvée et récupérable. Ne retirez pas des accès étrangers au travail et ne détruisez pas les preuves. Signalez les limites restantes.

[↗](https://aguja.transcendenceia.net/fr/docs#terminar)

## Ce qui est vérifié et ce qu’on ne peut pas déduire

L’édition publique supprime comptes LA AGUJA et relais propriétaire. Tests de préparation, paquets et VM documentent certains parcours, pas tous les PC physiques. L’Imager 0.9.2 corrige le titre en sept langues ; l’image reste 0.9.0. Les captures antérieures gardent leur version réelle.

Relecture ne signifie pas démarrage universel ; panneau/CLI/session portable ne signifie pas authentification IA. Inscription locale ne signifie pas SSH autorisé. Windows n’a pas de sauvegarde USB intégrée ni de signature Authenticode reconnue. Aucune chaîne Secure Boot universelle signée.

[↗](https://aguja.transcendenceia.net/fr/docs#validacion)

## Références et prochaine étape

Les liens du haut donnent téléchargements et code. La référence espagnole approfondie conserve le manuel original de 26 chapitres. Ce guide couvre les mêmes étapes opérationnelles en français. Les captures gardent leur provenance et leur version. Imprimez cette page pour un PDF français ; le PDF historique séparé est espagnol.

Consultez OpenSSH, Tailscale/Headscale, ddrescue, TestDisk et Microsoft BitLocker pour vos versions. Code propre GPL-3.0-or-later ; composants tiers sous leurs licences. Décrivez versions et symptômes expurgés dans les tickets, sans mots de passe, jetons, clés privées ni images privées.

[↗](https://aguja.transcendenceia.net/fr/docs#referencias)
