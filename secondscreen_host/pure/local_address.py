"""Choisit quelle(s) adresse(s) IP locale(s) proposer à l'utilisateur
(HOST-050).

Fonctions pures : décident à partir de résultats déjà obtenus (l'adresse
que le système choisirait pour une connexion sortante, la liste des
interfaces énumérées via `ip -4 -o addr show`) — voir
`secondscreen_host.system.local_address` pour ces deux appels réels.
Aucun appel réseau ni système ici.
"""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass

# Motifs de noms d'interfaces manifestement pas le réseau local du PC :
# ponts Docker, VPN, interfaces internes de conteneurs... Vérifié utile sur
# une vraie machine de développement (voir tests/fixtures/
# ip_addr_multi_interface_real.txt) : sans ce filtre, plusieurs adresses de
# ponts Docker et une adresse Tailscale (VPN) auraient été proposées comme
# si elles étaient joignables depuis le réseau local, ce qui est faux. Pas
# une garantie absolue (aucune liste blanche universelle n'existe), juste
# un filtre du bruit le plus courant.
_VIRTUAL_INTERFACE_NAME_PREFIXES = (
    "lo",
    "docker",
    "br-",
    "veth",
    "virbr",
    "vmnet",
    "vboxnet",
    "tun",
    "tap",
    "wg",
    "tailscale",
    "zt",  # ZeroTier
)

_ADDR_LINE_RE = re.compile(r"^\d+:\s+(?P<iface>\S+)\s+inet\s+(?P<addr>[0-9.]+)/\d+")


@dataclass(frozen=True)
class NetworkInterfaceAddress:
    interface: str
    address: str


def parse_ip_addr_output(text: str) -> list[NetworkInterfaceAddress]:
    """Analyse la sortie de `ip -4 -o addr show`. Une ligne dans un format
    non reconnu est ignorée plutôt que de faire planter l'analyse (voir
    AGENTS.md, règle 2, déjà appliquée à l'analyseur `xrandr`, HOST-012)."""
    results: list[NetworkInterfaceAddress] = []
    for line in text.splitlines():
        match = _ADDR_LINE_RE.match(line)
        if match is None:
            continue
        results.append(
            NetworkInterfaceAddress(interface=match.group("iface"), address=match.group("addr"))
        )
    return results


def _looks_virtual(interface: str) -> bool:
    name = interface.lower()
    return any(name.startswith(prefix) for prefix in _VIRTUAL_INTERFACE_NAME_PREFIXES)


def is_usable_lan_address(candidate: NetworkInterfaceAddress) -> bool:
    """Exclut la boucle locale, les adresses lien-local (169.254.x.x),
    l'IPv6 (le client SecondScreen actuel se connecte en IPv4, voir
    GUIDE_UBUNTU.md/GUIDE_MX_LINUX.md), et les interfaces dont le nom
    indique un réseau virtuel."""
    try:
        parsed = ipaddress.ip_address(candidate.address)
    except ValueError:
        return False
    if parsed.version != 4:
        return False
    if parsed.is_loopback or parsed.is_link_local or parsed.is_unspecified or parsed.is_multicast:
        return False
    if _looks_virtual(candidate.interface):
        return False
    return True


def usable_lan_addresses(
    candidates: list[NetworkInterfaceAddress],
) -> list[NetworkInterfaceAddress]:
    """Filtre, dans l'ordre reçu (pas de tri qui laisserait croire à une
    préférence non justifiée) : plusieurs interfaces valides (Ethernet +
    Wi-Fi) peuvent coexister (CAHIER_DES_CHARGES.md) — à l'interface de les
    présenter toutes plutôt que d'en deviner une seule silencieusement
    (HOST-070). Voir `pick_primary_address` pour un choix par défaut."""
    return [c for c in candidates if is_usable_lan_address(c)]


def pick_primary_address(
    outbound_address: str | None, candidates: list[NetworkInterfaceAddress]
) -> str | None:
    """Choisit l'adresse à mettre en avant : celle que le système
    utiliserait pour une connexion sortante si elle correspond à l'une des
    sorties jugées utilisables ; sinon la première candidate utilisable ;
    sinon aucune (l'utilisateur devra choisir parmi les détails
    techniques, HOST-071)."""
    usable = usable_lan_addresses(candidates)
    usable_addresses = {c.address for c in usable}
    if outbound_address is not None and outbound_address in usable_addresses:
        return outbound_address
    if usable:
        return usable[0].address
    return None
