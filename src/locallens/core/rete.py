"""Utilità rete e percorsi binari: nessuna dipendenza da backend o subprocess."""

import ipaddress
from pathlib import Path
from urllib.parse import urlparse


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


def resolve_binary(platform: str, backend_gpu: str, bins_root: str | None = None) -> Path:
    """bins/<os>/<backend>/llama-server[.exe]. Default = bundle o CWD."""
    from locallens.config.percorsi import risorsa

    root = Path(bins_root) if bins_root else risorsa("bins")
    nome = "llama-server.exe" if platform == "win32" else "llama-server"
    return root / platform / backend_gpu / nome


def verifica_health(base_url: str, timeout: float = 2) -> bool:
    """True se GET {base_url}/health risponde 200. Mai eccezioni."""
    import urllib.request

    try:
        with urllib.request.urlopen(base_url.rstrip("/") + "/health", timeout=timeout) as r:
            return r.status == 200
    except (OSError, ValueError):
        return False
