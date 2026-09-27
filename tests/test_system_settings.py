"""Tests de `secondscreen_host.system.settings` (HOST-060, partie
exécutante). Utilise de vrais fichiers (`tmp_path`), pas de simulation :
lire/écrire des fichiers est précisément ce que ce module fait.
"""

from __future__ import annotations

import json

from secondscreen_host.pure.settings import Settings
from secondscreen_host.system.settings import config_file_path, load_settings, save_settings


def test_config_file_path_respects_xdg_config_home(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    path = config_file_path()

    assert path == tmp_path / "secondscreen-host" / "config.json"


def test_config_file_path_falls_back_to_dot_config(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

    path = config_file_path()

    assert path == tmp_path / ".config" / "secondscreen-host" / "config.json"


def test_load_settings_returns_defaults_when_file_is_missing(tmp_path) -> None:
    settings = load_settings(tmp_path / "does-not-exist.json")

    assert settings == Settings()


def test_load_settings_returns_defaults_on_invalid_json(tmp_path) -> None:
    path = tmp_path / "config.json"
    path.write_text("ceci n'est pas du JSON {{{", encoding="utf-8")

    settings = load_settings(path)

    assert settings == Settings()


def test_load_settings_returns_defaults_on_truncated_json(tmp_path) -> None:
    # Simule une écriture interrompue par un plantage (avant que
    # `save_settings` n'écrive de façon atomique, voir le test dédié) :
    # un JSON tronqué doit rester un simple retour aux réglages par défaut.
    path = tmp_path / "config.json"
    path.write_text('{"virtual_output": "VIRTUAL1", "po', encoding="utf-8")

    settings = load_settings(path)

    assert settings == Settings()


def test_save_then_load_round_trip(tmp_path) -> None:
    path = tmp_path / "config.json"
    original = Settings(virtual_output="VIRTUAL1", port=5901)

    save_settings(original, path)
    loaded = load_settings(path)

    assert loaded == original


def test_save_settings_creates_parent_directories(tmp_path) -> None:
    path = tmp_path / "nested" / "dirs" / "config.json"

    save_settings(Settings(virtual_output="VIRTUAL1"), path)

    assert path.exists()


def test_save_settings_does_not_leave_a_temporary_file_behind(tmp_path) -> None:
    path = tmp_path / "config.json"

    save_settings(Settings(virtual_output="VIRTUAL1"), path)

    leftover = list(tmp_path.glob("*.tmp"))
    assert leftover == []


def test_save_settings_overwrites_a_previous_value(tmp_path) -> None:
    path = tmp_path / "config.json"
    save_settings(Settings(virtual_output="VIRTUAL1", port=5900), path)

    save_settings(Settings(virtual_output="VIRTUAL2", port=5901), path)

    assert load_settings(path) == Settings(virtual_output="VIRTUAL2", port=5901)


def test_saved_file_never_contains_a_password_like_field(tmp_path) -> None:
    # Canari (même principe que hygiene/SecretCanaryTest du projet
    # SecondScreen) : le fichier écrit sur disque ne doit jamais contenir
    # de champ qui ressemblerait à un mot de passe mémorisé.
    path = tmp_path / "config.json"

    save_settings(Settings(virtual_output="VIRTUAL1", port=5900), path)

    raw = path.read_text(encoding="utf-8")
    lowered = raw.lower()
    assert "password" not in lowered
    assert "passwd" not in lowered
    assert "motdepasse" not in lowered.replace(" ", "").replace("_", "")

    data = json.loads(raw)
    assert set(data.keys()) == {"virtual_output", "port"}
