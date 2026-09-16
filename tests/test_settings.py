"""RED: impostazioni utente persistenti (TOML, path OS-standard)."""

from locallens.config.settings import DEFAULTS, carica, percorso_config, salva


def test_default():
    assert DEFAULTS["sorgente"] == "bundlato"
    assert DEFAULTS["preset_id"] == "lighton-ocr-q8_0"
    assert DEFAULTS["porta"] == 8011
    assert DEFAULTS["dpi_pdf"] == 300
    assert DEFAULTS["max_side_px"] == 2048


def test_percorso_linux():
    p = percorso_config(piattaforma="linux", home="/home/u", appdata="")
    assert str(p) == "/home/u/.config/locallens/config.toml"


def test_percorso_win():
    p = percorso_config(piattaforma="win32", home="", appdata="C:/A")
    assert str(p) == "C:/A/LocalLens/config.toml"


def test_roundtrip(tmp_path):
    conf = dict(DEFAULTS)
    conf.update({"sorgente": "esterno", "url_esterno": "http://10.0.0.1:8011", "preset_id": "x"})
    salva(conf, path=tmp_path / "c.toml")
    assert carica(path=tmp_path / "c.toml") == conf


def test_file_mancante_default(tmp_path):
    assert carica(path=tmp_path / "no.toml") == DEFAULTS
