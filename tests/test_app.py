"""Tests de `secondscreen_host.ui.app`.

Construire un `Gtk.Application` ne se connecte pas à un serveur
d'affichage (vérifié manuellement : ça fonctionne même sans `$DISPLAY`) ;
seule l'activation (`do_activate`, donc `app.run()`) en a besoin. Ce fichier
ne teste donc que la construction, pas l'affichage réel d'une fenêtre — la
vérification qu'une fenêtre s'affiche réellement se fait dans un
environnement avec un serveur X (voir `scripts/gtk-smoke-test.sh`, exécuté
dans un conteneur jetable avec Xvfb).

Si PyGObject / GTK 3 ne sont pas installés (paquets système, voir
README.md), ces tests sont ignorés plutôt qu'en échec : ce n'est pas une
dépendance Python ordinaire (voir AGENTS.md).
"""

import pytest

gi = pytest.importorskip("gi")
gi.require_version("Gtk", "3.0")

from secondscreen_host.ui.app import APPLICATION_ID, Application  # noqa: E402
from secondscreen_host.ui.main_window import WINDOW_TITLE  # noqa: E402


def test_application_constructs_without_a_display() -> None:
    app = Application()
    assert app.get_application_id() == APPLICATION_ID


def test_application_self_test_flag_is_stored() -> None:
    app = Application(self_test=True)
    assert app._self_test is True


def test_window_title_constant_is_not_empty() -> None:
    assert WINDOW_TITLE
