"""Tests de `secondscreen_host.pure.local_address` (HOST-050).

`tests/fixtures/ip_addr_multi_interface_real.txt` est une capture
**réelle** de `ip -4 -o addr show` (voir le commentaire en tête de ce
fichier) : une vraie machine de développement, avec une interface Wi-Fi
normale, six ponts Docker et une interface VPN Tailscale — un bien
meilleur cas de test qu'un exemple inventé, puisqu'il expose exactement le
bruit que le filtrage doit éliminer.
"""

from pathlib import Path

from secondscreen_host.pure.local_address import (
    NetworkInterfaceAddress,
    is_usable_lan_address,
    parse_ip_addr_output,
    pick_primary_address,
    usable_lan_addresses,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _real_capture() -> list[NetworkInterfaceAddress]:
    text = (FIXTURES / "ip_addr_multi_interface_real.txt").read_text(encoding="utf-8")
    return parse_ip_addr_output(text)


def test_parses_all_nine_interfaces_from_the_real_capture() -> None:
    parsed = _real_capture()

    assert len(parsed) == 9
    assert NetworkInterfaceAddress("wlan0", "192.168.1.199") in parsed
    assert NetworkInterfaceAddress("lo", "127.0.0.1") in parsed
    assert NetworkInterfaceAddress("tailscale0", "100.97.175.52") in parsed


def test_usable_lan_addresses_keeps_only_wlan0_from_the_real_capture() -> None:
    parsed = _real_capture()

    usable = usable_lan_addresses(parsed)

    assert [c.interface for c in usable] == ["wlan0"]
    assert usable[0].address == "192.168.1.199"


def test_loopback_is_not_usable() -> None:
    assert is_usable_lan_address(NetworkInterfaceAddress("lo", "127.0.0.1")) is False


def test_docker_bridge_is_not_usable_even_with_a_private_looking_address() -> None:
    # 172.17.0.1 ressemble à une adresse privée normale : seul le nom de
    # l'interface permet de savoir qu'elle n'est pas joignable depuis le
    # réseau local du PC.
    assert is_usable_lan_address(NetworkInterfaceAddress("docker0", "172.17.0.1")) is False
    assert is_usable_lan_address(NetworkInterfaceAddress("br-edd4c4558a57", "172.22.0.1")) is False


def test_tailscale_vpn_address_is_not_usable() -> None:
    assert is_usable_lan_address(NetworkInterfaceAddress("tailscale0", "100.97.175.52")) is False


def test_link_local_address_is_not_usable() -> None:
    assert is_usable_lan_address(NetworkInterfaceAddress("eth0", "169.254.1.5")) is False


def test_ipv6_address_is_not_usable() -> None:
    assert is_usable_lan_address(NetworkInterfaceAddress("wlan0", "fe80::1")) is False


def test_ordinary_wifi_and_ethernet_addresses_are_usable() -> None:
    assert is_usable_lan_address(NetworkInterfaceAddress("wlan0", "192.168.1.199")) is True
    assert is_usable_lan_address(NetworkInterfaceAddress("eth0", "10.0.0.5")) is True


def test_pick_primary_prefers_the_outbound_address_when_it_is_usable() -> None:
    candidates = [
        NetworkInterfaceAddress("eth0", "192.168.1.10"),
        NetworkInterfaceAddress("wlan0", "192.168.1.199"),
    ]

    assert pick_primary_address("192.168.1.199", candidates) == "192.168.1.199"


def test_pick_primary_falls_back_to_first_usable_when_outbound_is_not_in_the_list() -> None:
    candidates = [NetworkInterfaceAddress("eth0", "192.168.1.10")]

    # Adresse de sortie sur une interface non présente dans la liste
    # (situation anormale mais pas supposée impossible) : repli sur la
    # première candidate utilisable plutôt que de planter.
    assert pick_primary_address("10.9.9.9", candidates) == "192.168.1.10"


def test_pick_primary_ignores_a_docker_bridge_outbound_guess() -> None:
    candidates = [
        NetworkInterfaceAddress("docker0", "172.17.0.1"),
        NetworkInterfaceAddress("wlan0", "192.168.1.199"),
    ]

    # Même si l'astuce de détection sortante désignait par erreur le pont
    # Docker, le filtrage par nom d'interface l'exclut du choix final.
    assert pick_primary_address("172.17.0.1", candidates) == "192.168.1.199"


def test_pick_primary_returns_none_when_nothing_is_usable() -> None:
    candidates = [NetworkInterfaceAddress("lo", "127.0.0.1")]

    assert pick_primary_address(None, candidates) is None


def test_unrecognized_lines_are_skipped_not_raised() -> None:
    text = "une ligne totalement inattendue\n2: eth0    inet 10.0.0.5/24 brd 10.0.0.255\n"

    parsed = parse_ip_addr_output(text)

    assert parsed == [NetworkInterfaceAddress("eth0", "10.0.0.5")]


def test_empty_input_produces_no_results() -> None:
    assert parse_ip_addr_output("") == []
