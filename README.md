# SecondScreenHost

Application PC (Ubuntu, MX Linux) qui automatise la configuration d'un écran virtuel 1280×800 et d'un serveur VNC restreint à cette zone, pour servir de second écran à [SecondScreen](https://github.com/PoongalOO/virtualScreen) sur une tablette Android.

Voir [CAHIER_DES_CHARGES.md](CAHIER_DES_CHARGES.md), [ISSUES.md](ISSUES.md) et [AGENTS.md](AGENTS.md).

## État

Fenêtre principale fonctionnelle (HOST-070/071/072) : détection au lancement (outils système, session Xorg/Wayland), bouton unique qui configure l'écran virtuel (étendu si une sortie `VIRTUAL*` est disponible, sinon repli sur un écran isolé), démarre/arrête `x11vnc`, affiche l'adresse/le port/le mot de passe une fois le serveur actif, panneau de détails techniques, avertissement de sécurité visible en permanence. La sortie choisie et le port sont mémorisés entre deux lancements (HOST-060), jamais le mot de passe. Nettoyage systématique des processus externes à la fermeture, sur `SIGTERM`/`SIGINT` et sur plantage (HOST-080). Intégration continue en place (HOST-002) : lint et tests à chaque push/pull request, y compris dans un environnement sans GTK ni aucun outil système (HOST-100).

Note honnête sur cette V1 : les actions s'exécutent de façon synchrone (l'interface se fige brièvement, moins de 2 secondes en pratique).

Fonctionnement de bout en bout vérifié par des tests automatisés (conteneurs jetables), **pas encore sur un vrai PC Ubuntu ou MX Linux** (HOST-101/HOST-102, à faire — voir ISSUES.md). L'empaquetage (`.deb`/AppImage) reste volontairement différé jusque-là (décision documentée dans CAHIER_DES_CHARGES.md, « Hors périmètre initial », HOST-111) : seule l'installation depuis les sources ci-dessous est proposée pour l'instant.

## Installation (Ubuntu, MX Linux)

### Paquets système

PyGObject (les liaisons Python de GTK) s'installe par les paquets système, pas par `pip` : c'est la façon fiable de l'obtenir sur ces distributions, et `pip install PyGObject` demande par ailleurs les en-têtes de développement de GObject Introspection. Voir AGENTS.md, « Contraintes non négociables ».

```bash
sudo apt install python3 python3-venv python3-gi gir1.2-gtk-3.0
```

Toujours nécessaires en plus pour que l'application fonctionne (pas seulement pour la développer) — vérifiés au lancement par l'application elle-même (HOST-010), qui affiche un message clair et bloque l'action si l'un manque plutôt que de planter :

```bash
sudo apt install x11-xserver-utils xcvt x11vnc iproute2
```

- `x11-xserver-utils` fournit `xrandr` ;
- `xcvt` fournit `cvt` — **paquet séparé** de `x11-xserver-utils` depuis Ubuntu 22.04/Debian récent, vérifié (bogue déjà rencontré et documenté dans `GUIDE_UBUNTU.md`/`GUIDE_MX_LINUX.md` du projet SecondScreen) ;
- `x11vnc` sert l'écran en VNC (F04) ;
- `iproute2` fournit `ip`, utilisé pour détecter l'adresse IP locale à afficher (HOST-050) — présent par défaut sur la quasi-totalité des installations, listé ici pour l'exhaustivité.

Nécessaires **seulement** si aucune sortie `VIRTUAL*` n'est disponible sur votre carte graphique (repli « écran isolé », F03 — voir CAHIER_DES_CHARGES.md) :

```bash
sudo apt install xserver-xorg-core xserver-xorg-video-dummy policykit-1
```

- `xserver-xorg-core` (le binaire `Xorg`) et `xserver-xorg-video-dummy` (le pilote factice) pour le second serveur X ;
- `policykit-1` fournit `pkexec`, utilisé pour obtenir les privilèges nécessaires à ce second serveur X (aucun mot de passe root permanent, une élévation ponctuelle seulement — voir CAHIER_DES_CHARGES.md, « Plateforme cible »).

### Environnement virtuel Python

Créer l'environnement virtuel avec `--system-site-packages` pour qu'il hérite de `python3-gi` installé au niveau système (sinon `import gi` échoue à l'intérieur du venv) :

```bash
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .[dev]
```

`pip install --upgrade pip` n'est pas cosmétique : sans lui, la version de `pip` fournie par Ubuntu 22.04 (22.0.2) échoue à installer le projet en mode éditable avec l'erreur *« build backend is missing the 'build_editable' hook »* (vérifié).

## Lancer l'application

```bash
python3 -m secondscreen_host
# ou, une fois installée (pip install -e .) :
secondscreen-host
```

## Lancer les tests

```bash
pytest
```

Les tests qui utilisent GTK (`tests/test_app.py`, `tests/test_main_window.py`) ne testent que la construction de l'application, pas l'affichage réel d'une fenêtre (cela ne demande pas de serveur d'affichage — vérifié). Pour vérifier qu'une fenêtre s'affiche réellement, dans un environnement isolé qui ne touche pas l'affichage de la machine courante :

```bash
./scripts/gtk-smoke-test.sh          # ubuntu:22.04 par défaut
./scripts/gtk-smoke-test.sh debian:trixie
```

La logique pure (`secondscreen_host/pure/`) ne dépend jamais de GTK, d'un vrai serveur X, ni d'un vrai `x11vnc`/`xrandr`/`cvt` (HOST-100) : la suite entière tourne (ou s'ignore proprement pour ce qui en a réellement besoin) dans un environnement qui n'a **aucun** de ces paquets installés, pas seulement une session sans affichage :

```bash
python3 -m venv .venv-minimal   # sans --system-site-packages : aucun accès à python3-gi
.venv-minimal/bin/pip install pytest
.venv-minimal/bin/pip install -e .
.venv-minimal/bin/pytest -q
```

Vérifié par un job CI dédié (`.github/workflows/ci.yml`, job `pure-tests-minimal-env`), qui n'installe ni GTK ni aucun outil système : ça a déjà trouvé un vrai bogue une fois (un import GTK caché en tête de `secondscreen_host/__main__.py`, qui faisait planter la collecte de tests au lieu de l'ignorer proprement).

## Lint

```bash
ruff check .
```

La CI (`.github/workflows/ci.yml`, HOST-002) exécute le lint et les tests à chaque push et pull request sur `main`, avec un rapport de tests publié en artefact.

## Licence

[MIT](LICENSE). Dépendances tierces documentées dans [NOTICE.md](NOTICE.md).
