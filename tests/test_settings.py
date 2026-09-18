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


def test_roundtrip_cloud(tmp_path):
    from locallens.config.settings import DEFAULTS, carica, salva

    conf = {
        "sorgente": "esterno",
        "token_esterno": "tk",
        "modello_esterno": "vision-x",
        "prompt_esterno": "Leggi.",
    }
    salva(conf, path=tmp_path / "c.toml")
    atteso = {**DEFAULTS, **conf, "token_esterno": ""}
    assert carica(path=tmp_path / "c.toml") == atteso


def test_token_mai_salvato_su_disco(tmp_path):
    from locallens.config.settings import carica, salva

    conf = {"sorgente": "esterno", "token_esterno": "tk-segreto"}
    path = tmp_path / "c.toml"
    salva(conf, path=path)
    assert "tk-segreto" not in path.read_text()
    assert "token_esterno" not in path.read_text()
    assert carica(path=path)["token_esterno"] == ""


def test_lingua_default_it():
    assert DEFAULTS["lingua"] == "it"


def test_roundtrip_lingua(tmp_path):
    conf = dict(DEFAULTS)
    conf["lingua"] = "en"
    salva(conf, path=tmp_path / "c.toml")
    assert carica(path=tmp_path / "c.toml")["lingua"] == "en"


def test_lingua_non_valida_forza_it(tmp_path):
    path = tmp_path / "c.toml"
    path.write_text('lingua = "fr"\n', encoding="utf-8")
    assert carica(path=path)["lingua"] == "it"
