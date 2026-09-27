"""Démarre et arrête le second serveur X du repli « écran isolé »
(HOST-031, F03).

Démarrer un serveur X sur un nouvel affichage demande des privilèges élevés
sur les distributions ciblées (voir CAHIER_DES_CHARGES.md, « Plateforme
cible ») : ce module utilise `pkexec`, cohérent avec une application GTK
(fenêtre graphique de demande de mot de passe). `sudo` n'est volontairement
pas utilisé en repli : sans terminal ni `SUDO_ASKPASS` configuré, il reste
bloqué indéfiniment en attente d'un mot de passe qu'il ne peut pas
demander — un mauvais compromis pour une application graphique. Si
`pkexec` s'avère insuffisant en pratique sur les deux systèmes cibles
(HOST-101/HOST-102), ce sera une décision à documenter, pas une supposition
à ajouter ici sans la vérifier.

Le lancement de Xorg lui-même (une fois les privilèges obtenus), sa
détection de démarrage réussi/échoué et son arrêt propre sont vérifiés
avec un vrai Xorg + pilote `dummy` dans un conteneur jetable (déjà root,
donc sans élévation à observer côté conteneur — voir
tests/test_system_dummy_xorg.py, qui passe `elevation_command=[]` pour
cette raison). Ce que ce conteneur ne peut pas vérifier : le comportement
réel de la boîte de dialogue `pkexec` elle-même, qui suppose un agent
polkit et une session graphique — à confirmer sur le vrai matériel
(HOST-101/HOST-102).
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from secondscreen_host.pure.cvt import CvtMode
from secondscreen_host.pure.dummy_xorg import generate_dummy_xorg_config
from secondscreen_host.system.display_number import pick_free_display_number

READY_TIMEOUT_SECONDS = 5.0
POLL_INTERVAL_SECONDS = 0.1


class DummyScreenStartError(RuntimeError):
    """Le second serveur X n'a pas pu démarrer (privilège manquant, pilote
    `dummy` absent, fichier de configuration invalide...) : message
    compréhensible, jamais une trace brute (AGENTS.md, règle 5)."""


@dataclass
class DummyScreenProcess:
    """Le second serveur X en cours d'exécution. `stop()` est idempotent :
    appelable sans risque même si le processus est déjà arrêté (utile
    depuis le nettoyage systématique, HOST-080)."""

    display_number: int
    config_path: Path
    process: subprocess.Popen

    @property
    def display(self) -> str:
        return f":{self.display_number}"

    def stop(self) -> None:
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        self.config_path.unlink(missing_ok=True)


def _elevation_command() -> list[str]:
    if shutil.which("pkexec"):
        return ["pkexec"]
    return []


def _write_config_file(content: str) -> Path:
    handle = tempfile.NamedTemporaryFile(
        mode="w", suffix=".conf", prefix="secondscreen-host-dummy-", delete=False
    )
    try:
        handle.write(content)
    finally:
        handle.close()
    return Path(handle.name)


def _wait_until_ready_or_raise(process: subprocess.Popen, display_number: int) -> None:
    lock_path = Path(f"/tmp/.X{display_number}-lock")
    deadline = time.monotonic() + READY_TIMEOUT_SECONDS

    while time.monotonic() < deadline:
        if lock_path.exists():
            return
        if process.poll() is not None:
            stderr = process.stderr.read() if process.stderr else ""
            raise DummyScreenStartError(
                f"Xorg s'est arrêté immédiatement (code {process.returncode}) : "
                f"{stderr.strip()}"
            )
        time.sleep(POLL_INTERVAL_SECONDS)

    process.kill()
    raise DummyScreenStartError(
        f"Xorg n'a pas démarré dans le délai imparti (affichage :{display_number})."
    )


def start_dummy_screen(
    mode: CvtMode,
    *,
    width: int = 1280,
    height: int = 800,
    elevation_command: list[str] | None = None,
) -> DummyScreenProcess:
    """`elevation_command` : surtout un point d'entrée de test (les tests
    tournent déjà en root dans un conteneur jetable, donc sans élévation à
    ajouter — `elevation_command=[]` dit explicitement « aucune », ce n'est
    pas la même chose que « indisponible », voir plus bas) ; en usage
    normal, laissé à `None` pour la détection réelle (`pkexec`)."""
    if elevation_command is None:
        elevation_command = _elevation_command()
        if not elevation_command:
            raise DummyScreenStartError(
                "« pkexec » est introuvable : impossible de démarrer un second serveur "
                "X avec les privilèges nécessaires. Installez le paquet « policykit-1 »."
            )

    config_path = _write_config_file(generate_dummy_xorg_config(mode, width=width, height=height))
    display_number = pick_free_display_number()
    command = [
        *elevation_command,
        "Xorg",
        "-noreset",
        "-config",
        str(config_path),
        f":{display_number}",
    ]

    try:
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
    except FileNotFoundError as exc:
        config_path.unlink(missing_ok=True)
        raise DummyScreenStartError("La commande « Xorg » est introuvable.") from exc

    try:
        _wait_until_ready_or_raise(process, display_number)
    except DummyScreenStartError:
        config_path.unlink(missing_ok=True)
        raise

    return DummyScreenProcess(
        display_number=display_number, config_path=config_path, process=process
    )
