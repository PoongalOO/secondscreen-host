"""Modélise l'état global de l'application (HOST-070, UX V1 du cahier des
charges).

Fonction pure : décide l'état affiché et le libellé du bouton principal à
partir de deux faits déjà connus (un écran virtuel est-il configuré ? le
serveur VNC tourne-t-il ?) — jamais d'appel GTK ni système ici.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AppState(Enum):
    NOT_CONFIGURED = "not_configured"
    """Aucun écran virtuel détecté ou configuré."""
    READY = "ready"
    """Écran virtuel prêt, serveur VNC arrêté."""
    RUNNING = "running"
    """Serveur VNC actif."""


@dataclass(frozen=True)
class AppStatus:
    state: AppState
    headline: str
    button_label: str
    button_enabled: bool


def compute_status(*, screen_configured: bool, server_running: bool) -> AppStatus:
    if server_running:
        return AppStatus(
            state=AppState.RUNNING,
            headline="Serveur actif",
            button_label="Arrêter",
            button_enabled=True,
        )
    if screen_configured:
        return AppStatus(
            state=AppState.READY,
            headline="Écran virtuel prêt, serveur arrêté",
            button_label="Démarrer le serveur",
            button_enabled=True,
        )
    return AppStatus(
        state=AppState.NOT_CONFIGURED,
        headline="Aucun écran virtuel détecté",
        button_label="Configurer",
        button_enabled=True,
    )
