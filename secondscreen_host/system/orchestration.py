"""Orchestre la configuration de l'écran virtuel pour le bouton
« Configurer » (HOST-070) : détection (HOST-012), puis choix entre écran
étendu (HOST-021, F02) et écran isolé (HOST-031, F03) selon ce qui est
disponible — jamais d'échec silencieux (préparation de HOST-081 : chaque
échec possible remonte comme un message compréhensible unique, sans que
l'appelant ait besoin de connaître le détail de chaque module).
"""

from __future__ import annotations

from dataclasses import dataclass

from secondscreen_host.pure.clip import InvalidClipGeometryError, format_clip_rectangle
from secondscreen_host.system.cvt import CvtError, compute_mode
from secondscreen_host.system.dummy_xorg import (
    DummyScreenProcess,
    DummyScreenStartError,
    start_dummy_screen,
)
from secondscreen_host.system.extended_screen import setup_extended_screen
from secondscreen_host.system.x11vnc import X11VncProcess
from secondscreen_host.system.xrandr import XrandrQueryError, query_xrandr
from secondscreen_host.system.xrandr_commands import ExtendedScreenConfigurationError

PRIMARY_DISPLAY = ":0"
DUMMY_SCREEN_WIDTH = 1280
DUMMY_SCREEN_HEIGHT = 800
DUMMY_SCREEN_REFRESH_HZ = 60


class ScreenConfigurationError(RuntimeError):
    """Regroupe les échecs possibles (détection, cvt, xrandr, Xorg) sous un
    seul type que l'interface peut afficher sans connaître le détail de
    chaque module."""


@dataclass(frozen=True)
class ConfiguredScreen:
    """Où se trouve l'écran virtuel prêt à être servi en VNC."""

    display: str
    clip: str | None
    """`None` pour l'écran isolé (F03) : il ne contient déjà que la zone
    voulue, rien à découper."""
    dummy_process: DummyScreenProcess | None
    """`None` pour l'écran étendu (F02) : rien à arrêter à part le serveur
    VNC lui-même."""
    virtual_output_name: str | None
    """Nom de la sortie `VIRTUAL*` utilisée (écran étendu), pour la
    mémoriser (HOST-060) ; `None` pour l'écran isolé, qui n'en a pas."""


def configure_screen(
    *, remembered_output: str | None = None, elevation_command: list[str] | None = None
) -> ConfiguredScreen:
    """`elevation_command` : transmis tel quel à `start_dummy_screen`
    (HOST-031) si le repli écran isolé est nécessaire — surtout un point
    d'entrée de test (voir sa docstring), laissé à `None` en usage normal
    pour la détection réelle (`pkexec`)."""
    try:
        query = query_xrandr()
    except XrandrQueryError as exc:
        raise ScreenConfigurationError(str(exc)) from exc

    if query.virtual_candidates:
        candidate = next(
            (c for c in query.virtual_candidates if c.name == remembered_output),
            query.virtual_candidates[0],
        )
        primary = query.primary
        if primary is None:
            raise ScreenConfigurationError(
                "Aucun écran principal détecté (xrandr) : impossible de placer "
                "l'écran virtuel à côté."
            )
        try:
            output = setup_extended_screen(
                virtual_output=candidate.name, primary_output=primary.name
            )
        except (CvtError, ExtendedScreenConfigurationError) as exc:
            raise ScreenConfigurationError(str(exc)) from exc

        if output.geometry is None:
            raise ScreenConfigurationError(
                f"La sortie « {candidate.name} » est connectée mais sans géométrie "
                "exploitable après configuration."
            )
        try:
            clip = format_clip_rectangle(output.geometry)
        except InvalidClipGeometryError as exc:
            raise ScreenConfigurationError(str(exc)) from exc

        return ConfiguredScreen(
            display=PRIMARY_DISPLAY,
            clip=clip,
            dummy_process=None,
            virtual_output_name=candidate.name,
        )

    # Repli : écran isolé (F03), aucune sortie VIRTUAL* disponible.
    try:
        mode = compute_mode(DUMMY_SCREEN_WIDTH, DUMMY_SCREEN_HEIGHT, DUMMY_SCREEN_REFRESH_HZ)
    except CvtError as exc:
        raise ScreenConfigurationError(str(exc)) from exc

    try:
        dummy = start_dummy_screen(
            mode,
            width=DUMMY_SCREEN_WIDTH,
            height=DUMMY_SCREEN_HEIGHT,
            elevation_command=elevation_command,
        )
    except DummyScreenStartError as exc:
        raise ScreenConfigurationError(str(exc)) from exc

    return ConfiguredScreen(
        display=dummy.display, clip=None, dummy_process=dummy, virtual_output_name=None
    )


def teardown_screen(
    configured_screen: ConfiguredScreen | None, vnc: X11VncProcess | None
) -> None:
    """Arrête le serveur VNC puis, s'il y en a un, le second serveur X du
    repli isolé (F03) — jamais l'inverse : ne pas laisser le serveur VNC
    pointer un instant vers un affichage qui vient de disparaître."""
    if vnc is not None:
        vnc.stop()
    if configured_screen is not None and configured_screen.dummy_process is not None:
        configured_screen.dummy_process.stop()
