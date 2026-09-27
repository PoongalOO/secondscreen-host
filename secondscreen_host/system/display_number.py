"""Détecte réellement les numéros d'affichage occupés (HOST-031, partie
exécutante), via l'existence de `/tmp/.X<N>-lock` — c'est le même mécanisme
de verrou que Xorg utilise lui-même pour un numéro d'affichage.
"""

from __future__ import annotations

from pathlib import Path

from secondscreen_host.pure.display_number import find_free_display_number


def _is_display_busy(number: int) -> bool:
    return Path(f"/tmp/.X{number}-lock").exists()


def pick_free_display_number(*, start: int = 1, max_number: int = 63) -> int:
    busy = {n for n in range(start, max_number + 1) if _is_display_busy(n)}
    return find_free_display_number(busy, start=start, max_number=max_number)
