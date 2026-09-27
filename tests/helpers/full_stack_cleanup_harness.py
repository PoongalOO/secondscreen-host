"""Utilisé par test_system_cleanup.py, jamais lancé directement.

Configure un vrai écran isolé (F03, `configure_screen` avec
`elevation_command=[]` puisque déjà root — voir `system/dummy_xorg.py` pour
pourquoi) et un vrai serveur `x11vnc` dessus, installe le nettoyage
(HOST-080), affiche `XORG_PID=<pid> VNC_PID=<pid>` sur stdout une fois
prêt, puis attend indéfiniment un signal. `$DISPLAY` doit pointer vers un
vrai serveur X (Xvfb) sans sortie `VIRTUAL*`, pour que la détection prenne
bien ce chemin.
"""

from __future__ import annotations

import time

from secondscreen_host.pure.secret import Secret
from secondscreen_host.pure.x11vnc_command import X11VncTarget
from secondscreen_host.system.cleanup import install_cleanup
from secondscreen_host.system.orchestration import configure_screen, teardown_screen
from secondscreen_host.system.x11vnc import start_x11vnc

configured = configure_screen(elevation_command=[])
assert configured.dummy_process is not None  # attendu : Xvfb n'expose jamais de sortie VIRTUAL*

vnc = start_x11vnc(
    target=X11VncTarget(display=configured.display, clip=configured.clip),
    password=Secret("hunter2"),
)

install_cleanup(lambda: teardown_screen(configured, vnc))

print(f"XORG_PID={configured.dummy_process.process.pid} VNC_PID={vnc.process.pid}", flush=True)

while True:
    time.sleep(0.1)
