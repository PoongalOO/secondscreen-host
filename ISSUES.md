# Backlog / Issues

Numérotation `HOST-xxx` (pour ne pas confondre avec les `SS-xxx` du projet SecondScreen). Labels conseillés : `P0`, `P1`, `P2`, `gtk`, `system`, `security`, `test`, `docs`. Voir [CAHIER_DES_CHARGES.md](CAHIER_DES_CHARGES.md) pour le F0x référencé par chaque epic, et [AGENTS.md](AGENTS.md) pour les contraintes de développement.

## Résumé

| Epic | Fait | Partiel | À faire |
|---|---|---|---|
| E0 — Initialisation | 2/2 | 0 | 0 |
| E1 — Détection de l'environnement | 3/3 | 0 | 0 |
| E2 — Écran virtuel étendu | 3/3 | 0 | 0 |
| E3 — Repli : écran isolé | 2/2 | 0 | 0 |
| E4 — Serveur VNC | 3/3 | 0 | 0 |
| E5 — Informations de connexion | 1/1 | 0 | 0 |
| E6 — Persistance des réglages | 1/1 | 0 | 0 |
| E7 — Interface GTK / UX | 3/3 | 0 | 0 |
| E8 — Fiabilité | 2/2 | 0 | 0 |
| E9 — Sécurité | 2/2 | 0 | 0 |
| E10 — Tests et compatibilité | 0/4 | 0 | 4 |
| E11 — Documentation et distribution | 0/3 | 0 | 3 |
| **Total** | **22/29** | **0** | **7** |

## Epic E0 — Initialisation

### HOST-001 — Squelette du projet Python + GTK 3 — P0
Structure de paquets (logique pure séparée du code GTK, voir AGENTS.md), point d'entrée exécutable, environnement virtuel documenté (README). Une fenêtre GTK vide se lance sur Ubuntu et sur MX Linux.

**Statut : ✅ Fait** — Paquet `secondscreen_host` (`pure/`, `ui/`), point d'entrée `python3 -m secondscreen_host` / script `secondscreen-host` (`pyproject.toml`). Vérifié dans un conteneur Ubuntu 22.04 jetable avec Xvfb (`scripts/gtk-smoke-test.sh`) : la fenêtre se construit et s'affiche réellement, code de sortie 0. Test MX Linux réel non fait à ce stade (voir HOST-102) ; le venv `--system-site-packages` est documenté dans le README mais pas exécuté ici (pas de `python3-venv` disponible dans cet environnement de développement, sans lien avec le code produit).

### HOST-002 — CI : lint et tests unitaires — P1
GitHub Actions : lint Python, `pytest` sur la logique pure (pas besoin d'un vrai serveur X ni d'un environnement graphique pour ces tests-là). Artefact de rapport de tests.

**Statut : ✅ Fait** — `.github/workflows/ci.yml` : `ubuntu-22.04` (version minimale visée), installation des paquets système GTK 3, `ruff check` puis `pytest --junitxml`, rapport publié en artefact (`actions/upload-artifact`, `if: always()` pour l'avoir même en cas d'échec). Toute la chaîne testée telle quelle dans un conteneur Ubuntu 22.04 jetable avant de l'écrire dans le workflow : lint propre, 6/6 tests, `report.xml` généré correctement. Non vérifié : le run réel sur GitHub Actions lui-même (nécessite le push).

## Epic E1 — Détection de l'environnement (F01)

### HOST-010 — Détecter les outils système requis — P0
Vérifie la présence de `xrandr`, `cvt`, `x11vnc` (et `Xorg` + le pilote `dummy` pour le repli, HOST-030). Message clair et action bloquée si l'un manque ; jamais un plantage.

