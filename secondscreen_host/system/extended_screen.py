"""Point d'entrée unique pour configurer l'écran virtuel étendu (F02) :
enchaîne HOST-020 (construction des commandes), HOST-021 (exécution et
relecture) — ce que l'interface (HOST-070) appellera pour le bouton
« Configurer ».
"""

from __future__ import annotations

from secondscreen_host.pure.xrandr import XrandrOutput
from secondscreen_host.pure.xrandr_commands import build_extended_screen_commands
from secondscreen_host.system.cvt import compute_mode
from secondscreen_host.system.xrandr_commands import configure_extended_screen

DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 800
DEFAULT_REFRESH_HZ = 60


def setup_extended_screen(
    *,
    virtual_output: str,
    primary_output: str,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    refresh_hz: int = DEFAULT_REFRESH_HZ,
) -> XrandrOutput:
    """Calcule le mode (`cvt`), construit les commandes (HOST-020),
    les exécute et relit la position réellement assignée (HOST-021).

    Peut lever `secondscreen_host.system.cvt.CvtError` ou
    `secondscreen_host.system.xrandr_commands.ExtendedScreenConfigurationError` ;
    à charge de l'appelant (interface, HOST-081) d'en faire un message
    compréhensible plutôt que de laisser l'exception remonter brute.
    """
    mode = compute_mode(width, height, refresh_hz)
    commands = build_extended_screen_commands(
        mode=mode, virtual_output=virtual_output, primary_output=primary_output
    )
    return configure_extended_screen(commands, virtual_output=virtual_output)
