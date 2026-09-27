# SecondScreenHost

Application PC (Ubuntu, MX Linux) qui automatise la configuration d'un écran virtuel 1280×800 et d'un serveur VNC restreint à cette zone, pour servir de second écran à [SecondScreen](https://github.com/PoongalOO/virtualScreen) sur une tablette Android.

Voir [CAHIER_DES_CHARGES.md](CAHIER_DES_CHARGES.md), [ISSUES.md](ISSUES.md) et [AGENTS.md](AGENTS.md).

## État

Squelette de l'application (HOST-001) : une fenêtre GTK 3 vide se lance. Pas encore de détection d'écran ni de serveur VNC.

## Installation (Ubuntu, MX Linux)

PyGObject (les liaisons Python de GTK) s'installe par les paquets système, pas par `pip` : c'est la façon fiable de l'obtenir sur ces distributions, et `pip install PyGObject` demande par ailleurs les en-têtes de développement de GObject Introspection. Voir AGENTS.md, « Contraintes non négociables ».

```bash
sudo apt install python3 python3-venv python3-gi gir1.2-gtk-3.0
```

Créer l'environnement virtuel avec `--system-site-packages` pour qu'il hérite de `python3-gi` installé au niveau système (sinon `import gi` échoue à l'intérieur du venv) :

```bash
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install -e .[dev]
```

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
