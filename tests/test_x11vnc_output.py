"""Tests de `secondscreen_host.pure.x11vnc_output` (HOST-041).

Les lignes utilisées ici sont recopiées de la sortie **réelle** de x11vnc
0.9.16, observée dans un conteneur jetable (voir le commentaire en tête de
`secondscreen_host/pure/x11vnc_output.py`).
"""

from secondscreen_host.pure.x11vnc_output import is_ready_line


def test_recognizes_the_real_port_line() -> None:
    assert is_ready_line("PORT=5900\n") is True


def test_recognizes_the_port_line_with_leading_whitespace() -> None:
    assert is_ready_line("  PORT=5900") is True


def test_does_not_recognize_unrelated_log_lines() -> None:
    assert is_ready_line("27/09/2026 14:04:07 screen setup finished.\n") is False
    assert is_ready_line("The VNC desktop is:      6190914a0591:0\n") is False


def test_does_not_recognize_the_error_line() -> None:
    assert is_ready_line("27/09/2026 14:05:02 Error: could not obtain listening port.\n") is False


def test_empty_line_is_not_ready() -> None:
    assert is_ready_line("") is False
    assert is_ready_line("\n") is False
