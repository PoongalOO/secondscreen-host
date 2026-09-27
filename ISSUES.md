# Backlog / Issues

Numérotation `HOST-xxx` (pour ne pas confondre avec les `SS-xxx` du projet SecondScreen). Labels conseillés : `P0`, `P1`, `P2`, `gtk`, `system`, `security`, `test`, `docs`. Voir [CAHIER_DES_CHARGES.md](CAHIER_DES_CHARGES.md) pour le F0x référencé par chaque epic, et [AGENTS.md](AGENTS.md) pour les contraintes de développement.

## Epic E0 — Initialisation

### HOST-001 — Squelette du projet Python + GTK 3 — P0
Structure de paquets (logique pure séparée du code GTK, voir AGENTS.md), point d'entrée exécutable, environnement virtuel documenté (README). Une fenêtre GTK vide se lance sur Ubuntu et sur MX Linux.

### HOST-002 — CI : lint et tests unitaires — P1
GitHub Actions : lint Python, `pytest` sur la logique pure (pas besoin d'un vrai serveur X ni d'un environnement graphique pour ces tests-là). Artefact de rapport de tests.

## Epic E1 — Détection de l'environnement (F01)

### HOST-010 — Détecter les outils système requis — P0
Vérifie la présence de `xrandr`, `cvt`, `x11vnc` (et `Xorg` + le pilote `dummy` pour le repli, HOST-030). Message clair et action bloquée si l'un manque ; jamais un plantage.

### HOST-011 — Détecter la session graphique (Xorg/Wayland) — P0
Message explicite et renvoi vers les guides manuels du projet SecondScreen si la session n'est pas Xorg. Vérifier la méthode de détection sur les deux systèmes cibles : `$XDG_SESSION_TYPE` seul n'est pas garanti fiable sur toutes les configurations, à confirmer.

### HOST-012 — Analyser la sortie de `xrandr --query` — P0
Fonction pure (aucun appel système dans cette fonction elle-même) : écran principal, sorties `VIRTUAL*` disponibles et leur état (`connected`/`disconnected`), position `+X+Y` d'une sortie déjà active. Fixtures de test à partir de plusieurs sorties réelles : avec sortie virtuelle (Intel/AMD), sans (NVIDIA propriétaire), une sortie déjà positionnée.

## Epic E2 — Écran virtuel étendu (F02)

### HOST-020 — Construire les commandes `xrandr` — P0
Fonction pure qui construit `--newmode`/`--addmode`/`--output ... --right-of` à partir du nom de sortie détecté (HOST-012) et de la ligne `Modeline` de `cvt`. Ne les exécute pas : seulement la construction, testable sans appel système.

