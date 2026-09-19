"""Entry point: python -m locallens. Boot con degradazione gestita (RNF4)."""

import sys

from locallens.config.presets import preset_da_conf


def costruisci_da_conf(conf):
    """Boot completo: EngineFactory owns SorgenteModello. Ritorna (engine, stato, banner)."""
    from locallens.config.settings import Config, as_dict
    from locallens.core.fabbrica import EngineFactory

    cfg = conf if isinstance(conf, Config) else Config.from_dict(as_dict(conf))
    factory = EngineFactory(cfg)
    return factory.rebuild(cfg)


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
