"""HOST-090, partie à l'exécution : le mot de passe VNC ne doit apparaître
nulle part ailleurs que là où c'est prévu (le fichier de mot de passe
temporaire, lu puis supprimé par x11vnc lui-même).

Méthode : un canari — une valeur de mot de passe distinctive, jamais
utilisée ailleurs dans le code ni les tests — transite par le vrai
programme (vrai `x11vnc`, vrai `Xvfb`), puis on cherche ce canari partout
où il pourrait fuiter : la ligne de commande réelle du processus (celle que
`ps(1)` montrerait à n'importe quel utilisateur local du système, lue ici
via `/proc/<pid>/cmdline`), la sortie capturée de x11vnc, les messages
d'erreur, le fichier de réglages écrit sur disque. Même principe que
`hygiene/SecretCanaryTest` du projet SecondScreen (dépôt virtualScreen).
"""

from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

import pytest

from secondscreen_host.pure.secret import Secret
from secondscreen_host.pure.settings import Settings
from secondscreen_host.pure.x11vnc_command import X11VncTarget
from secondscreen_host.system.settings import save_settings
from secondscreen_host.system.x11vnc import X11VncStartError, start_x11vnc

CANARY_PASSWORD = "CANARI-JAMAIS-UTILISE-AILLEURS-4f8a2b91"


def _read_cmdline(pid: int) -> str:
    raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    return raw.replace(b"\x00", b" ").decode(errors="replace")


@pytest.mark.skipif(
    shutil.which("x11vnc") is None or shutil.which("Xvfb") is None,
    reason="x11vnc et/ou Xvfb non installés",
)
def test_canary_password_never_appears_in_the_real_process_or_its_output() -> None:
    xvfb = subprocess.Popen(["Xvfb", ":232", "-screen", "0", "1280x800x24", "-nolisten", "tcp"])
    try:
        for _ in range(50):
            if Path("/tmp/.X232-lock").exists():
                break
            time.sleep(0.1)
        else:
            pytest.fail("Xvfb n'a pas démarré à temps")

        vnc = start_x11vnc(
            target=X11VncTarget(display=":232", clip=None), password=Secret(CANARY_PASSWORD)
        )
        try:
            cmdline = _read_cmdline(vnc.process.pid)
            assert CANARY_PASSWORD not in cmdline, (
                "le canari est visible dans la ligne de commande réelle du "
                f"processus (ps(1) le montrerait à tout utilisateur local) : {cmdline!r}"
            )

            time.sleep(0.3)  # laisse le fil d'arrière-plan drainer un peu plus de sortie
            log_text = " | ".join(vnc.recent_log_lines())
            assert CANARY_PASSWORD not in log_text, (
                f"le canari apparaît dans la sortie capturée de x11vnc : {log_text!r}"
            )
        finally:
            vnc.stop()
    finally:
        xvfb.terminate()
        xvfb.wait(timeout=5)


@pytest.mark.skipif(shutil.which("x11vnc") is None, reason="x11vnc non installé")
def test_canary_password_never_appears_in_a_start_failure_message() -> None:
    # Échec réel (aucun serveur X sur cet affichage) : le message d'erreur
    # ne doit pas non plus contenir le mot de passe.
    target = X11VncTarget(display=":9999", clip=None)
    with pytest.raises(X11VncStartError) as excinfo:
        start_x11vnc(target=target, password=Secret(CANARY_PASSWORD))

    assert CANARY_PASSWORD not in str(excinfo.value)


def test_canary_password_never_appears_in_the_saved_settings_file(tmp_path) -> None:
    # Settings n'a structurellement pas de champ prévu pour un mot de passe
    # (voir HOST-060, et test_log_hygiene.py pour la revue statique) : ce
    # test le confirme avec une vraie valeur de canari plutôt que de se
    # fier seulement à la structure.
    path = tmp_path / "config.json"
    save_settings(Settings(virtual_output="VIRTUAL1", port=5900), path)

    raw = path.read_text(encoding="utf-8")
    assert CANARY_PASSWORD not in raw
