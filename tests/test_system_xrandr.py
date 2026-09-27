"""Tests de `secondscreen_host.system.xrandr` (HOST-012, partie
exécutante).

Les cas d'échec (AGENTS.md : « tout appel à une commande système a un test
qui vérifie le comportement en cas d'échec ») sont testés en remplaçant
`subprocess.run` : on ne peut pas fiablement forcer `xrandr` lui-même à
échouer de chaque façon voulue (binaire absent, dépassement de délai) sans
modifier l'environnement réel de la machine qui exécute les tests.

Le succès, lui, est aussi vérifié avec le vrai binaire `xrandr` quand il
est disponible et qu'un affichage est accessible (voir
`test_query_xrandr_real_invocation_on_this_machine`) : un test entièrement
simulé ne prouverait pas que la commande réelle produit un texte que notre
analyseur sait lire.
"""

from __future__ import annotations

import shutil
import subprocess

import pytest

import secondscreen_host.system.xrandr as xrandr_module
from secondscreen_host.system.xrandr import XrandrQueryError, query_xrandr


def test_query_xrandr_raises_a_clear_error_when_the_binary_is_missing(monkeypatch) -> None:
    def fake_run(*args, **kwargs):
        raise FileNotFoundError("xrandr")

    monkeypatch.setattr(xrandr_module.subprocess, "run", fake_run)

    with pytest.raises(XrandrQueryError, match="introuvable"):
        query_xrandr()


def test_query_xrandr_raises_a_clear_error_on_timeout(monkeypatch) -> None:
    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="xrandr --query", timeout=10)

    monkeypatch.setattr(xrandr_module.subprocess, "run", fake_run)

    with pytest.raises(XrandrQueryError, match="répondu à temps"):
        query_xrandr()


def test_query_xrandr_raises_a_clear_error_on_non_zero_exit_code(monkeypatch) -> None:
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=["xrandr", "--query"],
            returncode=1,
            stdout="",
            stderr="Can't open display",
        )

    monkeypatch.setattr(xrandr_module.subprocess, "run", fake_run)

    with pytest.raises(XrandrQueryError, match="Can't open display"):
        query_xrandr()


def test_query_xrandr_parses_the_real_output_shape_when_run_succeeds(monkeypatch) -> None:
    fake_stdout = (
        "Screen 0: minimum 320 x 200, current 1920 x 1080, maximum 8192 x 8192\n"
        "eDP-1 connected primary 1920x1080+0+0 (normal left inverted right x axis y axis)\n"
    )

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=["xrandr", "--query"], returncode=0, stdout=fake_stdout, stderr=""
        )

    monkeypatch.setattr(xrandr_module.subprocess, "run", fake_run)

    result = query_xrandr()

    assert result.primary is not None
    assert result.primary.name == "eDP-1"


@pytest.mark.skipif(shutil.which("xrandr") is None, reason="xrandr non installé")
def test_query_xrandr_real_invocation_on_this_machine() -> None:
    # Vérité de terrain, sans simulation : si un affichage est accessible,
    # la vraie commande doit produire un résultat exploitable.
    import os

    if not os.environ.get("DISPLAY"):
        pytest.skip("aucun $DISPLAY accessible dans cet environnement")

    result = query_xrandr()

    assert len(result.outputs) > 0
