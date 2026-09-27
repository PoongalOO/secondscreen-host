"""Point d'entrée en ligne de commande de SecondScreenHost.

Deux façons de lancer l'application, équivalentes :
    python3 -m secondscreen_host
    secondscreen-host        (script installé, voir pyproject.toml)

C'est le seul module qui lit `sys.argv` : voir `ui/app.py`.
"""

from __future__ import annotations

import sys

SELF_TEST_FLAG = "--self-test"


def self_test_requested(argv: list[str]) -> bool:
    """Fonction pure : dit si `argv` (sans le nom du programme) demande le
    mode d'auto-test. Séparée de `run()` pour rester testable sans GTK.

    `ui.app` (donc `gi`/GTK) n'est importé qu'à l'intérieur de `run()`, pas
    en tête de ce module : importer `secondscreen_host.__main__` pour
    cette seule fonction (HOST-100, tests/test_main.py) ne doit pas exiger
    GTK — vérifié : sans cet import local, le simple fait d'importer ce
    module pour tester `self_test_requested` faisait planter la collecte
    de test dans un environnement sans GTK, malgré l'intention déjà
    documentée ici."""
    return SELF_TEST_FLAG in argv


def run() -> None:
    from secondscreen_host.ui.app import main

    sys.exit(main(self_test=self_test_requested(sys.argv[1:])))


if __name__ == "__main__":
    run()
