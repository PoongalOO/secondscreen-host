"""Tests de `secondscreen_host.pure.dummy_xorg` (HOST-030).

`tests/fixtures/dummy_xorg_expected.conf` est un fichier golden : sa
structure (sections Device/Monitor/Screen, valeurs fixes) recopie celle
déjà écrite et vérifiée dans GUIDE_UBUNTU.md/GUIDE_MX_LINUX.md ; sa
`Modeline` vient du `CvtMode` réel de `tests/fixtures/cvt_1280x800_60.txt`
(HOST-020) plutôt que d'être recopiée à la main, pour rester cohérente si
`generate_dummy_xorg_config` change de forme.
"""

from pathlib import Path

from secondscreen_host.pure.cvt import parse_cvt_output
from secondscreen_host.pure.dummy_xorg import describe_dummy_screen, generate_dummy_xorg_config

FIXTURES = Path(__file__).parent / "fixtures"


def test_generated_config_matches_the_golden_file() -> None:
    cvt_text = (FIXTURES / "cvt_1280x800_60.txt").read_text(encoding="utf-8")
    mode = parse_cvt_output(cvt_text)

    generated = generate_dummy_xorg_config(mode)

    expected = (FIXTURES / "dummy_xorg_expected.conf").read_text(encoding="utf-8")
    assert generated == expected


def test_config_uses_the_dummy_driver() -> None:
    cvt_text = (FIXTURES / "cvt_1280x800_60.txt").read_text(encoding="utf-8")
    mode = parse_cvt_output(cvt_text)

    generated = generate_dummy_xorg_config(mode)

    assert 'Driver      "dummy"' in generated
    assert 'Modeline "1280x800_60.00"' in generated
    assert "Virtual 1280 800" in generated


def test_config_respects_a_custom_resolution() -> None:
    cvt_text = (FIXTURES / "cvt_1280x800_60.txt").read_text(encoding="utf-8")
    mode = parse_cvt_output(cvt_text)

    generated = generate_dummy_xorg_config(mode, width=1920, height=1080)

    assert "Virtual 1920 1080" in generated


def test_describe_dummy_screen_says_it_is_a_separate_desktop() -> None:
    message = describe_dummy_screen(1)

    assert "séparé" in message
    assert ":1" in message
    assert "DISPLAY=:1" in message
