"""Interprète les lignes affichées par x11vnc (HOST-041).

Fonction pure : ne lit aucune sortie de processus elle-même (voir
`secondscreen_host.system.x11vnc`) ; décide seulement, ligne par ligne, si
elle signale que le serveur écoute effectivement.

Basé sur un comportement réellement observé (x11vnc 0.9.16, dans un
conteneur jetable avec un vrai Xvfb) : une ligne « PORT=<num> » apparaît
une fois que `x11vnc` a réussi à se mettre à l'écoute — jamais avant, et
pas du tout s'il échoue (par exemple port déjà utilisé, message
« Error: could not obtain listening port. » puis arrêt du processus sans
jamais afficher de ligne PORT=). Une fenêtre de temps fixe supposée
suffisante n'aurait pas permis de distinguer ces deux cas.
"""

from __future__ import annotations

_READY_PREFIX = "PORT="


def is_ready_line(line: str) -> bool:
    return line.strip().startswith(_READY_PREFIX)
