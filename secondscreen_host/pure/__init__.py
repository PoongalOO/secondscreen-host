"""Logique pure de SecondScreenHost.

Tout ce qui vit dans ce sous-paquet doit rester testable sans lancer X11,
GTK, ni un vrai `x11vnc` : analyse de la sortie de commandes système
(`xrandr --query`...), construction de commandes, calculs de rectangles
`--clip`, génération de fichiers de configuration. Voir AGENTS.md, règle 3.

Rien n'y est implémenté pour l'instant (squelette, HOST-001) : les modules
arriveront avec les issues qui les concernent (HOST-012, HOST-020, HOST-022,
HOST-030, HOST-040...).
"""
