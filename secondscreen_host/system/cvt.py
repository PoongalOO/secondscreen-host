"""Appelle réellement `cvt` (HOST-020, partie exécutante).

Ne fait aucune interprétation du résultat : voir
`secondscreen_host.pure.cvt` pour l'analyse, testable sans lancer `cvt`.
"""

from __future__ import annotations

import subprocess

from secondscreen_host.pure.cvt import CvtMode, CvtParseError, parse_cvt_output


class CvtError(RuntimeError):
    """`cvt` a échoué, n'a pas répondu à temps, le binaire est introuvable,
    ou sa sortie n'a pas pu être interprétée — jamais une trace brute
    remontée telle quelle jusqu'à l'interface (voir AGENTS.md, règle 5)."""


def compute_mode(width: int, height: int, refresh_hz: int = 60) -> CvtMode:
    try:
        completed = subprocess.run(
            ["cvt", str(width), str(height), str(refresh_hz)],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except FileNotFoundError as exc:
        raise CvtError("La commande « cvt » est introuvable.") from exc
    except subprocess.TimeoutExpired as exc:
        raise CvtError("« cvt » n'a pas répondu à temps.") from exc

    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        detail = f" : {stderr}" if stderr else ""
        raise CvtError(f"« cvt » a échoué (code {completed.returncode}){detail}")

    try:
        return parse_cvt_output(completed.stdout)
    except CvtParseError as exc:
        raise CvtError(f"Sortie de « cvt » inattendue : {exc}") from exc
