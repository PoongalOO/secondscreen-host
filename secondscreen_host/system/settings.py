"""Charge et sauvegarde les réglages utilisateur (HOST-060, partie
exécutante), dans le répertoire de configuration XDG :
`$XDG_CONFIG_HOME/secondscreen-host/config.json`, ou `~/.config/...` par
défaut si `XDG_CONFIG_HOME` n'est pas positionnée (spécification XDG Base
Directory).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from secondscreen_host.pure.settings import Settings, parse_settings

APP_DIR_NAME = "secondscreen-host"
CONFIG_FILE_NAME = "config.json"


def config_file_path() -> Path:
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg_config_home) if xdg_config_home else Path.home() / ".config"
    return base / APP_DIR_NAME / CONFIG_FILE_NAME


def load_settings(path: Path | None = None) -> Settings:
    """Ne lève jamais : un fichier absent, illisible, ou dont le contenu
    n'est pas du JSON valide retombe sur les réglages par défaut plutôt que
    d'empêcher l'application de démarrer. Cohérent avec AGENTS.md, règle 1,
    appliqué ici à un fichier qu'on a soi-même écrit mais qui reste une
    donnée externe du point de vue du code qui le relit : édition manuelle,
    panne pendant une écriture précédente, ancienne version du format..."""
    target = path if path is not None else config_file_path()
    try:
        raw = target.read_text(encoding="utf-8")
    except OSError:
        return Settings()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return Settings()

    return parse_settings(data)


def save_settings(settings: Settings, path: Path | None = None) -> None:
    target = path if path is not None else config_file_path()
    target.parent.mkdir(parents=True, exist_ok=True)

    # Écriture atomique (fichier temporaire puis renommage) : un plantage
    # pendant l'écriture ne doit jamais laisser un fichier à moitié écrit
    # que `load_settings` lirait comme un JSON invalide au prochain
    # démarrage — `os.replace` est atomique sur un même système de fichiers.
    tmp_path = target.with_suffix(target.suffix + ".tmp")
    tmp_path.write_text(json.dumps(settings.to_dict(), indent=2) + "\n", encoding="utf-8")
    os.replace(tmp_path, target)
