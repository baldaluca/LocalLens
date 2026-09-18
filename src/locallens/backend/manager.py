"""Avvio/supervisione llama-server bundlato come subprocess."""
from dataclasses import dataclass
from pathlib import Path

from locallens.core.rete import is_url_privata, resolve_binary, verifica_health

__all__ = [
    "BackendHandle",
    "BackendManager",
    "is_url_privata",
    "resolve_binary",
    "trova_porta_libera",
    "verifica_health",
]


@dataclass
class BackendHandle:
    backend_gpu: str
    base_url: str
    porta: int
    pid: int | None = None


def trova_porta_libera(partenza: int = 8011, occupate: set[int] | None = None) -> int:
    """Scan verso l'alto da `partenza` (max +10). Versione pura e testabile."""
    occupate = occupate or set()
    for porta in range(partenza, partenza + 11):
        if porta not in occupate:
            return porta
    raise OSError("nessuna porta libera in 8011-8020")


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
        from collections.abc import (
            Callable,  # noqa: F401 (import locale, niente dipendenze extra)
        )

        self._platform = platform
        self._bins_root = bins_root
        self.handle: BackendHandle | None = None
        self._proc = None

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
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._proc = proc
            return proc.pid

        def _verifica(url: str) -> bool:
            return verifica_health(url)

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
            if self._proc is not None:
                self._finalizza_proc()
            else:
                # Lancia iniettato (solo pid, nessun Popen registrato).
                self._uccidi(pid)
            raise RuntimeError(f"healthcheck fallito su {base_url} ({backend_gpu})")
        self.handle = BackendHandle(backend_gpu, base_url, libera, pid)
        return self.handle

    def _finalizza_proc(self) -> None:
        """terminate()+wait sul Popen registrato, senza mai lasciare zombie."""
        proc, self._proc = self._proc, None
        if proc is None:
            return
        import contextlib
        import subprocess as _sp

        # Cleanup best-effort: qualunque errore qui è ignorabile, l'importante
        # è non lasciare zombie e mai bloccare start/stop.
        with contextlib.suppress(Exception):
            proc.terminate()
        with contextlib.suppress(Exception):
            try:
                proc.wait(timeout=5)
            except _sp.TimeoutExpired:
                # Kill best-effort, poi secondo wait best-effort.
                with contextlib.suppress(Exception):
                    proc.kill()
                proc.wait(timeout=5)

    def stop(self) -> None:
        if self._proc is not None:
            self._finalizza_proc()
        elif self.handle and self.handle.pid is not None:
            self._uccidi(self.handle.pid)
        self.handle = None

    def health(self) -> bool:
        if self.handle is None:
            return False
        try:
            return bool(self._verifica(self.handle.base_url))
        except OSError:
            return False
