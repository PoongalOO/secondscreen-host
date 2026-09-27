"""Tests de `secondscreen_host.ui.main_window` (HOST-070, HOST-071,
HOST-072).

Contrairement à `Gtk.Application` seul (voir test_app.py), construire de
vrais widgets (`Gtk.Label`, `Gtk.Box`...) demande un vrai contexte de style
GTK, donc un vrai affichage — vérifié : ça échoue immédiatement avec une
erreur fatale (`Gtk-ERROR **: Can't create a GtkStyleContext without a
display connection`) sans `$DISPLAY`. Ce module est donc entièrement sauté
sans affichage réel (Xvfb dans un conteneur jetable, voir
`scripts/gtk-smoke-test.sh`, ou une vraie session graphique).
"""

from __future__ import annotations

import os

import pytest

gi = pytest.importorskip("gi")
gi.require_version("Gtk", "3.0")

from gi.repository import Gtk  # noqa: E402

if not os.environ.get("DISPLAY"):
    pytest.skip(
        "nécessite un vrai affichage pour construire de vrais widgets GTK",
        allow_module_level=True,
    )

from secondscreen_host.pure.security_notice import SECURITY_NOTICE  # noqa: E402
from secondscreen_host.ui.main_window import MainWindow  # noqa: E402


def _make_window() -> MainWindow:
    app = Gtk.Application(application_id="org.poongaloo.secondscreenhost.test")
    return MainWindow(application=app)


def _find_label_with_text(widget: Gtk.Widget, text: str) -> bool:
    if isinstance(widget, Gtk.Label) and widget.get_text() == text:
        return True
    if isinstance(widget, Gtk.Container):
        return any(_find_label_with_text(child, text) for child in widget.get_children())
    return False


def test_window_constructs_with_the_expected_title() -> None:
    window = _make_window()
    try:
        assert window.get_title() == "SecondScreenHost"
    finally:
        window.destroy()


def test_connection_info_is_hidden_before_the_server_starts() -> None:
    window = _make_window()
    try:
        assert window._connection_box.get_visible() is False
    finally:
        window.destroy()


def test_primary_button_says_configurer_when_nothing_blocks_it() -> None:
    window = _make_window()
    try:
        if window._blocked_message is None:
            assert window._primary_button.get_label() == "Configurer"
            assert window._primary_button.get_sensitive() is True
    finally:
        window.destroy()


def test_security_notice_is_displayed_in_the_window() -> None:
    window = _make_window()
    try:
        assert _find_label_with_text(window, SECURITY_NOTICE)
    finally:
        window.destroy()


def test_destroy_does_not_raise_when_nothing_was_started() -> None:
    window = _make_window()
    window.destroy()  # ne doit pas lever


def test_clicking_configure_for_real_surfaces_a_clear_error_without_crashing() -> None:
    # Vérité de terrain : un vrai clic (Gtk.Button.clicked() déclenche
    # réellement le signal, pas une simulation) déclenche la vraie
    # détection xrandr puis, faute de sortie VIRTUAL* sur ce vrai serveur X
    # (Xvfb n'en expose jamais), le repli écran isolé — qui échoue
    # proprement ici faute de pkexec (voir la docstring du module
    # system.dummy_xorg pour pourquoi ce n'est volontairement pas testé
    # avec un vrai pkexec, y compris son incompatibilité connue avec
    # Docker). Le point vérifié : ça ne plante pas, l'erreur réelle est
    # affichée.
    if os.geteuid() != 0:
        pytest.skip("le repli écran isolé a besoin d'un environnement root pour ce test")

    window = _make_window()
    try:
        if window._blocked_message is not None:
            pytest.skip(f"outils/session bloqués : {window._blocked_message}")

        window._primary_button.clicked()

        assert window._last_error is not None
        assert "pkexec" in window._last_error or "Xorg" in window._last_error
        assert window._error_label.get_visible() is True
    finally:
        window.destroy()
