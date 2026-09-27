"""Analyse la sortie de `cvt` (HOST-020).

`cvt LARGEUR HAUTEUR [FREQUENCE]` produit une ligne de commentaire puis une
ligne `Modeline`, par exemple (capturé réellement, voir tests/fixtures) :

    # 1280x800 59.81 Hz (CVT 1.02MA) hsync: 49.70 kHz; pclk: 83.50 MHz
    Modeline "1280x800_60.00"   83.50  1280 1352 1480 1680  800 803 809 831 -hsync +vsync

Cette fonction pure extrait le nom du mode et ses paramètres bruts, sans
interpréter leur sens (fréquences, polarités de synchronisation...) :
`xrandr --newmode` sait déjà les consommer tels quels.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class CvtMode:
    name: str
    parameters: tuple[str, ...]
    """Tout ce qui suit le nom sur la ligne Modeline, dans l'ordre — passé
    tel quel à `xrandr --newmode`."""


class CvtParseError(ValueError):
    """La sortie de `cvt` ne contient aucune ligne « Modeline »
    reconnaissable (voir AGENTS.md, règle 2 : ne pas planter sur un format
    inattendu, mais ici il n'y a rien d'exploitable sans elle)."""


_MODELINE_RE = re.compile(r'^Modeline\s+"([^"]+)"\s+(.+)$')


def parse_cvt_output(text: str) -> CvtMode:
    for line in text.splitlines():
        match = _MODELINE_RE.match(line.strip())
        if match:
            name = match.group(1)
            parameters = tuple(match.group(2).split())
            return CvtMode(name=name, parameters=parameters)

    raise CvtParseError("Aucune ligne « Modeline » reconnaissable dans la sortie de cvt.")
