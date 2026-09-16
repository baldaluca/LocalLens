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
    """Gestisce il subprocess llama-server. Dipendenze iniettabili per i test."""

    def __init__(
        self,
        platform: str = "linux",
        bins_root: str = "bins",
        esiste=None,
        porte_occupate=None,
        lancia=None,
        verifica=None,
        uccidi=None,
    ) -> None:
        import socket
        import subprocess
        import urllib.request
        from collections.abc import (
            Callable,  # noqa: F401 (import locale, niente dipendenze extra)
        )

        self._platform = platform
        self._bins_root = bins_root
        self.handle: BackendHandle | None = None

        def _esiste(p) -> bool:
            return Path(p).exists()

        def _occupate() -> set[int]:
            occ: set[int] = set()
            for porta in range(8011, 8021):
                with socket.socket() as s:
                    s.settimeout(0.05)
                    if s.connect_ex(("127.0.0.1", porta)) == 0:
                        occ.add(porta)
            return occ

        def _lancia(cmd: list[str]) -> int:
            proc = subprocess.Popen(cmd)
            return proc.pid

        def _verifica(url: str) -> bool:
            try:
                with urllib.request.urlopen(url + "/health", timeout=2) as r:
                    return r.status == 200
            except OSError:
                return False

        def _uccidi(pid: int) -> None:
            import signal

            try:
                import os

                os.kill(pid, signal.SIGTERM)
            except OSError:
                pass

        self._esiste = esiste or _esiste
        self._porte_occupate = porte_occupate or _occupate
        self._lancia = lancia or _lancia
        self._verifica = verifica or _verifica
        self._uccidi = uccidi or _uccidi

    def start(
        self,
        backend_gpu: str,
        preset=None,
        porta: int = 8011,
        modello: str = "",
        mmproj: str = "",
    ) -> BackendHandle:
        """Avvia bins/<os>/<backend>/llama-server sulla prima porta libera, con healthcheck."""
        binario = resolve_binary(self._platform, backend_gpu, self._bins_root)
        if not self._esiste(binario):
            raise FileNotFoundError(f"binario mancante: {binario}")
        libera = trova_porta_libera(porta, self._porte_occupate())
        if preset is None:
            cmd = [str(binario), "--port", str(libera)]
        else:
            from locallens.backend.cli import preset_to_argv

            cmd = preset_to_argv(preset, str(binario), modello, mmproj, libera)
        pid = self._lancia(cmd)
        base_url = f"http://127.0.0.1:{libera}"
        if not self._verifica(base_url):
            self._uccidi(pid)
            raise RuntimeError(f"healthcheck fallito su {base_url} ({backend_gpu})")
        self.handle = BackendHandle(backend_gpu, base_url, libera, pid)
        return self.handle

    def stop(self) -> None:
        if self.handle and self.handle.pid is not None:
            self._uccidi(self.handle.pid)
        self.handle = None

    def health(self) -> bool:
        if self.handle is None:
            return False
        try:
            return bool(self._verifica(self.handle.base_url))
        except OSError:
            return False
