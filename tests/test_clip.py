"""Tests de `secondscreen_host.pure.clip` (HOST-022)."""

import pytest

from secondscreen_host.pure.clip import InvalidClipGeometryError, format_clip_rectangle
from secondscreen_host.pure.xrandr import OutputGeometry


def test_typical_right_of_placement() -> None:
    # Écran principal 1920x1080 à gauche, écran virtuel accolé à droite.
    geometry = OutputGeometry(width=1280, height=800, x=1920, y=0)

    assert format_clip_rectangle(geometry) == "1280x800+1920+0"


def test_position_zero_zero() -> None:
    # Cas limite explicitement demandé (ISSUES.md, HOST-022) : l'écran
    # virtuel est en position (0,0), par exemple sur l'écran isolé (F03)
    # ou si c'est lui qui a été configuré en premier.
    geometry = OutputGeometry(width=1280, height=800, x=0, y=0)

    assert format_clip_rectangle(geometry) == "1280x800+0+0"


def test_large_coordinates() -> None:
    # Cas limite explicitement demandé : grandes coordonnées (plusieurs
    # écrans 4K déjà en place avant l'écran virtuel).
    geometry = OutputGeometry(width=1280, height=800, x=7680, y=2160)

    assert format_clip_rectangle(geometry) == "1280x800+7680+2160"


def test_primary_screen_on_the_right_instead_of_the_left() -> None:
    # Cas limite explicitement demandé : l'écran virtuel est placé à
    # GAUCHE de l'écran principal (--left-of plutôt que --right-of) : sa
    # position x vaut alors 0, l'écran principal étant à x=1280. Le calcul
    # ne dépend que de la géométrie relue, pas de la disposition choisie.
    geometry = OutputGeometry(width=1280, height=800, x=0, y=0)

    assert format_clip_rectangle(geometry) == "1280x800+0+0"


def test_rejects_zero_width_or_height() -> None:
    with pytest.raises(InvalidClipGeometryError):
        format_clip_rectangle(OutputGeometry(width=0, height=800, x=0, y=0))
    with pytest.raises(InvalidClipGeometryError):
        format_clip_rectangle(OutputGeometry(width=1280, height=0, x=0, y=0))


def test_rejects_negative_width_or_height() -> None:
    with pytest.raises(InvalidClipGeometryError):
        format_clip_rectangle(OutputGeometry(width=-1, height=800, x=0, y=0))


def test_rejects_negative_position() -> None:
    with pytest.raises(InvalidClipGeometryError):
        format_clip_rectangle(OutputGeometry(width=1280, height=800, x=-1, y=0))
    with pytest.raises(InvalidClipGeometryError):
        format_clip_rectangle(OutputGeometry(width=1280, height=800, x=0, y=-1))