**Statut : ✅ Fait** — `pure/tools.py` (liste des outils requis, message d'installation avec le bon paquet apt, déduplication des paquets partagés) + `system/tools.py` (`shutil.which`, aucune exécution). `Xorg` séparé dans `FALLBACK_TOOLS` : son absence ne bloque que le repli (F03), pas l'écran étendu (F02). Testé avec de vrais binaires (`python3`) plutôt qu'un `shutil.which` simulé.

### HOST-011 — Détecter la session graphique (Xorg/Wayland) — P0
Message explicite et renvoi vers les guides manuels du projet SecondScreen si la session n'est pas Xorg. Vérifier la méthode de détection sur les deux systèmes cibles : `$XDG_SESSION_TYPE` seul n'est pas garanti fiable sur toutes les configurations, à confirmer.

**Statut : ✅ Fait** — `pure/session.py` : croise `XDG_SESSION_TYPE`, `WAYLAND_DISPLAY` et `DISPLAY` (`WAYLAND_DISPLAY` prioritaire, car XWayland positionne souvent `DISPLAY` aussi). Testé avec la vraie session de la machine de développement (Debian, Xorg) et le comportement documenté de GNOME/Wayland. **Non confirmé** sur les deux systèmes cibles réels (Ubuntu, MX Linux) — reporté à HOST-101/HOST-102, aucun accès à ces machines dans cet environnement.

### HOST-012 — Analyser la sortie de `xrandr --query` — P0
Fonction pure (aucun appel système dans cette fonction elle-même) : écran principal, sorties `VIRTUAL*` disponibles et leur état (`connected`/`disconnected`), position `+X+Y` d'une sortie déjà active. Fixtures de test à partir de plusieurs sorties réelles : avec sortie virtuelle (Intel/AMD), sans (NVIDIA propriétaire), une sortie déjà positionnée.

**Statut : ✅ Fait** — `pure/xrandr.py` + `system/xrandr.py`. Fixture **réellement capturée** sur la machine de développement (Debian, GPU Intel, aucune sortie `VIRTUAL*`) ; fixtures « sortie virtuelle disponible » et « déjà positionnée » **représentatives** du format documenté dans `GUIDE_UBUNTU.md` (pas recapturées sur du matériel réel ici, aucun GPU disponible n'exposant de sortie `VIRTUAL*`) — voir le commentaire en tête de `tests/test_xrandr.py` pour le détail honnête de la provenance. Tolérance aux lignes non reconnues testée explicitement (pas de plantage).

## Epic E2 — Écran virtuel étendu (F02)

### HOST-020 — Construire les commandes `xrandr` — P0
Fonction pure qui construit `--newmode`/`--addmode`/`--output ... --right-of` à partir du nom de sortie détecté (HOST-012) et de la ligne `Modeline` de `cvt`. Ne les exécute pas : seulement la construction, testable sans appel système.

**Statut : ✅ Fait** — `pure/cvt.py` (analyse de la sortie de `cvt`, fixture réellement capturée via `xcvt`, absent de la machine de développement) + `pure/xrandr_commands.py` (construit des `tuple[str, ...]`, jamais de chaîne shell — pas de risque d'injection). `system/cvt.py` pour l'appel réel.

### HOST-021 — Exécuter la configuration et relire la position assignée — P0
Exécute les commandes réelles (HOST-020), puis relit `xrandr --query` pour connaître le `+X+Y` réellement assigné (jamais supposé ou recalculé à l'avance). Un échec à n'importe quelle étape doit être rapporté clairement, sans laisser le système dans un état à moitié configuré non signalé.

**Statut : ✅ Fait** — `system/xrandr_commands.py::configure_extended_screen` : exécute les trois commandes dans l'ordre, s'arrête et rapporte l'étape précise en cas d'échec (`ExtendedScreenConfigurationError.step`), relit `xrandr --query` après coup plutôt que de supposer la position. `system/extended_screen.py::setup_extended_screen` enchaîne le tout (cvt → commandes → relecture) en un seul point d'entrée pour l'interface (HOST-070). Testé avec de vrais `cvt`/`xrandr` sous Xvfb en plus des simulations d'échec par étape.

### HOST-022 — Calculer le rectangle `--clip` pour x11vnc — P0
Fonction pure : combine largeur, hauteur et position (HOST-021) en la chaîne attendue par `x11vnc -clip`. Cas limites testés : position (0,0), grandes coordonnées, écran principal à droite au lieu de à gauche.

**Statut : ✅ Fait** — `pure/clip.py`, prend directement l'`OutputGeometry` de HOST-012/HOST-021. Rejette une géométrie sans sens (taille ou position négative). Les 3 cas limites demandés sont couverts (voir `tests/test_clip.py`).

## Epic E3 — Repli : écran isolé (F03)

### HOST-030 — Générer la configuration Xorg `dummy` — P1
Fonction pure qui produit le contenu du fichier de configuration (mode 1280×800, pilote `dummy`), comparable à celui déjà écrit et vérifié dans `GUIDE_UBUNTU.md`/`GUIDE_MX_LINUX.md` du projet SecondScreen. Testée par comparaison de contenu, pas par exécution réelle de Xorg.

**Statut : ✅ Fait** — `pure/dummy_xorg.py`, structure identique aux guides (sections Device/Monitor/Screen, pilote `dummy`), testée par comparaison avec un fichier golden (`tests/fixtures/dummy_xorg_expected.conf`). Différence assumée avec les guides : la `Modeline` n'est pas figée en dur, elle vient du même `CvtMode` que HOST-020 (calculé une seule fois, réutilisé pour les deux) — utile car la version d'`xcvt` réellement installée ne produit pas exactement les mêmes valeurs que l'exemple des guides.

### HOST-031 — Démarrer/arrêter le second serveur X — P1
Trouve un numéro d'affichage libre, lance `Xorg` avec la configuration (HOST-030), gère une éventuelle élévation de privilèges nécessaire. L'état affiché à l'utilisateur doit dire clairement que c'est un **second bureau séparé**, pas une extension du bureau existant (cahier des charges, F03).

**Statut : ✅ Fait** — `pure/display_number.py` + `system/display_number.py` (numéro libre via `/tmp/.X<N>-lock`) ; `system/dummy_xorg.py` (démarrage via `pkexec`, détection de disponibilité par sondage du verrou plutôt qu'un délai fixe supposé suffisant, arrêt propre et idempotent). `pure/dummy_xorg.py::describe_dummy_screen` porte le message « second bureau séparé » exigé. `sudo` n'a volontairement pas été ajouté en repli de `pkexec` : sans terminal ni `SUDO_ASKPASS`, il resterait bloqué indéfiniment depuis une appli GTK — documenté dans le code plutôt que supposé fonctionner. **Vérifié avec un vrai `Xorg` + pilote `dummy`** dans un conteneur jetable exécuté en root (`elevation_command=[]`, contournant volontairement `pkexec` puisque déjà root) : démarrage réel, `xdpyinfo` confirme 1280×800, arrêt propre, aucun processus orphelin. **Non vérifié** : la boîte de dialogue `pkexec` elle-même (suppose un agent polkit + session graphique réels) — reporté à HOST-101/HOST-102. Un vrai bogue de conception trouvé et corrigé en écrivant les tests : `elevation_command=[]` (« explicitement aucune élévation ») était confondu avec « élévation indisponible » et levait une erreur à tort.

## Epic E4 — Serveur VNC (F04)

### HOST-040 — Construire la commande `x11vnc` — P0
Fonction pure : assemble la commande selon le mode (étendu avec `--clip`, HOST-022 ; ou isolé sans, HOST-031), le port, le mot de passe. **Le mot de passe ne doit apparaître dans aucune représentation textuelle journalisable de la commande construite** (voir HOST-090) : à concevoir pour que ce soit structurellement impossible de l'oublier, pas seulement vérifié a posteriori.

**Statut : ✅ Fait** — `pure/x11vnc_command.py`. Le mot de passe n'est **jamais** un paramètre de cette fonction : elle prend le chemin d'un fichier de mot de passe déjà écrit, transmis via `-passwdfile rm:<chemin>` (jamais `-passwd`, qui l'exposerait en clair dans `ps(1)`). Le préfixe `rm:` fait supprimer le fichier par x11vnc lui-même après une seule lecture — comportement documenté (`x11vnc -help`) et vérifié en conditions réelles. Aucun mot de passe possible en argument par erreur : structurellement, pas seulement vérifié après coup.

### HOST-041 — Démarrer/arrêter x11vnc et suivre son état — P0
Lance le processus, détecte le succès ou l'échec réel (pas seulement « la commande a été lancée » : lire sa sortie/erreur), bouton Démarrer/Arrêter dans l'interface. Aucun processus orphelin après arrêt (voir HOST-080).

**Statut : ✅ Fait** — `system/x11vnc.py`. Démarrage confirmé par la ligne `PORT=<num>` que x11vnc affiche une fois qu'il écoute réellement (`pure/x11vnc_output.py`), jamais par un délai fixe supposé suffisant — distingue un succès (port réellement ouvert) d'un échec silencieux (port déjà utilisé : x11vnc s'arrête tout seul avec un message clair, sans jamais afficher `PORT=`). **Bug d'environnement réel trouvé et contourné** : x11vnc bufferise entièrement sa sortie standard tant qu'elle n'est pas un vrai terminal (comportement libc, pas un bogue x11vnc) — avec un simple tube, la ligne `PORT=` pouvait rester bloquée indéfiniment ; `stdbuf -oL` essayé sans effet ; résolu avec un pseudo-terminal (pty), qui force x11vnc à l'afficher immédiatement (vérifié). Un fil d'arrière-plan continue à lire le pty pendant toute la durée de vie du serveur (pas seulement au démarrage) pour éviter qu'un tampon plein ne bloque x11vnc en usage prolongé, en gardant les dernières lignes pour le diagnostic. **Vérifié avec un vrai `x11vnc` + `Xvfb`** : connexion TCP réelle qui reçoit la bannière du protocole RFB (`RFB 003.008\n`), arrêt propre, aucun processus orphelin.

### HOST-042 — Redemander le mot de passe à chaque démarrage — P0
Champ de saisie masqué (pas en clair à l'écran), jamais écrit sur disque (CAHIER_DES_CHARGES.md, décision prise), effacé de la mémoire du processus dès que le serveur s'arrête — en notant explicitement la limite de Python sur ce point (une `str` n'est pas effaçable de façon garantie, contrairement au `CharArray` utilisé côté Android).

**Statut : ✅ Fait** — `pure/secret.py::Secret` : le mot de passe transite par un `bytearray` mutable, mis à zéro (vérifié par un test qui inspecte les octets, pas seulement l'état) dès `clear()` — appelé automatiquement par `X11VncProcess.stop()` (HOST-041). Jamais écrit sur disque de façon persistante (voir HOST-040 : seulement un fichier temporaire supprimé par x11vnc lui-même). Limite documentée dans le code, pas ignorée : Python ne garantit pas l'effacement d'une `str` sous-jacente. Champ de saisie masqué ajouté avec HOST-070 (`_PasswordDialog`, `Gtk.Entry` avec `set_visibility(False)`), jamais pré-rempli.

## Epic E5 — Informations de connexion (F05)

### HOST-050 — Afficher IP/port/mot de passe copiables — P1
Détection de l'adresse IP locale réelle (pas `127.0.0.1` ; gérer le cas de plusieurs interfaces réseau). Bouton « Copier » pour l'adresse et le port. Mot de passe masqué par défaut, révélable par l'utilisateur.

**Statut : ✅ Fait** — `pure/local_address.py` + `system/local_address.py`. Deux informations combinées : l'adresse que le système choisirait pour une connexion sortante (astuce socket UDP, aucune donnée réellement envoyée, aucun privilège requis) comme suggestion par défaut, et la liste de toutes les adresses IPv4 par interface (`ip -4 -o addr show`, nouvel outil ajouté à HOST-010) pour les cas à plusieurs interfaces. **Filtrage trouvé nécessaire en testant sur une vraie machine** : la machine de développement a une interface Wi-Fi normale, six ponts Docker et un VPN Tailscale — sans filtrer par nom d'interface, plusieurs adresses de ponts Docker (172.17-22.0.1, qui ressemblent à des adresses privées ordinaires) et l'adresse Tailscale auraient été proposées comme si elles étaient joignables depuis le réseau local, ce qui est faux. Fixture de test basée sur cette capture réelle plutôt qu'un exemple inventé. Interface ajoutée avec HOST-070 : adresse et port affichés avec un bouton « Copier » chacun (`Gtk.Clipboard`), mot de passe masqué par défaut avec bouton « Afficher »/« Masquer ».

## Epic E6 — Persistance des réglages (F06)

### HOST-060 — Mémoriser la sortie virtuelle choisie et le port — P2
Fichier de configuration utilisateur (répertoire de configuration XDG). Ne mémorise jamais le mot de passe (voir HOST-042). Doit rester compatible avec une configuration matérielle qui change entre deux lancements (ne pas supposer qu'une sortie mémorisée existe toujours).

**Statut : ✅ Fait** — `pure/settings.py` + `system/settings.py`. Fichier `$XDG_CONFIG_HOME/secondscreen-host/config.json` (repli `~/.config/...`), écriture atomique (fichier temporaire puis renommage) pour qu'un plantage en cours d'écriture ne laisse jamais un fichier à moitié écrit. Chargement défensif : fichier absent, JSON invalide, tronqué, ou avec des champs du mauvais type retombe silencieusement sur les valeurs par défaut plutôt que d'empêcher le démarrage — y compris le piège classique `{"port": true}` (`bool` est une sous-classe d'`int` en Python, gardé explicitement). `resolve_remembered_output` ne réutilise la sortie mémorisée que si elle existe encore parmi les sorties détectées (HOST-012) : jamais supposée valide après un changement de matériel. Aucun champ mot de passe possible : `Settings` n'en a structurellement pas, vérifié aussi par un test canari qui inspecte le fichier écrit sur disque.

## Epic E7 — Interface GTK / UX

### HOST-070 — Fenêtre principale avec état global — P0
États explicites (aucun écran virtuel détecté / écran prêt, serveur arrêté / serveur actif avec adresse). Un bouton d'action principal dont le libellé change selon l'état (cahier des charges, UX V1).

**Statut : ✅ Fait** — `pure/app_state.py` (les 3 états et le libellé du bouton, fonction pure testée) + `ui/main_window.py` (`MainWindow`) qui relie tout ce qui a été construit depuis E1 : détection au lancement (F01, outils + session), bouton unique qui appelle `system/orchestration.py::configure_screen` (choix automatique entre écran étendu F02 et repli isolé F03 selon ce que `xrandr` expose), démarre `x11vnc` via une boîte de dialogue de mot de passe (HOST-042), arrête proprement. Réutilise HOST-060 : sortie choisie et port mémorisés, jamais le mot de passe. **Vérifié avec un vrai clic** (`Gtk.Button.clicked()`, pas une simulation) sous Xvfb : un vrai clic sur « Configurer » déclenche la vraie détection `xrandr`, le vrai repli écran isolé, et échoue proprement (message clair, pas de plantage) faute de `pkexec` — `pkexec` lui-même s'est avéré fondamentalement incompatible avec les conteneurs Docker (« Refusing to render service to dead parents », bogue connu), confirmant que le point de test déjà utilisé ailleurs (`elevation_command=[]`) était le bon choix plutôt qu'une tentative de le contourner. **Limites assumées pour cette V1, documentées dans le code** : actions synchrones (l'interface se fige brièvement pendant l'opération, < 2 s mesuré) ; nettoyage à la fermeture limité à la fermeture normale (HOST-080 traitera les plantages/signaux).

### HOST-071 — Panneau de détails techniques — P2
Résultat de la détection (HOST-010/011/012), sorties `xrandr`, dernière erreur : visible sur demande, pas imposé par défaut.

**Statut : ✅ Fait** — `pure/technical_details.py::format_technical_details`, dans un `Gtk.Expander` (replié par défaut). Réutilise directement les types déjà définis par HOST-010/011/012 (`ToolCheckResult`, `SessionInfo`, `XrandrQueryResult`) plutôt que de dupliquer leur structure.

### HOST-072 — Avertissement de sécurité visible — P0
Rappel dans l'interface que VNC classique n'est pas chiffré, à réserver à un réseau local de confiance — cohérent avec l'avertissement déjà présent dans l'application Android SecondScreen.

**Statut : ✅ Fait** — `pure/security_notice.py`, affiché en permanence en haut de la fenêtre (pas seulement dans les détails techniques).

## Epic E8 — Fiabilité

### HOST-080 — Nettoyage systématique des processus — P0
À la fermeture normale de l'application, sur erreur, et sur plantage (gestion de signal / `atexit`) : aucun `x11vnc` ni `Xorg` (HOST-031) ne doit survivre. Test qui le vérifie, pas seulement une relecture du code.

**Statut : ✅ Fait** — `system/cleanup.py::install_cleanup` : un seul nettoyage idempotent, appelé par la fermeture normale (déjà en place depuis HOST-070), par des gestionnaires `SIGTERM`/`SIGINT` explicites (sans eux, un signal termine Python immédiatement sans exécuter quoi que ce soit), et par un filet `atexit` (pour une exception Python non gérée qui remonterait jusqu'en haut de `main()`). Le gestionnaire de signal rétablit le comportement par défaut puis se re-signale lui-même après le nettoyage : le code de sortie reste celui, conventionnel, d'un arrêt par signal. **Vérifié par de vrais sous-processus et de vrais signaux envoyés depuis l'extérieur** (pas une simulation en mémoire) : le critère d'acceptation de l'issue elle-même — un vrai `Xorg` (écran isolé) et un vrai `x11vnc`, un vrai `SIGTERM` envoyé au processus parent, plus aucun des deux processus après coup, vérifié par l'OS (`os.kill(pid, 0)`), pas par relecture du code. Testé aussi pour `SIGINT` et la sortie normale (`atexit`), stable sur plusieurs exécutions.

### HOST-081 — Gestion des erreurs de commandes externes — P0
Toute commande externe (HOST-021, HOST-041) dont le code de retour est non nul, ou dont la sortie ne correspond pas au format attendu, produit un message compréhensible dans l'interface. Jamais une exception non gérée qui ne serait visible que dans un terminal.

**Statut : ✅ Fait** — la partie « code de retour non nul / sortie inattendue » était déjà couverte au fil des epics précédentes (chaque module `system/*` transforme ses échecs en exception typée avec un message clair : `XrandrQueryError`, `CvtError`, `DummyScreenStartError`, `ExtendedScreenConfigurationError`, `X11VncStartError`, `LocalAddressDetectionError`, regroupées par `ScreenConfigurationError` pour l'interface). Ce qui manquait : un filet de sécurité dans `ui/main_window.py::_on_primary_button_clicked` pour ce qui n'a pas été anticipé (un bogue, une exception d'un module tiers) — ajouté (`except Exception`, volontairement large et documenté comme tel), testé en simulant un échec d'un type non prévu et en vérifiant qu'il est affiché plutôt que de remonter.

## Epic E9 — Sécurité

### HOST-090 — Ne jamais journaliser le mot de passe — P0
Revue systématique du code et test qui recherche le mot de passe (un canari, comme `hygiene/SecretCanaryTest` du projet SecondScreen) dans toute sortie journalisée ou affichée en dehors du champ de saisie prévu.

**Statut : ✅ Fait** — Revue statique (`tests/test_log_hygiene.py`) : aucun `print()` dans le code de l'application (vérifié, zéro résultat) ; la liste des appels à `Secret.reveal()` est figée à deux endroits revus (fichier de mot de passe temporaire, champ masqué GTK) — un nouvel appel ajouté ailleurs fait échouer ce test, comme rappel à revoir à la main. Canari à l'exécution (`tests/test_secret_canary.py`, même principe que `hygiene/SecretCanaryTest` du projet SecondScreen) : une valeur de mot de passe distinctive traverse un vrai `x11vnc` réel, recherchée ensuite dans la ligne de commande réelle du processus (`/proc/<pid>/cmdline`, ce que `ps(1)` montrerait), sa sortie capturée, un message d'échec, et le fichier de réglages — absente partout. **Nettoyage trouvé en cours de route** : un attribut `_pending_secret` déclaré mais jamais utilisé (reliquat d'une itération de conception antérieure) — supprimé.

### HOST-091 — Pas de serveur sans mot de passe par défaut — P1
Le champ mot de passe est obligatoire par défaut avant de pouvoir démarrer le serveur. Si un mode sans mot de passe existe un jour, ce doit être un choix explicite et déconseillé dans l'interface, jamais le comportement par défaut.

**Statut : ✅ Fait** — **Vrai bogue trouvé en vérifiant** : le refus d'un mot de passe vide n'était garanti que dans la boîte de dialogue (HOST-070) ; `system/x11vnc.py::start_x11vnc`, appelé directement, acceptait un `Secret("")` sans broncher. Corrigé à la source : refusé avant même d'écrire un fichier ou de lancer un processus, structurellement, pas seulement dans l'interface. Vérifié aussi que `x11vnc` lui-même refuse un fichier de mot de passe vide plutôt que de servir sans authentification (« cannot read a valid line from passwdfile », comportement réel confirmé, pas supposé) — mais notre propre garde-fou ne s'appuie pas uniquement sur ce comportement externe.

## Epic E10 — Tests et compatibilité

### HOST-100 — Suite de tests de la logique pure — P0
Rassemble et maintient les tests unitaires de HOST-012, HOST-020, HOST-022, HOST-030, HOST-040 : aucun ne doit dépendre d'un vrai serveur X, de GTK, ni d'un vrai `x11vnc`.

**Statut : ⬜ À faire**

### HOST-101 — Test sur PC Ubuntu réel — P0
Écran étendu (F02) **et** repli isolé (F03), les deux, avec une vraie tablette SecondScreen qui se connecte au résultat.

**Statut : ⬜ À faire**

### HOST-102 — Test sur PC MX Linux réel — P0
Idem HOST-101, sur MX Linux.

**Statut : ⬜ À faire**

### HOST-103 — Test avec pilote NVIDIA propriétaire — P1
Confirme que l'absence de sortie `VIRTUAL*` déclenche bien, et seulement dans ce cas, le repli vers l'écran isolé (pas de faux positif qui proposerait le repli alors qu'une sortie virtuelle existe, ni l'inverse).

**Statut : ⬜ À faire**

## Epic E11 — Documentation et distribution

### HOST-110 — README : installation et utilisation — P0
Dépendances système à installer avant de lancer l'application, lancement depuis les sources (environnement virtuel Python).

**Statut : ⬜ À faire**

### HOST-111 — Choisir et documenter le mode de distribution — P2
`.deb`, AppImage, ou installation via `pip`/environnement virtuel uniquement : décision différée dans le cahier des charges (« Hors périmètre initial »), à reprendre ici une fois la V1 utile.

**Statut : ⬜ À faire**

### HOST-112 — Licence et notices — P2
Fichier `LICENSE` et notices des dépendances tierces (PyGObject et ce qu'elle entraîne), sur le modèle de `LICENSE`/`NOTICE.md` du projet SecondScreen, sauf décision contraire.

**Statut : ⬜ À faire**

## Reporté après la V1 (hors périmètre initial, voir CAHIER_DES_CHARGES.md)

Non détaillé tant que la V1 n'existe pas ; à transformer en issues complètes le moment venu.

- **HOST-200** — Icône de zone de notification (dépend de l'environnement de bureau, GNOME en particulier) ;
- **HOST-201** — Équivalent Windows (pilote d'affichage indirect signé — projet à part) ;
- **HOST-202** — QR code pour la connexion (suppose une modification séparée de l'application Android SecondScreen) ;
- **HOST-203** — Mémorisation optionnelle du mot de passe via le trousseau du bureau (`libsecret`), en choix explicite seulement.
