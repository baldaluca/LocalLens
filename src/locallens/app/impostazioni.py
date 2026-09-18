"""Sorgente modello (RF10) + avviso privacy su URL non locale (RNF1)."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
)

from locallens.app.tema import qss
from locallens.backend.manager import is_url_privata


class DialogoImpostazioni(QDialog):
    def __init__(self, preset_ids: list[str], parent=None, tema: str = "chiaro") -> None:
        super().__init__(parent)
        self.setWindowTitle("Impostazioni LocalLens")
        self.setStyleSheet(qss(tema))  # come la finestra principale (stessi token)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, True)
        layout = QFormLayout(self)

        self.sorgente = QComboBox()
        self.sorgente.addItems(["bundlato", "esterno", "nessuno"])
        self.sorgente.currentTextChanged.connect(lambda _: self._aggiorna_avviso())
        layout.addRow("Sorgente modello", self.sorgente)

        self.url = QLineEdit("http://127.0.0.1:8011")
        self.url.textChanged.connect(lambda _: self._aggiorna_avviso())
        layout.addRow("URL server esterno", self.url)

        self.preset = QComboBox()
        self.preset.addItems(preset_ids)
        layout.addRow("Preset (auto se invariato)", self.preset)

        self.lingue = QLineEdit("it")
        self.lingue.setWhatsThis(
            "Lingue ammesse nel testo trascritto, separate da virgola (es. it,en). "
            "Una Pagina scritta in altre lingue viene scartata e riprocessata con Tesseract."
        )
        layout.addRow("Lingue filtro (it,en)", self.lingue)

        self.soglia = QSpinBox()
        self.soglia.setRange(1, 20)
        self.soglia.setValue(5)
        self.soglia.setWhatsThis(
            "Numero minimo di righe identiche oltre il quale l'output del modello "
            "è considerato un loop degenere. Alzalo su Documenti legittimamente "
            "ripetitivi (verbali, elenchi)."
        )
        layout.addRow("Soglia righe loop", self.soglia)

        self.ignora_eco = QCheckBox("Istruzioni stampate nella sorgente")
        self.ignora_eco.setWhatsThis(
            "Attivalo se le istruzioni di trascrizione sono stampate nel Documento: "
            "evita che la loro presenza faccia scartare una trascrizione valida."
        )
        layout.addRow("Ignora eco prompt", self.ignora_eco)

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

    def set_sorgente(self, valore: str) -> None:
        self.sorgente.setCurrentText(valore)

    def set_preset(self, preset_id: str) -> None:
        self.preset.setCurrentText(preset_id)

    def set_contesto(self, lingue: str = "it", soglia: int = 5, ignora_eco: bool = False) -> None:
        self.lingue.setText(lingue)
        self.soglia.setValue(soglia)
        self.ignora_eco.setChecked(ignora_eco)

    def _aggiorna_avviso(self) -> None:
        mostra = self.sorgente.currentText() == "esterno" and not is_url_privata(
            self.url.text()
        )
        self.avviso.setVisible(mostra)

    def valori(self) -> dict:
        return {
            "sorgente": self.sorgente.currentText(),
            "url_esterno": self.url.text(),
            "preset_id": self.preset.currentText(),
            "lingue_filtro": self.lingue.text().strip() or "it",
            "soglia_righe_loop": self.soglia.value(),
            "ignora_eco": self.ignora_eco.isChecked(),
        }
