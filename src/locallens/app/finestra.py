"""Finestra principale. Parla solo con core via OcrWorker, mai con backend/URL ( §8)."""

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

from locallens.core.orchestrator import Estrazione


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("LocalLens")
        centrale = QWidget()
        self.setCentralWidget(centrale)
        layout = QVBoxLayout(centrale)

        self.banner = QLabel()
        self.banner.setStyleSheet("background: #fff3cd; padding: 6px;")
        self.banner.hide()
        layout.addWidget(self.banner)

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

        self.progress = QProgressBar()
        self.progress.hide()
        layout.addWidget(self.progress)
        self.statusBar().showMessage("pronto")

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
