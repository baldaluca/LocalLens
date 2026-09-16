"""Finestra principale. Parla solo con core via OcrWorker, mai con backend/URL ( §8)."""

from PySide6.QtCore import QThreadPool
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from locallens.app.icone import percorso_icona
from locallens.app.impostazioni import DialogoImpostazioni
from locallens.app.tema import NOMI_TEMI, qss
from locallens.app.worker import OcrWorker
from locallens.config.settings import salva as salva_impostazioni
from locallens.core.orchestrator import Estrazione, OcrEngine

TESTO_VUOTO = (
    "Apri un Documento (immagine o PDF) per iniziare.\n\n"
    "Sorgenti: file • appunti • screenshot."
)


def tempo_breve(ms: int) -> str:
    """Durata umana per liste e separatori: '52 s', '800 ms'."""
    if ms < 1000:
        return f"{ms} ms"
    return f"{round(ms / 1000)} s"


def _icona(nome_tema: str, standard: QStyle.StandardPixmap, widget) -> QIcon:
    icona = QIcon.fromTheme(nome_tema)
    if icona.isNull():
        icona = widget.style().standardIcon(standard)
    return icona


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("LocalLens")
        self.setWindowIcon(QIcon(percorso_icona()))
        self.resize(1120, 700)
        self.setMinimumSize(900, 600)
        centrale = QWidget()
        centrale.setObjectName("centrale")
        self.setCentralWidget(centrale)
        layout = QVBoxLayout(centrale)

        self.banner = QLabel()
        self.banner.setObjectName("banner")
        self.banner.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.banner.hide()
        layout.addWidget(self.banner)
        self.tema_corrente = "chiaro"
        self.setStyleSheet(qss(self.tema_corrente))

        intestazione = QHBoxLayout()
        layout.addLayout(intestazione)
        self.titolo = QLabel("LocalLens")
        self.titolo.setObjectName("titolo")
        intestazione.addWidget(self.titolo)
        self.doc = QLabel("Nessun Documento")
        self.doc.setObjectName("doc")
        intestazione.addWidget(self.doc, stretch=1)
        self.pill = QLabel()
        self.pill.setObjectName("pill")
        intestazione.addWidget(self.pill)

        corpo = QHBoxLayout()
        layout.addLayout(corpo, stretch=1)

        divisore = QSplitter()
        corpo.addWidget(divisore)
        self.lista = QListWidget()
        self.lista.setMinimumWidth(220)
        divisore.addWidget(self.lista)

        destra = QWidget()
        layout_destra = QVBoxLayout(destra)
        layout_destra.setContentsMargins(0, 0, 0, 0)
        divisore.addWidget(destra)
        divisore.setStretchFactor(0, 0)
        divisore.setStretchFactor(1, 1)
        self.testo = QPlainTextEdit()
        self.testo.setReadOnly(True)
        self.testo.setPlainText(TESTO_VUOTO)
        layout_destra.addWidget(self.testo)

        Azioni = QHBoxLayout()
        Azioni.setSpacing(8)
        layout_destra.addLayout(Azioni)
        self.btn_apri = QPushButton("Apri file/PDF")
        self.btn_apri.setIcon(_icona("document-open", QStyle.StandardPixmap.SP_DialogOpenButton, self))
        self.btn_apri.clicked.connect(lambda: self._apri_file())
        self.btn_incolla = QPushButton("Incolla")
        self.btn_incolla.setIcon(_icona("edit-paste", QStyle.StandardPixmap.SP_FileDialogDetailedView, self))
        self.btn_incolla.clicked.connect(lambda: self._da_appunti())
        self.btn_schermo = QPushButton("Screenshot")
        self.btn_schermo.setIcon(_icona("camera-photo", QStyle.StandardPixmap.SP_ComputerIcon, self))
        self.btn_schermo.clicked.connect(lambda: self._da_screenshot())
        self.btn_annulla = QPushButton("Annulla")
        self.btn_annulla.setIcon(_icona("process-stop", QStyle.StandardPixmap.SP_DialogCancelButton, self))
        self.btn_annulla.clicked.connect(lambda: self._annulla())
        self.btn_annulla.setEnabled(False)
        for b in (self.btn_apri, self.btn_incolla, self.btn_schermo, self.btn_annulla):
            b.setMinimumHeight(40)
            b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            Azioni.addWidget(b, stretch=1)

        secondarie = QHBoxLayout()
        secondarie.setSpacing(8)
        layout_destra.addLayout(secondarie)
        self.btn_copia = QPushButton("Copia")
        self.btn_copia.setIcon(_icona("edit-copy", QStyle.StandardPixmap.SP_FileDialogContentsView, self))
        self.btn_copia.clicked.connect(lambda: self.copia())
        self.btn_salva = QPushButton("Salva .txt")
        self.btn_salva.setIcon(_icona("document-save", QStyle.StandardPixmap.SP_DialogSaveButton, self))
        self.btn_salva.clicked.connect(lambda: self._salva_file())
        self.btn_setup = QPushButton("Impostazioni")
        self.btn_setup.setIcon(_icona("preferences-system", QStyle.StandardPixmap.SP_FileDialogListView, self))
        self.btn_setup.clicked.connect(lambda: self._impostazioni())
        self.btn_tema = QPushButton("Tema: chiaro")
        self.btn_tema.setIcon(_icona("weather-clear-night", QStyle.StandardPixmap.SP_TitleBarShadeButton, self))
        self.btn_tema.clicked.connect(lambda: self.cambia_tema())
        for b in (
            self.btn_copia,
            self.btn_salva,
            self.btn_setup,
            self.btn_tema,
        ):
            b.setProperty("secondario", "true")
            b.setMinimumHeight(40)
            b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            secondarie.addWidget(b, stretch=1)

        self.progress = QProgressBar()
        self.progress.setFormat("Pagina %v di %m")
        self.progress.hide()
        layout.addWidget(self.progress)
        self.statusBar().showMessage("pronto")
        self._correnti: list[Estrazione] = []
        self._worker: OcrWorker | None = None
        self._engine: OcrEngine | None = None
        self.conf: dict = {"sorgente": "bundlato", "url_esterno": "", "preset_id": ""}
        self._aggiorna_bottoni()
        self.aggiorna_intestazione()

    def set_tema(self, nome: str) -> None:
        if nome not in NOMI_TEMI:
            raise ValueError(f"tema ignoto: {nome}")
        self.tema_corrente = nome
        self.setStyleSheet(qss(nome))
        self.btn_tema.setText(f"Tema: {nome}")

    def cambia_tema(self) -> None:
        self.set_tema("scuro" if self.tema_corrente == "chiaro" else "chiaro")
        self.conf["tema"] = self.tema_corrente
        self.aggiorna_intestazione()
        self._ricolora_lista()

    def _ricolora_lista(self) -> None:
        from PySide6.QtGui import QColor

        from locallens.app.tema import TEMI

        t = TEMI[self.tema_corrente]
        for i in range(self.lista.count()):
            item = self.lista.item(i)
            caduta = "cpu-tesseract" in item.text()
            item.setForeground(QColor(t["fallback" if caduta else "success"]))

    def set_engine(self, engine: OcrEngine) -> None:
        self._engine = engine
        self.aggiorna_intestazione()

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
            self.avvia(carica_documento(percorso), engine, documento=percorso)
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

    def _preset_ids_disponibili(self) -> list[str]:
        """Tutti i PresetModello (shipped + utente), col corrente garantito."""
        from locallens.config.percorsi import risorsa
        from locallens.config.presets import elenco_preset
        from locallens.config.settings import percorso_config

        ids = elenco_preset(
            [risorsa("presets"), percorso_config().parent / "presets"]
        )
        corrente = self.conf.get("preset_id", "") or "lighton-ocr-q8_0"
        if corrente not in ids:
            ids = [corrente, *ids]
        return ids

    def _impostazioni(self) -> None:
        dlg = DialogoImpostazioni(preset_ids=self._preset_ids_disponibili())
        dlg.set_sorgente(self.conf.get("sorgente", "bundlato"))
        dlg.set_preset(self.conf.get("preset_id", "") or "lighton-ocr-q8_0")
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

    def avvia(
        self, immagini: list[bytes], engine: OcrEngine, documento: str = ""
    ) -> None:
        """Elabora in background: la GUI resta responsiva (RF8)."""
        import os

        self.nascondi_banner()
        self._correnti = []
        nome = os.path.basename(documento) if documento else f"{len(immagini)} immagini"
        self.doc.setText(nome)
        self.doc.setToolTip(documento or nome)
        self.testo.setPlainText("Elaborazione in corso…")
        self.btn_copia.setEnabled(False)
        self.btn_salva.setEnabled(False)
        self.progress.setValue(0)
        self.progress.show()
        self.btn_annulla.setEnabled(True)
        worker = OcrWorker(
            job_id="doc",
            engine=engine,
            immagini=immagini,
            diario=self._nuovo_diario(documento),
        )
        worker.segnali.pagina.connect(self._on_pagina)
        worker.segnali.finito.connect(self._on_finito)
        worker.segnali.errore.connect(self._on_errore)
        self._worker = worker  # evita GC prima della fine
        QThreadPool.globalInstance().start(worker)

    def _nuovo_diario(self, documento: str):
        """Diario JSONL per l'esecuzione; mai un ostacolo (None se non scrivibile)."""
        try:
            from locallens.core.diario import avvia_job

            return avvia_job(
                None,
                documento=documento,
                sorgente=self.conf.get("sorgente", ""),
                preset_id=self.conf.get("preset_id", ""),
            )
        except OSError:
            return None

    def _on_pagina(self, estrazione, i: int, n: int) -> None:
        self._correnti.append(estrazione)
        self.progress.setMaximum(n)
        self.progress.setValue(i)

    def _on_finito(self, job_id: str) -> None:
        self.progress.hide()
        self.btn_annulla.setEnabled(False)
        self.mostra_estrazioni(self._correnti)
        self._worker = None
        n = len(self._correnti)
        if n:
            base = self.doc.toolTip() or self.doc.text()
            self.doc.setText(f"{base} — {n} pagine")

    def _on_errore(self, job_id: str, messaggio: str) -> None:
        self.progress.hide()
        self.btn_annulla.setEnabled(False)
        self.mostra_banner(f"Errore: {messaggio}")
        self._worker = None
        self._aggiorna_bottoni()

    def set_stato(self, messaggio: str) -> None:
        self.statusBar().showMessage(messaggio)

    def mostra_banner(self, messaggio: str) -> None:
        self.banner.setText(messaggio)
        self.banner.show()

    def nascondi_banner(self) -> None:
        self.banner.hide()

    def mostra_estrazioni(self, estrazioni: list[Estrazione]) -> None:
        from PySide6.QtGui import QColor
        from PySide6.QtWidgets import QListWidgetItem

        from locallens.app.tema import TEMI

        t = TEMI[self.tema_corrente]
        self.lista.clear()
        testi = []
        for e in estrazioni:
            caduta = e.motore_usato == "cpu-tesseract"
            item = QListWidgetItem(f"Pagina {e.pagina_id} • {e.motore_usato} • {tempo_breve(e.ms)}")
            item.setForeground(QColor(t["fallback" if caduta else "success"]))
            self.lista.addItem(item)
            testi.append(f"── Pagina {e.pagina_id} • {e.motore_usato} • {tempo_breve(e.ms)} ──\n{e.testo}")
            if caduta:
                self.mostra_banner(f"Pagina {e.pagina_id} elaborata via CPU (fallback)")
        self.testo.setPlainText("\n\n".join(testi) if testi else TESTO_VUOTO)
        self._aggiorna_bottoni()

    def aggiorna_intestazione(self) -> None:
        """Pill motore in linguaggio umano: '● esterno • lighton-ocr-q8_0'."""
        sorgente = self.conf.get("sorgente", "bundlato")
        preset = self.conf.get("preset_id", "") or "—"
        colori = {
            "esterno": "success",
            "bundlato": "success",
            "nessuno": "fallback",
        }
        from locallens.app.tema import TEMI

        t = TEMI[self.tema_corrente]
        colore = t[colori.get(sorgente, "muted")]
        self.pill.setText(f"<span style='color:{colore}'>●</span> {sorgente} • {preset}")

    def _aggiorna_bottoni(self) -> None:
        ha_testo = bool(self.testo.toPlainText().strip()) and self.testo.toPlainText() != TESTO_VUOTO
        self.btn_copia.setEnabled(ha_testo)
        self.btn_salva.setEnabled(ha_testo)

    def _annulla(self) -> None:
        if self._worker is not None:
            self._worker.annulla()
            self.btn_annulla.setEnabled(False)
            self.mostra_banner("Annullamento richiesto: finisco la Pagina corrente.")

    def copia(self) -> None:
        from PySide6.QtWidgets import QApplication

        QApplication.clipboard().setText(self.testo.toPlainText())

    def salva(self, percorso: str) -> None:
        if not percorso:
            QMessageBox.information(
                self, "Salva", "Scegli un file da dialogo (non in test)."
            )
            return
        with open(percorso, "w", encoding="utf-8") as f:
            f.write(self.testo.toPlainText())

    def _salva_file(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        percorso, _ = QFileDialog.getSaveFileName(
            self, "Salva estrazione", "", "Testo (*.txt)"
        )
        if percorso:
            self.salva(percorso)
