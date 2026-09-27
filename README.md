# SecondScreenHost

Application PC (Ubuntu, MX Linux) qui automatise la configuration d'un écran virtuel 1280×800 et d'un serveur VNC restreint à cette zone, pour servir de second écran à [SecondScreen](https://github.com/PoongalOO/virtualScreen) sur une tablette Android.

Voir [CAHIER_DES_CHARGES.md](CAHIER_DES_CHARGES.md), [ISSUES.md](ISSUES.md) et [AGENTS.md](AGENTS.md).

## État

Fenêtre principale fonctionnelle (HOST-070/071/072) : détection au lancement (outils système, session Xorg/Wayland), bouton unique qui configure l'écran virtuel (étendu si une sortie `VIRTUAL*` est disponible, sinon repli sur un écran isolé), démarre/arrête `x11vnc`, affiche l'adresse/le port/le mot de passe une fois le serveur actif, panneau de détails techniques, avertissement de sécurité visible en permanence. La sortie choisie et le port sont mémorisés entre deux lancements (HOST-060), jamais le mot de passe. Intégration continue en place (HOST-002) : lint et tests à chaque push/pull request.

Notes honnêtes sur cette V1 : les actions s'exécutent de façon synchrone (l'interface se fige brièvement, moins de 2 secondes en pratique) ; le nettoyage à la fermeture ne couvre que la fermeture normale de la fenêtre (le traitement systématique des plantages est HOST-080, pas encore fait).

## Installation (Ubuntu, MX Linux)

PyGObject (les liaisons Python de GTK) s'installe par les paquets système, pas par `pip` : c'est la façon fiable de l'obtenir sur ces distributions, et `pip install PyGObject` demande par ailleurs les en-têtes de développement de GObject Introspection. Voir AGENTS.md, « Contraintes non négociables ».

```bash
sudo apt install python3 python3-venv python3-gi gir1.2-gtk-3.0
```

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

Les tests qui utilisent GTK (`tests/test_app.py`) ne testent que la construction de l'application, pas l'affichage réel d'une fenêtre (cela ne demande pas de serveur d'affichage — vérifié). Pour vérifier qu'une fenêtre s'affiche réellement, dans un environnement isolé qui ne touche pas l'affichage de la machine courante :

```bash
./scripts/gtk-smoke-test.sh          # ubuntu:22.04 par défaut
./scripts/gtk-smoke-test.sh debian:trixie
```

## Lint

```bash
ruff check .
```

La CI (`.github/workflows/ci.yml`, HOST-002) exécute le lint et les tests à chaque push et pull request sur `main`, avec un rapport de tests publié en artefact.
