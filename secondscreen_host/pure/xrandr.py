"""Logique pure de HOST-012 : analyser le texte déjà produit par
`xrandr --query` (voir `secondscreen_host.system.xrandr` pour l'appel réel).

Le format de `xrandr --query` varie selon le pilote et la version (voir
AGENTS.md, règle 2) : une ligne de sortie dans un format non reconnu est
ignorée plutôt que de faire planter l'analyse — mieux vaut un résultat
partiel qu'un plantage sur une machine dont on n'a pas anticipé la sortie
exacte.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Exemples de lignes réellement rencontrées (voir tests/fixtures) :
#   eDP-1 connected primary 1920x1080+0+0 (normal left inverted ...) 293mm x 165mm
#   HDMI-1 disconnected (normal left inverted right x axis y axis)
#   VIRTUAL1 connected 1280x800+1920+0 (normal left inverted ...)
# Le `.match` (pas `.fullmatch`) : on ignore volontairement tout ce qui suit
# la géométrie (rotation, taille physique en mm...), non pertinent ici.
_HEADER_RE = re.compile(
    r"^(?P<name>\S+)\s+(?P<state>connected|disconnected)"
    r"(?P<primary>\s+primary)?"
    r"(?:\s+(?P<width>\d+)x(?P<height>\d+)\+(?P<x>\d+)\+(?P<y>\d+))?"
)


@dataclass(frozen=True)
class OutputGeometry:
    width: int
    height: int
    x: int
    y: int


@dataclass(frozen=True)
class XrandrOutput:
    name: str
    connected: bool
    is_primary: bool
    geometry: OutputGeometry | None

    @property
    def is_virtual_candidate(self) -> bool:
        """Une sortie factice (`VIRTUAL*`) pas encore utilisée : candidate
        pour F02 (écran virtuel étendu)."""
        return self.name.startswith("VIRTUAL") and not self.connected


@dataclass(frozen=True)
class XrandrQueryResult:
    outputs: tuple[XrandrOutput, ...]

    @property
    def primary(self) -> XrandrOutput | None:
        for output in self.outputs:
            if output.is_primary:
                return output
        return None

    @property
    def virtual_candidates(self) -> tuple[XrandrOutput, ...]:
        """Sorties `VIRTUAL*` disponibles mais pas encore configurées."""
        return tuple(output for output in self.outputs if output.is_virtual_candidate)

    @property
    def active_virtual_outputs(self) -> tuple[XrandrOutput, ...]:
        """Sorties `VIRTUAL*` déjà connectées (déjà configurées par un
        lancement précédent) : leur géométrie sert directement au calcul du
        `--clip` (HOST-022), sans reconfigurer l'écran."""
        return tuple(
            output
            for output in self.outputs
            if output.name.startswith("VIRTUAL") and output.connected
        )


def parse_xrandr_query(text: str) -> XrandrQueryResult:
    outputs: list[XrandrOutput] = []
    for line in text.splitlines():
        if not line or line[0].isspace():
            # Ligne de mode (indentée sous une sortie), pas une ligne de
            # sortie : ignorée.
            continue
        if line.startswith("Screen "):
            continue

        match = _HEADER_RE.match(line)
        if match is None:
            # Format de ligne non reconnu : ignorée plutôt qu'un plantage
            # (voir AGENTS.md, règle 2).
            continue

        geometry = None
        if match.group("width"):
            geometry = OutputGeometry(
                width=int(match.group("width")),
                height=int(match.group("height")),
                x=int(match.group("x")),
                y=int(match.group("y")),
            )

        outputs.append(
            XrandrOutput(
                name=match.group("name"),
                connected=match.group("state") == "connected",
                is_primary=match.group("primary") is not None,
                geometry=geometry,
            )
        )

    return XrandrQueryResult(outputs=tuple(outputs))
