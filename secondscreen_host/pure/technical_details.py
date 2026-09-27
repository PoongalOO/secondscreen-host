"""Formate le panneau de détails techniques (HOST-071).

Fonction pure : met en forme des résultats déjà obtenus (HOST-010/011/012)
en texte lisible — jamais d'appel système ici. Visible sur demande dans
l'interface (un panneau repliable), pas imposé par défaut
(CAHIER_DES_CHARGES.md, UX V1).
"""

from __future__ import annotations

from secondscreen_host.pure.session import SessionInfo
from secondscreen_host.pure.tools import ToolCheckResult
from secondscreen_host.pure.xrandr import XrandrQueryResult


def format_technical_details(
    *,
    tool_results: list[ToolCheckResult],
    session_info: SessionInfo | None,
    xrandr_result: XrandrQueryResult | None,
    last_error: str | None,
) -> str:
    lines: list[str] = []

    lines.append("Outils système :")
    if tool_results:
        for result in tool_results:
            if result.is_available:
                lines.append(f"  {result.tool.name} : trouvé ({result.found_at})")
            else:
                lines.append(
                    f"  {result.tool.name} : MANQUANT (paquet : {result.tool.package_hint})"
                )
    else:
        lines.append("  (pas encore vérifiés)")

    lines.append("")
    if session_info is not None:
        lines.append(
            f"Session graphique : {session_info.session_type.value} ({session_info.detail})"
        )
    else:
        lines.append("Session graphique : pas encore vérifiée")

    lines.append("")
    lines.append("Sorties détectées (xrandr) :")
    if xrandr_result is not None:
        if xrandr_result.outputs:
            for output in xrandr_result.outputs:
                state = "connectée" if output.connected else "déconnectée"
                geometry = (
                    f" {output.geometry.width}x{output.geometry.height}"
                    f"+{output.geometry.x}+{output.geometry.y}"
                    if output.geometry is not None
                    else ""
                )
                primary = " [principale]" if output.is_primary else ""
                lines.append(f"  {output.name} : {state}{geometry}{primary}")
        else:
            lines.append("  (aucune sortie trouvée)")
    else:
        lines.append("  (pas encore interrogées)")

    if last_error:
        lines.append("")
        lines.append(f"Dernière erreur : {last_error}")

    return "\n".join(lines)
