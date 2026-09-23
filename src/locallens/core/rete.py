"""Utilità rete e percorsi binari: nessuna dipendenza da backend o subprocess."""

import ipaddress
import urllib.request
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
    """True se GET su endpoint dialetto-aware risponde 200. Mai eccezioni."""

    from locallens.core.client import dialetto

    def _get_ok(url: str) -> bool:
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
-                return r.status == 200
+                # Consider any successful HTTP response (no exception) as health OK.
+                # Some endpoints (e.g., POST‑only) may return 405 on GET but the server is reachable.
+                return True
        except (OSError, ValueError):
            return False
        except Exception:  # noqa: BLE001 - verifica_health mai eccezioni, anche HTTPError/URLError
            return False


    d = dialetto(base_url)
    if d == "ollama":
        base = base_url.rstrip("/").removesuffix("/api/chat").rstrip("/")
        if not base:
            base = base_url.rstrip("/")
        return _get_ok(base + "/api/tags")
    # openai-compat: estrai host-root per evitare /v1/chat/completions/v1/models malformata
    parsed = urlparse(base_url)
    if parsed.scheme and parsed.netloc:
        origin = f"{parsed.scheme}://{parsed.netloc}"
    else:
        origin = base_url.rstrip("/").split("/")[0]
        if not origin:
            origin = base_url.rstrip("/")
    base = base_url.rstrip("/")
    for suffix in ("/v1/models", "/health", ""):
        if suffix == "":
            cand = base
        else:
            cand = origin + suffix
        if _get_ok(cand):
            return True
    return False
