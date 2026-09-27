"""Tests de `secondscreen_host.system.x11vnc` (HOST-041).

`_wait_until_ready_or_raise` lit un vrai descripteur de pseudo-terminal
(`select.select`/`os.read`) : elle a donc besoin d'un vrai pty avec un vrai
processus derrière, pas d'un double qui ne fournirait pas de vrais
descripteurs de fichier. Les cas sont testés avec de vrais sous-processus
synthétiques (`sh -c ...`) qui imitent la forme du comportement réel de
x11vnc (une ligne « PORT=... », ou une sortie immédiate en erreur) — le
vrai x11vnc, lui, est vérifié séparément (voir
`test_start_and_stop_a_real_x11vnc_against_a_real_xvfb`, sautée si
`x11vnc`/`Xvfb` ne sont pas installés).
"""

from __future__ import annotations

import os
import pty
import shutil
import socket
import subprocess
import time
from collections import deque
from pathlib import Path

import pytest

import secondscreen_host.system.x11vnc as x11vnc_module
from secondscreen_host.pure.secret import Secret
from secondscreen_host.pure.x11vnc_command import X11VncTarget
from secondscreen_host.system.x11vnc import (
    X11VncStartError,
    _wait_until_ready_or_raise,
    start_x11vnc,
)


def _spawn_on_a_pty(script: str) -> tuple[subprocess.Popen, int]:
    master_fd, slave_fd = pty.openpty()
    process = subprocess.Popen(["sh", "-c", script], stdout=slave_fd, stderr=slave_fd)
    os.close(slave_fd)
    return process, master_fd


def test_wait_until_ready_returns_as_soon_as_the_port_line_appears() -> None:
    process, fd = _spawn_on_a_pty("echo something-else; echo 'PORT=5900'; sleep 5")
    log_lines: deque[str] = deque(maxlen=200)
    try:
        _wait_until_ready_or_raise(process, fd, log_lines)  # ne doit pas attendre les 5s
        assert any(line.startswith("PORT=") for line in log_lines)
    finally:
        process.kill()
        process.wait(timeout=5)
        os.close(fd)


def test_wait_until_ready_raises_with_the_real_error_output_on_immediate_exit() -> None:
    process, fd = _spawn_on_a_pty("echo 'Error: could not obtain listening port.'; exit 1")
    log_lines: deque[str] = deque(maxlen=200)
    try:
        with pytest.raises(X11VncStartError, match="could not obtain listening port"):
            _wait_until_ready_or_raise(process, fd, log_lines)
    finally:
        os.close(fd)


def test_wait_until_ready_kills_the_process_and_raises_on_timeout(monkeypatch) -> None:
    monkeypatch.setattr(x11vnc_module, "READY_TIMEOUT_SECONDS", 0.3)
    monkeypatch.setattr(x11vnc_module, "POLL_INTERVAL_SECONDS", 0.05)
    process, fd = _spawn_on_a_pty("sleep 30")
    log_lines: deque[str] = deque(maxlen=200)
    try:
        with pytest.raises(X11VncStartError, match="délai"):
            _wait_until_ready_or_raise(process, fd, log_lines)
        time.sleep(0.2)
        assert process.poll() is not None  # bien tué, pas laissé tourner
    finally:
        os.close(fd)


def test_start_x11vnc_raises_before_touching_disk_if_secret_already_cleared() -> None:
    secret = Secret("hunter2")
    secret.clear()

    with pytest.raises(X11VncStartError, match="déjà été effacé"):
        start_x11vnc(target=X11VncTarget(display=":99", clip=None), password=secret)


def test_start_x11vnc_raises_a_clear_error_when_binary_is_missing(monkeypatch) -> None:
    def fake_popen(command, **kwargs):
        raise FileNotFoundError("x11vnc")

    monkeypatch.setattr(x11vnc_module.subprocess, "Popen", fake_popen)

    with pytest.raises(X11VncStartError, match="introuvable"):
        start_x11vnc(target=X11VncTarget(display=":99", clip=None), password=Secret("hunter2"))


def _fake_popen_writing_to_the_same_pty(script: str):
    """Construit un remplaçant de `subprocess.Popen` qui ignore la commande
    demandée (x11vnc) mais écrit sur le **même** pty (`stdout`/`stderr`
    reçus en argument) — pour que la mécanique de lecture réelle du module
    (pty + fil d'arrière-plan) soit exercée pour de vrai, sans dépendre du
    vrai binaire x11vnc."""
    real_popen = subprocess.Popen

    def fake_popen(command, *, stdout, stderr, close_fds):
        return real_popen(["sh", "-c", script], stdout=stdout, stderr=stderr, close_fds=close_fds)

    return fake_popen


