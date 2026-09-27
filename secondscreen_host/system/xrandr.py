"""Appelle réellement `xrandr --query` (HOST-012, partie exécutante).

Ne fait aucune interprétation du résultat : voir
`secondscreen_host.pure.xrandr` pour l'analyse, testable sans lancer X.
"""

from __future__ import annotations

import subprocess

from secondscreen_host.pure.xrandr import XrandrQueryResult, parse_xrandr_query


class XrandrQueryError(RuntimeError):
    """`xrandr --query` a échoué (code de retour non nul), n'a pas répondu,
    ou le binaire est introuvable.

    HOST-010 devrait avoir déjà empêché d'en arriver là (outil manquant
    détecté avant toute action), mais on ne suppose jamais qu'un appel
    système réussit (voir AGENTS.md, règle 1) : cette exception porte un
    message compréhensible, jamais une trace brute remontée telle quelle
    jusqu'à l'interface (voir AGENTS.md, règle 5)."""


def query_xrandr() -> XrandrQueryResult:
    try:
        completed = subprocess.run(
            ["xrandr", "--query"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except FileNotFoundError as exc:
        raise XrandrQueryError("La commande « xrandr » est introuvable.") from exc
    except subprocess.TimeoutExpired as exc:
        raise XrandrQueryError("« xrandr --query » n'a pas répondu à temps.") from exc

    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        detail = f" : {stderr}" if stderr else ""
        raise XrandrQueryError(
            f"« xrandr --query » a échoué (code {completed.returncode}){detail}"
        )

    return parse_xrandr_query(completed.stdout)
