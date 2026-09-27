"""Tests de `secondscreen_host.system.orchestration` (HOST-070).

Le chemin repli écran isolé (F03) est vérifié de bout en bout avec un vrai
serveur X (Xvfb, qui n'expose jamais de sortie `VIRTUAL*` — exerce donc ce
chemin en conditions réelles) : `elevation_command=[]` contourne `pkexec`
puisque le test tourne déjà en root (même raison que
tests/test_system_dummy_xorg.py). Le chemin écran étendu (F02) est déjà
vérifié séparément par les tests de HOST-021 (aucun GPU disponible dans un
environnement de test n'expose de sortie `VIRTUAL*`, voir
tests/test_xrandr.py) ; il est réutilisé tel quel ici, sans le retester.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

from secondscreen_host.pure.secret import Secret
from secondscreen_host.pure.x11vnc_command import X11VncTarget
from secondscreen_host.system.orchestration import configure_screen, teardown_screen
from secondscreen_host.system.x11vnc import start_x11vnc

REQUIRED_BINARIES = ("Xvfb", "Xorg", "x11vnc")


@pytest.mark.skipif(os.geteuid() != 0, reason="nécessite root (conteneur jetable, pour Xorg dummy)")
@pytest.mark.skipif(
    any(shutil.which(binary) is None for binary in REQUIRED_BINARIES),
    reason="Xvfb/Xorg/x11vnc non installés",
)
def test_configure_and_teardown_the_isolated_fallback_end_to_end(monkeypatch) -> None:
    xvfb = subprocess.Popen(["Xvfb", ":230", "-screen", "0", "1920x1080x24", "-nolisten", "tcp"])
    configured = None
    try:
        for _ in range(50):
            if Path("/tmp/.X230-lock").exists():
                break
            time.sleep(0.1)
        else:
            pytest.fail("Xvfb n'a pas démarré à temps")

        monkeypatch.setenv("DISPLAY", ":230")

        # Xvfb n'expose jamais de sortie VIRTUAL* : exerce le repli isolé.
        configured = configure_screen(elevation_command=[])
        assert configured.clip is None
        assert configured.virtual_output_name is None
        assert configured.dummy_process is not None
        dummy_display_number = configured.dummy_process.display_number
        assert Path(f"/tmp/.X{dummy_display_number}-lock").exists()

        vnc = start_x11vnc(
            target=X11VncTarget(display=configured.display, clip=configured.clip),
            password=Secret("hunter2"),
        )
        assert vnc.is_running() is True

        teardown_screen(configured, vnc)

        time.sleep(0.3)
        assert vnc.process.poll() is not None
        assert not Path(f"/tmp/.X{dummy_display_number}-lock").exists()
    finally:
        if configured is not None and configured.dummy_process is not None:
            configured.dummy_process.stop()  # idempotent : sans effet si déjà arrêté
        xvfb.terminate()
        xvfb.wait(timeout=5)


def test_configure_screen_reports_a_clear_error_when_xrandr_is_missing(monkeypatch) -> None:
    import secondscreen_host.system.xrandr as xrandr_module
    from secondscreen_host.system.orchestration import ScreenConfigurationError

    def fake_run(*args, **kwargs):
        raise FileNotFoundError("xrandr")

    monkeypatch.setattr(xrandr_module.subprocess, "run", fake_run)

    with pytest.raises(ScreenConfigurationError, match="introuvable"):
        configure_screen()


def test_teardown_screen_handles_none_values_without_raising() -> None:
    teardown_screen(None, None)  # ne doit jamais lever
