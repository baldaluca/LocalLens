"""Avvio/supervisione llama-server bundlato come subprocess."""
import ipaddress
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


@dataclass
class BackendHandle:
    backend_gpu: str
    base_url: str
    porta: int
    pid: int | None = None


def resolve_binary(platform: str, backend_gpu: str, bins_root: str = "bins") -> Path:
    """bins/<os>/<backend>/llama-server[.exe]. Nessun check di esistenza qui."""
    nome = "llama-server.exe" if platform == "win32" else "llama-server"
    return Path(bins_root) / platform / backend_gpu / nome


def trova_porta_libera(partenza: int = 8011, occupate: set[int] | None = None) -> int:
    """Scan verso l'alto da `partenza` (max +10). Versione pura e testabile."""
    occupate = occupate or set()
    for porta in range(partenza, partenza + 11):
        if porta not in occupate:
            return porta
    raise OSError("nessuna porta libera in 8011-8020")


def is_url_privata(url: str) -> bool:
    """True se localhost o rete privata RFC1918/loopback (RNF1). False = mostrare avviso esplicito."""
    host = (urlparse(url).hostname or "").lower().strip("[]")
    if host in ("localhost",):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    if ip.is_loopback:
        return True
    reti = [
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
        ipaddress.ip_network("127.0.0.0/8"),
        ipaddress.ip_network("::1/128"),
        ipaddress.ip_network("fc00::/7"),
        ipaddress.ip_network("fe80::/10"),
    ]
    return any(ip in r for r in reti)


class BackendManager:
    def start(self, backend_gpu: str, preset_id: str, porta: int = 8011) -> BackendHandle:
        """Sceglie bins/<os>/<backend>/llama-server, scan porta 8011-8020, healthcheck. Da implementare."""
        raise NotImplementedError

    def stop(self) -> None:
        raise NotImplementedError

    def health(self) -> bool:
        raise NotImplementedError
