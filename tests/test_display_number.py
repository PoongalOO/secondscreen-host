"""Tests de `secondscreen_host.pure.display_number` (HOST-031)."""

import pytest

from secondscreen_host.pure.display_number import (
    NoFreeDisplayNumberError,
    find_free_display_number,
)


def test_returns_start_when_nothing_is_busy() -> None:
    assert find_free_display_number(set(), start=1) == 1


def test_skips_busy_numbers_in_order() -> None:
    assert find_free_display_number({1, 2, 3}, start=1) == 4


def test_ignores_busy_numbers_outside_the_searched_range() -> None:
    # :0 est presque toujours le bureau existant : jamais un candidat, même
    # si on ne l'a pas explicitement marqué occupé (la recherche commence à
    # `start`, jamais avant).
    assert find_free_display_number({99}, start=1) == 1


def test_raises_when_the_whole_range_is_busy() -> None:
    busy = set(range(1, 4))
    with pytest.raises(NoFreeDisplayNumberError):
        find_free_display_number(busy, start=1, max_number=3)
