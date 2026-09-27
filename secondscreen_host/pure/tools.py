"""Logique pure de HOST-010 : quels outils système sont requis, et comment
interpréter le résultat de leur recherche.

La recherche elle-même (`shutil.which`) est un appel système, fait dans
`secondscreen_host.system.tools`. Ce module ne fait qu'interpréter des
résultats déjà obtenus : testable sans qu'aucun de ces outils ne soit
réellement installé.
"""

from __future__ import annotations

from dataclasses import dataclass

# xrandr, cvt, x11vnc : nécessaires pour l'écran étendu (F02) et le serveur
# VNC (F04), donc toujours requis. Xorg n'est requis que pour le repli
# écran isolé (F03) : son absence ne doit pas bloquer l'écran étendu, elle
# est donc vérifiée séparément (voir `check_fallback_tools`).


@dataclass(frozen=True)
class RequiredTool:
    """Un outil externe dont l'application a besoin."""

    name: str
    package_hint: str
    reason: str


REQUIRED_TOOLS: tuple[RequiredTool, ...] = (
    RequiredTool(
        name="xrandr",
        package_hint="x11-xserver-utils",
        reason="détecter et configurer les sorties d'affichage",
    ),
    RequiredTool(
        name="cvt",
        package_hint="xcvt",
        reason="calculer le mode d'affichage 1280x800",
    ),
    RequiredTool(
        name="x11vnc",
        package_hint="x11vnc",
        reason="servir l'écran en VNC",
    ),
    RequiredTool(
        name="ip",
        package_hint="iproute2",
        reason="détecter l'adresse IP locale à afficher (HOST-050)",
    ),
)

# Requis seulement pour le repli « écran isolé » (F03, HOST-030/HOST-031) :
# son absence n'empêche pas l'écran étendu (F02) de fonctionner.
FALLBACK_TOOLS: tuple[RequiredTool, ...] = (
    RequiredTool(
        name="Xorg",
        package_hint="xserver-xorg-core xserver-xorg-video-dummy",
        reason="démarrer le second serveur X du repli « écran isolé »",
    ),
)


@dataclass(frozen=True)
class ToolCheckResult:
    """Résultat de la recherche d'un outil (déjà faite, voir
    `secondscreen_host.system.tools.check_tool`)."""

    tool: RequiredTool
    found_at: str | None

    @property
    def is_available(self) -> bool:
        return self.found_at is not None


def missing_tools(results: list[ToolCheckResult]) -> list[ToolCheckResult]:
    """Fonction pure : filtre les résultats pour ne garder que les outils
    absents, dans l'ordre où ils ont été fournis."""
    return [r for r in results if not r.is_available]


def format_missing_tools_message(missing: list[ToolCheckResult]) -> str:
    """Fonction pure : message clair et actionnable (quoi manque, quel
    paquet installer), jamais une erreur technique brute. Voir AGENTS.md,
    règle 1. Chaîne vide si `missing` est vide."""
    if not missing:
        return ""

    lines = ["Outils système manquants :"]
    for result in missing:
        lines.append(
            f"  - {result.tool.name} (paquet : {result.tool.package_hint}) "
            f"— nécessaire pour {result.tool.reason}"
        )

    # dict.fromkeys plutôt que set() : conserve l'ordre de première
    # apparition, pour un message reproductible (utile en test).
    packages = list(dict.fromkeys(result.tool.package_hint for result in missing))
    lines.append("")
    lines.append("Installer avec :")
    lines.append(f"  sudo apt install {' '.join(packages)}")
    return "\n".join(lines)
