"""Point d'entrée en ligne de commande de SecondScreenHost.

Deux façons de lancer l'application, équivalentes :
    python3 -m secondscreen_host
    secondscreen-host        (script installé, voir pyproject.toml)

C'est le seul module qui lit `sys.argv` : voir `ui/app.py`.
"""

from __future__ import annotations

import sys

from secondscreen_host.ui.app import main

SELF_TEST_FLAG = "--self-test"


def self_test_requested(argv: list[str]) -> bool:
    """Fonction pure : dit si `argv` (sans le nom du programme) demande le
    mode d'auto-test. Séparée de `run()` pour rester testable sans GTK."""
    return SELF_TEST_FLAG in argv


def run() -> None:
    sys.exit(main(self_test=self_test_requested(sys.argv[1:])))


if __name__ == "__main__":
    run()
