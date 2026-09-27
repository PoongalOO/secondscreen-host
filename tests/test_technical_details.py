"""Tests de `secondscreen_host.pure.technical_details` (HOST-071)."""

from secondscreen_host.pure.session import SessionInfo, SessionType
from secondscreen_host.pure.technical_details import format_technical_details
from secondscreen_host.pure.tools import RequiredTool, ToolCheckResult
from secondscreen_host.pure.xrandr import OutputGeometry, XrandrOutput, XrandrQueryResult


def test_shows_not_yet_checked_when_nothing_is_available_yet() -> None:
    text = format_technical_details(
        tool_results=[], session_info=None, xrandr_result=None, last_error=None
    )

    assert "pas encore vérifiés" in text
    assert "pas encore vérifiée" in text
    assert "pas encore interrogées" in text
    assert "Dernière erreur" not in text


def test_shows_available_and_missing_tools() -> None:
    xrandr_tool = RequiredTool("xrandr", "x11-xserver-utils", "détecter les écrans")
    cvt_tool = RequiredTool("cvt", "xcvt", "calculer un mode")
    results = [
        ToolCheckResult(xrandr_tool, found_at="/usr/bin/xrandr"),
        ToolCheckResult(cvt_tool, found_at=None),
    ]

    text = format_technical_details(
        tool_results=results, session_info=None, xrandr_result=None, last_error=None
    )

    assert "xrandr : trouvé (/usr/bin/xrandr)" in text
    assert "cvt : MANQUANT (paquet : xcvt)" in text


def test_shows_session_info() -> None:
    info = SessionInfo(SessionType.X11, detail="XDG_SESSION_TYPE='x11'")

    text = format_technical_details(
        tool_results=[], session_info=info, xrandr_result=None, last_error=None
    )

    assert "x11" in text
    assert "XDG_SESSION_TYPE='x11'" in text


def test_shows_xrandr_outputs_with_geometry_and_primary_marker() -> None:
    result = XrandrQueryResult(
        outputs=(
            XrandrOutput(
                name="eDP-1",
                connected=True,
                is_primary=True,
                geometry=OutputGeometry(1920, 1080, 0, 0),
            ),
            XrandrOutput(name="VIRTUAL1", connected=False, is_primary=False, geometry=None),
        )
    )

    text = format_technical_details(
        tool_results=[], session_info=None, xrandr_result=result, last_error=None
    )

    assert "eDP-1 : connectée 1920x1080+0+0 [principale]" in text
    assert "VIRTUAL1 : déconnectée" in text


def test_shows_no_output_found_when_xrandr_result_is_empty() -> None:
    text = format_technical_details(
        tool_results=[],
        session_info=None,
        xrandr_result=XrandrQueryResult(outputs=()),
        last_error=None,
    )

    assert "aucune sortie trouvée" in text


def test_shows_the_last_error_when_present() -> None:
    text = format_technical_details(
        tool_results=[], session_info=None, xrandr_result=None, last_error="x11vnc introuvable"
    )

    assert "Dernière erreur : x11vnc introuvable" in text
