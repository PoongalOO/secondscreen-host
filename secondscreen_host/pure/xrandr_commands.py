"""Construit les commandes `xrandr` de l'écran virtuel étendu (HOST-020).

Fonction pure : construit des listes d'arguments (`tuple[str, ...]`),
jamais une chaîne shell — pas de risque d'injection, et c'est directement
ce que `subprocess.run` attend (voir `secondscreen_host.system.
xrandr_commands`, HOST-021, pour l'exécution réelle). Ne lance rien.
"""

from __future__ import annotations

from dataclasses import dataclass

from secondscreen_host.pure.cvt import CvtMode


@dataclass(frozen=True)
class ExtendedScreenCommands:
    """Les trois commandes à exécuter dans l'ordre pour configurer l'écran
    virtuel étendu (F02, CAHIER_DES_CHARGES.md). Voir HOST-021 pour leur
    exécution et la relecture de la position réellement assignée."""

    newmode: tuple[str, ...]
    addmode: tuple[str, ...]
    activate: tuple[str, ...]


def build_extended_screen_commands(
    *, mode: CvtMode, virtual_output: str, primary_output: str
) -> ExtendedScreenCommands:
    """`virtual_output` : la sortie `VIRTUAL*` détectée (HOST-012,
    `XrandrQueryResult.virtual_candidates`). `primary_output` : la sortie
    principale (HOST-012, `XrandrQueryResult.primary`), à droite de
    laquelle l'écran virtuel est activé (voir GUIDE_UBUNTU.md)."""
    return ExtendedScreenCommands(
        newmode=("xrandr", "--newmode", mode.name, *mode.parameters),
        addmode=("xrandr", "--addmode", virtual_output, mode.name),
        activate=(
            "xrandr",
            "--output",
            virtual_output,
            "--mode",
            mode.name,
            "--right-of",
            primary_output,
        ),
    )
