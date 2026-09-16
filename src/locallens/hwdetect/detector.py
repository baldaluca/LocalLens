"""Rilevamento GPU/backend/VRAM. Nessuna dipendenza Qt."""
from dataclasses import dataclass


@dataclass(frozen=True)
class HardwareInfo:
    platform: str  # linux | win32
    gpu_vendor: str  # nvidia | amd | intel | none | unknown
    candidati: tuple[str, ...]  # es. ("cuda", "vulkan", "cpu")
    vram_mb: int | None
    is_hybrid_optimus: bool = False


def decide(
    platform: str,
    gpu_vendor: str,
    vram_mb: int | None,
    is_hybrid_optimus: bool,
    bins_disponibili: set[str],
) -> HardwareInfo:
    """Scelta pura e testabile dell'ordine di BackendGpu. CPU sempre ultima."""
    ordine: list[str] = []
    if gpu_vendor == "nvidia" and "cuda" in bins_disponibili:
        ordine.append("cuda")
    elif gpu_vendor == "amd" and platform == "linux" and "hip" in bins_disponibili:
        ordine.append("hip")
    if gpu_vendor in ("nvidia", "amd", "intel", "unknown") and "vulkan" in bins_disponibili:
        ordine.append("vulkan")
    ordine.append("cpu")
    return HardwareInfo(
        platform=platform,
        gpu_vendor=gpu_vendor,
        candidati=tuple(ordine),
        vram_mb=vram_mb,
        is_hybrid_optimus=is_hybrid_optimus,
    )


def detect(
    piattaforma: str | None = None,
    esegui=None,
    lspci=None,
    bins_presenti: set[str] | None = None,
    bins_root: str = "bins",
) -> HardwareInfo:
    """Rileva GPU/backend/VRAM. Probe iniettabili; default = sistema reale."""
    import subprocess
    import sys
    from pathlib import Path

    from locallens.backend.manager import resolve_binary

    piattaforma = piattaforma or sys.platform
    os = "linux" if piattaforma.startswith("linux") else "win32"

    def _esegui(cmd: list[str]) -> str | None:
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=False)
            return out.stdout.strip() or None
        except (OSError, subprocess.SubprocessError):
            return None

    esegui = esegui or _esegui

    def _lspci() -> str:
        return esegui(["lspci"]) or ""

    lspci_out = (lspci or _lspci)()

    vram_mb: int | None = None
    vendor = "none"
    smi = esegui(
        ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"]
    )
    if smi:
        vendor = "nvidia"
        try:
            vram_mb = int(smi.splitlines()[0].strip().split()[0])
        except (ValueError, IndexError):
            vram_mb = None

    if bins_presenti is None:
        bins_presenti = set()
        for backend in ("cuda", "hip", "vulkan", "cpu"):
            try:
                if Path(resolve_binary(os, backend, bins_root)).exists():
                    bins_presenti.add(backend)
            except ValueError:
                pass
    if vendor == "none" and bins_presenti:
        vendor = "unknown"

    optimus = (
        piattaforma.startswith("linux")
        and vendor == "nvidia"
        and "intel" in lspci_out.lower()
    )
    return decide(
        platform=os if os in ("linux", "win32") else piattaforma,
        gpu_vendor=vendor,
        vram_mb=vram_mb,
        is_hybrid_optimus=optimus,
        bins_disponibili=bins_presenti,
    )
