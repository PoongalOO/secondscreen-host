"""Tests de `secondscreen_host.pure.settings` (HOST-060)."""

from secondscreen_host.pure.settings import (
    DEFAULT_PORT,
    Settings,
    parse_settings,
    resolve_remembered_output,
)


def test_default_settings_have_no_remembered_output() -> None:
    settings = Settings()

    assert settings.virtual_output is None
    assert settings.port == DEFAULT_PORT


def test_parse_settings_reads_valid_data() -> None:
    settings = parse_settings({"virtual_output": "VIRTUAL1", "port": 5901})

    assert settings.virtual_output == "VIRTUAL1"
    assert settings.port == 5901


def test_parse_settings_falls_back_to_defaults_when_not_a_dict() -> None:
    assert parse_settings(None) == Settings()
    assert parse_settings("un texte") == Settings()
    assert parse_settings([1, 2, 3]) == Settings()


def test_parse_settings_falls_back_when_virtual_output_has_the_wrong_type() -> None:
    settings = parse_settings({"virtual_output": 42, "port": 5900})

    assert settings.virtual_output is None


def test_parse_settings_falls_back_when_virtual_output_is_empty() -> None:
    settings = parse_settings({"virtual_output": "", "port": 5900})

    assert settings.virtual_output is None


def test_parse_settings_ignores_missing_keys() -> None:
    settings = parse_settings({})

    assert settings == Settings()


def test_parse_settings_falls_back_when_port_is_out_of_range() -> None:
    assert parse_settings({"port": 0}).port == DEFAULT_PORT
    assert parse_settings({"port": 70000}).port == DEFAULT_PORT
    assert parse_settings({"port": -1}).port == DEFAULT_PORT


def test_parse_settings_falls_back_when_port_has_the_wrong_type() -> None:
    assert parse_settings({"port": "5900"}).port == DEFAULT_PORT
    assert parse_settings({"port": 5900.5}).port == DEFAULT_PORT


def test_parse_settings_rejects_a_boolean_port() -> None:
    # bool est une sous-classe d'int en Python : sans garde explicite,
    # {"port": true} deviendrait silencieusement le port 1.
    assert parse_settings({"port": True}).port == DEFAULT_PORT


def test_resolve_remembered_output_keeps_it_when_still_available() -> None:
    settings = Settings(virtual_output="VIRTUAL1")

    assert resolve_remembered_output(settings, ["VIRTUAL1", "VIRTUAL2"]) == "VIRTUAL1"


def test_resolve_remembered_output_drops_it_when_hardware_changed() -> None:
    # La configuration matérielle a changé entre deux lancements (autre
    # poste, docking station différente...) : ne jamais supposer que le
    # réglage mémorisé est toujours valide (CAHIER_DES_CHARGES.md, F06).
    settings = Settings(virtual_output="VIRTUAL1")

    assert resolve_remembered_output(settings, ["VIRTUAL2", "VIRTUAL3"]) is None


def test_resolve_remembered_output_is_none_when_nothing_was_remembered() -> None:
    settings = Settings(virtual_output=None)

    assert resolve_remembered_output(settings, ["VIRTUAL1"]) is None


def test_resolve_remembered_output_is_none_when_no_candidates_at_all() -> None:
    settings = Settings(virtual_output="VIRTUAL1")

    assert resolve_remembered_output(settings, []) is None
