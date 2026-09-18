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
