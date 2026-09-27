"""Tests de `secondscreen_host.pure.secret` (HOST-042)."""

import pytest

from secondscreen_host.pure.secret import Secret, SecretAlreadyClearedError


def test_reveal_returns_the_original_value() -> None:
    secret = Secret("hunter2")

    assert secret.reveal() == "hunter2"


def test_is_not_cleared_right_after_creation() -> None:
    secret = Secret("hunter2")

    assert secret.is_cleared is False


def test_clear_marks_the_secret_as_cleared() -> None:
    secret = Secret("hunter2")

    secret.clear()

    assert secret.is_cleared is True


def test_reveal_after_clear_raises_instead_of_returning_stale_data() -> None:
    secret = Secret("hunter2")
    secret.clear()

    with pytest.raises(SecretAlreadyClearedError):
        secret.reveal()


def test_clear_is_idempotent() -> None:
    secret = Secret("hunter2")

    secret.clear()
    secret.clear()  # ne doit pas lever

    assert secret.is_cleared is True


def test_clear_actually_overwrites_the_underlying_bytes() -> None:
    # Vérifie l'effacement réel, pas seulement le changement d'état :
    # accès volontaire à l'attribut interne pour le prouver.
    secret = Secret("hunter2")
    buffer_reference = secret._buffer

    secret.clear()

    assert buffer_reference is not None
    assert all(byte == 0 for byte in buffer_reference)


def test_supports_non_ascii_passwords() -> None:
    secret = Secret("mötdepassé😀")

    assert secret.reveal() == "mötdepassé😀"
