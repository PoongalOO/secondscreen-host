"""Avertissement de sécurité affiché dans l'interface (HOST-072).

Cohérent avec l'avertissement déjà présent dans l'application Android
SecondScreen (voir SECURITY.md du projet SecondScreen, dépôt
virtualScreen) : le protocole RFB/VNC classique n'est pas chiffré, son
usage doit rester sur un réseau local de confiance.
"""

SECURITY_NOTICE = (
    "⚠ VNC (protocole RFB) n'est pas chiffré : à réserver à un réseau local "
    "de confiance, jamais exposé directement sur Internet."
)
