"""Choisit un numéro d'affichage libre pour le second serveur X (HOST-031).

Fonction pure : décide à partir d'un ensemble de numéros déjà occupés
(obtenu en vérifiant l'existence de `/tmp/.X<N>-lock`, voir
`secondscreen_host.system.display_number`), jamais en touchant le système
de fichiers elle-même. Commence à `:1` par défaut : `:0` est presque
toujours le bureau existant, jamais un candidat pour le second serveur X.
"""

from __future__ import annotations


class NoFreeDisplayNumberError(RuntimeError):
    """Aucun numéro d'affichage libre trouvé dans la plage explorée —
    situation anormale (63 affichages simultanés), mais on ne suppose
    jamais qu'il y en a toujours un (AGENTS.md, règle 1)."""


def find_free_display_number(
    busy_numbers: set[int], *, start: int = 1, max_number: int = 63
) -> int:
    for candidate in range(start, max_number + 1):
        if candidate not in busy_numbers:
            return candidate
    raise NoFreeDisplayNumberError(
        f"Aucun numéro d'affichage libre entre :{start} et :{max_number}."
    )
