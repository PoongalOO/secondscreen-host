# Cahier des charges — SecondScreenHost

## 1. Contexte

[SecondScreen](https://github.com/PoongalOO/virtualScreen) transforme une tablette Android (GT-P5110, Android 4.2.2) en second écran d'un PC, en s'y connectant en RFB/VNC. Le PC doit, de son côté, exposer un écran virtuel 1280×800 et un serveur VNC qui ne partage que cette zone.

Cette configuration côté PC (guides `GUIDE_UBUNTU.md`, `GUIDE_MX_LINUX.md` du projet SecondScreen) demande aujourd'hui une dizaine de commandes en ligne de commande (`xrandr --newmode`, `--addmode`, `--output ... --right-of`, calcul du décalage `+X+Y`, lancement de `x11vnc --clip`...), dont certaines valeurs doivent être recopiées d'une commande à l'autre. C'est fiable une fois compris, mais trop complexe pour un usage courant.

**SecondScreenHost** est une application PC séparée qui automatise cette configuration : elle ne remplace pas les guides (qui restent la référence technique et le filet de sécurité en cas de problème), elle fait à la place de l'utilisateur ce qu'ils décrivent.

## 2. Objectifs

### 2.1 Objectif principal

Permettre de préparer et de lancer, en une action, un écran virtuel 1280×800 et un serveur VNC restreint à cette zone, sur un PC Linux (Ubuntu, MX Linux), sans commande à taper ni valeur à recopier à la main.

### 2.2 Objectifs secondaires

- détecter automatiquement une sortie d'affichage virtuelle utilisable (`VIRTUAL*`) et l'écran principal ;
- si aucune sortie virtuelle n'est disponible (pilote qui ne l'expose pas), proposer automatiquement le repli « écran isolé » (pilote `dummy`) plutôt que de simplement échouer ;
- gérer la saisie du mot de passe VNC et le cycle de vie du serveur (démarrer, arrêter, état courant) ;
- afficher clairement l'adresse, le port et le mot de passe à saisir dans SecondScreen ;
- rester lisible et modifiable par quelqu'un qui ne connaît pas le projet ;
- fonctionner avec ce qui est déjà installé sur une machine de bureau Ubuntu/MX Linux standard, sans dépendance lourde à ajouter.

## 3. Hors périmètre initial

- **réimplémentation d'un serveur RFB/VNC** : ce projet enveloppe `x11vnc` (le lance, le configure, le surveille) ; il ne recode pas un serveur — un serveur RFB robuste (capture d'écran, encodages, edge cases réseau) est un projet à lui seul, `x11vnc` fait déjà ce travail ;
- **Windows** : un écran virtuel sous Windows suppose un pilote d'affichage indirect (IddCx) tiers, avec ses propres contraintes de signature — décision et projet séparés, à reconsidérer après une V1 Linux ;
- **Wayland** : la création d'une sortie d'affichage virtuelle réutilisable par n'importe quel programme suppose une session **Xorg** ; Wayland (GNOME par défaut sur Ubuntu récent) n'est pas pris en charge dans un premier temps (voir « Plateforme cible ») ;
- **détection automatique sur tous les pilotes graphiques** : la sortie `VIRTUAL*` dépend du pilote (`modesetting`, `intel`, `amdgpu`) ; le pilote propriétaire NVIDIA ne l'expose généralement pas — dans ce cas, le mode « écran isolé » (pilote `dummy`) reste disponible, mais ce n'est pas une vraie extension du bureau ;
- **QR code / appairage automatique avec la tablette** : l'application Android n'a pas de lecteur de QR code aujourd'hui ; en ajouter un serait une modification séparée du projet SecondScreen, décidée à part ;
- **icône de zone de notification en V1** (voir « UX ») : la prise en charge des icônes système varie selon l'environnement de bureau (GNOME en particulier demande une extension) ; ce n'est pas un blocage pour l'objectif principal, donc reporté après une première version qui fonctionne en fenêtre simple ;
- **empaquetage définitif** (`.deb`, AppImage...) : la V1 peut se lancer depuis les sources (environnement virtuel Python) ; le mode de distribution est une décision à part, une fois l'application utile.

## 4. Plateforme cible

