"""Application GTK 3 et fenêtre principale (squelette, HOST-001).

Les états réels (résultat de la détection, démarrage/arrêt du serveur,
informations de connexion...) arriveront avec HOST-070 et les issues
suivantes. Pour l'instant, l'activation affiche une fenêtre vide.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gtk, GLib  # noqa: E402  (après gi.require_version)

APPLICATION_ID = "org.poongaloo.secondscreenhost"
WINDOW_TITLE = "SecondScreenHost"
DEFAULT_WIDTH = 480
DEFAULT_HEIGHT = 320


class Application(Gtk.Application):
    """Application GTK de SecondScreenHost.

    Le paramètre `self_test`, s'il vaut True, referme l'application juste
    après l'affichage de la fenêtre : utilisé uniquement pour vérifier de
    façon automatisée (sans intervention humaine) que la fenêtre se
    construit et s'affiche sans erreur, par exemple dans un environnement
    isolé avec Xvfb. Il n'est jamais activé lors d'un usage normal.
    """

    def __init__(self, self_test: bool = False) -> None:
        super().__init__(application_id=APPLICATION_ID)
        self._self_test = self_test

    def do_activate(self) -> None:  # noqa: N802 (nom imposé par GTK)
        window = self.props.active_window
        if window is None:
            window = Gtk.ApplicationWindow(application=self, title=WINDOW_TITLE)
            window.set_default_size(DEFAULT_WIDTH, DEFAULT_HEIGHT)
        window.present()

        if self._self_test:
            GLib.idle_add(self._quit_after_self_test)

    def _quit_after_self_test(self) -> bool:
        self.quit()
        return GLib.SOURCE_REMOVE


def main(self_test: bool = False) -> int:
    """Construit l'application et lance sa boucle d'événements.

    Ne prend pas les arguments de la ligne de commande bruts : GTK sait les
    interpréter lui-même (`Gtk.Application.run`), ce qui inclurait des
    options GTK/GLib standard non pertinentes ici. Voir `__main__.py`, qui
    est le seul endroit qui lit `sys.argv`.
    """
    app = Application(self_test=self_test)
    return app.run([])
