"""Tests de `secondscreen_host.pure.x11vnc_command` (HOST-040)."""

import pytest

from secondscreen_host.pure.x11vnc_command import (
    MissingPasswordFileError,
    X11VncTarget,
    build_x11vnc_command,
)


def test_extended_screen_command_includes_clip() -> None:
    target = X11VncTarget(display=":0", clip="1280x800+1920+0")
    password_file_path = "/tmp/secondscreen-host-x.pass"

    command = build_x11vnc_command(target=target, password_file_path=password_file_path)

    assert command[0] == "x11vnc"
    assert "-display" in command and ":0" in command
    assert "-clip" in command
    assert command[command.index("-clip") + 1] == "1280x800+1920+0"
    assert "-forever" in command
    assert "-shared" in command


def test_isolated_screen_command_has_no_clip() -> None:
    target = X11VncTarget(display=":1", clip=None)
    password_file_path = "/tmp/secondscreen-host-x.pass"

    command = build_x11vnc_command(target=target, password_file_path=password_file_path)

    assert "-clip" not in command


def test_command_uses_the_given_port() -> None:
    target = X11VncTarget(display=":0", clip=None)

    command = build_x11vnc_command(
        target=target, password_file_path="/tmp/p.pass", port=5901
    )

    assert "-rfbport" in command
    assert command[command.index("-rfbport") + 1] == "5901"


def test_command_never_contains_a_bare_passwd_flag() -> None:
    # -passwd (plutôt que -passwdfile) exposerait le mot de passe en clair
    # dans la liste des processus (ps(1)) : jamais utilisé.
    target = X11VncTarget(display=":0", clip=None)

    command = build_x11vnc_command(target=target, password_file_path="/tmp/p.pass")

    assert "-passwd" not in command
    assert "-passwdfile" in command


def test_password_file_is_referenced_with_the_rm_prefix_so_x11vnc_deletes_it() -> None:
    target = X11VncTarget(display=":0", clip=None)

    command = build_x11vnc_command(target=target, password_file_path="/tmp/p.pass")

    passwdfile_arg = command[command.index("-passwdfile") + 1]
    assert passwdfile_arg == "rm:/tmp/p.pass"


def test_rejects_an_empty_password_file_path() -> None:
    target = X11VncTarget(display=":0", clip=None)

    with pytest.raises(MissingPasswordFileError):
        build_x11vnc_command(target=target, password_file_path="")


def test_command_is_a_tuple_of_strings_not_a_shell_string() -> None:
    target = X11VncTarget(display=":0", clip="1280x800+0+0")

    command = build_x11vnc_command(target=target, password_file_path="/tmp/p.pass")

    assert isinstance(command, tuple)
    assert all(isinstance(part, str) for part in command)
