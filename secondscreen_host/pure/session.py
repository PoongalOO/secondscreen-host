"""Logique pure de HOST-011 : décider du type de session graphique à partir
de variables d'environnement déjà lues (voir `secondscreen_host.system.
session` pour la lecture réelle de `os.environ`).

`XDG_SESSION_TYPE` seul n'est pas garanti fiable sur toutes les
configurations (absent sous certains gestionnaires de session, ou en
retard sur la réalité) : on le croise avec `WAYLAND_DISPLAY` et `DISPLAY`,
qui reflètent ce à quoi l'application peut réellement se connecter.
`WAYLAND_DISPLAY` prime sur `DISPLAY` : sous XWayland, une application X11
classique peut très bien avoir `DISPLAY` positionnée alors que la session
est réellement Wayland — sa seule présence ne suffit donc pas à conclure
« X11 ».
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

GUIDE_UBUNTU_URL = "https://github.com/PoongalOO/virtualScreen/blob/main/GUIDE_UBUNTU.md"
GUIDE_MX_LINUX_URL = "https://github.com/PoongalOO/virtualScreen/blob/main/GUIDE_MX_LINUX.md"


class SessionType(Enum):
    X11 = "x11"
    WAYLAND = "wayland"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class SessionInfo:
    session_type: SessionType
    detail: str
    """Les valeurs brutes ayant mené à la décision, pour le panneau de
    détails techniques (HOST-071) — jamais affiché seul à la place d'un
    message clair (voir `explain_session_type`)."""


def detect_session_type(
    *,
    xdg_session_type: str | None,
    wayland_display: str | None,
    display: str | None,
) -> SessionInfo:
    """Fonction pure. Ne lit jamais `os.environ` elle-même."""
    normalized = (xdg_session_type or "").strip().lower()
    detail = (
        f"XDG_SESSION_TYPE={xdg_session_type!r}, "
        f"WAYLAND_DISPLAY={wayland_display!r}, DISPLAY={display!r}"
    )

    if wayland_display:
        return SessionInfo(SessionType.WAYLAND, detail)
    if normalized == "wayland":
        return SessionInfo(SessionType.WAYLAND, detail)
    if display:
        return SessionInfo(SessionType.X11, detail)
    if normalized == "x11":
        return SessionInfo(SessionType.X11, detail)
    return SessionInfo(SessionType.UNKNOWN, detail)


def explain_session_type(info: SessionInfo) -> str:
    """Message à afficher à l'utilisateur (fonction pure : le texte, pas
    l'affichage GTK). Chaîne vide si tout va bien (session Xorg) : voir
    CAHIER_DES_CHARGES.md, F01 — pas d'avertissement quand il n'y a rien à
    signaler."""
    if info.session_type is SessionType.X11:
        return ""

    guides = f"{GUIDE_UBUNTU_URL} ou {GUIDE_MX_LINUX_URL}"

    if info.session_type is SessionType.WAYLAND:
        return (
            "Session Wayland détectée : SecondScreenHost a besoin d'une session Xorg "
            "pour créer un écran virtuel (voir CAHIER_DES_CHARGES.md, « Hors périmètre »). "
            "Reconnectez-vous en choisissant une session Xorg à l'écran de connexion "
            "(souvent une icône en engrenage à côté du mot de passe), ou suivez la "
            f"configuration manuelle : {guides}"
        )

    return (
        "Type de session graphique indéterminé : SecondScreenHost n'a pas pu confirmer "
        "qu'il s'agit d'une session Xorg. Si la configuration automatique échoue, "
        f"suivez la configuration manuelle : {guides}"
    )
