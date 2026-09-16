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


@pytest.fixture(autouse=True)
def _home_isolata(tmp_path, monkeypatch):
    """Il Diario di avvia() non deve sporcare ~/.config reale."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("APPDATA", str(tmp_path))


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


def test_layout_tutto_schermo_bottoni_compatti(qapp):
    w = MainWindow()
    assert w.minimumWidth() >= 900
    assert w.minimumHeight() >= 600
    w.resize(1920, 1080)
    w.show()
    w.mostra_estrazioni(_estrazioni())
    # Bottoni inferiori: riempiono la larghezza, altezza touch-friendly, niente spazio vuoto a destra
    assert 200 < w.btn_apri.width() < 600
    assert 200 < w.btn_salva.width() < 600
    assert w.btn_apri.minimumHeight() >= 40
    assert w.btn_salva.minimumHeight() >= 40
    assert abs(w.btn_apri.width() - w.btn_incolla.width()) < 60
    assert abs(w.btn_copia.width() - w.btn_salva.width()) < 60
    assert w.lista.width() < 600
    w.close()
    lay = w.centralWidget().layout()
    assert lay.stretch(2) == 1  # corpo assorbe lo spazio verticale


def test_banner_non_si_stira_in_verticale(qapp):
    from PySide6.QtWidgets import QSizePolicy

    w = MainWindow()
    assert w.banner.sizePolicy().verticalPolicy() == QSizePolicy.Policy.Maximum


def test_lista_con_badge_motore_e_testo(qapp):
    w = MainWindow()
    w.mostra_estrazioni(_estrazioni())
    assert w.lista.count() == 2
    assert "cuda •" in w.lista.item(0).text()
    assert "cpu-tesseract •" in w.lista.item(1).text()
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


def test_pulsante_salva_apre_dialogo_e_scrive(qapp, monkeypatch, tmp_path):
    from PySide6.QtWidgets import QFileDialog

    dest = tmp_path / "salvato.txt"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", lambda *a, **k: (str(dest), "")
    )
    w = MainWindow()
    w.mostra_estrazioni(_estrazioni())
    w.btn_salva.click()
    assert "riga due" in dest.read_text()


def test_tempo_breve_ore_umane():
    from locallens.app.finestra import TESTO_VUOTO, tempo_breve

    assert tempo_breve(51917) == "52 s"
    assert tempo_breve(800) == "800 ms"
    assert "Apri un Documento" in TESTO_VUOTO


def test_intestazione_mostra_sorgente_e_preset(qapp):
    w = MainWindow()
    w.conf = {"sorgente": "esterno", "url_esterno": "", "preset_id": "lighton-ocr-q8_0"}
    w.aggiorna_intestazione()
    assert w.titolo.text() == "LocalLens"
    assert "esterno" in w.pill.text()
    assert "lighton-ocr-q8_0" in w.pill.text()


def test_stato_vuoto_e_bottoni_disabilitati(qapp):
    w = MainWindow()
    assert "Apri un Documento" in w.testo.toPlainText()
    assert not w.btn_copia.isEnabled()
    assert not w.btn_salva.isEnabled()
    assert not w.btn_annulla.isEnabled()


def test_mostra_estrazioni_tempi_umani_e_bottoni(qapp):
    w = MainWindow()
    w.mostra_estrazioni(_estrazioni())
    assert "100 ms" in w.lista.item(0).text()
    assert "200 ms" in w.lista.item(1).text()
    assert w.btn_copia.isEnabled()
    assert w.btn_salva.isEnabled()


def test_annulla_chiama_worker(qapp):
    chiamate = []

    class WorkerFinto:
        def annulla(self):
            chiamate.append(True)

    w = MainWindow()
    w._worker = WorkerFinto()
    w.btn_annulla.setEnabled(True)
    w.btn_annulla.click()
    assert chiamate == [True]
    assert not w.btn_annulla.isEnabled()


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


def test_preset_ids_elenca_tutti_gli_shipped(qapp):
    w = MainWindow()
    w.conf = {"sorgente": "esterno", "url_esterno": "", "preset_id": "glm-ocr-q8_0"}
    ids = w._preset_ids_disponibili()
    assert "lighton-ocr-q8_0" in ids
    assert "glm-ocr-q8_0" in ids


def test_impostazioni_ricostruiscono_engine(qapp, monkeypatch, tmp_path):
    from locallens.app import finestra as mod_finestra

    viste = {}

    class DialogoFinto:
        def __init__(self, preset_ids=None, parent=None):
            self.url = type("U", (), {"setText": lambda self, t: None})()

        def set_sorgente(self, valore):
            pass

        def set_preset(self, valore):
            pass

        def exec(self):
            return True

        def valori(self):
            return {"sorgente": "nessuno", "url_esterno": "", "preset_id": "glm-ocr-q8_0"}

    monkeypatch.setattr(mod_finestra, "DialogoImpostazioni", DialogoFinto)
    monkeypatch.setattr(
        mod_finestra, "salva_impostazioni", lambda conf: viste.update(conf=conf)
    )
    w = MainWindow()
    w.set_ricostruttore(lambda conf: viste.update(ricostrutito=True) or ("ENG", "stato-x", ""))
    w._impostazioni()
    assert viste["conf"]["sorgente"] == "nessuno"
    assert viste["ricostrutito"] is True
    assert "stato-x" in w.statusBar().currentMessage()


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
