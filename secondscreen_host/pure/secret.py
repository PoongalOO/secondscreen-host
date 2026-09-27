"""Détient un mot de passe en mémoire le temps que le serveur VNC tourne,
et l'efface dès qu'il s'arrête (HOST-042).

Limite documentée plutôt qu'ignorée (CAHIER_DES_CHARGES.md, « Sécurité ») :
Python ne garantit pas qu'une `str` soit effaçable de la mémoire du
processus — les chaînes sont immuables, et l'interpréteur peut en garder
des copies internes (interning, tampons temporaires...) hors du contrôle
de ce module. C'est différent du `CharArray` utilisé côté Android
(SecondScreen, SECURITY.md), réellement mutable.

Ce module fait ce qui reste possible malgré cette limite : le mot de passe
transite par un `bytearray` (mutable, donc réellement récrivable en place),
mis à zéro dès `clear()`. Cela réduit la fenêtre d'exposition sans
l'annuler complètement — le texte tel que saisi dans le champ GTK (HOST-070)
avant d'être enveloppé ici, ou une éventuelle copie faite par `.encode()`,
échappent au contrôle de cette seule classe.
"""

from __future__ import annotations


class SecretAlreadyClearedError(RuntimeError):
    """Le mot de passe a déjà été effacé : le relire serait un bogue (par
    exemple l'utiliser après l'arrêt du serveur qui aurait dû l'effacer)."""


class Secret:
    """Mot de passe détenu en mémoire, effaçable une seule fois (`clear()`
    est cependant idempotent : l'appeler plusieurs fois ne lève pas)."""

    def __init__(self, value: str) -> None:
        self._buffer: bytearray | None = bytearray(value.encode("utf-8"))

    def reveal(self) -> str:
        if self._buffer is None:
            raise SecretAlreadyClearedError("Ce mot de passe a déjà été effacé.")
        return self._buffer.decode("utf-8")

    def clear(self) -> None:
        if self._buffer is not None:
            for index in range(len(self._buffer)):
                self._buffer[index] = 0
            self._buffer = None

    @property
    def is_cleared(self) -> bool:
        return self._buffer is None

    def __del__(self) -> None:
        # Filet de sécurité si `clear()` n'a pas été appelé explicitement ;
        # ne remplace pas un appel explicite au bon moment (le moment du
        # ramasse-miettes n'est pas déterministe en CPython au-delà du
        # comptage de références, et ne l'est pas du tout garanti par le
        # langage).
        self.clear()
