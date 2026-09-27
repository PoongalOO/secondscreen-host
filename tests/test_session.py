"""Tests de `secondscreen_host.pure.session` (HOST-011).

Les combinaisons de variables d'environnement viennent de deux sources :
- la session réelle de la machine qui a servi à développer ce module
  (Debian, session Xorg — voir `test_detect_session_type_real_x11_capture`) ;
- le comportement documenté de GNOME sous Wayland, où `WAYLAND_DISPLAY` et
  `DISPLAY` sont tous les deux positionnés (XWayland) : ce cas n'a pas été
  recapturé sur une vraie session GNOME/Wayland dans cet environnement,
  d'où son nom `_documented_` plutôt que `_real_`.
"""

from secondscreen_host.pure.session import SessionType, detect_session_type, explain_session_type


def test_detect_session_type_real_x11_capture() -> None:
    # Valeurs réellement lues sur la machine de développement (Debian 13,
    # session Xorg) : XDG_SESSION_TYPE=x11, WAYLAND_DISPLAY absente, DISPLAY=:0.
    info = detect_session_type(xdg_session_type="x11", wayland_display=None, display=":0")

    assert info.session_type is SessionType.X11


def test_detect_session_type_documented_gnome_wayland() -> None:
    # XWayland positionne souvent DISPLAY même sous Wayland : sa seule
    # présence ne doit pas suffire à conclure X11.
    info = detect_session_type(
        xdg_session_type="wayland", wayland_display="wayland-0", display=":0"
    )

    assert info.session_type is SessionType.WAYLAND


def test_detect_session_type_wayland_display_wins_even_if_xdg_session_type_disagrees() -> None:
    # WAYLAND_DISPLAY reflète ce à quoi l'application peut réellement se
    # connecter : il l'emporte même si XDG_SESSION_TYPE dit autre chose
    # (configuration incohérente, mais WAYLAND_DISPLAY est le signal le
    # plus direct).
    info = detect_session_type(xdg_session_type="x11", wayland_display="wayland-0", display=":0")

    assert info.session_type is SessionType.WAYLAND


def test_detect_session_type_x11_without_xdg_session_type() -> None:
    # XDG_SESSION_TYPE n'est pas garanti positionnée (voir AGENTS.md,
    # règle 2 côté xrandr, même principe ici) : DISPLAY seule doit suffire.
    info = detect_session_type(xdg_session_type=None, wayland_display=None, display=":0")

    assert info.session_type is SessionType.X11


def test_detect_session_type_unknown_when_nothing_is_set() -> None:
    info = detect_session_type(xdg_session_type=None, wayland_display=None, display=None)

    assert info.session_type is SessionType.UNKNOWN


def test_detect_session_type_ignores_empty_strings_like_missing_values() -> None:
    # os.environ.get peut renvoyer une chaîne vide selon comment la
    # variable a été exportée : traité comme absent, pas comme une valeur.
    info = detect_session_type(xdg_session_type="", wayland_display="", display="")

    assert info.session_type is SessionType.UNKNOWN


def test_explain_session_type_is_empty_for_x11() -> None:
    info = detect_session_type(xdg_session_type="x11", wayland_display=None, display=":0")

    assert explain_session_type(info) == ""


def test_explain_session_type_mentions_xorg_and_a_guide_for_wayland() -> None:
    info = detect_session_type(
        xdg_session_type="wayland", wayland_display="wayland-0", display=":0"
    )

    message = explain_session_type(info)

    assert "Xorg" in message
    assert "GUIDE_UBUNTU.md" in message
    assert "GUIDE_MX_LINUX.md" in message


def test_explain_session_type_is_non_empty_for_unknown() -> None:
    info = detect_session_type(xdg_session_type=None, wayland_display=None, display=None)

    assert explain_session_type(info) != ""
