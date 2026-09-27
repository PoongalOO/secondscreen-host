"""Tests de `secondscreen_host.system.xrandr_commands` (HOST-021).

Un échec est simulé à chaque étape (`--newmode`, `--addmode`, `--output`,
relecture) pour vérifier que `ExtendedScreenConfigurationError.step`
identifie bien laquelle a échoué, sans exécuter les étapes suivantes —
voir CAHIER_DES_CHARGES.md, « Fiabilité » : ne jamais laisser un échec
partiel sans le signaler clairement.
"""

from __future__ import annotations

import subprocess

import pytest

import secondscreen_host.system.xrandr as xrandr_module
import secondscreen_host.system.xrandr_commands as xrandr_commands_module
from secondscreen_host.pure.xrandr_commands import ExtendedScreenCommands
from secondscreen_host.system.xrandr_commands import (
    ExtendedScreenConfigurationError,
    configure_extended_screen,
)

COMMANDS = ExtendedScreenCommands(
    newmode=("xrandr", "--newmode", "1280x800_60.00", "83.50"),
    addmode=("xrandr", "--addmode", "VIRTUAL1", "1280x800_60.00"),
    activate=(
        "xrandr",
        "--output",
        "VIRTUAL1",
        "--mode",
        "1280x800_60.00",
        "--right-of",
        "eDP-1",
    ),
)


def _ok(*args, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="", stderr="")


def test_stops_at_newmode_failure_without_running_the_rest(monkeypatch) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_run(command, **kwargs):
        calls.append(tuple(command))
        return subprocess.CompletedProcess(
            args=command, returncode=1, stdout="", stderr="X Error: bad mode"
        )

    monkeypatch.setattr(xrandr_commands_module.subprocess, "run", fake_run)

    with pytest.raises(ExtendedScreenConfigurationError) as excinfo:
        configure_extended_screen(COMMANDS, virtual_output="VIRTUAL1")

    assert excinfo.value.step == "création du mode (--newmode)"
    assert "bad mode" in str(excinfo.value)
    assert calls == [COMMANDS.newmode]  # ni addmode ni activate n'ont été lancées


def test_stops_at_addmode_failure_after_newmode_succeeded(monkeypatch) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_run(command, **kwargs):
        calls.append(tuple(command))
        if tuple(command) == COMMANDS.addmode:
            return subprocess.CompletedProcess(
                args=command, returncode=1, stdout="", stderr="cannot find mode"
            )
        return _ok(command)

    monkeypatch.setattr(xrandr_commands_module.subprocess, "run", fake_run)

    with pytest.raises(ExtendedScreenConfigurationError) as excinfo:
        configure_extended_screen(COMMANDS, virtual_output="VIRTUAL1")

    assert excinfo.value.step == "association à la sortie (--addmode)"
    assert calls == [COMMANDS.newmode, COMMANDS.addmode]  # activate jamais lancée


def test_stops_at_activate_failure(monkeypatch) -> None:
    def fake_run(command, **kwargs):
        if tuple(command) == COMMANDS.activate:
            return subprocess.CompletedProcess(
                args=command, returncode=1, stdout="", stderr="cannot find output"
            )
        return _ok(command)

    monkeypatch.setattr(xrandr_commands_module.subprocess, "run", fake_run)

    with pytest.raises(ExtendedScreenConfigurationError) as excinfo:
        configure_extended_screen(COMMANDS, virtual_output="VIRTUAL1")

    assert excinfo.value.step == "activation (--output --right-of)"


def test_reports_a_clear_error_if_binary_is_missing_mid_sequence(monkeypatch) -> None:
    def fake_run(command, **kwargs):
        raise FileNotFoundError("xrandr")

    monkeypatch.setattr(xrandr_commands_module.subprocess, "run", fake_run)

    with pytest.raises(ExtendedScreenConfigurationError, match="introuvable"):
        configure_extended_screen(COMMANDS, virtual_output="VIRTUAL1")


def test_succeeds_and_returns_the_reread_geometry(monkeypatch) -> None:
    monkeypatch.setattr(xrandr_commands_module.subprocess, "run", _ok)

    fake_query_stdout = (
        "Screen 0: minimum 320 x 200, current 3200 x 1080, maximum 8192 x 8192\n"
        "eDP-1 connected primary 1920x1080+0+0 (normal left inverted right x axis y axis)\n"
        "VIRTUAL1 connected 1280x800+1920+0 (normal left inverted right x axis y axis)\n"
    )

    def fake_query_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=["xrandr", "--query"], returncode=0, stdout=fake_query_stdout, stderr=""
        )

    monkeypatch.setattr(xrandr_module.subprocess, "run", fake_query_run)

    output = configure_extended_screen(COMMANDS, virtual_output="VIRTUAL1")

    assert output.name == "VIRTUAL1"
    assert output.geometry is not None
    assert (output.geometry.width, output.geometry.height) == (1280, 800)
    assert (output.geometry.x, output.geometry.y) == (1920, 0)


def test_fails_clearly_if_the_output_is_not_visible_after_configuration(monkeypatch) -> None:
    # Les trois commandes réussissent, mais xrandr --query ne montre pas la
    # sortie comme connectée : signalé, pas ignoré silencieusement.
    monkeypatch.setattr(xrandr_commands_module.subprocess, "run", _ok)

    fake_query_stdout = (
        "Screen 0: minimum 320 x 200, current 1920 x 1080, maximum 8192 x 8192\n"
        "eDP-1 connected primary 1920x1080+0+0 (normal left inverted right x axis y axis)\n"
        "VIRTUAL1 disconnected (normal left inverted right x axis y axis)\n"
    )

    def fake_query_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=["xrandr", "--query"], returncode=0, stdout=fake_query_stdout, stderr=""
        )

    monkeypatch.setattr(xrandr_module.subprocess, "run", fake_query_run)

    with pytest.raises(ExtendedScreenConfigurationError) as excinfo:
        configure_extended_screen(COMMANDS, virtual_output="VIRTUAL1")

    assert excinfo.value.step == "relecture de la position (xrandr --query)"
