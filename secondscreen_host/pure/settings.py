"""Réglages persistés par l'utilisateur (HOST-060, F06).

Fonctions pures : structurent les réglages et décident comment les
interpréter (JSON déjà lu, candidats déjà détectés) — jamais d'accès
disque ni au système ici, voir `secondscreen_host.system.settings`.

Ne contient jamais le mot de passe VNC (CAHIER_DES_CHARGES.md, F06: « ne
mémorise jamais le mot de passe VNC ») : structurellement impossible de
l'y glisser par erreur, `Settings` n'a tout simplement pas de champ prévu
pour ça, et n'en aura pas sans une mise à jour explicite de ce document
(voir AGENTS.md, interdictions).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

DEFAULT_PORT = 5900


@dataclass(frozen=True)
class Settings:
    virtual_output: str | None = None
    """Nom de la sortie `VIRTUAL*` choisie la dernière fois (HOST-012) ;
    `None` si jamais configuré."""
    port: int = DEFAULT_PORT

    def to_dict(self) -> dict:
        return asdict(self)


def parse_settings(data: object) -> Settings:
    """Interprète un objet déjà décodé depuis JSON (voir
    `secondscreen_host.system.settings.load_settings`). Traite les données
    comme non fiables (fichier corrompu, édité à la main, ancienne version
    du format...) : jamais une exception, un réglage manquant ou du
    mauvais type retombe silencieusement sur sa valeur par défaut plutôt
    que de faire échouer le chargement de tous les autres réglages."""
    if not isinstance(data, dict):
        return Settings()

    virtual_output = data.get("virtual_output")
    if not isinstance(virtual_output, str) or not virtual_output:
        virtual_output = None

    port = data.get("port")
    # `bool` est une sous-classe d'`int` en Python : sans l'exclure
    # explicitement, un fichier contenant `"port": true` serait accepté et
    # deviendrait silencieusement le port 1.
    if isinstance(port, bool) or not isinstance(port, int) or not (1 <= port <= 65535):
        port = DEFAULT_PORT

    return Settings(virtual_output=virtual_output, port=port)


def resolve_remembered_output(
    settings: Settings, available_candidate_names: list[str]
) -> str | None:
    """La sortie mémorisée n'est réutilisée que si elle existe encore
    parmi les sorties `VIRTUAL*` actuellement détectées (HOST-012) : une
    configuration matérielle différente d'une session à l'autre (autre
    poste, docking station changée...) ne doit jamais faire supposer
    qu'un réglage obsolète est toujours valide (CAHIER_DES_CHARGES.md,
    F06)."""
    if settings.virtual_output is not None and settings.virtual_output in available_candidate_names:
        return settings.virtual_output
    return None
