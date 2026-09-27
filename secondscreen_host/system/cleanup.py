"""Nettoyage systématique des processus externes à la fermeture, une
erreur, ou un plantage de l'application (HOST-080).

`Gtk.Widget.connect("destroy", ...)` (déjà utilisé par `MainWindow`) ne
couvre que la fermeture normale de la fenêtre. Un signal `SIGTERM` (envoyé
par exemple par une session qui se termine, `systemd`, ou `kill`) ou
`SIGINT` (Ctrl+C dans un terminal) termine le processus Python
immédiatement, sans exécuter ce gestionnaire ni les callbacks `atexit`,
sauf si un gestionnaire de signal explicite est installé — ce que ce
module fait. Un filet `atexit` couvre en plus le cas d'une exception
Python non gérée qui remonterait jusqu'en haut de `main()`.

`callback` doit être idempotent (rappelable plusieurs fois sans effet
indésirable) : `X11VncProcess.stop()` et `DummyScreenProcess.stop()` le
sont déjà (vérifiés, voir leurs tests) — plusieurs mécanismes (fermeture
normale, signal, `atexit`) peuvent chacun l'appeler, dans n'importe quel
ordre, y compris plus d'une fois.
"""

from __future__ import annotations

import atexit
import signal
from collections.abc import Callable

CleanupCallback = Callable[[], None]

_TERMINATION_SIGNALS = (signal.SIGTERM, signal.SIGINT)


def install_cleanup(callback: CleanupCallback) -> None:
    """Installe `callback` comme gestionnaire pour `SIGTERM`/`SIGINT` et
    comme filet `atexit`."""
    atexit.register(callback)

    def _handle_signal(signum: int, _frame: object) -> None:
        callback()
        # Rétablit le comportement par défaut puis se re-signale
        # soi-même : le processus se termine avec le code de sortie
        # conventionnel d'un arrêt par signal, plutôt qu'un simple
        # `sys.exit()` qui donnerait un code de sortie différent.
        signal.signal(signum, signal.SIG_DFL)
        signal.raise_signal(signum)

    for sig in _TERMINATION_SIGNALS:
        signal.signal(sig, _handle_signal)