- Ubuntu LTS (22.04, 24.04) et MX Linux, en session **Xorg** (pas Wayland) ;
- Python 3 + GTK 3 (PyGObject, `python3-gi`) : présent ou installable simplement sur ces deux systèmes (Xfce, l'environnement par défaut de MX Linux, est lui-même construit sur GTK 3) ; GTK 4 n'est pas visé pour l'instant, pour rester compatible avec des environnements de bureau plus anciens ;
- dépendances système externes au projet, à documenter et vérifier au démarrage plutôt qu'à supposer présentes : `xrandr` (paquet `x11-xserver-utils`), `cvt` (paquet `xcvt`), `x11vnc`, et pour le repli « écran isolé » `xserver-xorg-video-dummy` ;
- aucune administration système requise pour l'usage courant (pas de service système/`root` permanent) ; une élévation ponctuelle (`pkexec`/`sudo`) peut être nécessaire pour le mode « écran isolé » (`Xorg` sur un second affichage), à confirmer en le testant.

## 5. Architecture fonctionnelle

```text
PC (Ubuntu / MX Linux, session Xorg)
        │
        ├── SecondScreenHost (Python + GTK)
        │         │
        │         ├── détection (xrandr --query : sortie VIRTUAL* + écran principal)
        │         ├── configuration de la sortie virtuelle (xrandr --newmode/--addmode/--output)
        │         │      └── repli : écran isolé (Xorg + pilote dummy) si aucune sortie VIRTUAL*
        │         ├── gestion du mot de passe VNC
        │         └── lancement/arrêt de x11vnc, avec le --clip calculé automatiquement
        │
        └── x11vnc (processus externe, pas réécrit)
                  │ RFB/TCP
                  │ LAN Wi-Fi
                  ▼
        Tablette / application SecondScreen (dépôt séparé)
```

## 6. Fonctionnalités

### F01 — Détection de l'environnement

Au lancement, l'application vérifie et affiche clairement :

- la présence des outils requis (`xrandr`, `cvt`, `x11vnc`) — message explicite et action bloquée si l'un manque, pas une erreur technique brute ;
- la session graphique courante (Xorg/Wayland) — message explicite si Wayland, avec renvoi vers les guides manuels ;
- la liste des sorties `xrandr`, en distinguant l'écran principal (`connected primary`) d'une éventuelle sortie `VIRTUAL*` `disconnected`.

### F02 — Configuration automatique de l'écran virtuel

Si une sortie virtuelle est disponible (F01) :

1. création du mode 1280×800 (équivalent de `cvt 1280 800 60` puis `xrandr --newmode`) ;
2. association à la sortie virtuelle détectée (`--addmode`) ;
3. activation, positionnée à droite de l'écran principal (`--output ... --right-of ...`) ;
4. lecture de la position réelle assignée (`+X+Y`) dans la sortie de `xrandr --query`, pour la suite (F04) — jamais recopiée à la main par l'utilisateur.

Si aucune sortie virtuelle n'est disponible : proposer le repli « écran isolé » (F03) plutôt qu'un échec sans solution.

### F03 — Repli : écran isolé (pilote `dummy`)

Génère la configuration Xorg nécessaire (fichier équivalent à celui des guides), démarre un second serveur X (`:1` ou le premier numéro libre) avec cette configuration, et le signale clairement comme un **second bureau séparé** (pas une extension du bureau existant), pour ne pas laisser croire à l'utilisateur qu'il peut y glisser une fenêtre depuis son bureau principal.

### F04 — Serveur VNC

- **demande le mot de passe VNC à chaque démarrage du serveur** (décision prise, voir « Sécurité ») : jamais stocké sur disque, gardé seulement en mémoire le temps que le serveur tourne, effacé quand il s'arrête ;
- lance `x11vnc` avec `-clip LARGEURxHAUTEUR+X+Y` calculé automatiquement (F02) ou sans `-clip` sur l'écran isolé (F03, qui ne contient déjà que la zone voulue) ;
- affiche l'état du serveur (arrêté / en cours / erreur, avec le message d'erreur réel de `x11vnc` s'il y en a un) ;
- bouton Démarrer / Arrêter.

### F05 — Informations de connexion

Affiche, de façon copiable (sélection/bouton « Copier ») :

- l'adresse IP locale du PC ;
- le port VNC utilisé ;
- (le mot de passe reste masqué par défaut, révélable par l'utilisateur — ce sont les mêmes informations que l'utilisateur doit saisir dans l'écran de connexion de SecondScreen).

### F06 — Persistance des réglages

Mémorise, entre deux lancements : la sortie virtuelle choisie, le port VNC. **Ne mémorise jamais le mot de passe VNC** (F04) : il est redemandé à chaque démarrage du serveur, y compris après un redémarrage de l'application. Ne mémorise rien d'autre qui empêcherait de rejouer la détection (F01) si la configuration matérielle a changé.

## 7. Exigences non fonctionnelles

### Fiabilité

- ne jamais laisser un processus `x11vnc` ou `Xorg` orphelin après un arrêt normal ou un plantage de l'application (nettoyage systématique, y compris à la fermeture de la fenêtre) ;
- toute commande externe (`xrandr`, `x11vnc`...) dont le code de retour est non nul doit produire un message comcompréhensible dans l'interface, jamais un plantage silencieux ni une exception non gérée visible seulement dans un terminal ;
- l'absence d'un outil requis (F01) ne doit jamais planter l'application, seulement bloquer l'action qui en a besoin avec une explication.

### Sécurité

- **mot de passe VNC : décision prise, pas de persistance pour l'instant.** Il est ressaisi à chaque démarrage du serveur (F04/F06), jamais écrit sur disque. Une mémorisation optionnelle (trousseau du bureau via `libsecret`/`Secret Service`, disponible sur GNOME et Xfce) pourra être proposée plus tard, mais seulement comme un choix explicite de l'utilisateur, jamais par défaut — même principe que SECURITY.md pour la reconnexion automatique du projet SecondScreen (mot de passe gardé en mémoire, jamais sur le disque, décision affichée et réversible) ;
- rappel visible dans l'interface que VNC classique n'est pas chiffré et doit rester sur un réseau local de confiance (cohérent avec l'avertissement déjà présent dans l'application Android) ;
- ne jamais lancer `x11vnc` sans mot de passe par défaut ; un mode sans mot de passe, si proposé, doit être un choix explicite et déconseillé dans l'interface ;
- ne journaliser aucun mot de passe ; l'effacer de la mémoire du processus dès que le serveur s'arrête (au mieux : Python ne garantit pas l'effacement d'une `str`, contrairement au `CharArray` utilisé côté Android — à documenter comme limite, pas à ignorer).

### Maintenabilité

- séparation claire entre la détection/orchestration système (xrandr, x11vnc — testable en simulant les commandes) et l'interface GTK ;
- pas de dépendance Python au-delà de PyGObject sans justification explicite ajoutée à ce document ;
- tests automatisés pour la logique pure (analyse de la sortie de `xrandr --query`, calcul du `--clip`, construction des commandes) — la logique qui ne dépend pas de GTK ni d'un vrai serveur X doit rester testable sans les deux, comme le fait le projet SecondScreen pour son protocole RFB.

## 8. UX (V1)

Une fenêtre simple (pas d'icône de zone de notification en V1, voir « Hors périmètre ») :

- un état global visible immédiatement (« Aucun écran virtuel détecté », « Écran virtuel prêt, serveur arrêté », « Serveur actif, adresse ... ») ;
- un bouton d'action principal, dont le libellé change selon l'état (« Configurer », « Démarrer le serveur », « Arrêter ») ;
- un panneau d'informations de connexion (F05), visible seulement une fois le serveur démarré ;
- un accès aux détails techniques (résultat de la détection F01, sorties `xrandr`, dernière erreur) pour ne pas cacher l'information à qui veut comprendre — sans l'imposer à qui veut juste que ça marche.

## 9. Critères d'acceptation V1

La V1 est acceptée si, sur un PC Ubuntu **et** un PC MX Linux, en session Xorg :

1. l'application détecte correctement la présence ou l'absence d'une sortie `VIRTUAL*` ;
2. quand une sortie `VIRTUAL*` existe, un clic configure l'écran virtuel 1280×800 et démarre `x11vnc` restreint à cette zone, sans qu'aucune commande ni valeur n'ait été saisie à la main ;
3. quand aucune sortie `VIRTUAL*` n'existe, le repli « écran isolé » se propose et fonctionne, avec un avertissement clair sur sa limite ;
4. l'application SecondScreen, sur la GT-P5110, se connecte à l'adresse/port affichés et montre un écran 1280×800 exact, sans configuration manuelle côté PC ;
5. arrêter le serveur depuis l'application ne laisse aucun processus `x11vnc`/`Xorg` orphelin ;
6. aucun mot de passe n'apparaît dans un journal ou une sortie console ;
7. la documentation d'installation (dépendances système, lancement) est reproductible par quelqu'un qui découvre le projet.
