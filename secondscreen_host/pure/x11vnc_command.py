"""Construit la commande `x11vnc` (HOST-040, F04).

Fonction pure : assemble les arguments, jamais le mot de passe en clair sur
la ligne de commande elle-même (visible via `ps(1)` à n'importe quel
utilisateur local du système) — voir HOST-090 et CAHIER_DES_CHARGES.md,
« Sécurité ».

Cette fonction ne prend d'ailleurs pas le mot de passe en paramètre : elle
prend le CHEMIN d'un fichier de mot de passe déjà écrit (voir
`secondscreen_host.system.x11vnc`, qui l'écrit avec des permissions
restrictives juste avant de lancer x11vnc, préfixé `rm:` pour que x11vnc le
supprime lui-même après l'avoir lu une seule fois — comportement documenté
par x11vnc lui-même, `x11vnc -help`, vérifié en conditions réelles). Il est
donc structurellement impossible d'appeler cette fonction avec un mot de
passe en clair par erreur : sa signature ne permet même pas de lui en
passer un.
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_PORT = 5900


class MissingPasswordFileError(ValueError):
    """Un chemin de fichier de mot de passe vide : on ne construit jamais
    de commande x11vnc sans authentification (voir HOST-091, et
    CAHIER_DES_CHARGES.md, « ne jamais lancer x11vnc sans mot de passe par
    défaut »)."""


@dataclass(frozen=True)
class X11VncTarget:
    """Où et quoi partager :
    - écran étendu (F02) : `display` du bureau existant, `clip` calculé par
      HOST-022 pour ne partager que la zone virtuelle ;
    - écran isolé (F03) : `display` du second serveur X (HOST-031),
      `clip=None` — il ne contient déjà que les 1280x800 voulus, rien à
      découper (voir GUIDE_UBUNTU.md, partie B).
    """

    display: str
    clip: str | None


def build_x11vnc_command(
    *, target: X11VncTarget, password_file_path: str, port: int = DEFAULT_PORT
) -> tuple[str, ...]:
    if not password_file_path:
        raise MissingPasswordFileError(
            "Un chemin de fichier de mot de passe est requis pour construire "
            "la commande x11vnc."
        )

    command = [
        "x11vnc",
        "-display",
        target.display,
        "-forever",
        "-shared",
        "-rfbport",
        str(port),
        "-passwdfile",
        f"rm:{password_file_path}",
    ]
    if target.clip is not None:
        command.extend(["-clip", target.clip])
    return tuple(command)
