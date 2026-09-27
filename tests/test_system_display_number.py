"""Tests de `secondscreen_host.system.display_number` (HOST-031, partie
exécutante).
"""

import pytest

from secondscreen_host.system.display_number import _is_display_busy, pick_free_display_number


def test_is_display_busy_is_false_for_an_implausible_display_number() -> None:
    # :62 n'a aucune raison d'être occupé sur une machine de développement
    # ou un runner de CI ordinaire.
    assert _is_display_busy(62) is False


@pytest.mark.skipif(
    not __import__("pathlib").Path("/tmp/.X0-lock").exists(),
    reason="pas de session X réelle sur :0 dans cet environnement",
)
def test_is_display_busy_detects_the_real_x_session_on_this_machine() -> None:
    # Vérité de terrain : cette machine de développement fait tourner une
    # vraie session X sur :0 (voir le contexte de session), donc son
    # verrou existe réellement — pas une simulation.
    assert _is_display_busy(0) is True


def test_pick_free_display_number_returns_a_plausible_number() -> None:
    number = pick_free_display_number()

    assert isinstance(number, int)
    assert 1 <= number <= 63
