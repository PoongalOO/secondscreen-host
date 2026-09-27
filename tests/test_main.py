"""Tests de `secondscreen_host.__main__` (fonctions pures uniquement,
voir AGENTS.md règle 3 : pas besoin de GTK ni d'un affichage pour ceux-ci)."""

from secondscreen_host.__main__ import self_test_requested


def test_self_test_requested_absent() -> None:
    assert self_test_requested([]) is False


def test_self_test_requested_present() -> None:
    assert self_test_requested(["--self-test"]) is True


def test_self_test_requested_ignores_other_args() -> None:
    assert self_test_requested(["--verbose", "--self-test", "--port=5900"]) is True
    assert self_test_requested(["--verbose", "--port=5900"]) is False
