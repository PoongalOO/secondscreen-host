"""Tests de `secondscreen_host.system.cleanup` (HOST-080).

Chaque cas lance un vrai sous-processus Python autonome (voir
`tests/helpers/`) qui installe le nettoyage et démarre un « processus
externe », puis le test envoie un vrai signal (ou laisse le sous-processus
se terminer normalement) et vérifie **depuis l'extérieur**, par le système
d'exploitation, que le processus externe a bien disparu — pas seulement
que le code a été appelé.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

HELPERS = Path(__file__).parent / "helpers"
REPO_ROOT = Path(__file__).parent.parent


def _process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # existe, appartient à quelqu'un d'autre (ne devrait pas arriver ici)
    return True


def _wait_until_gone(pid: int, timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _process_exists(pid):
            return True
        time.sleep(0.05)
    return False


def _start_harness(*args: str, env: dict[str, str] | None = None) -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, str(HELPERS / "cleanup_harness.py"), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(REPO_ROOT),
        env=env,
    )


@pytest.mark.parametrize("sig", [signal.SIGTERM, signal.SIGINT])
def test_cleanup_kills_the_child_process_on_signal(sig: int) -> None:
    harness = _start_harness()
    try:
        child_pid = int(harness.stdout.readline().strip())
        assert _process_exists(child_pid)  # vérité de terrain avant le signal

        os.kill(harness.pid, sig)
        harness.wait(timeout=5)

        assert _wait_until_gone(child_pid)
    finally:
        if harness.poll() is None:
            harness.kill()


def test_cleanup_runs_via_atexit_on_normal_process_exit() -> None:
    harness = _start_harness("exit")
    try:
        child_pid = int(harness.stdout.readline().strip())
        harness.wait(timeout=5)

        assert _wait_until_gone(child_pid)
    finally:
        if harness.poll() is None:
            harness.kill()


def test_signal_handler_preserves_the_conventional_exit_status() -> None:
    # Le processus doit se terminer « par le signal », pas juste quitter
    # avec un code 0 quelconque : vérifie que le gestionnaire ne masque pas
    # la cause réelle de l'arrêt (utile pour un supervisor de processus qui
    # regarderait ce code).
    harness = _start_harness()
    try:
        harness.stdout.readline()  # attend que le processus soit prêt
        os.kill(harness.pid, signal.SIGTERM)
        harness.wait(timeout=5)

        assert harness.returncode == -signal.SIGTERM
    finally:
        if harness.poll() is None:
            harness.kill()


REQUIRED_BINARIES = ("Xvfb", "Xorg", "x11vnc")


@pytest.mark.skipif(os.geteuid() != 0, reason="nécessite root (conteneur jetable, pour Xorg dummy)")
@pytest.mark.skipif(
    any(shutil.which(binary) is None for binary in REQUIRED_BINARIES),
    reason="Xvfb/Xorg/x11vnc non installés",
)
def test_cleanup_kills_a_real_dummy_xorg_and_x11vnc_on_sigterm() -> None:
    # Vérité de terrain la plus proche du critère d'acceptation de
    # HOST-080 lui-même : « aucun processus x11vnc/Xorg orphelin ».
    xvfb = subprocess.Popen(["Xvfb", ":231", "-screen", "0", "1920x1080x24", "-nolisten", "tcp"])
    harness = None
    try:
        for _ in range(50):
            if Path("/tmp/.X231-lock").exists():
                break
            time.sleep(0.1)
        else:
            pytest.fail("Xvfb n'a pas démarré à temps")

        env = os.environ.copy()
        env["DISPLAY"] = ":231"
        harness = subprocess.Popen(
            [sys.executable, str(HELPERS / "full_stack_cleanup_harness.py")],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(REPO_ROOT),
            env=env,
        )

        line = harness.stdout.readline().strip()
        parts = dict(item.split("=") for item in line.split())
        xorg_pid = int(parts["XORG_PID"])
        vnc_pid = int(parts["VNC_PID"])
        assert _process_exists(xorg_pid)
        assert _process_exists(vnc_pid)

        os.kill(harness.pid, signal.SIGTERM)
        harness.wait(timeout=10)

        assert _wait_until_gone(xorg_pid)
        assert _wait_until_gone(vnc_pid)
    finally:
        if harness is not None and harness.poll() is None:
            harness.kill()
        xvfb.terminate()
        xvfb.wait(timeout=5)
