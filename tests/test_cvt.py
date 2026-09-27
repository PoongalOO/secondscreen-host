"""Tests de `secondscreen_host.pure.cvt` (HOST-020).

`tests/fixtures/cvt_1280x800_60.txt` : sortie **réelle** de
`cvt 1280 800 60` (paquet `xcvt`, capturée dans un conteneur Ubuntu 22.04
jetable — absent de la machine de développement elle-même, voir le bogue
`xcvt` déjà documenté dans GUIDE_UBUNTU.md).
"""

from pathlib import Path

import pytest

from secondscreen_host.pure.cvt import CvtParseError, parse_cvt_output

FIXTURES = Path(__file__).parent / "fixtures"


def test_parses_real_cvt_output() -> None:
    text = (FIXTURES / "cvt_1280x800_60.txt").read_text(encoding="utf-8")

    mode = parse_cvt_output(text)

    assert mode.name == "1280x800_60.00"
    assert mode.parameters == (
        "83.50",
        "1280",
        "1352",
        "1480",
        "1680",
        "800",
        "803",
        "809",
        "831",
        "-hsync",
        "+vsync",
    )


def test_ignores_the_leading_comment_line() -> None:
    text = "# un commentaire quelconque\nModeline \"x\" 1 2 3\n"

    mode = parse_cvt_output(text)

    assert mode.name == "x"
    assert mode.parameters == ("1", "2", "3")


def test_raises_a_clear_error_when_no_modeline_is_present() -> None:
    with pytest.raises(CvtParseError):
        parse_cvt_output("une sortie inattendue sans aucune ligne Modeline\n")


def test_raises_a_clear_error_on_empty_output() -> None:
    with pytest.raises(CvtParseError):
        parse_cvt_output("")
