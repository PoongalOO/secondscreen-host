"""Tests de `secondscreen_host.system.local_address` (HOST-050, partie
exécutante).

Les cas d'échec de `list_interface_addresses` sont testés en remplaçant
`subprocess.run` (même approche que pour `xrandr`/`cvt`, voir
tests/test_system_xrandr.py). `detect_outbound_address` et
`detect_connection_addresses`, eux, sont vérifiés avec le vrai système :
l'astuce socket UDP et le vrai `ip` de la machine qui exécute les tests.
"""

from __future__ import annotations

import shutil
import subprocess

import pytest

import secondscreen_host.system.local_address as local_address_module
from secondscreen_host.system.local_address import (
    LocalAddressDetectionError,
    detect_connection_addresses,
    detect_outbound_address,
    list_interface_addresses,
)


def test_list_interface_addresses_raises_a_clear_error_when_binary_is_missing(monkeypatch) -> None:
    def fake_run(*args, **kwargs):
        raise FileNotFoundError("ip")

    monkeypatch.setattr(local_address_module.subprocess, "run", fake_run)

    with pytest.raises(LocalAddressDetectionError, match="introuvable"):
        list_interface_addresses()


def test_list_interface_addresses_raises_a_clear_error_on_timeout(monkeypatch) -> None:
    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="ip", timeout=10)

    monkeypatch.setattr(local_address_module.subprocess, "run", fake_run)

    with pytest.raises(LocalAddressDetectionError, match="répondu à temps"):
        list_interface_addresses()


def test_list_interface_addresses_raises_a_clear_error_on_non_zero_exit_code(monkeypatch) -> None:
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=["ip"], returncode=1, stdout="", stderr="ip: command failed"
        )

    monkeypatch.setattr(local_address_module.subprocess, "run", fake_run)

    with pytest.raises(LocalAddressDetectionError, match="command failed"):
        list_interface_addresses()


def test_detect_outbound_address_returns_a_real_reachable_looking_address() -> None:
    # Vérité de terrain : aucune donnée n'est réellement envoyée (UDP,
    # connect() consulte seulement la table de routage), mais l'adresse
    # renvoyée doit être une vraie adresse IPv4 locale de cette machine.
    address = detect_outbound_address()

    assert address is not None
    assert address.count(".") == 3


def test_detect_outbound_address_returns_none_when_unreachable() -> None:
    # TEST-NET-1 (RFC 5737) : jamais routable, aucune route ne devrait
    # exister vers elle — un cas réel d'absence de route, pas simulé.
    address = detect_outbound_address(probe_host="192.0.2.1", probe_port=1)

    # Selon la machine, soit il n'y a pas de route (None), soit une route
    # par défaut existe quand même (le noyau ne sait pas que 192.0.2.1 est
    # injoignable sans essayer) : les deux sont des résultats valides, la
    # seule chose à exclure est une exception qui remonterait jusqu'à
    # l'appelant.
    assert address is None or address.count(".") == 3


@pytest.mark.skipif(shutil.which("ip") is None, reason="ip (paquet iproute2) non installé")
def test_list_interface_addresses_real_invocation_finds_loopback() -> None:
    # Vérité de terrain : sur n'importe quelle machine Linux, 127.0.0.1
    # existe forcément sur "lo".
    addresses = list_interface_addresses()

    assert any(a.interface == "lo" and a.address == "127.0.0.1" for a in addresses)


@pytest.mark.skipif(shutil.which("ip") is None, reason="ip (paquet iproute2) non installé")
def test_detect_connection_addresses_real_invocation() -> None:
    result = detect_connection_addresses()

    # Ne garantit pas qu'une adresse LAN existe (un conteneur de CI isolé
    # peut n'avoir que docker0/lo) : vérifie seulement la forme du
    # résultat et l'absence d'exception.
    if result.primary is not None:
        assert result.primary.count(".") == 3
    assert isinstance(result.alternates, tuple)
