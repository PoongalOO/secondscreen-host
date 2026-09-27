"""Exécute la configuration de l'écran virtuel étendu (HOST-021) et relit
la position réellement assignée.

Chaque commande construite par `secondscreen_host.pure.xrandr_commands`
est exécutée dans l'ordre. Un échec à n'importe quelle étape est rapporté
avec le message d'erreur réel de la commande, sans continuer aveuglément
aux étapes suivantes (AGENTS.md, règles 1 et 5). Le système peut rester
partiellement configuré après un échec (une commande a réussi, la
suivante non) : `ExtendedScreenConfigurationError.step` dit laquelle a
échoué, pour que le message affiché à l'utilisateur soit honnête sur ce
qui a déjà été fait plutôt que de le cacher (CAHIER_DES_CHARGES.md,
« Fiabilité »).
"""

from __future__ import annotations

import subprocess

from secondscreen_host.pure.xrandr import XrandrOutput
from secondscreen_host.pure.xrandr_commands import ExtendedScreenCommands
from secondscreen_host.system.xrandr import XrandrQueryError, query_xrandr


class ExtendedScreenConfigurationError(RuntimeError):
    def __init__(self, step: str, message: str) -> None:
        self.step = step
        self.message = message
        super().__init__(f"Échec à l'étape « {step} » : {message}")


def _run_step(step: str, command: tuple[str, ...]) -> None:
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)
    except FileNotFoundError as exc:
        raise ExtendedScreenConfigurationError(
            step, "la commande « xrandr » est introuvable."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise ExtendedScreenConfigurationError(
            step, "la commande n'a pas répondu à temps."
        ) from exc

    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        detail = stderr if stderr else f"code de retour {completed.returncode}"
        raise ExtendedScreenConfigurationError(step, detail)


def configure_extended_screen(
    commands: ExtendedScreenCommands, *, virtual_output: str
) -> XrandrOutput:
    """Exécute les trois commandes dans l'ordre, puis relit la position
    réellement assignée à `virtual_output` : jamais supposée ni recalculée
    à l'avance (CAHIER_DES_CHARGES.md, F02, point 4).

    Retourne la sortie (`XrandrOutput`) telle que vue par `xrandr --query`
    juste après configuration, avec sa géométrie réelle.
    """
    _run_step("création du mode (--newmode)", commands.newmode)
    _run_step("association à la sortie (--addmode)", commands.addmode)
    _run_step("activation (--output --right-of)", commands.activate)

    try:
        result = query_xrandr()
    except XrandrQueryError as exc:
        raise ExtendedScreenConfigurationError(
            "relecture de la position (xrandr --query)", str(exc)
        ) from exc

    for output in result.outputs:
        if output.name == virtual_output and output.connected and output.geometry is not None:
            return output

    raise ExtendedScreenConfigurationError(
        "relecture de la position (xrandr --query)",
        f"la sortie « {virtual_output} » n'apparaît pas connectée avec une géométrie "
        "après configuration : les commandes ont réussi mais leur effet n'est pas visible.",
    )
