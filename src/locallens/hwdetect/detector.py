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


def detect() -> HardwareInfo:
    """Rileva backend disponibili ordinati per preferenza. Da implementare (Q8)."""
    raise NotImplementedError
