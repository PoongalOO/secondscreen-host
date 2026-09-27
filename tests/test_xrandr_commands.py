"""Tests de `secondscreen_host.pure.xrandr_commands` (HOST-020)."""

from secondscreen_host.pure.cvt import CvtMode
from secondscreen_host.pure.xrandr_commands import build_extended_screen_commands


def test_build_extended_screen_commands_shapes_the_three_commands() -> None:
    mode = CvtMode(
        name="1280x800_60.00",
        parameters=("83.50", "1280", "1352", "1480", "1680", "800", "803", "809", "831"),
    )

    commands = build_extended_screen_commands(
        mode=mode, virtual_output="VIRTUAL1", primary_output="eDP-1"
    )

    assert commands.newmode == (
        "xrandr",
        "--newmode",
        "1280x800_60.00",
        "83.50",
        "1280",
        "1352",
        "1480",
        "1680",
        "800",
        "803",
        "809",
        "831",
    )
    assert commands.addmode == ("xrandr", "--addmode", "VIRTUAL1", "1280x800_60.00")
    assert commands.activate == (
        "xrandr",
        "--output",
        "VIRTUAL1",
        "--mode",
        "1280x800_60.00",
        "--right-of",
        "eDP-1",
    )


def test_build_extended_screen_commands_are_argument_tuples_not_shell_strings() -> None:
    # Pas de risque d'injection : chaque élément est un argument séparé,
    # jamais une chaîne à interpréter par un shell.
    mode = CvtMode(name="mode test", parameters=("1", "2"))

    commands = build_extended_screen_commands(
        mode=mode, virtual_output="VIRTUAL1", primary_output="eDP-1"
    )

    for command in (commands.newmode, commands.addmode, commands.activate):
        assert isinstance(command, tuple)
        assert all(isinstance(part, str) for part in command)
