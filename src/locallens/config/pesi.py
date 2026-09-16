"""Pesi GGUF/mmproj: riuso cache HF-Hub condivisa, download solo se mancano."""

import os
from collections.abc import Callable
from pathlib import Path

from locallens.config.presets import PresetModello


def _cache_root() -> Path:
    override = os.environ.get("HF_HOME") or os.environ.get("HUGGINGFACE_HUB_CACHE")
    if override:
        return Path(override)
    return Path.home() / ".cache" / "huggingface" / "hub"


def snapshot_completo(preset: PresetModello, cache_root: Path | None = None) -> Path | None:
    """Snapshot che contiene sia GGUF sia mmproj; None se assente/incompleto."""
    root = cache_root or _cache_root()
    cartella = root / ("models--" + preset.hf_repo.replace("/", "--"))
    if not cartella.is_dir():
        return None
    for snap in sorted((cartella / "snapshots").glob("*")):
        if (snap / preset.gguf_file).is_file() and (snap / preset.mmproj_file).is_file():
            return snap
    return None


def _scarica_default(repo: str) -> None:
    from huggingface_hub import snapshot_download

    snapshot_download(repo_id=repo)


def risolvi_pesi(
    preset: PresetModello,
    cache_root: Path | None = None,
    scarica: Callable[[str], None] | None = None,
) -> tuple[str, str]:
    """(modello, mmproj). Scarica solo se snapshot incompleto e `scarica` fornito."""
    snap = snapshot_completo(preset, cache_root)
    if snap is None:
        if scarica is None:
            raise FileNotFoundError(
                f"pesi {preset.hf_repo} assenti in cache e download non richiesto"
            )
        scarica(preset.hf_repo)
        snap = snapshot_completo(preset, cache_root)
    if snap is None:
        raise FileNotFoundError(f"pesi {preset.hf_repo} non disponibili dopo download")
    return str(snap / preset.gguf_file), str(snap / preset.mmproj_file)


scarica_pesi = _scarica_default
