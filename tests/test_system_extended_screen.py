"""Test de bout en bout (simulé) de `secondscreen_host.system.
extended_screen.setup_extended_screen` : enchaîne `cvt`, les trois
commandes `xrandr`, et la relecture — chaque étape déjà testée séparément
(test_system_cvt.py, test_system_xrandr_commands.py) ; ce fichier vérifie
seulement qu'elles s'enchaînent correctement.
"""

from __future__ import annotations

import subprocess

import pytest

from secondscreen_host.system.cvt import CvtError
from secondscreen_host.system.extended_screen import setup_extended_screen

CVT_STDOUT = (
    "# 1280x800 59.81 Hz (CVT 1.02MA) hsync: 49.70 kHz; pclk: 83.50 MHz\n"
    'Modeline "1280x800_60.00"   83.50  1280 1352 1480 1680  800 803 809 831 -hsync +vsync\n'
)

QUERY_STDOUT_AFTER_CONFIG = (
    "Screen 0: minimum 320 x 200, current 3200 x 1080, maximum 8192 x 8192\n"
    "eDP-1 connected primary 1920x1080+0+0 (normal left inverted right x axis y axis)\n"
    "VIRTUAL1 connected 1280x800+1920+0 (normal left inverted right x axis y axis)\n"
)


def _patch_happy_path(monkeypatch) -> list[tuple[str, ...]]:
    # cvt_module, xrandr_commands_module et xrandr_module font tous les
    # trois `import subprocess` : c'est le même objet module dans les
    # trois cas (un seul `subprocess` chargé par interpréteur). Un seul
    # dispatcher, posé une fois, suffit donc — en poser un par module
    # écraserait silencieusement les précédents (bogue réellement rencontré
    # en écrivant ce test avant cette correction).
    executed: list[tuple[str, ...]] = []

    def fake_run(command, **kwargs):
        executed.append(tuple(command))
        if command[:2] == ["xrandr", "--query"]:
            return subprocess.CompletedProcess(
                args=command, returncode=0, stdout=QUERY_STDOUT_AFTER_CONFIG, stderr=""
            )
        if command[0] == "cvt":
            return subprocess.CompletedProcess(
                args=command, returncode=0, stdout=CVT_STDOUT, stderr=""
            )
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    return executed


def test_setup_extended_screen_happy_path(monkeypatch) -> None:
    executed = _patch_happy_path(monkeypatch)

    output = setup_extended_screen(virtual_output="VIRTUAL1", primary_output="eDP-1")

    assert output.name == "VIRTUAL1"
    assert output.geometry is not None
    assert (output.geometry.x, output.geometry.y) == (1920, 0)

    # cvt appelé avec les dimensions par défaut (1280x800 @ 60Hz), puis les
    # trois commandes xrandr, dans l'ordre.
    assert executed[0] == ("cvt", "1280", "800", "60")
    assert executed[1][:2] == ("xrandr", "--newmode")
    assert executed[2][:2] == ("xrandr", "--addmode")
    assert executed[3][:2] == ("xrandr", "--output")


def test_setup_extended_screen_propagates_cvt_failure_without_touching_xrandr(monkeypatch) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_run(command, **kwargs):
        calls.append(tuple(command))
        if command[0] == "cvt":
            return subprocess.CompletedProcess(
                args=command, returncode=1, stdout="", stderr="cvt: bad arguments"
            )
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(CvtError, match="bad arguments"):
        setup_extended_screen(virtual_output="VIRTUAL1", primary_output="eDP-1")

    assert calls == [("cvt", "1280", "800", "60")]  # aucune commande xrandr lancée si cvt échoue
