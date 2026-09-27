"""Tests de `secondscreen_host.system.dummy_xorg` (HOST-031).

Les chemins d'échec (élévation absente, binaire absent, Xorg qui s'arrête
immédiatement, délai dépassé) sont testés en remplaçant `subprocess.Popen`
et `shutil.which` : on ne peut pas fiablement forcer un vrai `Xorg` à
échouer de chaque façon voulue sans modifier l'environnement réel de la
machine de test.

Le succès, lui, est vérifié avec un **vrai** `Xorg` + pilote `dummy` quand
le test tourne en root (voir `test_start_and_stop_a_real_dummy_xorg`) :
c'est le cas dans un conteneur jetable utilisé pour cette vérification,
jamais sur la machine de développement elle-même ni en CI (qui tournent
toutes deux sans privilèges root). Ce test contourne volontairement
`pkexec` (`elevation_command=[]`) puisqu'il est déjà root : il vérifie donc
le cycle de vie réel du serveur X (démarrage, détection de disponibilité,
arrêt propre, absence de processus orphelin), pas la boîte de dialogue
`pkexec` elle-même — qui suppose un agent polkit et une session graphique,
à confirmer sur le vrai matériel (HOST-101/HOST-102).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

import secondscreen_host.system.dummy_xorg as dummy_xorg_module
from secondscreen_host.pure.cvt import CvtMode
from secondscreen_host.system.dummy_xorg import DummyScreenStartError, start_dummy_screen

MODE = CvtMode(
    name="1280x800_60.00",
    parameters=("83.50", "1280", "1352", "1480", "1680", "800", "803", "809", "831"),
)


class FakeProcess:
    """Double de `subprocess.Popen` : pas de vrai processus, juste de quoi
    piloter `poll()`/`terminate()`/`kill()`/`wait()` depuis le test."""

    def __init__(self, *, returncode: int | None = None, stderr_text: str = "") -> None:
        self.returncode = returncode
        self._stderr_text = stderr_text
        self.stderr = _FakeStream(stderr_text)
        self.terminated = False
        self.killed = False

    def poll(self):
        return self.returncode

    def terminate(self) -> None:
        self.terminated = True
        self.returncode = 0

    def kill(self) -> None:
        self.killed = True
        self.returncode = -9

    def wait(self, timeout=None) -> int:
        return self.returncode if self.returncode is not None else 0


class _FakeStream:
    def __init__(self, text: str) -> None:
        self._text = text

    def read(self) -> str:
        return self._text


def test_raises_immediately_when_pkexec_is_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(dummy_xorg_module.shutil, "which", lambda name: None)

    with pytest.raises(DummyScreenStartError, match="pkexec"):
        start_dummy_screen(MODE)


def test_raises_a_clear_error_when_xorg_binary_is_missing(monkeypatch) -> None:
    def fake_popen(*args, **kwargs):
        raise FileNotFoundError("Xorg")

    monkeypatch.setattr(dummy_xorg_module.subprocess, "Popen", fake_popen)

    with pytest.raises(DummyScreenStartError, match="introuvable"):
        start_dummy_screen(MODE, elevation_command=[])


def test_config_file_is_removed_when_xorg_binary_is_missing(monkeypatch, tmp_path) -> None:
    written_paths: list[Path] = []
    original_write = dummy_xorg_module._write_config_file

    def spying_write(content: str) -> Path:
        path = original_write(content)
        written_paths.append(path)
        return path

    monkeypatch.setattr(dummy_xorg_module, "_write_config_file", spying_write)

    def fake_popen(*args, **kwargs):
        raise FileNotFoundError("Xorg")

    monkeypatch.setattr(dummy_xorg_module.subprocess, "Popen", fake_popen)

    with pytest.raises(DummyScreenStartError):
        start_dummy_screen(MODE, elevation_command=[])

    assert len(written_paths) == 1
    assert not written_paths[0].exists()


def test_raises_a_clear_error_when_xorg_exits_immediately(monkeypatch) -> None:
    fake_process = FakeProcess(returncode=1, stderr_text="(EE) dummy driver not found")

    monkeypatch.setattr(dummy_xorg_module.subprocess, "Popen", lambda *a, **k: fake_process)

    with pytest.raises(DummyScreenStartError, match="dummy driver not found"):
        start_dummy_screen(MODE, elevation_command=[])


def test_raises_a_clear_error_on_readiness_timeout(monkeypatch) -> None:
    # Processus jamais prêt (poll() reste None, aucun verrou ne se crée) :
    # timeout raccourci pour ne pas ralentir la suite de tests.
    monkeypatch.setattr(dummy_xorg_module, "READY_TIMEOUT_SECONDS", 0.2)
    monkeypatch.setattr(dummy_xorg_module, "POLL_INTERVAL_SECONDS", 0.05)
    fake_process = FakeProcess(returncode=None)

    monkeypatch.setattr(dummy_xorg_module.subprocess, "Popen", lambda *a, **k: fake_process)

    with pytest.raises(DummyScreenStartError, match="délai"):
        start_dummy_screen(MODE, elevation_command=[])

    assert fake_process.killed is True


def test_stop_terminates_a_running_process_and_removes_the_config(tmp_path) -> None:
    from secondscreen_host.system.dummy_xorg import DummyScreenProcess

    config_path = tmp_path / "fake.conf"
    config_path.write_text("contenu factice")
    fake_process = FakeProcess(returncode=None)

    screen = DummyScreenProcess(display_number=42, config_path=config_path, process=fake_process)
    screen.stop()

    assert fake_process.terminated is True
    assert not config_path.exists()


def test_stop_is_idempotent_on_an_already_stopped_process(tmp_path) -> None:
    from secondscreen_host.system.dummy_xorg import DummyScreenProcess

    config_path = tmp_path / "fake.conf"
    config_path.write_text("contenu factice")
    fake_process = FakeProcess(returncode=0)  # déjà arrêté

    screen = DummyScreenProcess(display_number=42, config_path=config_path, process=fake_process)
    screen.stop()  # ne doit rien lever
    screen.stop()  # ni la seconde fois

    assert fake_process.terminated is False  # jamais appelé : déjà arrêté
    assert not config_path.exists()


@pytest.mark.skipif(os.geteuid() != 0, reason="nécessite root (conteneur jetable)")
@pytest.mark.skipif(shutil.which("Xorg") is None, reason="Xorg non installé")
def test_start_and_stop_a_real_dummy_xorg() -> None:
    # Vérité de terrain, sans simulation : démarre un vrai Xorg avec le
    # pilote dummy, vérifie qu'il répond réellement (xdpyinfo), l'arrête,
    # et vérifie qu'aucun processus Xorg n'est resté orphelin.
    screen = start_dummy_screen(MODE, elevation_command=[])
    try:
        assert Path(f"/tmp/.X{screen.display_number}-lock").exists()

        result = subprocess.run(
            ["xdpyinfo", "-display", screen.display],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "1280x800" in result.stdout
    finally:
        screen.stop()

    time.sleep(0.3)  # laisser le temps au processus de disparaître de la table des tâches
    assert not Path(f"/tmp/.X{screen.display_number}-lock").exists()
    assert screen.process.poll() is not None  # plus orphelin : bien arrêté
