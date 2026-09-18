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

from locallens.app.lingua import LINGUE, t
from locallens.app.tema import applica_tavolozza, qss
from locallens.core.rete import is_url_privata

_ID_SORGENTI = ("bundlato", "esterno", "nessuno")
_CHIAVE_SORGENTE = {"bundlato": "sorgente_bundlato", "esterno": "sorgente_esterno", "nessuno": "sorgente_nessuno"}

_ID_LINGUE = ("it", "en")


class DialogoImpostazioni(QDialog):
    def __init__(
        self, parent=None, tema: str = "chiaro", gpu_locale_disponibile: bool = True,
        lingua: str = "it",
    ) -> None:
        super().__init__(parent)
        if lingua not in LINGUE:
            lingua = "it"
        self._lingua = lingua
        self.setWindowTitle(t(lingua, "dlg_impostazioni_titolo"))
        self.setStyleSheet(qss(tema))  # come la finestra principale (stessi token)
        applica_tavolozza(tema)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, True)  # type: ignore[attr-defined]  # stub: enum spostato in Qt.WindowType, a runtime ancora esposto su Qt
        layout = QFormLayout(self)

        self.etichetta_lingua = QLabel(t(lingua, "etichetta_lingua"))
        self.selettore_lingua = QComboBox()
        self.selettore_lingua.addItems(
            [t(lingua, "lingua_nome_it"), t(lingua, "lingua_nome_en")]
        )
        self.selettore_lingua.setCurrentIndex(_ID_LINGUE.index(self._lingua))
        layout.addRow(self.etichetta_lingua, self.selettore_lingua)

        self.sorgente = QComboBox()
        self._sorgente_ids = [
            ident for ident in _ID_SORGENTI
            if ident != "bundlato" or gpu_locale_disponibile
        ]
        self.sorgente.addItems([t(lingua, _CHIAVE_SORGENTE[i]) for i in self._sorgente_ids])
        self.sorgente.currentTextChanged.connect(lambda _: self._aggiorna_avviso())
        self.sorgente.currentTextChanged.connect(lambda _: self._aggiorna_viste())
        layout.addRow(t(lingua, "etichetta_sorgente"), self.sorgente)

        self.etichetta_url = QLabel(t(lingua, "etichetta_url"))
        self.url = QLineEdit("http://127.0.0.1:8011")
        self.url.textChanged.connect(lambda _: self._aggiorna_avviso())
        layout.addRow(self.etichetta_url, self.url)
        self._url_memoria = {"bundlato": self.url.text(), "esterno": self.url.text()}
        self._opzione_precedente = self._id_corrente()

        self.etichetta_token = QLabel(t(lingua, "etichetta_token"))
        self.token = QLineEdit()
        self.token.setEchoMode(QLineEdit.EchoMode.Password)
        self.token.setPlaceholderText(t(lingua, "token_placeholder"))
        self.token.setToolTip(t(lingua, "token_tooltip"))
        layout.addRow(self.etichetta_token, self.token)

        self.etichetta_modello = QLabel(t(lingua, "etichetta_modello"))
        self.modello = QLineEdit()
        self.modello.setPlaceholderText("es. gpt-4o")
        layout.addRow(self.etichetta_modello, self.modello)

        self.etichetta_prompt = QLabel(t(lingua, "etichetta_prompt"))
        self.prompt = QPlainTextEdit("Transcribe the document text exactly. No commentary.")
        self.prompt.setFixedHeight(60)
        layout.addRow(self.etichetta_prompt, self.prompt)

        self.lingue = QLineEdit("it")
        self.lingue.setWhatsThis(t(lingua, "aiuto_lingue"))
        self.aiuto_lingue_btn, self.aiuto_lingue = self._riga_aiuto(
            layout, t(lingua, "etichetta_lingue"), self.lingue, "lingue"
        )

        self.soglia = QSpinBox()
        self.soglia.setRange(1, 20)
        self.soglia.setValue(5)
        self.soglia.setWhatsThis(t(lingua, "aiuto_soglia"))
        self.aiuto_soglia_btn, self.aiuto_soglia = self._riga_aiuto(
            layout, t(lingua, "etichetta_soglia"), self.soglia, "soglia"
        )

        self.ignora_eco = QCheckBox(t(lingua, "checkbox_istruzioni"))
        self.ignora_eco.setWhatsThis(t(lingua, "aiuto_eco"))
        self.aiuto_eco_btn, self.aiuto_eco = self._riga_aiuto(
            layout, t(lingua, "etichetta_ignora_eco"), self.ignora_eco, "eco"
        )

        self.avviso = QLabel(t(lingua, "avviso_privacy_esterno"))
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
        if valore in self._sorgente_ids:
            self.sorgente.setCurrentIndex(self._sorgente_ids.index(valore))

    def set_lingua(self, valore: str) -> None:
        if valore not in LINGUE:
            return
        self._lingua = valore
        self.selettore_lingua.setCurrentIndex(_ID_LINGUE.index(valore))

    def set_url_esterno(self, valore: str) -> None:
        self._url_memoria["esterno"] = valore
        if self._id_corrente() == "esterno":
            self.url.setText(valore)

    def set_url_gpu_locale(self, valore: str) -> None:
        self._url_memoria["bundlato"] = valore
        if self._id_corrente() == "bundlato":
            self.url.setText(valore)

    def set_cloud(self, token: str = "", modello: str = "", prompt: str = "") -> None:
        self.token.setPlaceholderText(t(self._lingua, "token_placeholder"))
        self.token.setToolTip(t(self._lingua, "token_tooltip"))
        self.token.setText(token)
        self.modello.setText(modello)
        if prompt:
            self.prompt.setPlainText(prompt)

    def set_contesto(self, lingue: str = "it", soglia: int = 5, ignora_eco: bool = False) -> None:
        self.lingue.setText(lingue)
        self.soglia.setValue(soglia)
        self.ignora_eco.setChecked(ignora_eco)

    def _riga_aiuto(self, layout, etichetta: str, campo, chiave: str):
        """Riga campo + '?' che espande la spiegazione sotto (collassata di default)."""
        contenitore = QWidget()
        riga = QHBoxLayout(contenitore)
        riga.setContentsMargins(0, 0, 0, 0)
        riga.addWidget(campo)
        bottone = QPushButton("?")
        bottone.setFixedWidth(32)
        bottone.setProperty("secondario", True)
        bottone.setProperty("aiuto", True)
        bottone.setToolTip(t(self._lingua, "tooltip_aiuto"))
        spiega = QLabel(t(self._lingua, f"aiuto_{chiave}"))
        spiega.setObjectName("suggerimento")
        spiega.setWordWrap(True)
        spiega.hide()
        bottone.clicked.connect(lambda: spiega.setVisible(spiega.isHidden()))
        riga.addWidget(bottone)
        layout.addRow(etichetta, contenitore)
        layout.addRow(spiega)
        return bottone, spiega

    def _aggiorna_viste(self) -> None:
        """Esterno = URL+cloud; nessuno = niente URL né cloud; altre = solo URL.

        Il campo URL ha una memoria per opzione: cambiando voce il valore
        corrente viene parcheggiato e ricaricato l'ultimo della nuova voce.
        """
        if self._opzione_precedente in self._url_memoria:
            self._url_memoria[self._opzione_precedente] = self.url.text()
        ident = self._id_corrente()
        self._opzione_precedente = ident
        if ident in self._url_memoria:
            self.url.setText(self._url_memoria[ident])
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
        return self._sorgente_ids[self.sorgente.currentIndex()]

    def _aggiorna_avviso(self) -> None:
        mostra = self._id_corrente() == "esterno" and not is_url_privata(
            self.url.text()
        )
        self.avviso.setVisible(mostra)

    def valori(self) -> dict:
        ident = self._id_corrente()
        if ident in self._url_memoria:
            self._url_memoria[ident] = self.url.text()
        return {
            "sorgente": ident,
            "url_esterno": self._url_memoria["esterno"],
            "url_gpu_locale": self._url_memoria["bundlato"],
            "token_esterno": self.token.text().strip(),
            "modello_esterno": self.modello.text().strip(),
            "prompt_esterno": self.prompt.toPlainText().strip(),
            "lingue_filtro": self.lingue.text().strip() or "it",
            "soglia_righe_loop": self.soglia.value(),
            "ignora_eco": self.ignora_eco.isChecked(),
            "lingua": _ID_LINGUE[self.selettore_lingua.currentIndex()],
        }
