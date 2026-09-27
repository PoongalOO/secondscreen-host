"""Tests de `secondscreen_host.pure.app_state` (HOST-070)."""

from secondscreen_host.pure.app_state import AppState, compute_status


def test_not_configured_when_nothing_is_ready() -> None:
    status = compute_status(screen_configured=False, server_running=False)

    assert status.state is AppState.NOT_CONFIGURED
    assert status.button_label == "Configurer"
    assert status.button_enabled is True


def test_ready_when_screen_configured_but_server_stopped() -> None:
    status = compute_status(screen_configured=True, server_running=False)

    assert status.state is AppState.READY
    assert status.button_label == "Démarrer le serveur"


def test_running_when_server_is_running() -> None:
    status = compute_status(screen_configured=True, server_running=True)

    assert status.state is AppState.RUNNING
    assert status.button_label == "Arrêter"


def test_running_takes_priority_even_if_screen_configured_flag_is_stale() -> None:
    # Un serveur qui tourne implique forcément un écran configuré ; en cas
    # d'incohérence (bogue ailleurs), le fait le plus fort (le serveur
    # tourne réellement) l'emporte plutôt que de mélanger les deux états.
    status = compute_status(screen_configured=False, server_running=True)

    assert status.state is AppState.RUNNING
