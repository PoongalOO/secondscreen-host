"""Fenêtre principale (HOST-070, HOST-071, HOST-072).

Relie l'interface GTK à la logique déjà construite (E1-E6) : ce module ne
contient pas de logique de détection ou de construction de commande — voir
AGENTS.md, règle 3 — seulement l'affichage d'un état et la réaction aux
clics, en déléguant tout le travail réel aux modules `pure`/`system`.

Portée assumée pour cette V1 (à ne pas confondre avec un oubli) :
- les actions (« Configurer », « Démarrer le serveur », « Arrêter »)
  s'exécutent de façon synchrone : l'interface se fige brièvement pendant
  l'opération (typiquement moins de 2 secondes, mesuré pendant les tests).
  Un traitement asynchrone est un vrai gain de confort, pas un prérequis
  du cahier des charges pour la V1.

Nettoyage (HOST-080) : la fermeture normale (signal GTK « destroy ») et les
signaux `SIGTERM`/`SIGINT` ainsi qu'un filet `atexit` (voir
`secondscreen_host.system.cleanup`) appellent tous le même nettoyage
idempotent — peu importe l'ordre ou le nombre de fois où il est déclenché.

Toute exception inattendue pendant l'action du bouton principal est
rattrapée et affichée plutôt que de laisser planter l'application
(HOST-081) : voir `_on_primary_button_clicked`.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gdk, Gtk  # noqa: E402  (après gi.require_version)

from secondscreen_host.pure.app_state import AppState, compute_status  # noqa: E402
from secondscreen_host.pure.secret import Secret  # noqa: E402
from secondscreen_host.pure.security_notice import SECURITY_NOTICE  # noqa: E402
from secondscreen_host.pure.settings import Settings  # noqa: E402
from secondscreen_host.pure.technical_details import format_technical_details  # noqa: E402
from secondscreen_host.pure.tools import format_missing_tools_message, missing_tools  # noqa: E402
from secondscreen_host.pure.x11vnc_command import X11VncTarget  # noqa: E402
from secondscreen_host.system.cleanup import install_cleanup  # noqa: E402
from secondscreen_host.system.local_address import (  # noqa: E402
    LocalAddressDetectionError,
    detect_connection_addresses,
)
from secondscreen_host.system.orchestration import (  # noqa: E402
    ConfiguredScreen,
    ScreenConfigurationError,
    configure_screen,
    teardown_screen,
)
from secondscreen_host.system.session import get_session_info  # noqa: E402
from secondscreen_host.system.settings import load_settings, save_settings  # noqa: E402
from secondscreen_host.system.tools import (  # noqa: E402
    check_fallback_tools,
    check_required_tools,
)
from secondscreen_host.system.x11vnc import (  # noqa: E402
    X11VncProcess,
    X11VncStartError,
    start_x11vnc,
)
from secondscreen_host.system.xrandr import XrandrQueryError, query_xrandr  # noqa: E402

WINDOW_TITLE = "SecondScreenHost"
DEFAULT_WIDTH = 520
DEFAULT_HEIGHT = 420


class _PasswordDialog(Gtk.Dialog):
    """Demande le mot de passe VNC (HOST-042) : jamais pré-rempli, jamais
    enregistré — voir CAHIER_DES_CHARGES.md, F04/F06."""

    def __init__(self, parent: Gtk.Window) -> None:
        super().__init__(title="Mot de passe VNC", transient_for=parent, modal=True)
        self.add_button("Annuler", Gtk.ResponseType.CANCEL)
        self.add_button("Démarrer", Gtk.ResponseType.OK)
        self.set_default_response(Gtk.ResponseType.OK)

        content = self.get_content_area()
        content.set_spacing(8)
        content.set_border_width(12)

        explanation = Gtk.Label(
            label="Redemandé à chaque démarrage : jamais enregistré sur le disque."
        )
        explanation.set_line_wrap(True)
        explanation.set_xalign(0.0)
        content.add(explanation)

        self._entry = Gtk.Entry()
        self._entry.set_visibility(False)
        self._entry.set_activates_default(True)
        content.add(self._entry)

        self.show_all()

    def get_password(self) -> str:
        return self._entry.get_text()


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, application: Gtk.Application) -> None:
        super().__init__(application=application, title=WINDOW_TITLE)
        self.set_default_size(DEFAULT_WIDTH, DEFAULT_HEIGHT)

        self._settings: Settings = load_settings()
        self._tool_results: list = []
        self._session_info = None
        self._xrandr_result = None
        self._configured_screen: ConfiguredScreen | None = None
        self._vnc: X11VncProcess | None = None
        self._last_error: str | None = None
        self._blocked_message: str | None = None

        self._build_widgets()
        self.connect("destroy", self._on_destroy)
        install_cleanup(self._emergency_cleanup)

        self._run_initial_checks()
        self._refresh()

    # ------------------------------------------------------------------
    # Construction de l'interface

    def _build_widgets(self) -> None:
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        root.set_border_width(12)
        self.add(root)

        security_label = Gtk.Label(label=SECURITY_NOTICE)
        security_label.set_line_wrap(True)
        security_label.set_xalign(0.0)
        root.pack_start(security_label, False, False, 0)

        self._error_label = Gtk.Label(label="")
        self._error_label.set_line_wrap(True)
        self._error_label.set_xalign(0.0)
        self._error_label.set_no_show_all(True)
        root.pack_start(self._error_label, False, False, 0)

        self._status_label = Gtk.Label(label="")
        self._status_label.set_xalign(0.0)
        root.pack_start(self._status_label, False, False, 0)

        self._primary_button = Gtk.Button(label="Configurer")
        self._primary_button.connect("clicked", self._on_primary_button_clicked)
        root.pack_start(self._primary_button, False, False, 0)

        self._connection_box = self._build_connection_box()
        self._connection_box.set_no_show_all(True)
        root.pack_start(self._connection_box, False, False, 0)

        expander = Gtk.Expander(label="Détails techniques")
        self._details_label = Gtk.Label(label="")
        self._details_label.set_xalign(0.0)
        self._details_label.set_line_wrap(True)
        self._details_label.set_selectable(True)
        expander.add(self._details_label)
        root.pack_start(expander, True, True, 0)

        self.show_all()
        self._connection_box.hide()
        self._error_label.hide()

    def _build_connection_box(self) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        address_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._address_label = Gtk.Label(label="Adresse : —")
        self._address_label.set_xalign(0.0)
        address_copy = Gtk.Button(label="Copier")
        address_copy.connect("clicked", self._on_copy_address_clicked)
        address_row.pack_start(self._address_label, True, True, 0)
        address_row.pack_start(address_copy, False, False, 0)
        box.pack_start(address_row, False, False, 0)

        port_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._port_label = Gtk.Label(label="Port : —")
        self._port_label.set_xalign(0.0)
        port_copy = Gtk.Button(label="Copier")
        port_copy.connect("clicked", self._on_copy_port_clicked)
        port_row.pack_start(self._port_label, True, True, 0)
        port_row.pack_start(port_copy, False, False, 0)
        box.pack_start(port_row, False, False, 0)

        password_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._password_entry = Gtk.Entry()
        self._password_entry.set_editable(False)
        self._password_entry.set_visibility(False)
        self._password_reveal = Gtk.ToggleButton(label="Afficher")
        self._password_reveal.connect("toggled", self._on_password_reveal_toggled)
        password_row.pack_start(self._password_entry, True, True, 0)
        password_row.pack_start(self._password_reveal, False, False, 0)
        box.pack_start(password_row, False, False, 0)

        return box

    # ------------------------------------------------------------------
    # Vérifications initiales (F01)

    def _run_initial_checks(self) -> None:
        self._tool_results = check_required_tools() + check_fallback_tools()
        self._session_info = get_session_info()

        missing = missing_tools(self._tool_results)
        if missing:
            self._blocked_message = format_missing_tools_message(missing)
            return

        from secondscreen_host.pure.session import SessionType, explain_session_type

        if self._session_info.session_type is not SessionType.X11:
            self._blocked_message = explain_session_type(self._session_info)
            return

        self._blocked_message = None

    # ------------------------------------------------------------------
    # État affiché

    def _refresh(self) -> None:
        status = compute_status(
            screen_configured=self._configured_screen is not None,
            server_running=self._vnc is not None and self._vnc.is_running(),
        )
        self._status_label.set_text(status.headline)
        self._primary_button.set_label(status.button_label)
        self._primary_button.set_sensitive(status.button_enabled and self._blocked_message is None)

        if self._blocked_message:
            self._error_label.set_text(self._blocked_message)
            self._error_label.show()
        elif self._last_error:
            self._error_label.set_text(f"Erreur : {self._last_error}")
            self._error_label.show()
        else:
            self._error_label.hide()

        if status.state is AppState.RUNNING:
            self._connection_box.show()
        else:
            self._connection_box.hide()

        self._details_label.set_text(
            format_technical_details(
                tool_results=self._tool_results,
                session_info=self._session_info,
                xrandr_result=self._xrandr_result,
                last_error=self._last_error,
            )
        )

    # ------------------------------------------------------------------
    # Action principale

    def _on_primary_button_clicked(self, _button: Gtk.Button) -> None:
        status = compute_status(
            screen_configured=self._configured_screen is not None,
            server_running=self._vnc is not None and self._vnc.is_running(),
        )
        try:
            if status.state is AppState.NOT_CONFIGURED:
                self._do_configure()
            elif status.state is AppState.READY:
                self._do_start_server()
            else:
                self._do_stop_server()
        except Exception as exc:
            # Filet de sécurité (HOST-081) : chaque étape interne attrape
            # déjà les échecs qu'elle anticipe (voir leurs propres
            # try/except) et les transforme en message clair. Celui-ci
            # n'est là que pour ce qui n'a pas été anticipé — un bogue, une
            # exception d'un module tiers — pour ne jamais laisser une
            # trace Python remonter jusqu'au terminal (ou nulle part du
            # tout si l'application n'a pas été lancée depuis un terminal)
            # à la place d'un message compréhensible dans l'interface.
            self._last_error = f"Erreur inattendue : {exc}"
        self._refresh()

    def _do_configure(self) -> None:
        try:
            self._xrandr_result = query_xrandr()
        except XrandrQueryError as exc:
            self._last_error = str(exc)
            return

        try:
            configured = configure_screen(remembered_output=self._settings.virtual_output)
        except ScreenConfigurationError as exc:
            self._last_error = str(exc)
            return

        self._configured_screen = configured
        self._last_error = None
        self._settings = Settings(
            virtual_output=configured.virtual_output_name, port=self._settings.port
        )
        save_settings(self._settings)

    def _do_start_server(self) -> None:
        assert self._configured_screen is not None
        dialog = _PasswordDialog(self)
        response = dialog.run()
        password_text = dialog.get_password()
        dialog.destroy()

        if response != Gtk.ResponseType.OK:
            return
        if not password_text:
            self._last_error = "Un mot de passe est requis pour démarrer le serveur."
            return

        secret = Secret(password_text)
        target = X11VncTarget(
            display=self._configured_screen.display, clip=self._configured_screen.clip
        )
        try:
            self._vnc = start_x11vnc(target=target, password=secret, port=self._settings.port)
        except X11VncStartError as exc:
            self._last_error = str(exc)
            secret.clear()
            return

        self._last_error = None
        self._update_connection_info()

    def _do_stop_server(self) -> None:
        teardown_screen(self._configured_screen, self._vnc)
        self._vnc = None
        screen = self._configured_screen
        had_dummy_screen = screen is not None and screen.dummy_process is not None
        if had_dummy_screen:
            # Écran isolé (F03) : le second serveur X vient d'être arrêté
            # aussi, il n'y a donc plus rien de configuré à réutiliser.
            self._configured_screen = None
        self._last_error = None

    # ------------------------------------------------------------------
    # Informations de connexion (F05)

    def _update_connection_info(self) -> None:
        assert self._vnc is not None
        try:
            addresses = detect_connection_addresses()
            address_text = addresses.primary or "aucune adresse LAN détectée"
        except LocalAddressDetectionError as exc:
            address_text = f"indisponible ({exc})"

        self._address_label.set_text(f"Adresse : {address_text}")
        self._port_label.set_text(f"Port : {self._vnc.port}")
        self._password_entry.set_text(self._vnc.secret.reveal())
        self._password_reveal.set_active(False)
        self._password_entry.set_visibility(False)

    def _on_password_reveal_toggled(self, button: Gtk.ToggleButton) -> None:
        self._password_entry.set_visibility(button.get_active())
        button.set_label("Masquer" if button.get_active() else "Afficher")

    def _on_copy_address_clicked(self, _button: Gtk.Button) -> None:
        text = self._address_label.get_text().removeprefix("Adresse : ")
        Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).set_text(text, -1)

    def _on_copy_port_clicked(self, _button: Gtk.Button) -> None:
        text = self._port_label.get_text().removeprefix("Port : ")
        Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).set_text(text, -1)

    # ------------------------------------------------------------------
    # Fermeture

    def _on_destroy(self, *_args) -> None:
        self._emergency_cleanup()

    def _emergency_cleanup(self) -> None:
        """Appelée à la fermeture normale (`_on_destroy`), sur `SIGTERM`/
        `SIGINT`, ou via le filet `atexit` (voir `install_cleanup` dans
        `__init__`, et `secondscreen_host.system.cleanup` pour pourquoi les
        trois sont nécessaires). Idempotente : `teardown_screen` l'est déjà
        (HOST-080)."""
        teardown_screen(self._configured_screen, self._vnc)
