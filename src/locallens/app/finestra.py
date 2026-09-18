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
from locallens.app.lingua import t
from locallens.app.tema import NOMI_TEMI, qss
from locallens.app.worker import OcrWorker
from locallens.config.settings import salva as salva_impostazioni
from locallens.core.orchestrator import Estrazione, OcrEngine

TESTO_VUOTO = (
    "Apri un Documento (immagine o PDF) per iniziare.\n\n"
    "Sorgenti: file • appunti • screenshot."
)

_CHIAVE_SORGENTE = {
    "bundlato": "sorgente_bundlato",
    "esterno": "sorgente_esterno",
    "nessuno": "sorgente_nessuno",
}

# Alias di compatibilità (it) — il codice usa il catalogo via `t`.
ETICHETTE_SORGENTE = {k: t("it", v) for k, v in _CHIAVE_SORGENTE.items()}

_CHIAVE_TEMA_NOME = {
    "chiaro": "tema_nome_chiaro",
    "scuro": "tema_nome_scuro",
}


def nome_tema_display(lingua: str, tema: str) -> str:
    """Nome tema solo per display: il config resta chiaro/scuro."""
    return t(lingua, _CHIAVE_TEMA_NOME[tema])


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
        self.applica_lingua()

    def _lingua(self) -> str:
        return self.conf.get("lingua", "it")

    def applica_lingua(self) -> None:
        """(Ri)imposta tutti i testi statici dal catalogo `lingua.py`."""
        lingua = self._lingua()
        self.btn_apri.setText(t(lingua, "btn_apri"))
        self.btn_incolla.setText(t(lingua, "btn_incolla"))
        self.btn_schermo.setText(t(lingua, "btn_schermo"))
        self.btn_annulla.setText(t(lingua, "btn_annulla"))
        self.btn_copia.setText(t(lingua, "btn_copia"))
        self.btn_salva.setText(t(lingua, "btn_salva"))
        self.btn_setup.setText(t(lingua, "btn_impostazioni"))
        self.btn_tema.setText(t(lingua, "btn_tema", nome=nome_tema_display(lingua, self.tema_corrente)))
        if self._correnti:
            self.mostra_estrazioni(list(self._correnti))
        else:
            self.testo.setPlainText(t(lingua, "testo_vuoto"))
        if not self.doc.toolTip():
            self.doc.setText(t(lingua, "nessun_documento"))
        self.progress.setFormat(t(lingua, "progress_formato"))
        if self.statusBar().currentMessage() in (
            t("it", "status_pronto"),
            t("en", "status_pronto"),
        ):
            self.set_stato(t(lingua, "status_pronto"))
        self.aggiorna_intestazione()
        self._aggiorna_bottoni()

    def set_tema(self, nome: str) -> None:
        if nome not in NOMI_TEMI:
            raise ValueError(f"tema ignoto: {nome}")
        from locallens.app.tema import applica_tavolozza

        self.tema_corrente = nome
        self.setStyleSheet(qss(nome))
        applica_tavolozza(nome)
        self.btn_tema.setText(t(self._lingua(), "btn_tema", nome=nome_tema_display(self._lingua(), nome)))

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

    def closeEvent(self, evento) -> None:
        """Il token API vive solo in sessione: azzerato alla chiusura."""
        self.conf["token_esterno"] = ""
        super().closeEvent(evento)

    def _richiedi_engine(self) -> OcrEngine | None:
        if self._engine is None:
            self.mostra_banner(t(self._lingua(), "banner_motore_non_pronto"))
            return None
        return self._engine

    def _apri_file(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        from locallens.app.ingresso import carica_documento

        percorso, _ = QFileDialog.getOpenFileName(
            self,
            t(self._lingua(), "dialogo_apri_titolo"),
            "",
            t(self._lingua(), "dialogo_apri_filtro"),
        )
        if not percorso:
            return
        engine = self._richiedi_engine()
        if engine is None:
            return
        try:
            self.avvia(carica_documento(percorso), engine, documento=percorso)
        except (FileNotFoundError, ValueError) as e:
            self.mostra_banner(t(self._lingua(), "banner_errore", dettaglio=e))

    def _da_appunti(self) -> None:
        from PySide6.QtWidgets import QApplication

        from locallens.app.ingresso import da_appunti

        engine = self._richiedi_engine()
        if engine is None:
            return
        png = da_appunti(QApplication.clipboard())
        if png is None:
            self.mostra_banner(t(self._lingua(), "banner_appunti_vuoti"))
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
            self.mostra_banner(t(self._lingua(), "banner_errore", dettaglio=e))

    def _preset_corrente(self):
        from locallens.config.presets import preset_da_conf
        return preset_da_conf(self.conf)

    def _gpu_locale_disponibile(self) -> bool:
        from locallens.core.fabbrica import disponibilita_gpu_locale_da_conf
        return disponibilita_gpu_locale_da_conf(self.conf, self._preset_corrente())

    def _impostazioni(self) -> None:
        from locallens.core.fabbrica import normalizza_sorgente_da_conf

        dlg = DialogoImpostazioni(
            parent=self,
            tema=self.tema_corrente,
            gpu_locale_disponibile=self._gpu_locale_disponibile(),
            lingua=self.conf.get("lingua", "it"),
        )
        dlg.set_sorgente(self.conf.get("sorgente", "bundlato"))
        dlg.set_lingua(self.conf.get("lingua", "it"))
        dlg.set_url_esterno(self.conf.get("url_esterno", ""))
        dlg.set_url_gpu_locale(self.conf.get("url_gpu_locale", self.conf.get("url_esterno", "")))
        dlg.set_cloud(
            self.conf.get("token_esterno", ""),
            self.conf.get("modello_esterno", ""),
            self.conf.get("prompt_esterno", ""),
        )
        dlg.set_contesto(
            self.conf.get("lingue_filtro", "it"),
            int(self.conf.get("soglia_righe_loop", 5)),
            bool(self.conf.get("ignora_eco", False)),
        )
        if dlg.exec():
            self.conf.update(dlg.valori())
            self.conf, avviso = normalizza_sorgente_da_conf(self.conf, self._preset_corrente())
            if avviso:
                self.mostra_banner(avviso)
            salva_impostazioni(self.conf)
            self.applica_lingua()
            self.aggiorna_intestazione()
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
        nome = (
            os.path.basename(documento)
            if documento
            else t(self._lingua(), "doc_nome_immagini", n=len(immagini))
        )
        self.doc.setText(nome)
        self.doc.setToolTip(documento or nome)
        self.testo.setPlainText(t(self._lingua(), "elaborazione_in_corso"))
        self.btn_copia.setEnabled(False)
        self.btn_salva.setEnabled(False)
        self.progress.setValue(0)
        self.progress.show()
        self.btn_annulla.setEnabled(True)
        diario = self._nuovo_diario(documento)
        job_id = getattr(diario, "job_id", None) or "doc"
        worker = OcrWorker(
            job_id=job_id,
            engine=engine,
            immagini=immagini,
            diario=diario,
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
            self.doc.setText(t(self._lingua(), "doc_titolo_pagine", base=base, n=n))

    def _on_errore(self, job_id: str, messaggio: str) -> None:
        self.progress.hide()
        self.btn_annulla.setEnabled(False)
        self.mostra_banner(t(self._lingua(), "banner_errore", dettaglio=messaggio))
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

        t_tema = TEMI[self.tema_corrente]
        self._correnti = list(estrazioni)
        self.lista.clear()
        testi = []
        lingua = self._lingua()
        for e in estrazioni:
            caduta = e.motore_usato == "cpu-tesseract"
            item = QListWidgetItem(
                t(lingua, "riga_pagina", id=e.pagina_id, motore=e.motore_usato, tempo=tempo_breve(e.ms))
            )
            item.setForeground(QColor(t_tema["fallback" if caduta else "success"]))
            self.lista.addItem(item)
            testi.append(
                t(
                    lingua,
                    "blocco_pagina",
                    id=e.pagina_id,
                    motore=e.motore_usato,
                    tempo=tempo_breve(e.ms),
                    testo=e.testo,
                )
            )
            if caduta:
                self.mostra_banner(t(lingua, "banner_fallback_cpu", id=e.pagina_id))
        self.testo.setPlainText("\n\n".join(testi) if testi else t(lingua, "testo_vuoto"))
        self._aggiorna_bottoni()

    def aggiorna_intestazione(self) -> None:
        """Pill motore in linguaggio umano: '● GPU locale • http://...'."""
        lingua = self._lingua()
        sorgente = self.conf.get("sorgente", "bundlato")
        if sorgente == "bundlato":
            dettaglio = self.conf.get("url_gpu_locale") or self.conf.get("url_esterno", "") or "—"
        elif sorgente == "esterno":
            dettaglio = self.conf.get("modello_esterno", "") or self.conf.get("preset_id", "") or "—"
        else:
            dettaglio = t(lingua, "dettaglio_solo_cpu")
        colori = {
            "esterno": "success",
            "bundlato": "success",
            "nessuno": "fallback",
        }
        from locallens.app.tema import TEMI

        t_tema = TEMI[self.tema_corrente]
        colore = t_tema[colori.get(sorgente, "muted")]
        etichetta = t(lingua, _CHIAVE_SORGENTE[sorgente]) if sorgente in _CHIAVE_SORGENTE else sorgente
        self.pill.setText(
            f"<span style='color:{colore}'>●</span> "
            f"{t(lingua, 'pill_formato', etichetta=etichetta, dettaglio=dettaglio)}"
        )

    def _aggiorna_bottoni(self) -> None:
        corrente = self.testo.toPlainText()
        vuoti = {
            TESTO_VUOTO,
            t("it", "testo_vuoto"),
            t("en", "testo_vuoto"),
            t("it", "elaborazione_in_corso"),
            t("en", "elaborazione_in_corso"),
        }
        ha_testo = bool(corrente.strip()) and corrente not in vuoti
        self.btn_copia.setEnabled(ha_testo)
        self.btn_salva.setEnabled(ha_testo)

    def _annulla(self) -> None:
        if self._worker is not None:
            self._worker.annulla()
            self.btn_annulla.setEnabled(False)
            self.mostra_banner(t(self._lingua(), "banner_annullamento"))

    def copia(self) -> None:
        from PySide6.QtWidgets import QApplication

        QApplication.clipboard().setText(self.testo.toPlainText())

    def salva(self, percorso: str) -> None:
        if not percorso:
            QMessageBox.information(
                self,
                t(self._lingua(), "salva_titolo"),
                t(self._lingua(), "salva_messaggio"),
            )
            return
        with open(percorso, "w", encoding="utf-8") as f:
            f.write(self.testo.toPlainText())

    def _salva_file(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        percorso, _ = QFileDialog.getSaveFileName(
            self,
            t(self._lingua(), "dialogo_salva_titolo"),
            "",
            t(self._lingua(), "dialogo_salva_filtro"),
        )
        if percorso:
            self.salva(percorso)
