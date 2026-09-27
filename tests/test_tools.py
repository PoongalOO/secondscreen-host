"""Tests de `secondscreen_host.pure.tools` (HOST-010)."""

from secondscreen_host.pure.tools import (
    REQUIRED_TOOLS,
    RequiredTool,
    ToolCheckResult,
    format_missing_tools_message,
    missing_tools,
)


def test_required_tools_cover_xrandr_cvt_x11vnc_ip() -> None:
    names = {tool.name for tool in REQUIRED_TOOLS}
    assert names == {"xrandr", "cvt", "x11vnc", "ip"}


def test_tool_check_result_is_available() -> None:
    tool = RequiredTool("xrandr", "x11-xserver-utils", "test")
    assert ToolCheckResult(tool, found_at="/usr/bin/xrandr").is_available is True
    assert ToolCheckResult(tool, found_at=None).is_available is False


def test_missing_tools_filters_only_absent_ones() -> None:
    xrandr = RequiredTool("xrandr", "x11-xserver-utils", "détecter les écrans")
    cvt = RequiredTool("cvt", "xcvt", "calculer un mode")
    results = [
        ToolCheckResult(xrandr, found_at="/usr/bin/xrandr"),
        ToolCheckResult(cvt, found_at=None),
    ]

    missing = missing_tools(results)

    assert missing == [results[1]]


def test_missing_tools_empty_when_all_present() -> None:
    tool = RequiredTool("xrandr", "x11-xserver-utils", "détecter les écrans")
    results = [ToolCheckResult(tool, found_at="/usr/bin/xrandr")]

    assert missing_tools(results) == []


def test_format_missing_tools_message_is_empty_when_nothing_missing() -> None:
    assert format_missing_tools_message([]) == ""


def test_format_missing_tools_message_lists_tool_and_package() -> None:
    tool = RequiredTool("cvt", "xcvt", "calculer le mode d'affichage 1280x800")
    missing = [ToolCheckResult(tool, found_at=None)]

    message = format_missing_tools_message(missing)

    assert "cvt" in message
    assert "xcvt" in message
    assert "calculer le mode d'affichage 1280x800" in message
    assert "sudo apt install xcvt" in message


def test_format_missing_tools_message_deduplicates_shared_package() -> None:
    # xserver-xorg-core et xserver-xorg-video-dummy sont dans le même
    # RequiredTool.package_hint : vérifie qu'un paquet commun à plusieurs
    # outils manquants n'apparaît qu'une fois dans la commande à lancer.
    tool_a = RequiredTool("a", "paquet-commun", "raison a")
    tool_b = RequiredTool("b", "paquet-commun", "raison b")
    missing = [
        ToolCheckResult(tool_a, found_at=None),
        ToolCheckResult(tool_b, found_at=None),
    ]

    message = format_missing_tools_message(missing)

    assert message.count("paquet-commun") == 3  # 2 lignes de détail + 1 commande
    install_line = [line for line in message.splitlines() if line.strip().startswith("sudo")][0]
    assert install_line.count("paquet-commun") == 1
