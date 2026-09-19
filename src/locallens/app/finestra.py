"""Finestra principale. Parla solo con core via OcrWorker, mai con backend/URL ( §8)."""

from PySide6.QtCore import Qt, QThreadPool
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
from locallens.app.lingua import SORGENTE_LABELS, t
from locallens.app.tema import NOMI_TEMI, qss
from locallens.app.worker import OcrWorker
from locallens.config.settings import Config, as_dict, salva as salva_impostazioni
from locallens.core.orchestrator import Estrazione, OcrEngine

TESTO_VUOTO = (
    "Apri un Documento (immagine o PDF) per iniziare.\n\n"
    "Sorgenti: file • appunti • screenshot."
)

# Back-compat: _CHIAVE_SORGENTE ora alias single source SORGENTE_LABELS in lingua
_CHIAVE_SORGENTE = SORGENTE_LABELS

# Alias di compatibilità (it) — il codice usa il catalogo via `t`.
ETICHETTE_SORGENTE = {k: t("it", v) for k, v in SORGENTE_LABELS.items()}

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


_MOTORI_LOCALI = {"cuda", "hip", "vulkan", "bundlato", "cpu-llama"}


def etichetta_motore(lingua: str, motore_usato: str, modello_esterno: str = "") -> str:
    """Etichetta comprensibile per la lista Pagine: nasconde i nomi tecnici BackendGpu."""
    if motore_usato == "cpu-tesseract":
        return t(lingua, "motore_cpu")
    if motore_usato == "esterno":
        nome = (modello_esterno or "").strip()
        if nome:
            return nome
        return t(lingua, "motore_esterno_generico")
    if motore_usato in _MOTORI_LOCALI:
        return t(lingua, "motore_locale")
    return motore_usato


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
        self._filtrata: int | None = None
        # Pulsante ripristino vista completa (sopra il testo, visibile solo quando filtrata)
        self.btn_tutte = QPushButton(t("it", "btn_mostra_tutte"))
        self.btn_tutte.setProperty("secondario", "true")
        self.btn_tutte.setMinimumHeight(32)
        self.btn_tutte.hide()
        self.btn_tutte.clicked.connect(lambda: self._mostra_tutte())
        layout_destra.insertWidget(0, self.btn_tutte)
        self.lista.itemClicked.connect(lambda item: self._filtra_per_riga(self.lista.row(item)))

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
        self.conf: dict | Config = {"lingua": "en", "sorgente": "bundlato", "url_esterno": "", "preset_id": ""}  # seam Config: View stores dict for compat, supports Config typed
        self.applica_lingua()

    def _conf_val(self, chiave: str, default: str = "") -> str:
        """Seam Config: legge da dict o Config via helper centralizzato as_dict."""
        return as_dict(self.conf).get(chiave, default)

    def _conf_set(self, chiave: str, valore) -> None:
        """Seam Config: scrittura compatibile con dict e Config frozen (via replace)."""
        if isinstance(self.conf, dict):
            self.conf[chiave] = valore  # type: ignore[index]
        else:
            from dataclasses import fields, replace

            if chiave in {f.name for f in fields(self.conf)}:
                self.conf = replace(self.conf, **{chiave: valore})  # type: ignore[arg-type]
            else:
                d = as_dict(self.conf)
                d[chiave] = valore
                self.conf = d  # type: ignore[assignment]

    def _conf_update(self, valori: dict) -> None:
        """Seam Config: update compatibile con dict e Config frozen (via replace)."""
        if isinstance(self.conf, dict):
            self.conf.update(valori)  # type: ignore[union-attr]
        else:
            from dataclasses import fields, replace

            cfg_fields = {f.name for f in fields(self.conf)}
            filtrati = {k: v for k, v in valori.items() if k in cfg_fields}
            if filtrati:
                self.conf = replace(self.conf, **filtrati)  # type: ignore[arg-type]

    def _lingua(self) -> str:
        return self._conf_val("lingua", "en")

    def applica_lingua(self) -> None:
        """(Ri)imposta tutti i testi statici dal catalogo `lingua.py`."""
        lingua = self._lingua()
        self.btn_apri.setText(t(lingua, "btn_apri"))
        self.btn_incolla.setText(t(lingua, "btn_incolla"))
        self.btn_schermo.setText(t(lingua, "btn_schermo"))
        self.btn_annulla.setText(t(lingua, "btn_annulla"))
        self.btn_copia.setText(t(lingua, "btn_copia"))
        self.btn_salva.setText(t(lingua, "btn_salva"))
        if hasattr(self, "btn_tutte"):
            self.btn_tutte.setText(t(lingua, "btn_mostra_tutte"))
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
            t("en", "status_pronto"),
            t("it", "status_pronto"),
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
        self._conf_set("tema", self.tema_corrente)
        self.aggiorna_intestazione()
        self._ricolora_lista()

    def _ricolora_lista(self) -> None:
        from PySide6.QtGui import QColor

        from locallens.app.tema import TEMI

        colori = TEMI[self.tema_corrente]
        for i in range(self.lista.count()):
            item = self.lista.item(i)
            motore = item.data(Qt.ItemDataRole.UserRole) or ""
            caduta = motore == "cpu-tesseract" or "cpu-tesseract" in item.toolTip()
            item.setForeground(QColor(colori["fallback" if caduta else "success"]))

    def set_engine(self, engine: OcrEngine) -> None:
        self._engine = engine
        self.aggiorna_intestazione()

    def set_ricostruttore(self, fn) -> None:
        """fn(conf) -> (engine, stato, banner). Iniettato da __main__."""
        self._ricostruttore = fn

    def closeEvent(self, evento) -> None:
        """Il token API vive solo in sessione: azzerato alla chiusura."""
        self._conf_set("token_esterno", "")
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
            lingua=self._conf_val("lingua", "en"),
        )
        dlg.set_sorgente(self._conf_val("sorgente", "bundlato"))
        dlg.set_lingua(self._conf_val("lingua", "en"))
        dlg.set_url_esterno(self._conf_val("url_esterno", ""))
        dlg.set_url_gpu_locale(self._conf_val("url_gpu_locale", self._conf_val("url_esterno", "")))
        dlg.set_cloud(
            self._conf_val("token_esterno", ""),
            self._conf_val("modello_esterno", ""),
            self._conf_val("prompt_esterno", ""),
        )
        dlg.set_contesto(
            self._conf_val("lingue_filtro", "it"),
            int(self._conf_val("soglia_righe_loop", "5")),
            bool(self._conf_val("ignora_eco", False)),
        )
        if dlg.exec():
            self._conf_update(dlg.valori())
            conf_dict = as_dict(self.conf)
            nuovo_dict, avviso = normalizza_sorgente_da_conf(conf_dict, self._preset_corrente())
            if isinstance(self.conf, dict):
                self.conf = nuovo_dict
            else:
                from locallens.config.settings import Config

                self.conf = Config.from_dict(nuovo_dict)
            if avviso:
                self.mostra_banner(avviso)
            salva_impostazioni(self.conf)
            self.applica_lingua()
            self.aggiorna_intestazione()
            ric = getattr(self, "_ricostruttore", None)
            if ric is not None:
                engine, stato, banner = ric(self.conf)
            else:
                # use EngineFactory directly when no ricostruttore injected (e.g., tests)
                from locallens.config.settings import Config as _Config

                from locallens.core.fabbrica import EngineFactory

                cfg = self.conf if isinstance(self.conf, _Config) else _Config.from_dict(as_dict(self.conf))
                factory = EngineFactory(cfg)
                engine, stato, banner = factory.rebuild(cfg)
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
        self.lista.clear()
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
                sorgente=self._conf_val("sorgente", ""),
                preset_id=self._conf_val("preset_id", ""),
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
        self._filtrata = None
        if hasattr(self, "btn_tutte"):
            self.btn_tutte.hide()
        self.lista.clear()
        lingua = self._lingua()
        modello_esterno = str(self._conf_val("modello_esterno", "") or "")
        for e in estrazioni:
            caduta = e.motore_usato == "cpu-tesseract"
            etichetta = etichetta_motore(lingua, e.motore_usato, modello_esterno)
            tempo = tempo_breve(e.ms)
            item = QListWidgetItem(
                t(lingua, "riga_pagina", id=e.pagina_id, motore=etichetta, tempo=tempo)
            )
            dettaglio = e.motore_usato
            if e.motore_usato == "esterno" and modello_esterno.strip():
                dettaglio += f" • {modello_esterno.strip()}"
            item.setToolTip(f"{dettaglio} • {tempo}")
            item.setData(Qt.ItemDataRole.UserRole, e.motore_usato)
            item.setForeground(QColor(t_tema["fallback" if caduta else "success"]))
            self.lista.addItem(item)
            if caduta:
                self.mostra_banner(t(lingua, "banner_fallback_cpu", id=e.pagina_id))
        # Output markdown pulito: solo testi, nessuna intestazione Pagina
        if estrazioni:
            corpo = "\n\n".join(e.testo for e in estrazioni)
        else:
            corpo = t(lingua, "testo_vuoto")
        self.testo.setPlainText(corpo)
        self._aggiorna_bottoni()

    def _filtra_per_riga(self, row: int) -> None:
        if row < 0 or row >= len(self._correnti):
            return
        self._filtrata = row
        self.testo.setPlainText(self._correnti[row].testo)
        if hasattr(self, "btn_tutte"):
            self.btn_tutte.show()
        self._aggiorna_bottoni()

    def _mostra_tutte(self) -> None:
        if not self._correnti:
            return
        self._filtrata = None
        self.lista.clearSelection()
        if hasattr(self, "btn_tutte"):
            self.btn_tutte.hide()
        self.testo.setPlainText("\n\n".join(e.testo for e in self._correnti))
        self._aggiorna_bottoni()

    def aggiorna_intestazione(self) -> None:
        """Pill motore in linguaggio umano: '● GPU locale • http://...'."""
        lingua = self._lingua()
        sorgente = self._conf_val("sorgente", "bundlato")
        if sorgente == "bundlato":
            dettaglio = self._conf_val("url_gpu_locale", "") or self._conf_val("url_esterno", "") or "—"
        elif sorgente == "esterno":
            dettaglio = self._conf_val("modello_esterno", "") or self._conf_val("preset_id", "") or "—"
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
        etichetta = t(lingua, SORGENTE_LABELS[sorgente]) if sorgente in SORGENTE_LABELS else sorgente
        self.pill.setText(
            f"<span style='color:{colore}'>●</span> "
            f"{t(lingua, 'pill_formato', etichetta=etichetta, dettaglio=dettaglio)}"
        )

    def _aggiorna_bottoni(self) -> None:
        corrente = self.testo.toPlainText()
        vuoti = {
            TESTO_VUOTO,
            t("en", "testo_vuoto"),
            t("it", "testo_vuoto"),
            t("en", "elaborazione_in_corso"),
            t("it", "elaborazione_in_corso"),
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
        # Default markdown: aggiunge .md se l'utente non ha messo estensione
        from pathlib import Path

        p = Path(percorso)
        if not p.suffix:
            percorso = str(p.with_suffix(".md"))
        with open(percorso, "w", encoding="utf-8") as f:
            f.write(self.testo.toPlainText())

    def _salva_file(self) -> None:
        from pathlib import Path

        from PySide6.QtWidgets import QFileDialog

        # Propone nome del file originale con estensione .md (solo nome, senza percorso)
        suggerito = ""
        base = (self.doc.toolTip() or self.doc.text() or "").strip()
        # Rimuove suffisso " — N pagine" aggiunto dopo l'elaborazione
        base = base.split(" — ")[0].strip()
        if base and base not in (t("it", "nessun_documento"), t("en", "nessun_documento")) and " immagini" not in base and " images" not in base:
            p = Path(base)
            if p.suffix:
                suggerito = p.stem + ".md"
            else:
                suggerito = base + ".md"
        percorso, _ = QFileDialog.getSaveFileName(
            self,
            t(self._lingua(), "dialogo_salva_titolo"),
            suggerito,
            t(self._lingua(), "dialogo_salva_filtro"),
        )
        if percorso:
            self.salva(percorso)
