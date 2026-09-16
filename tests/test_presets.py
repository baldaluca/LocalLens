"""RED: PresetModello caricato da TOML, mai hardcoded in core."""

import pytest

from locallens.config.presets import PresetModello, elenco_preset, load_preset


def test_carica_preset_fascia_bassa_shipped():
    p = load_preset("presets/glm-ocr-q8_0.toml")
    assert isinstance(p, PresetModello)
    assert p.id == "glm-ocr-q8_0"
    assert p.chat_template == "glm-ocr"
    assert p.mmproj_file != ""
    assert p.vram_min_mb == 2048
    assert p.max_side_px == 2048


def test_carica_preset_lighton_usato_nel_benchmark():
    p = load_preset("presets/lighton-ocr-q8_0.toml")
    assert isinstance(p, PresetModello)
    assert p.id == "lighton-ocr-q8_0"
    assert p.hf_repo == "ggml-org/LightOnOCR-1B-1025-GGUF"
    assert p.gguf_file == "LightOnOCR-1B-1025-Q8_0.gguf"
    assert p.mmproj_file == "mmproj-LightOnOCR-1B-1025-Q8_0.gguf"
    assert p.ctx_size == 8192
    assert p.max_side_px == 2048
    assert p.server_args.get("n_gpu_layers") == 99
    assert p.max_tokens == 2048  # cap anti-runaway dal benchmark 16/09/2026


def test_elenco_preset_da_cartelle(tmp_path):
    (tmp_path / "b.toml").write_text('id = "b-x"\n')
    (tmp_path / "a.toml").write_text('id = "a-x"\n')
    (tmp_path / "ignora.txt").write_text("x")
    assert elenco_preset([tmp_path]) == ["a-x", "b-x"]


def test_elenco_preset_salta_file_non_toml(tmp_path):
    (tmp_path / "rotto.toml").write_text("[[[ non toml")
    assert elenco_preset([tmp_path]) == []


def test_preset_incompleto_sollevato(tmp_path):
    f = tmp_path / "bad.toml"
    f.write_text('id = "x"\n')
    with pytest.raises(ValueError):
        load_preset(str(f))


def test_selezione_preset_per_vram():
    from locallens.config.presets import seleziona_preset

    basso = seleziona_preset(
        vram_mb=4096, candidati=["glm-ocr-q8_0", "placeholder-alta"]
    )
    assert basso == "glm-ocr-q8_0"
    nessun_gpu = seleziona_preset(vram_mb=None, candidati=["glm-ocr-q8_0"])
    assert (
        nessun_gpu == "glm-ocr-q8_0"
    )  # default CPU: nessun modello GPU, solo Tesseract
