"""Finestra principale. Parla solo con core via OcrWorker, mai con backend/URL ( §8)."""

from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from locallens.app.impostazioni import DialogoImpostazioni
from locallens.app.tema import NOMI_TEMI, qss
from locallens.app.worker import OcrWorker
from locallens.config.settings import salva as salva_impostazioni
from locallens.core.orchestrator import Estrazione, OcrEngine


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("LocalLens")
        from PySide6.QtGui import QIcon

        from locallens.app.icone import percorso_icona

        self.setWindowIcon(QIcon(percorso_icona()))
        centrale = QWidget()
        centrale.setObjectName("centrale")
        self.setCentralWidget(centrale)
        layout = QVBoxLayout(centrale)

        self.banner = QLabel()
        self.banner.setObjectName("banner")
        self.banner.hide()
        layout.addWidget(self.banner)
        self.tema_corrente = "chiaro"
        self.setStyleSheet(qss(self.tema_corrente))

        corpo = QHBoxLayout()
        layout.addLayout(corpo)

        self.lista = QListWidget()
        self.lista.setMaximumWidth(280)
        corpo.addWidget(self.lista)

        destra = QVBoxLayout()
        corpo.addLayout(destra)
        self.testo = QPlainTextEdit()
        self.testo.setReadOnly(True)
        destra.addWidget(self.testo)

        bottoni = QHBoxLayout()
        destra.addLayout(bottoni)
        self.btn_copia = QPushButton("Copia")
        self.btn_copia.clicked.connect(lambda: self.copia())
        self.btn_salva = QPushButton("Salva .txt")
        self.btn_salva.clicked.connect(lambda: self.salva(""))
        bottoni.addWidget(self.btn_copia)
        bottoni.addWidget(self.btn_salva)

        ingressi = QHBoxLayout()
        destra.addLayout(ingressi)
        self.btn_apri = QPushButton("Apri file/PDF")
        self.btn_apri.clicked.connect(lambda: self._apri_file())
        self.btn_incolla = QPushButton("Incolla")
        self.btn_incolla.clicked.connect(lambda: self._da_appunti())
        self.btn_schermo = QPushButton("Screenshot")
        self.btn_schermo.clicked.connect(lambda: self._da_screenshot())
        self.btn_setup = QPushButton("Impostazioni")
        self.btn_setup.clicked.connect(lambda: self._impostazioni())
        self.btn_tema = QPushButton("Tema: chiaro")
        self.btn_tema.clicked.connect(lambda: self.cambia_tema())
        for b in (self.btn_apri, self.btn_incolla, self.btn_schermo, self.btn_setup, self.btn_tema):
            b.setProperty("secondario", "true")
        ingressi.addWidget(self.btn_apri)
        ingressi.addWidget(self.btn_incolla)
        ingressi.addWidget(self.btn_schermo)
        ingressi.addWidget(self.btn_setup)
        ingressi.addWidget(self.btn_tema)

        self.progress = QProgressBar()
        self.progress.hide()
        layout.addWidget(self.progress)
        self.statusBar().showMessage("pronto")
        self._correnti: list[Estrazione] = []
        self._worker: OcrWorker | None = None
        self._engine: OcrEngine | None = None
        self.conf: dict = {"sorgente": "bundlato", "url_esterno": "", "preset_id": ""}

    def set_tema(self, nome: str) -> None:
        if nome not in NOMI_TEMI:
            raise ValueError(f"tema ignoto: {nome}")
        self.tema_corrente = nome
        self.setStyleSheet(qss(nome))
        self.btn_tema.setText(f"Tema: {nome}")

    def cambia_tema(self) -> None:
        self.set_tema("scuro" if self.tema_corrente == "chiaro" else "chiaro")
        self.conf["tema"] = self.tema_corrente

    def set_engine(self, engine: OcrEngine) -> None:
        self._engine = engine

    def set_ricostruttore(self, fn) -> None:
        """fn(conf) -> (engine, stato, banner). Iniettato da __main__."""
        self._ricostruttore = fn

    def _richiedi_engine(self) -> OcrEngine | None:
        if self._engine is None:
            self.mostra_banner("Motore non pronto: backend non avviato.")
            return None
        return self._engine

    def _apri_file(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        from locallens.app.ingresso import carica_documento

        percorso, _ = QFileDialog.getOpenFileName(
            self, "Apri immagine o PDF", "", "Documenti (*.png *.jpg *.jpeg *.pdf)"
        )
        if not percorso:
            return
        engine = self._richiedi_engine()
        if engine is None:
            return
        try:
            self.avvia(carica_documento(percorso), engine)
        except (FileNotFoundError, ValueError) as e:
            self.mostra_banner(f"Errore: {e}")

    def _da_appunti(self) -> None:
        from PySide6.QtWidgets import QApplication

        from locallens.app.ingresso import da_appunti

        engine = self._richiedi_engine()
        if engine is None:
            return
        png = da_appunti(QApplication.clipboard())
        if png is None:
            self.mostra_banner("Appunti vuoti: nessuna immagine.")
            return
        self.avvia([png], engine)

    def _da_screenshot(self) -> None:
        from locallens.app.ingresso import cattura_schermo

        engine = self._richiedi_engine()
        if engine is None:
            return
        try:
            self.avvia([cattura_schermo()], engine)
        except Exception as e:  # noqa: BLE001 — display assente ecc: banner, mai crash
            self.mostra_banner(f"Errore: {e}")

    def _impostazioni(self) -> None:
        dlg = DialogoImpostazioni(preset_ids=[self.conf.get("preset_id", "") or "glm-ocr-q8_0"])
        dlg.set_sorgente(self.conf.get("sorgente", "bundlato"))
        dlg.url.setText(self.conf.get("url_esterno", ""))
        if dlg.exec():
            self.conf.update(dlg.valori())
            salva_impostazioni(self.conf)
            ric = getattr(self, "_ricostruttore", None)
            if ric is not None:
                engine, stato, banner = ric(self.conf)
                self.set_engine(engine)
                self.set_stato(stato)
                if banner:
                    self.mostra_banner(banner)
                else:
                    self.nascondi_banner()

    def avvia(self, immagini: list[bytes], engine: OcrEngine) -> None:
        """Elabora in background: la GUI resta responsiva (RF8)."""
        self.nascondi_banner()
        self._correnti = []
        self.progress.setValue(0)
        self.progress.show()
        worker = OcrWorker(job_id="doc", engine=engine, immagini=immagini)
        worker.segnali.pagina.connect(self._on_pagina)
        worker.segnali.finito.connect(self._on_finito)
        worker.segnali.errore.connect(self._on_errore)
        self._worker = worker  # evita GC prima della fine
        QThreadPool.globalInstance().start(worker)

    def _on_pagina(self, estrazione, i: int, n: int) -> None:
        self._correnti.append(estrazione)
        self.progress.setMaximum(n)
        self.progress.setValue(i)

    def _on_finito(self, job_id: str) -> None:
        self.progress.hide()
        self.mostra_estrazioni(self._correnti)
        self._worker = None

    def _on_errore(self, job_id: str, messaggio: str) -> None:
        self.progress.hide()
        self.mostra_banner(f"Errore: {messaggio}")
        self._worker = None

    def set_stato(self, messaggio: str) -> None:
        self.statusBar().showMessage(messaggio)

    def mostra_banner(self, messaggio: str) -> None:
        self.banner.setText(messaggio)
        self.banner.show()

    def nascondi_banner(self) -> None:
        self.banner.hide()

    def mostra_estrazioni(self, estrazioni: list[Estrazione]) -> None:
        self.lista.clear()
        testi = []
        for e in estrazioni:
            self.lista.addItem(f"Pagina {e.pagina_id} [{e.motore_usato}] — {e.ms} ms")
            testi.append(e.testo)
            if e.motore_usato == "cpu-tesseract":
                self.mostra_banner(f"Pagina {e.pagina_id} elaborata via CPU (fallback)")
        self.testo.setPlainText("\n\n".join(testi))

    def copia(self) -> None:
        from PySide6.QtWidgets import QApplication

        QApplication.clipboard().setText(self.testo.toPlainText())

    def salva(self, percorso: str) -> None:
        if not percorso:
            QMessageBox.information(self, "Salva", "Scegli un file da dialogo (non in test).")
            return
        with open(percorso, "w", encoding="utf-8") as f:
            f.write(self.testo.toPlainText())
