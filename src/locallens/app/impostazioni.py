"""Sorgente modello (RF10) + avviso privacy su URL non locale (RNF1)."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QWidget,
)

from locallens.app.tema import applica_tavolozza, qss
from locallens.backend.manager import is_url_privata

_AIUTI = {
    "lingue": (
        "Lingue ammesse nel testo trascritto, separate da virgola (es. it,en). "
        "Una Pagina scritta in altre lingue viene scartata e riprocessata con Tesseract."
    ),
    "soglia": (
        "Numero minimo di righe identiche oltre il quale l'output del modello "
        "è considerato un loop degenere. Alzalo su Documenti legittimamente "
        "ripetitivi (verbali, elenchi)."
    ),
    "eco": (
        "Attivalo se le istruzioni di trascrizione sono stampate nel Documento: "
        "evita che la loro presenza faccia scartare una trascrizione valida."
    ),
}


VOCI_SORGENTE = (("GPU locale", "bundlato"), ("esterno", "esterno"), ("nessuno", "nessuno"))


class DialogoImpostazioni(QDialog):
    def __init__(self, parent=None, tema: str = "chiaro", gpu_locale_disponibile: bool = True) -> None:
        super().__init__(parent)
        self.setWindowTitle("Impostazioni LocalLens")
        self.setStyleSheet(qss(tema))  # come la finestra principale (stessi token)
        applica_tavolozza(tema)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, True)
        layout = QFormLayout(self)

        self.sorgente = QComboBox()
        voci = [v for v in VOCI_SORGENTE if v[1] != "bundlato" or gpu_locale_disponibile]
        self.sorgente.addItems([etichetta for etichetta, _ in voci])
        self.sorgente.currentTextChanged.connect(lambda _: self._aggiorna_avviso())
        self.sorgente.currentTextChanged.connect(lambda _: self._aggiorna_viste())
        layout.addRow("Sorgente modello", self.sorgente)

        self.etichetta_url = QLabel("URL server esterno")
        self.url = QLineEdit("http://127.0.0.1:8011")
        self.url.textChanged.connect(lambda _: self._aggiorna_avviso())
        layout.addRow(self.etichetta_url, self.url)

        self.etichetta_token = QLabel("Token API")
        self.token = QLineEdit()
        self.token.setEchoMode(QLineEdit.EchoMode.Password)
        self.token.setPlaceholderText("sk-...")
        layout.addRow(self.etichetta_token, self.token)

        self.etichetta_modello = QLabel("Modello")
        self.modello = QLineEdit()
        self.modello.setPlaceholderText("es. gpt-4o")
        layout.addRow(self.etichetta_modello, self.modello)

        self.etichetta_prompt = QLabel("Prompt")
        self.prompt = QPlainTextEdit("Transcribe the document text exactly. No commentary.")
        self.prompt.setFixedHeight(60)
        layout.addRow(self.etichetta_prompt, self.prompt)

        self.lingue = QLineEdit("it")
        self.lingue.setWhatsThis(_AIUTI["lingue"])
        self.aiuto_lingue_btn, self.aiuto_lingue = self._riga_aiuto(
            layout, "Lingue filtro (it,en)", self.lingue, "lingue"
        )

        self.soglia = QSpinBox()
        self.soglia.setRange(1, 20)
        self.soglia.setValue(5)
        self.soglia.setWhatsThis(_AIUTI["soglia"])
        self.aiuto_soglia_btn, self.aiuto_soglia = self._riga_aiuto(
            layout, "Soglia righe loop", self.soglia, "soglia"
        )

        self.ignora_eco = QCheckBox("Istruzioni stampate nella sorgente")
        self.ignora_eco.setWhatsThis(_AIUTI["eco"])
        self.aiuto_eco_btn, self.aiuto_eco = self._riga_aiuto(
            layout, "Ignora eco prompt", self.ignora_eco, "eco"
        )

        self.avviso = QLabel(
            "Attenzione privacy: l'URL non punta alla rete locale, "
            "immagini e testo lasceranno questa macchina."
        )
        self.avviso.setObjectName("avviso")
        self.avviso.hide()
        layout.addRow(self.avviso)

        bottoni = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        bottoni.accepted.connect(self.accept)
        bottoni.rejected.connect(self.reject)
        layout.addRow(bottoni)
        self._aggiorna_avviso()
        self._aggiorna_viste()

    def set_sorgente(self, valore: str) -> None:
        for etichetta, ident in VOCI_SORGENTE:
            if ident == valore and self.sorgente.findText(etichetta) >= 0:
                self.sorgente.setCurrentText(etichetta)
                return

    def set_cloud(self, token: str = "", modello: str = "", prompt: str = "") -> None:
        self.token.setText(token)
        self.modello.setText(modello)
        if prompt:
            self.prompt.setPlainText(prompt)

    def set_contesto(self, lingue: str = "it", soglia: int = 5, ignora_eco: bool = False) -> None:
        self.lingue.setText(lingue)
        self.soglia.setValue(soglia)
        self.ignora_eco.setChecked(ignora_eco)

    @staticmethod
    def _riga_aiuto(layout, etichetta: str, campo, chiave: str):
        """Riga campo + '?' che espande la spiegazione sotto (collassata di default)."""
        contenitore = QWidget()
        riga = QHBoxLayout(contenitore)
        riga.setContentsMargins(0, 0, 0, 0)
        riga.addWidget(campo)
        bottone = QPushButton("?")
        bottone.setFixedWidth(32)
        bottone.setProperty("secondario", True)
        bottone.setProperty("aiuto", True)
        bottone.setToolTip("Mostra la spiegazione")
        spiega = QLabel(_AIUTI[chiave])
        spiega.setObjectName("suggerimento")
        spiega.setWordWrap(True)
        spiega.hide()
        bottone.clicked.connect(lambda: spiega.setVisible(spiega.isHidden()))
        riga.addWidget(bottone)
        layout.addRow(etichetta, contenitore)
        layout.addRow(spiega)
        return bottone, spiega

    def _aggiorna_viste(self) -> None:
        """Esterno = URL+cloud; nessuno = niente URL né cloud; altre = solo URL."""
        ident = self._id_corrente()
        mostra_url = ident != "nessuno"
        mostra_cloud = ident == "esterno"
        self.etichetta_url.setVisible(mostra_url)
        self.url.setVisible(mostra_url)
        for w in (
            self.etichetta_token, self.token,
            self.etichetta_modello, self.modello,
            self.etichetta_prompt, self.prompt,
        ):
            w.setVisible(mostra_cloud)

    def _id_corrente(self) -> str:
        scelta = self.sorgente.currentText()
        return next(ident for etichetta, ident in VOCI_SORGENTE if etichetta == scelta)

    def _aggiorna_avviso(self) -> None:
        mostra = self.sorgente.currentText() == "esterno" and not is_url_privata(
            self.url.text()
        )
        self.avviso.setVisible(mostra)

    def valori(self) -> dict:
        scelta = self.sorgente.currentText()
        ident = next(ident for etichetta, ident in VOCI_SORGENTE if etichetta == scelta)
        return {
            "sorgente": ident,
            "url_esterno": self.url.text(),
            "token_esterno": self.token.text().strip(),
            "modello_esterno": self.modello.text().strip(),
            "prompt_esterno": self.prompt.toPlainText().strip(),
            "lingue_filtro": self.lingue.text().strip() or "it",
            "soglia_righe_loop": self.soglia.value(),
            "ignora_eco": self.ignora_eco.isChecked(),
        }