### HOST-021 — Exécuter la configuration et relire la position assignée — P0
Exécute les commandes réelles (HOST-020), puis relit `xrandr --query` pour connaître le `+X+Y` réellement assigné (jamais supposé ou recalculé à l'avance). Un échec à n'importe quelle étape doit être rapporté clairement, sans laisser le système dans un état à moitié configuré non signalé.

### HOST-022 — Calculer le rectangle `--clip` pour x11vnc — P0
Fonction pure : combine largeur, hauteur et position (HOST-021) en la chaîne attendue par `x11vnc -clip`. Cas limites testés : position (0,0), grandes coordonnées, écran principal à droite au lieu de à gauche.

## Epic E3 — Repli : écran isolé (F03)

### HOST-030 — Générer la configuration Xorg `dummy` — P1
Fonction pure qui produit le contenu du fichier de configuration (mode 1280×800, pilote `dummy`), comparable à celui déjà écrit et vérifié dans `GUIDE_UBUNTU.md`/`GUIDE_MX_LINUX.md` du projet SecondScreen. Testée par comparaison de contenu, pas par exécution réelle de Xorg.

### HOST-031 — Démarrer/arrêter le second serveur X — P1
Trouve un numéro d'affichage libre, lance `Xorg` avec la configuration (HOST-030), gère une éventuelle élévation de privilèges nécessaire. L'état affiché à l'utilisateur doit dire clairement que c'est un **second bureau séparé**, pas une extension du bureau existant (cahier des charges, F03).

## Epic E4 — Serveur VNC (F04)

### HOST-040 — Construire la commande `x11vnc` — P0
Fonction pure : assemble la commande selon le mode (étendu avec `--clip`, HOST-022 ; ou isolé sans, HOST-031), le port, le mot de passe. **Le mot de passe ne doit apparaître dans aucune représentation textuelle journalisable de la commande construite** (voir HOST-090) : à concevoir pour que ce soit structurellement impossible de l'oublier, pas seulement vérifié a posteriori.

### HOST-041 — Démarrer/arrêter x11vnc et suivre son état — P0
Lance le processus, détecte le succès ou l'échec réel (pas seulement « la commande a été lancée » : lire sa sortie/erreur), bouton Démarrer/Arrêter dans l'interface. Aucun processus orphelin après arrêt (voir HOST-080).

### HOST-042 — Redemander le mot de passe à chaque démarrage — P0
Champ de saisie masqué (pas en clair à l'écran), jamais écrit sur disque (CAHIER_DES_CHARGES.md, décision prise), effacé de la mémoire du processus dès que le serveur s'arrête — en notant explicitement la limite de Python sur ce point (une `str` n'est pas effaçable de façon garantie, contrairement au `CharArray` utilisé côté Android).

## Epic E5 — Informations de connexion (F05)

### HOST-050 — Afficher IP/port/mot de passe copiables — P1
Détection de l'adresse IP locale réelle (pas `127.0.0.1` ; gérer le cas de plusieurs interfaces réseau). Bouton « Copier » pour l'adresse et le port. Mot de passe masqué par défaut, révélable par l'utilisateur.

## Epic E6 — Persistance des réglages (F06)

### HOST-060 — Mémoriser la sortie virtuelle choisie et le port — P2
Fichier de configuration utilisateur (répertoire de configuration XDG). Ne mémorise jamais le mot de passe (voir HOST-042). Doit rester compatible avec une configuration matérielle qui change entre deux lancements (ne pas supposer qu'une sortie mémorisée existe toujours).

## Epic E7 — Interface GTK / UX

### HOST-070 — Fenêtre principale avec état global — P0
États explicites (aucun écran virtuel détecté / écran prêt, serveur arrêté / serveur actif avec adresse). Un bouton d'action principal dont le libellé change selon l'état (cahier des charges, UX V1).

### HOST-071 — Panneau de détails techniques — P2
Résultat de la détection (HOST-010/011/012), sorties `xrandr`, dernière erreur : visible sur demande, pas imposé par défaut.

### HOST-072 — Avertissement de sécurité visible — P0
Rappel dans l'interface que VNC classique n'est pas chiffré, à réserver à un réseau local de confiance — cohérent avec l'avertissement déjà présent dans l'application Android SecondScreen.

## Epic E8 — Fiabilité

### HOST-080 — Nettoyage systématique des processus — P0
À la fermeture normale de l'application, sur erreur, et sur plantage (gestion de signal / `atexit`) : aucun `x11vnc` ni `Xorg` (HOST-031) ne doit survivre. Test qui le vérifie, pas seulement une relecture du code.

### HOST-081 — Gestion des erreurs de commandes externes — P0
Toute commande externe (HOST-021, HOST-041) dont le code de retour est non nul, ou dont la sortie ne correspond pas au format attendu, produit un message compréhensible dans l'interface. Jamais une exception non gérée qui ne serait visible que dans un terminal.

## Epic E9 — Sécurité

### HOST-090 — Ne jamais journaliser le mot de passe — P0
Revue systématique du code et test qui recherche le mot de passe (un canari, comme `hygiene/SecretCanaryTest` du projet SecondScreen) dans toute sortie journalisée ou affichée en dehors du champ de saisie prévu.

### HOST-091 — Pas de serveur sans mot de passe par défaut — P1
Le champ mot de passe est obligatoire par défaut avant de pouvoir démarrer le serveur. Si un mode sans mot de passe existe un jour, ce doit être un choix explicite et déconseillé dans l'interface, jamais le comportement par défaut.

## Epic E10 — Tests et compatibilité

### HOST-100 — Suite de tests de la logique pure — P0
Rassemble et maintient les tests unitaires de HOST-012, HOST-020, HOST-022, HOST-030, HOST-040 : aucun ne doit dépendre d'un vrai serveur X, de GTK, ni d'un vrai `x11vnc`.

### HOST-101 — Test sur PC Ubuntu réel — P0
Écran étendu (F02) **et** repli isolé (F03), les deux, avec une vraie tablette SecondScreen qui se connecte au résultat.

### HOST-102 — Test sur PC MX Linux réel — P0
Idem HOST-101, sur MX Linux.

### HOST-103 — Test avec pilote NVIDIA propriétaire — P1
Confirme que l'absence de sortie `VIRTUAL*` déclenche bien, et seulement dans ce cas, le repli vers l'écran isolé (pas de faux positif qui proposerait le repli alors qu'une sortie virtuelle existe, ni l'inverse).

## Epic E11 — Documentation et distribution

### HOST-110 — README : installation et utilisation — P0
Dépendances système à installer avant de lancer l'application, lancement depuis les sources (environnement virtuel Python).

### HOST-111 — Choisir et documenter le mode de distribution — P2
`.deb`, AppImage, ou installation via `pip`/environnement virtuel uniquement : décision différée dans le cahier des charges (« Hors périmètre initial »), à reprendre ici une fois la V1 utile.

### HOST-112 — Licence et notices — P2
Fichier `LICENSE` et notices des dépendances tierces (PyGObject et ce qu'elle entraîne), sur le modèle de `LICENSE`/`NOTICE.md` du projet SecondScreen, sauf décision contraire.

## Reporté après la V1 (hors périmètre initial, voir CAHIER_DES_CHARGES.md)

Non détaillé tant que la V1 n'existe pas ; à transformer en issues complètes le moment venu.

- **HOST-200** — Icône de zone de notification (dépend de l'environnement de bureau, GNOME en particulier) ;
- **HOST-201** — Équivalent Windows (pilote d'affichage indirect signé — projet à part) ;
- **HOST-202** — QR code pour la connexion (suppose une modification séparée de l'application Android SecondScreen) ;
- **HOST-203** — Mémorisation optionnelle du mot de passe via le trousseau du bureau (`libsecret`), en choix explicite seulement.