def test_start_x11vnc_writes_and_then_removes_the_password_file(monkeypatch) -> None:
    written_paths: list[Path] = []
    real_popen = subprocess.Popen

    def fake_popen(command, *, stdout, stderr, close_fds):
        passwdfile_arg = next(a for a in command if a.startswith("rm:"))
        path = Path(passwdfile_arg[len("rm:") :])
        written_paths.append(path)
        assert path.exists()
        assert path.read_text(encoding="utf-8") == "hunter2"
        path.unlink()  # simule ce que fait vraiment x11vnc : lit puis supprime
        return real_popen(
            ["sh", "-c", "echo 'PORT=5900'; sleep 5"],
            stdout=stdout,
            stderr=stderr,
            close_fds=close_fds,
        )

    monkeypatch.setattr(x11vnc_module.subprocess, "Popen", fake_popen)

    vnc = start_x11vnc(target=X11VncTarget(display=":99", clip=None), password=Secret("hunter2"))
    try:
        assert vnc.port == 5900
        assert vnc.is_running() is True
        assert not written_paths[0].exists()
    finally:
        vnc.stop()


def test_background_reader_keeps_draining_output_after_startup(monkeypatch) -> None:
    # Preuve que le fil d'arrière-plan lit vraiment en continu (pas
    # seulement le temps de confirmer le démarrage) : la commande continue
    # à produire des lignes après le "PORT=", elles doivent apparaître dans
    # `recent_log_lines()` sans qu'on ait rien lu nous-mêmes.
    monkeypatch.setattr(
        x11vnc_module.subprocess,
        "Popen",
        _fake_popen_writing_to_the_same_pty(
            "echo 'PORT=5900'; for i in 1 2 3; do echo ligne-continue-$i; sleep 0.1; done; sleep 5"
        ),
    )

    vnc = start_x11vnc(target=X11VncTarget(display=":99", clip=None), password=Secret("hunter2"))
    try:
        time.sleep(0.6)
        lines = vnc.recent_log_lines()
        assert any("ligne-continue-3" in line for line in lines)
    finally:
        vnc.stop()


def test_stop_clears_the_secret(monkeypatch) -> None:
    secret = Secret("hunter2")
    monkeypatch.setattr(
        x11vnc_module.subprocess,
        "Popen",
        _fake_popen_writing_to_the_same_pty("echo 'PORT=5900'; sleep 5"),
    )

    vnc = start_x11vnc(target=X11VncTarget(display=":99", clip=None), password=secret)

    assert secret.is_cleared is False
    vnc.stop()
    assert secret.is_cleared is True


def test_stop_leaves_no_process_and_closes_the_pty(monkeypatch) -> None:
    monkeypatch.setattr(
        x11vnc_module.subprocess,
        "Popen",
        _fake_popen_writing_to_the_same_pty("echo 'PORT=5900'; sleep 30"),
    )

    vnc = start_x11vnc(target=X11VncTarget(display=":99", clip=None), password=Secret("hunter2"))
    vnc.stop()

    assert vnc.process.poll() is not None
    with pytest.raises(OSError):
        os.fstat(vnc._master_fd)  # le descripteur a bien été fermé


@pytest.mark.skipif(
    shutil.which("x11vnc") is None or shutil.which("Xvfb") is None,
    reason="x11vnc et/ou Xvfb non installés",
)
def test_start_and_stop_a_real_x11vnc_against_a_real_xvfb() -> None:
    # Vérité de terrain, sans simulation : un vrai Xvfb, un vrai x11vnc
    # dessus, une vraie connexion TCP qui reçoit la bannière du protocole
    # RFB — pas seulement « le processus a démarré ».
    xvfb = subprocess.Popen(["Xvfb", ":250", "-screen", "0", "1280x800x24", "-nolisten", "tcp"])
    try:
        for _ in range(50):
            if Path("/tmp/.X250-lock").exists():
                break
            time.sleep(0.1)
        else:
            pytest.fail("Xvfb n'a pas démarré à temps")

        vnc = start_x11vnc(
            target=X11VncTarget(display=":250", clip=None),
            password=Secret("hunter2"),
        )
        try:
            assert vnc.is_running() is True
            with socket.create_connection(("127.0.0.1", vnc.port), timeout=3) as sock:
                banner = sock.recv(12)
                assert banner.startswith(b"RFB ")
        finally:
            vnc.stop()

        time.sleep(0.3)
        assert vnc.process.poll() is not None  # bien arrêté, pas orphelin
    finally:
        xvfb.terminate()
        xvfb.wait(timeout=5)
