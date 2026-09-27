"""Calcule le rectangle `--clip` pour x11vnc (HOST-022).

Fonction pure : combine une géométrie déjà connue (par exemple celle
relue après configuration, HOST-021, ou celle d'une sortie `VIRTUAL*` déjà
active — voir `XrandrQueryResult.active_virtual_outputs`) en la chaîne
attendue par `x11vnc -clip LARGEURxHAUTEUR+X+Y` (format vérifié en
conditions réelles dans GUIDE_UBUNTU.md du projet SecondScreen).
"""

from __future__ import annotations

from secondscreen_host.pure.xrandr import OutputGeometry


class InvalidClipGeometryError(ValueError):
    """Une géométrie qui n'a pas de sens pour un `--clip` (taille nulle ou
    négative, position négative) : xrandr ne devrait jamais en produire une
    telle, mais on ne le suppose pas (voir AGENTS.md, règle 1)."""


def format_clip_rectangle(geometry: OutputGeometry) -> str:
    if geometry.width <= 0 or geometry.height <= 0:
        raise InvalidClipGeometryError(
            "Largeur et hauteur doivent être strictement positives "
            f"(reçu {geometry.width}x{geometry.height})."
        )
    if geometry.x < 0 or geometry.y < 0:
        raise InvalidClipGeometryError(
            "Une position négative n'est pas valide pour x11vnc -clip "
            f"(reçu +{geometry.x}+{geometry.y})."
        )
    return f"{geometry.width}x{geometry.height}+{geometry.x}+{geometry.y}"
