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


def test_avvia_elabora_in_background(qapp):
    from PySide6.QtCore import QCoreApplication, QThreadPool

    from locallens.core.orchestrator import OcrEngine

    w = MainWindow()
    eng = OcrEngine(infer=lambda p, i: (f"t{p}", "cuda"), fallback=lambda p, i: "fb")
    w.avvia([b"a", b"b"], eng)
    assert QThreadPool.globalInstance().waitForDone(5000)
    QCoreApplication.processEvents()
    assert w.lista.count() == 2
    assert w.progress.isHidden()


def test_pulsante_apri_carica_file(qapp, monkeypatch):
    from PySide6.QtCore import QCoreApplication, QThreadPool
    from PySide6.QtWidgets import QFileDialog

    from locallens.core.orchestrator import OcrEngine

    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", lambda *a, **k: ("tests/assets/ocr-test-01.png", "")
    )
    w = MainWindow()
    w.set_engine(OcrEngine(infer=lambda p, i: (f"t{p}", "cuda"), fallback=lambda p, i: "fb"))
    w._apri_file()
    assert QThreadPool.globalInstance().waitForDone(5000)
    QCoreApplication.processEvents()
    assert w.lista.count() == 1


def test_pulsante_incolla(qapp):
    from PySide6.QtCore import QCoreApplication, QThreadPool
    from PySide6.QtGui import QImage
    from PySide6.QtWidgets import QApplication

    from locallens.core.orchestrator import OcrEngine

    img = QImage(40, 20, QImage.Format_RGB888)
    img.fill(0xFFFFFF)
    QApplication.clipboard().setImage(img)
    w = MainWindow()
    w.set_engine(OcrEngine(infer=lambda p, i: ("t", "cuda"), fallback=lambda p, i: "fb"))
    w._da_appunti()
    assert QThreadPool.globalInstance().waitForDone(5000)
    QCoreApplication.processEvents()
    assert w.lista.count() == 1


def test_avvia_mostra_banner_su_errore(qapp):
    from PySide6.QtCore import QCoreApplication, QThreadPool

    from locallens.core.orchestrator import OcrEngine

    eng = OcrEngine(infer=lambda p, i: (f"t{p}", "cuda"), fallback=lambda p, i: "fb")
    eng.submit_document = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
    w = MainWindow()
    w.avvia([b"a"], eng)
    assert QThreadPool.globalInstance().waitForDone(5000)
    QCoreApplication.processEvents()
    assert not w.banner.isHidden()
    assert "boom" in w.banner.text()
