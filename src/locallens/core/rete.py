"""Utilità rete pura: nessun I/O, nessuna dipendenza di layer."""

import ipaddress
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
