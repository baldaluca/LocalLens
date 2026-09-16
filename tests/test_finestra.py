"""RED: MainWindow. RF5 (copia/salva), RF7 (badge motore), banner fallback."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from locallens.app.finestra import MainWindow
from locallens.core.orchestrator import Estrazione


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def _estrazioni():
    return [
        Estrazione(pagina_id=1, testo="riga uno", motore_usato="cuda", ms=100),
        Estrazione(pagina_id=2, testo="riga due", motore_usato="cpu-tesseract", ms=200),
    ]


def test_stato_e_banner(qapp):
    w = MainWindow()
    w.set_stato("cuda • 4096 MB • glm-ocr-q8_0")
    assert "cuda" in w.statusBar().currentMessage()
    assert w.banner.isHidden()
    w.mostra_banner("Pagina 2 via CPU (OOM)")
    assert not w.banner.isHidden()
    assert "CPU" in w.banner.text()
    w.nascondi_banner()
    assert w.banner.isHidden()


def test_lista_con_badge_motore_e_testo(qapp):
    w = MainWindow()
    w.mostra_estrazioni(_estrazioni())
    assert w.lista.count() == 2
    assert "[cuda]" in w.lista.item(0).text()
    assert "[cpu-tesseract]" in w.lista.item(1).text()
    assert "riga uno" in w.testo.toPlainText()
    assert "riga due" in w.testo.toPlainText()


def test_copia_negli_appunti(qapp):
    w = MainWindow()
    w.mostra_estrazioni(_estrazioni())
    w.copia()
    assert "riga uno" in QApplication.clipboard().text()


def test_salva_su_file(qapp, tmp_path):
    w = MainWindow()
    w.mostra_estrazioni(_estrazioni())
    dest = tmp_path / "out.txt"
    w.salva(str(dest))
    assert "riga due" in dest.read_text()
