"""Entry point: python -m locallens. Boot con degradazione gestita (RNF4)."""

import sys

from locallens.config.presets import preset_da_conf


def costruisci_da_conf(conf):
    """Boot completo: detect → preset → fabbrica. Ritorna (engine, stato, banner)."""
    from locallens.core.fabbrica import costruisci, normalizza_sorgente
    from locallens.hwdetect.detector import detect

    info = detect()
    preset = preset_da_conf(conf)
    conf = dict(conf, preset_id=preset.id)
    conf, avviso = normalizza_sorgente(conf, info, preset)
    engine, stato, banner = costruisci(conf, info, preset)
    banner = "; ".join(b for b in (avviso, banner) if b)
    return engine, stato, banner


def main() -> int:
    from PySide6.QtWidgets import QApplication

    from locallens.app.finestra import MainWindow
    from locallens.config.settings import carica

    app = QApplication(sys.argv)
    app.setApplicationName("LocalLens")
    app.setDesktopFileName("locallens")
    from PySide6.QtGui import QIcon

    from locallens.app.icone import percorso_icona

    try:
        app.setWindowIcon(QIcon(percorso_icona()))
    except FileNotFoundError:
        pass
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
