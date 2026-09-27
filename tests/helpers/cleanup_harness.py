"""Utilisé par test_system_cleanup.py, jamais lancé directement.

Un signal ne peut pas se tester en modifiant les gestionnaires du processus
de test lui-même (ça perturberait pytest) : ce script est un vrai
sous-processus autonome qui démarre un « processus externe » factice (une
vraie commande `sleep`, suffisant pour tester le mécanisme de nettoyage
lui-même, générique à n'importe quel sous-processus — pas la peine d'un
vrai x11vnc/Xorg ici, déjà testés ailleurs), installe le nettoyage
(HOST-080), affiche le PID de ce processus factice sur stdout, puis :
- `sys.argv[1] == "exit"` : se termine normalement (déclenche le filet
  `atexit`) ;
- sinon : attend indéfiniment un signal (`SIGTERM`/`SIGINT`).
"""

from __future__ import annotations

import subprocess
import sys
import time

from secondscreen_host.system.cleanup import install_cleanup

child = subprocess.Popen(["sleep", "60"])
install_cleanup(lambda: (child.terminate(), child.wait(timeout=5)))

print(child.pid, flush=True)

if len(sys.argv) > 1 and sys.argv[1] == "exit":
    sys.exit(0)

while True:
    time.sleep(0.1)
