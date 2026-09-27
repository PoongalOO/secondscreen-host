"""Tests de `secondscreen_host.system.cvt` (HOST-020, partie exécutante).

Les cas d'échec sont testés en remplaçant `subprocess.run` (voir
tests/test_system_xrandr.py pour la même approche et sa justification).
"""

from __future__ import annotations

import shutil
import subprocess

import pytest

import secondscreen_host.system.cvt as cvt_module
from secondscreen_host.system.cvt import CvtError, compute_mode


def test_compute_mode_raises_a_clear_error_when_the_binary_is_missing(monkeypatch) -> None:
    def fake_run(*args, **kwargs):
        raise FileNotFoundError("cvt")

    monkeypatch.setattr(cvt_module.subprocess, "run", fake_run)

    with pytest.raises(CvtError, match="introuvable"):
        compute_mode(1280, 800)


def test_compute_mode_raises_a_clear_error_on_timeout(monkeypatch) -> None:
    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="cvt", timeout=10)

    monkeypatch.setattr(cvt_module.subprocess, "run", fake_run)

    with pytest.raises(CvtError, match="répondu à temps"):
        compute_mode(1280, 800)


def test_compute_mode_raises_a_clear_error_on_non_zero_exit_code(monkeypatch) -> None:
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=["cvt"], returncode=1, stdout="", stderr="cvt: unknown option"
        )

    monkeypatch.setattr(cvt_module.subprocess, "run", fake_run)

    with pytest.raises(CvtError, match="unknown option"):
        compute_mode(1280, 800)


def test_compute_mode_raises_a_clear_error_on_unparsable_output(monkeypatch) -> None:
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=["cvt"], returncode=0, stdout="une sortie sans Modeline\n", stderr=""
        )

    monkeypatch.setattr(cvt_module.subprocess, "run", fake_run)

    with pytest.raises(CvtError, match="inattendue"):
        compute_mode(1280, 800)


def test_compute_mode_parses_a_successful_real_shaped_output(monkeypatch) -> None:
    fake_stdout = (
        "# 1280x800 59.81 Hz (CVT 1.02MA) hsync: 49.70 kHz; pclk: 83.50 MHz\n"
        'Modeline "1280x800_60.00"   83.50  1280 1352 1480 1680  800 803 809 831 -hsync +vsync\n'
    )

    def fake_run(*args, **kwargs):
        assert args[0] == ["cvt", "1280", "800", "60"]
        return subprocess.CompletedProcess(
            args=args[0], returncode=0, stdout=fake_stdout, stderr=""
        )

    monkeypatch.setattr(cvt_module.subprocess, "run", fake_run)

    mode = compute_mode(1280, 800, 60)

    assert mode.name == "1280x800_60.00"


@pytest.mark.skipif(shutil.which("cvt") is None, reason="cvt (paquet xcvt) non installé")
def test_compute_mode_real_invocation_on_this_machine() -> None:
    # Vérité de terrain si xcvt est installé : pas de simulation.
    mode = compute_mode(1280, 800, 60)

    assert "1280x800" in mode.name
    assert len(mode.parameters) >= 8
