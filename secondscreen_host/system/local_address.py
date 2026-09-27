"""Détecte réellement les adresses IP locales (HOST-050, partie exécutante).

Deux informations complémentaires :

- l'adresse que le système choisirait pour une connexion sortante (astuce
  socket UDP classique : `connect()` sur un socket UDP ne fait que
  consulter la table de routage du noyau, aucun paquet n'est réellement
  émis, aucun privilège requis) — un bon choix par défaut, vérifié sur une
  machine réelle à plusieurs interfaces (Wi-Fi + plusieurs ponts Docker +
  un VPN Tailscale) : elle désigne correctement l'interface Wi-Fi
  réellement joignable depuis le réseau local, jamais un pont Docker ni le
  VPN, sans qu'on ait eu besoin de les nommer explicitement ;
- la liste de toutes les adresses IPv4 par interface (`ip -4 -o addr
  show`), pour les cas où plusieurs interfaces LAN valides coexistent
  (CAHIER_DES_CHARGES.md) — voir `secondscreen_host.pure.local_address`
  pour le filtrage du bruit (ponts Docker, VPN...).
"""

from __future__ import annotations

import socket
import subprocess
from dataclasses import dataclass

from secondscreen_host.pure.local_address import (
    NetworkInterfaceAddress,
    parse_ip_addr_output,
    pick_primary_address,
    usable_lan_addresses,
)

DEFAULT_PROBE_HOST = "8.8.8.8"
DEFAULT_PROBE_PORT = 80


class LocalAddressDetectionError(RuntimeError):
    """`ip -4 -o addr show` a échoué ou n'a pas pu être lancé : message
    compréhensible, jamais une trace brute (AGENTS.md, règle 5)."""


def detect_outbound_address(
    probe_host: str = DEFAULT_PROBE_HOST, probe_port: int = DEFAULT_PROBE_PORT
) -> str | None:
    """`None` si la machine n'a aucune route disponible (pas de réseau du
    tout) : jamais une exception pour ce cas normal, juste « pas de
    suggestion », voir `pick_primary_address`."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect((probe_host, probe_port))
            return sock.getsockname()[0]
    except OSError:
        return None


def list_interface_addresses() -> list[NetworkInterfaceAddress]:
    try:
        completed = subprocess.run(
            ["ip", "-4", "-o", "addr", "show"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except FileNotFoundError as exc:
        raise LocalAddressDetectionError("La commande « ip » est introuvable.") from exc
    except subprocess.TimeoutExpired as exc:
        raise LocalAddressDetectionError("« ip -4 -o addr show » n'a pas répondu à temps.") from exc

    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        detail = f" : {stderr}" if stderr else ""
        raise LocalAddressDetectionError(
            f"« ip -4 -o addr show » a échoué (code {completed.returncode}){detail}"
        )

    return parse_ip_addr_output(completed.stdout)


@dataclass(frozen=True)
class ConnectionAddresses:
    primary: str | None
    alternates: tuple[str, ...]
    """Les autres adresses LAN utilisables, sans la primaire (ordre
    stable) : à afficher si l'utilisateur veut vérifier ou choisir une
    autre interface (HOST-071)."""


def detect_connection_addresses() -> ConnectionAddresses:
    outbound = detect_outbound_address()
    interfaces = list_interface_addresses()
    usable = usable_lan_addresses(interfaces)
    primary = pick_primary_address(outbound, interfaces)
    alternates = tuple(c.address for c in usable if c.address != primary)
    return ConnectionAddresses(primary=primary, alternates=alternates)
