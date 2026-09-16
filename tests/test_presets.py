"""RED: PresetModello caricato da TOML, mai hardcoded in core."""

import pytest

from locallens.config.presets import PresetModello, load_preset


def test_carica_preset_fascia_bassa_shipped():
    p = load_preset("presets/glm-ocr-q8_0.toml")
    assert isinstance(p, PresetModello)
    assert p.id == "glm-ocr-q8_0"
    assert p.chat_template == "glm-ocr"
    assert p.mmproj_file != ""
    assert p.vram_min_mb == 2048
    assert p.max_side_px == 2048


def test_preset_incompleto_sollevato(tmp_path):
    f = tmp_path / "bad.toml"
    f.write_text('id = "x"\n')
    with pytest.raises(ValueError):
        load_preset(str(f))


def test_selezione_preset_per_vram():
    from locallens.config.presets import seleziona_preset

    basso = seleziona_preset(vram_mb=4096, candidati=["glm-ocr-q8_0", "placeholder-alta"])
    assert basso == "glm-ocr-q8_0"
    nessun_gpu = seleziona_preset(vram_mb=None, candidati=["glm-ocr-q8_0"])
    assert nessun_gpu == "glm-ocr-q8_0"  # default CPU: nessun modello GPU, solo Tesseract
