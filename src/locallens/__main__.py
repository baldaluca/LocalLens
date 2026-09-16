"""Entry point: python -m locallens. Boot con degradazione gestita (RNF4)."""

import sys


def _solo_cpu(motivo: str):
    from locallens.core.errori import InferenzaError
    from locallens.core.orchestrator import OcrEngine
    from locallens.fallback.tesseract import estrai

    def infer(pagina_id: int, png: bytes):
        raise InferenzaError(motivo)

    return OcrEngine(infer=infer, fallback=lambda p, i: estrai(i), sorgente="nessuno")


def costruisci_engine():
    """hwdetect → preset → backend bundlato oppure fallback. Ritorna (engine, stato, banner)."""
    from locallens.backend.manager import BackendManager
    from locallens.config.presets import load_preset, seleziona_preset
    from locallens.core.orchestrator import crea_engine
    from locallens.hwdetect.detector import detect

    info = detect()
    try:
        preset = load_preset("presets/glm-ocr-q8_0.toml")
    except ValueError:
        return _solo_cpu("preset non valido"), "cpu (solo CPU)", "Solo CPU: preset non valido."
    stato = f"{info.candidati[0]} • preset={seleziona_preset(info.vram_mb, ['glm-ocr-q8_0'])}"
    if info.candidati[0] == "cpu":
        return (
            _solo_cpu("nessun backend GPU"),
            stato + " (solo CPU)",
            "Solo CPU: nessun backend GPU utilizzabile.",
        )
    from locallens.config.pesi import risolvi_pesi

    try:
        modello, mmproj = risolvi_pesi(preset)
    except FileNotFoundError as e:
        return _solo_cpu(str(e)), stato + " (solo CPU)", f"Solo CPU: {e}"
    try:
        handle = BackendManager().start(info.candidati[0], preset=preset, modello=modello, mmproj=mmproj)
        engine = crea_engine(handle.base_url, preset, motore=info.candidati[0])
        return engine, f"{stato} • {handle.base_url}", ""
    except (FileNotFoundError, RuntimeError, OSError) as e:
        return _solo_cpu(str(e)), stato + " (solo CPU)", f"Solo CPU: {e}"


def main() -> int:
    from PySide6.QtWidgets import QApplication

    from locallens.app.finestra import MainWindow

    app = QApplication(sys.argv)
    finestra = MainWindow()
    engine, stato, banner = costruisci_engine()
    finestra.set_engine(engine)
    finestra.set_stato(stato)
    if banner:
        finestra.mostra_banner(banner)
    finestra.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
