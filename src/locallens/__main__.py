"""Entry point: python -m locallens. Boot con degradazione gestita (RNF4)."""

import sys


def _solo_cpu(motivo: str):
    from locallens.core.errori import InferenzaError
    from locallens.core.orchestrator import OcrEngine
    from locallens.fallback.tesseract import estrai

    def infer(pagina_id: int, png: bytes):
        raise InferenzaError(motivo)

    return OcrEngine(infer=infer, fallback=lambda p, i: estrai(i), sorgente="nessuno")


def _preset_da_conf(conf):
    from locallens.config.percorsi import risorsa
    from locallens.config.presets import load_preset

    pid = conf.get("preset_id", "") or "glm-ocr-q8_0"
    try:
        return load_preset(str(risorsa("presets", f"{pid}.toml")))
    except (ValueError, OSError):
        return load_preset(str(risorsa("presets", "glm-ocr-q8_0.toml")))


def costruisci_da_conf(conf):
    """Boot completo: detect → preset → fabbrica. Ritorna (engine, stato, banner)."""
    from locallens.config.presets import seleziona_preset
    from locallens.core.fabbrica import costruisci
    from locallens.hwdetect.detector import detect

    info = detect()
    preset = _preset_da_conf(conf)
    conf = dict(conf, preset_id=preset.id)
    engine, stato, banner = costruisci(conf, info, preset)
    atteso = seleziona_preset(info.vram_mb, [preset.id])
    return engine, f"{stato} • atteso={atteso}", banner


def main() -> int:
    from PySide6.QtWidgets import QApplication

    from locallens.app.finestra import MainWindow
    from locallens.config.settings import carica

    app = QApplication(sys.argv)
    conf = carica()
    finestra = MainWindow()
    finestra.conf = conf
    finestra.set_ricostruttore(costruisci_da_conf)
    finestra.set_tema(conf.get("tema", "chiaro"))
    engine, stato, banner = costruisci_da_conf(conf)
    finestra.set_engine(engine)
    finestra.set_stato(stato)
    if banner:
        finestra.mostra_banner(banner)
    finestra.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
