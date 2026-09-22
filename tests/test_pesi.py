"""RED: pesi GGUF/mmproj da cache HF o download. Niente path hardcoded."""

from pathlib import Path

import pytest

from locallens.config.pesi import risolvi_pesi, snapshot_completo
from locallens.config.presets import load_preset


def _cache_finta(tmp_path, completa=True):
    snap = tmp_path / "models--ggml-org--GLM-OCR-GGUF" / "snapshots" / "abc123"
    snap.mkdir(parents=True)
    (snap / "GLM-OCR-Q8_0.gguf").write_bytes(b"gguf")
    if completa:
        (snap / "mmproj-GLM-OCR-Q8_0.gguf").write_bytes(b"mmproj")
    return tmp_path


def test_snapshot_completo_trovato(tmp_path):
    root = _cache_finta(tmp_path)
    preset = load_preset("presets/glm-ocr-q8_0.toml")
    snap = snapshot_completo(preset, cache_root=root)
    assert snap is not None and snap.name == "abc123"


def test_snapshot_incompleto_none(tmp_path):
    root = _cache_finta(tmp_path, completa=False)
    assert snapshot_completo(load_preset("presets/glm-ocr-q8_0.toml"), cache_root=root) is None


def test_risolvi_restituisce_path(tmp_path):
    root = _cache_finta(tmp_path)
    modello, mmproj = risolvi_pesi(
        load_preset("presets/glm-ocr-q8_0.toml"), cache_root=root
    )
    assert Path(modello).name == "GLM-OCR-Q8_0.gguf"
    assert Path(mmproj).name == "mmproj-GLM-OCR-Q8_0.gguf"


def test_risolvi_scarica_se_manca(tmp_path):
    chiamate = []

    def finto_download(repo):
        chiamate.append(repo)
        _cache_finta(tmp_path)

    modello, _ = risolvi_pesi(
        load_preset("presets/glm-ocr-q8_0.toml"),
        cache_root=tmp_path,
        scarica=finto_download,
    )
    assert chiamate == ["ggml-org/GLM-OCR-GGUF"]
    assert Path(modello).exists()


def test_risolvi_senza_download_sollevato(tmp_path):
    with pytest.raises(FileNotFoundError):
        risolvi_pesi(load_preset("presets/glm-ocr-q8_0.toml"), cache_root=tmp_path)


def test_cache_root_rispetta_hf_home(monkeypatch, tmp_path):
    from locallens.config import pesi

    monkeypatch.setenv("HF_HOME", str(tmp_path / "hf"))
    monkeypatch.delenv("HUGGINGFACE_HUB_CACHE", raising=False)
    assert pesi._cache_root() == tmp_path / "hf"


def test_cache_root_env_param_iniettabile(tmp_path):
    from locallens.config import pesi

    root = pesi._cache_root(env={"HF_HOME": str(tmp_path / "custom")})
    assert root == tmp_path / "custom"


def test_cache_root_delega_default_hub(monkeypatch, tmp_path):
    from locallens.config import pesi

    monkeypatch.delenv("HF_HOME", raising=False)
    monkeypatch.delenv("HUGGINGFACE_HUB_CACHE", raising=False)
    import huggingface_hub.constants as hub_const

    monkeypatch.setattr(hub_const, "HF_HUB_CACHE", str(tmp_path / "hub-default"))
    assert pesi._cache_root() == tmp_path / "hub-default"
