"""Code qui exécute réellement des commandes système ou lit l'environnement
du processus (variables d'environnement, appels à `xrandr`/`x11vnc`/`cvt`,
gestion de processus...).

Chaque module ici délègue l'interprétation à un module correspondant de
`secondscreen_host.pure`, qui reste testable sans lancer X11 ni ces
commandes. Voir AGENTS.md, règle 3.
"""
