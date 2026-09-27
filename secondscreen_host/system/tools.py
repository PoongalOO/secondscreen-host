"""Vérifie réellement la présence des outils système requis (HOST-010).

Un seul appel à `shutil.which` par outil : aucune exécution, aucune
modification du système. Voir `secondscreen_host.pure.tools` pour
l'interprétation du résultat.
"""

from __future__ import annotations

import shutil

from secondscreen_host.pure.tools import (
    FALLBACK_TOOLS,
    REQUIRED_TOOLS,
    RequiredTool,
    ToolCheckResult,
)


def check_tool(tool: RequiredTool) -> ToolCheckResult:
    return ToolCheckResult(tool=tool, found_at=shutil.which(tool.name))


def check_required_tools() -> list[ToolCheckResult]:
    return [check_tool(tool) for tool in REQUIRED_TOOLS]


def check_fallback_tools() -> list[ToolCheckResult]:
    return [check_tool(tool) for tool in FALLBACK_TOOLS]
