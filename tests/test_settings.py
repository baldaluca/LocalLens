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
    assert DEFAULTS["lingua"] == "en"


def test_roundtrip_lingua(tmp_path):
    conf = dict(DEFAULTS)
    conf["lingua"] = "en"
    salva(conf, path=tmp_path / "c.toml")
    assert carica(path=tmp_path / "c.toml")["lingua"] == "en"


def test_lingua_non_valida_forza_it(tmp_path):
    path = tmp_path / "c.toml"
    path.write_text('lingua = "fr"\n', encoding="utf-8")
    assert carica(path=path)["lingua"] == "en"


def test_roundtrip_escape_stringhe(tmp_path):
    conf = dict(DEFAULTS)
    conf["prompt_esterno"] = 'Trascrici "tutto" esatto \\ test\nseconda riga'
    salva(conf, path=tmp_path / "c.toml")
    assert carica(path=tmp_path / "c.toml")["prompt_esterno"] == conf["prompt_esterno"]


def test_config_typed_load(tmp_path):
    from locallens.config.settings import Config

    p = tmp_path / "c.toml"
    p.write_text('lingua="en"\nsorgente="esterno"\n', encoding="utf-8")
    cfg = Config.load(p)
    assert cfg.lingua == "en"
    assert cfg.sorgente == "esterno"
    assert cfg.effective_url() == "http://127.0.0.1:8011"


def test_config_validated_corrige():
    from locallens.config.settings import Config

    cfg = Config(lingua="fr", sorgente="bogus")  # type: ignore[arg-type]
    validata = cfg.validated()
    assert validata.lingua == "en"
    assert validata.sorgente == "bundlato"
    # originale frozen non mutata
    assert cfg.lingua == "fr"
    # già valida → stessa istanza
    ok = Config(lingua="it", sorgente="esterno")
    assert ok.validated() is ok


def test_config_save_non_scrive_segret(tmp_path):
    from locallens.config.settings import Config

    p = tmp_path / "c.toml"
    cfg = Config(token_esterno="tk-segreto", lingua="it")
    cfg.save(p)
    testo = p.read_text(encoding="utf-8")
    assert "tk-segreto" not in testo
    assert "token_esterno" not in testo
    ricaricata = Config.load(p)
    assert ricaricata.token_esterno == ""


def test_config_salva_dict_e_config_non_scrive_segret(tmp_path):
    from locallens.config.settings import Config, salva

    p1 = tmp_path / "c1.toml"
    p2 = tmp_path / "c2.toml"
    # via Config
    salva(Config(token_esterno="tk2", lingua="en"), path=p1)
    assert "tk2" not in p1.read_text(encoding="utf-8")
    assert "token_esterno" not in p1.read_text(encoding="utf-8")
    # via dict
    salva({"token_esterno": "tk3", "lingua": "en"}, path=p2)
    assert "tk3" not in p2.read_text(encoding="utf-8")


def test_config_from_dict_roundtrip():
    from locallens.config.settings import DEFAULTS, Config

    # roundtrip esatto
    cfg = Config(lingua="en", sorgente="esterno", preset_id="lighton-ocr-q8_0")
    assert Config.from_dict(cfg.to_dict()) == cfg
    # DEFAULTS == Config().to_dict()
    assert Config().to_dict() == DEFAULTS
    # chiavi ignote ignorate
    cfg2 = Config.from_dict({"lingua": "en", "chiave_ignota": "x", "sorgente": "bundlato"})
    assert "chiave_ignota" not in cfg2.to_dict()
    # validazione via from_dict
    cfg3 = Config.from_dict({"lingua": "fr", "sorgente": "bogus"})
    assert cfg3.lingua == "en"
    assert cfg3.sorgente == "bundlato"
