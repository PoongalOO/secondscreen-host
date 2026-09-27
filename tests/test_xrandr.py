"""Tests de `secondscreen_host.pure.xrandr` (HOST-012).

Fixtures dans `tests/fixtures/` :
- `xrandr_real_intel_no_virtual.txt` : capture **réelle**, `xrandr --query`
  tel que produit sur la machine de développement (Debian 13, GPU Intel,
  pilote `i915`/`modesetting`) : 6 sorties, aucune `VIRTUAL*`. Le format
  texte d'une absence de sortie `VIRTUAL*` est le même quel que soit le
  pilote — ce fichier couvre donc aussi, du point de vue de l'analyseur, le
  cas du pilote propriétaire NVIDIA (voir AGENTS.md, règle 2), sans
  prétendre avoir été capturé sur du matériel NVIDIA.
- `xrandr_virtual_available.txt`, `xrandr_virtual_positioned.txt` :
  représentatives du format documenté et déjà vérifié dans
  `GUIDE_UBUNTU.md` du projet SecondScreen (pilote `modesetting`), pas
  recapturées sur du matériel réel dans cet environnement (aucun GPU ici
  n'expose de sortie `VIRTUAL*`).
"""

from pathlib import Path

import pytest

from secondscreen_host.pure.xrandr import parse_xrandr_query

FIXTURES = Path(__file__).parent / "fixtures"


def _read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_real_capture_has_no_virtual_candidate() -> None:
    result = parse_xrandr_query(_read_fixture("xrandr_real_intel_no_virtual.txt"))

    assert result.virtual_candidates == ()
    assert result.active_virtual_outputs == ()


def test_real_capture_finds_the_primary_output() -> None:
    result = parse_xrandr_query(_read_fixture("xrandr_real_intel_no_virtual.txt"))

    primary = result.primary
    assert primary is not None
    assert primary.name == "eDP-1"
    assert primary.connected is True
    assert primary.geometry is not None
    assert (primary.geometry.width, primary.geometry.height) == (1920, 1080)
    assert (primary.geometry.x, primary.geometry.y) == (0, 0)


def test_real_capture_parses_all_six_outputs_with_correct_states() -> None:
    result = parse_xrandr_query(_read_fixture("xrandr_real_intel_no_virtual.txt"))

    by_name = {output.name: output for output in result.outputs}
    assert set(by_name) == {"eDP-1", "HDMI-1", "DP-1", "HDMI-2", "DP-1-8", "DP-1-9"}

    assert by_name["HDMI-1"].connected is False
    assert by_name["DP-1"].connected is False
    assert by_name["HDMI-2"].connected is False

    assert by_name["DP-1-8"].connected is True
    assert by_name["DP-1-8"].geometry.x == 1920
    assert by_name["DP-1-9"].connected is True
    assert by_name["DP-1-9"].geometry.x == 3840


def test_virtual_available_fixture_is_a_candidate() -> None:
    result = parse_xrandr_query(_read_fixture("xrandr_virtual_available.txt"))

    names = {output.name for output in result.virtual_candidates}
    assert names == {"VIRTUAL1", "VIRTUAL2", "VIRTUAL3", "VIRTUAL4"}
    assert result.active_virtual_outputs == ()


def test_virtual_positioned_fixture_is_active_not_a_candidate() -> None:
    result = parse_xrandr_query(_read_fixture("xrandr_virtual_positioned.txt"))

    active = result.active_virtual_outputs
    assert len(active) == 1
    assert active[0].name == "VIRTUAL1"
    assert active[0].geometry.width == 1280
    assert active[0].geometry.height == 800
    assert active[0].geometry.x == 1920
    assert active[0].geometry.y == 0

    # VIRTUAL1 est déjà connectée : ce n'est plus une candidate à
    # configurer, seules VIRTUAL2/3/4 (toujours disconnected) le sont.
    candidate_names = {output.name for output in result.virtual_candidates}
    assert candidate_names == {"VIRTUAL2", "VIRTUAL3", "VIRTUAL4"}


def test_empty_input_produces_no_outputs() -> None:
    result = parse_xrandr_query("")

    assert result.outputs == ()
    assert result.primary is None


@pytest.mark.parametrize(
    "text",
    [
        "ceci n'est pas du tout une sortie xrandr\navec plusieurs lignes\n",
        "eDP-1 something-unexpected 1920x1080+0+0\n",
    ],
)
def test_unrecognized_lines_are_skipped_not_raised(text: str) -> None:
    # Ne doit jamais lever d'exception, quelle que soit la variation de
    # format rencontrée (voir AGENTS.md, règle 2) : au pire, un résultat
    # vide.
    result = parse_xrandr_query(text)

    assert isinstance(result.outputs, tuple)


def test_partially_unrecognized_input_still_parses_the_valid_lines() -> None:
    text = (
        "Screen 0: minimum 320 x 200, current 1920 x 1080, maximum 8192 x 8192\n"
        "une-ligne-totalement-inattendue-dans-un-format-futur-de-xrandr\n"
        "eDP-1 connected primary 1920x1080+0+0 (normal left inverted right x axis y axis)\n"
    )

    result = parse_xrandr_query(text)

    assert len(result.outputs) == 1
    assert result.outputs[0].name == "eDP-1"
