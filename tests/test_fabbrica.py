"""RED: engine da SorgenteModello. Stessa interfaccia HTTP, cambia solo dove punta."""

from locallens.config.presets import load_preset
from locallens.core.fabbrica import costruisci


def _info(candidati=("cuda", "vulkan", "cpu"), vram=4096):
    from locallens.hwdetect.detector import HardwareInfo

    return HardwareInfo("linux", "nvidia", candidati, vram, False)


def _finte():
    chiamate = {}
    return chiamate


def test_esterno_punta_a_url():
    preset = load_preset("presets/glm-ocr-q8_0.toml")
    conf = {"sorgente": "esterno", "url_esterno": "http://127.0.0.1:8011"}
    crea = lambda url, p, motore, **k: ("engine", url, motore)
    eng, _stato, banner = costruisci(conf, _info(), preset, crea=crea)
    assert eng == ("engine", "http://127.0.0.1:8011", "esterno")
    assert banner == ""


def test_esterno_pubblico_avvisa():
    preset = load_preset("presets/glm-ocr-q8_0.toml")
    conf = {"sorgente": "esterno", "url_esterno": "http://203.0.113.10:8011"}
    _eng, _stato, banner = costruisci(conf, _info(), preset, crea=lambda u, p, motore, **k: u)
    assert banner != ""


def test_nessuno_solo_cpu():
    preset = load_preset("presets/glm-ocr-q8_0.toml")
    conf = {"sorgente": "nessuno"}
    eng, stato, _banner = costruisci(
        conf, _info(), preset, solo_cpu=lambda motivo: f"cpu:{motivo}"
    )
    assert eng.startswith("cpu:")
    assert "solo CPU" in stato


def test_bundlato_avvia_gestore():
    preset = load_preset("presets/glm-ocr-q8_0.toml")
    conf = {"sorgente": "bundlato"}
    avvii = {}

    class Gestore:
        def start(self, backend, preset=None, modello="", mmproj="", porta=8011):
            avvii["backend"] = backend
            from locallens.backend.manager import BackendHandle

            return BackendHandle(backend, "http://127.0.0.1:8011", 8011, 1)

    eng, _stato, banner = costruisci(
        conf,
        _info(),
        preset,
        gestore=Gestore(),
        crea=lambda url, p, motore, **k: (url, motore),
        pesi=("/m/g.gguf", "/m/p.gguf"),
    )
    assert avvii["backend"] == "cuda"
    assert eng == ("http://127.0.0.1:8011", "cuda")
    assert banner == ""


def test_bundlato_fallisce_cpu():
    preset = load_preset("presets/glm-ocr-q8_0.toml")
    conf = {"sorgente": "bundlato"}

    class GestoreKo:
        def start(self, *a, **k):
            raise FileNotFoundError("bins assenti")

    eng, _stato, banner = costruisci(
        conf, _info(), preset, gestore=GestoreKo(), solo_cpu=lambda m: "cpu"
    )
    assert eng == "cpu"
    assert "bins assenti" in banner


def test_esterno_trasmette_contesto_filtro():
    preset = load_preset("presets/glm-ocr-q8_0.toml")
    conf = {
        "sorgente": "esterno",
        "url_esterno": "http://127.0.0.1:8011",
        "lingue_filtro": "it,en",
        "soglia_righe_loop": 9,
        "ignora_eco": True,
    }
    viste = {}

    def crea(url, p, motore, **k):
        viste.update(k)
        return "engine"

    costruisci(conf, _info(), preset, crea=crea)
    assert viste["lingue_attese"] == ("it", "en")
    assert viste["soglia_righe_loop"] == 9
    assert viste["ignora_eco"] is True


def test_contesto_default_senza_chiavi():
    preset = load_preset("presets/glm-ocr-q8_0.toml")
    conf = {"sorgente": "esterno", "url_esterno": "http://127.0.0.1:8011"}
    viste = {}

    def crea(url, p, motore, **k):
        viste.update(k)
        return "engine"

    costruisci(conf, _info(), preset, crea=crea)
    assert viste["lingue_attese"] == ("it",)
    assert viste["soglia_righe_loop"] == 5
    assert viste["ignora_eco"] is False


def test_disponibilita_solo_se_binario_e_pesi(tmp_path):
    from locallens.core.fabbrica import disponibilita_gpu_locale

    preset = load_preset("presets/glm-ocr-q8_0.toml")
    (tmp_path / "linux" / "cuda").mkdir(parents=True)
    (tmp_path / "linux" / "cuda" / "llama-server").write_text("x")
    # Ermetico: bins_root vuota → binario assente → False (l'env reale ha binario+pesi).
    assert (
        disponibilita_gpu_locale(
            _info(), preset, piattaforma="linux", bins_root=tmp_path / "vuota"
        )
        is False
    )


def test_normalizza_ripiega_su_esterno_se_gpu_assente(monkeypatch):
    import locallens.core.fabbrica as fab
    from locallens.core.fabbrica import normalizza_sorgente

    monkeypatch.setattr(fab, "disponibilita_gpu_locale", lambda *a, **k: False)
    preset = load_preset("presets/glm-ocr-q8_0.toml")
    conf = {"sorgente": "bundlato"}
    nuova, banner = normalizza_sorgente(conf, _info(), preset)
    assert nuova["sorgente"] == "esterno"
    assert "GPU locale non rilevata" in banner


def test_normalizza_lascia_esterno_e_nessuno():
    from locallens.core.fabbrica import normalizza_sorgente

    preset = load_preset("presets/glm-ocr-q8_0.toml")
    for sorg in ("esterno", "nessuno"):
        nuova, banner = normalizza_sorgente({"sorgente": sorg}, _info(), preset)
        assert nuova["sorgente"] == sorg
        assert banner is None


def test_disponibilita_quattro_combinazioni(tmp_path, monkeypatch):
    import locallens.core.fabbrica as fab

    preset = load_preset("presets/glm-ocr-q8_0.toml")
    binario = tmp_path / "linux" / "cuda" / "llama-server"
    monkeypatch.setattr(fab.sys, "platform", "linux")
    casi = [
        (False, None, False),
        (True, None, False),
        (False, tmp_path / "snap", False),
        (True, tmp_path / "snap", True),
    ]
    for ha_binario, snap, atteso in casi:
        if ha_binario:
            binario.parent.mkdir(parents=True, exist_ok=True)
            binario.write_text("x")
        elif binario.is_file():
            binario.unlink()
        monkeypatch.setattr(
            "locallens.config.pesi.snapshot_completo", lambda p, c=None: snap
        )
        assert fab.disponibilita_gpu_locale(_info(), preset, bins_root=tmp_path) is atteso
