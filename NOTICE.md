# Notices tierces (HOST-112)

SecondScreenHost est sous licence MIT (voir [LICENSE](LICENSE)). Cette page documente les dépendances tierces, sur le modèle de [NOTICE.md](https://github.com/PoongalOO/virtualScreen/blob/main/NOTICE.md) du projet SecondScreen. Contrairement à ce projet-là (une application Android qui produit un unique APK), SecondScreenHost ne produit aucun binaire compilé : il n'y a rien à « embarquer » au sens strict. La distinction pertinente ici est plutôt entre ce qui s'installe avec l'application (dépendance Python) et ce qui reste un outil système séparé, simplement lancé comme processus externe (voir AGENTS.md, « on enveloppe x11vnc, on ne réimplémente pas »). Versions vérifiées le 2026-09-27 sur Ubuntu 22.04 (`apt-cache policy`, `pip show`), pas supposées.

## Dépendance d'exécution (paquet système, pas `pip`)

| Dépendance | Version (Ubuntu 22.04) | Licence | Rôle |
|---|---|---|---|
| [PyGObject](https://gitlab.gnome.org/GNOME/pygobject) (`python3-gi`) | 3.42.1 | [LGPL 2.1+](https://gitlab.gnome.org/GNOME/pygobject/-/blob/master/COPYING) | Liaisons Python de GObject Introspection, utilisées pour piloter GTK 3 depuis `secondscreen_host/ui/`. |
| [GTK 3](https://gitlab.gnome.org/GNOME/gtk) (`gir1.2-gtk-3.0`, `libgtk-3-0`) | 3.24.33 | [LGPL 2.1+](https://gitlab.gnome.org/GNOME/gtk/-/blob/gtk-3-24/COPYING) | Bibliothèque d'interface graphique elle-même (voir AGENTS.md, « Contraintes non négociables » : GTK 3 imposé, pas GTK 4/Qt/Electron). |

Installées via les paquets système (`sudo apt install python3-gi gir1.2-gtk-3.0`, voir README.md), jamais via `pip` : ce projet ne les vendorise pas, ne les redistribue pas, et ne modifie aucun de leurs fichiers. Étant en LGPL (et non GPL), leur usage depuis un projet sous licence MIT ne pose pas de problème de compatibilité tant qu'elles restent des bibliothèques dynamiques séparées, non liées statiquement — ce qui est le cas ici (liaison dynamique standard via GObject Introspection).

## Utilisées seulement pour développer et tester (jamais nécessaires pour exécuter l'application)

| Dépendance | Version | Licence | Rôle |
|---|---|---|---|
| [pytest](https://docs.pytest.org/) | 9.1.1 | [MIT](https://github.com/pytest-dev/pytest/blob/main/LICENSE) | Exécute la suite de tests (`tests/`). |
| [ruff](https://docs.astral.sh/ruff/) | 0.16.9 | [MIT](https://github.com/astral-sh/ruff/blob/main/LICENSE) | Lint (`ruff check .`, voir `pyproject.toml`). |

Déclarées uniquement dans `[project.optional-dependencies] dev` de `pyproject.toml` (`pip install -e .[dev]`) : absentes d'une installation normale (`pip install -e .` seul, ou `secondscreen-host` une fois le paquet construit).

## Outils système invoqués comme processus externes (ni dépendances Python, ni bibliothèques liées)

Ce projet lance ces programmes (`subprocess`), lit leur sortie, les arrête — il ne les modifie pas, ne les redistribue pas, et n'en a besoin d'aucune partie du code source (voir CAHIER_DES_CHARGES.md, « Hors périmètre initial » : « on enveloppe x11vnc, on ne réimplémente pas »). Listés ici par transparence, pas parce que leur licence engagerait celle de ce dépôt.

| Outil | Paquet Ubuntu/MX Linux | Licence | Rôle |
|---|---|---|---|
| [x11vnc](https://github.com/LibVNC/x11vnc) | `x11vnc` | [GPL 2.0](https://github.com/LibVNC/x11vnc/blob/master/COPYING) | Serveur VNC/RFB réel (F04). |
| `xrandr`, `Xorg` | `x11-xserver-utils`, `xserver-xorg-core` | [MIT/X11](https://gitlab.freedesktop.org/xorg/app/xrandr/-/blob/master/COPYING) | Configuration de l'écran virtuel (F02) et second serveur X du repli isolé (F03). |
| `xserver-xorg-video-dummy` | `xserver-xorg-video-dummy` | [MIT/X11](https://gitlab.freedesktop.org/xorg/driver/xf86-video-dummy) | Pilote d'affichage factice du repli isolé (F03). |
| `cvt` | `xcvt` | [MIT/X11](https://gitlab.freedesktop.org/xorg/app/xcvt) | Calcul du mode d'affichage 1280×800 (HOST-020). |
| `ip` | `iproute2` | [GPL 2.0](https://github.com/iproute2/iproute2/blob/main/COPYING) | Détection de l'adresse IP locale (HOST-050). |
| `pkexec` | `policykit-1` | [LGPL 2.1+](https://gitlab.freedesktop.org/polkit/polkit/-/blob/master/COPYING) | Élévation ponctuelle de privilèges pour le repli isolé (F03, HOST-031). |

## Vérifier soi-même

```bash
apt-cache policy python3-gi gir1.2-gtk-3.0
pip show pytest ruff
```

Toute nouvelle dépendance Python doit être ajoutée à cette page avant d'être fusionnée (voir AGENTS.md : « aucune dépendance Python au-delà de PyGObject sans justification explicite »).
