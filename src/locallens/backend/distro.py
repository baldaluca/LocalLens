"""Distribuzione binari llama-server: tag pinnato + nomi asset verificati su GitHub API.

Aggiornare TAG solo dopo test su entrambe le macchine di riferimento (§10 requisiti).
Verificato il: 2026-09-16 contro tag b10995 (33 asset).
"""

from pathlib import Path

TAG = "b10995"
BASE_URL = f"https://github.com/ggml-org/llama.cpp/releases/download/{TAG}"

_ASSETS: dict[tuple[str, str], str] = {
    ("linux", "cuda"): "llama-b10995-bin-ubuntu-cuda-12.8-x64.tar.gz",
    ("linux", "hip"): "llama-b10995-bin-ubuntu-rocm-10.0-x64.tar.gz",
    ("linux", "vulkan"): "llama-b10995-bin-ubuntu-vulkan-x64.tar.gz",
    ("linux", "cpu"): "llama-b10995-bin-ubuntu-x64.tar.gz",
    ("win32", "cuda"): "llama-b10995-bin-win-cuda-12.4-x64.zip",
    ("win32", "vulkan"): "llama-b10995-bin-win-vulkan-x64.zip",
    ("win32", "cpu"): "llama-b10995-bin-win-cpu-x64.zip",
}


def matrice_v1() -> dict[str, list[str]]:
    return {
        "linux": ["cuda", "hip", "vulkan", "cpu"],
        "win32": ["cuda", "vulkan", "cpu"],
    }


def asset_name(os: str, backend: str) -> str:
    try:
        return _ASSETS[(os, backend)]
    except KeyError:
        raise ValueError(f"nessun asset pinnato per {os}/{backend}") from None


def download_url(os: str, backend: str, tag: str = TAG) -> str:
    nome = asset_name(os, backend)
    base = f"https://github.com/ggml-org/llama.cpp/releases/download/{tag}"
    return f"{base}/{nome}"


def dest_dir(os: str, backend: str, bins_root: str = "bins") -> Path:
    return Path(bins_root) / os / backend
