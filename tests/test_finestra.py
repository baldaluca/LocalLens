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
    assert "Local GPU •" in w.lista.item(0).text()
    assert "cuda" in w.lista.item(0).toolTip()
    assert w.lista.item(1).text().endswith("CPU • 200 ms") or "CPU •" in w.lista.item(1).text()
    assert "cpu-tesseract" in w.lista.item(1).toolTip()
    assert "riga uno" in w.testo.toPlainText()
    assert "riga due" in w.testo.toPlainText()


def test_lista_esterna_mostra_nome_modello(qapp):
    w = MainWindow()
    w.conf["modello_esterno"] = "gpt-4o-mini"
    from locallens.core.orchestrator import Estrazione

    w.mostra_estrazioni([Estrazione(pagina_id=1, testo="ciao", motore_usato="esterno", ms=3000)])
    assert "gpt-4o-mini" in w.lista.item(0).text()
    assert "esterno" in w.lista.item(0).toolTip()


def test_lista_esterna_senza_modello_mostra_server_esterno(qapp):
    w = MainWindow()
    w.conf["modello_esterno"] = ""
    from locallens.core.orchestrator import Estrazione

    w.mostra_estrazioni([Estrazione(pagina_id=1, testo="ciao", motore_usato="esterno", ms=3000)])
    assert "External server" in w.lista.item(0).text()


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


def test_intestazione_mostra_modello_cloud(qapp):
    w = MainWindow()
    w.conf = {"sorgente": "esterno", "url_esterno": "", "modello_esterno": "vision-x", "preset_id": "lighton-ocr-q8_0"}
    w.aggiorna_intestazione()
    assert w.titolo.text() == "LocalLens"
    assert "vision-x" in w.pill.text()
    assert "lighton-ocr-q8_0" not in w.pill.text()


def test_stato_vuoto_e_bottoni_disabilitati(qapp):
    w = MainWindow()
    assert "Open a Document" in w.testo.toPlainText()
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


def test_impostazioni_ricostruiscono_engine(qapp, monkeypatch, tmp_path):
    from locallens.app import finestra as mod_finestra

    viste = {}

    class DialogoFinto:
        def __init__(self, parent=None, tema="chiaro", gpu_locale_disponibile=True, **k):
            self.url = type("U", (), {"setText": lambda self, t: None})()

        def set_sorgente(self, valore):
            pass

        def set_lingua(self, valore):
            pass

        def set_url_esterno(self, valore):
            pass

        def set_url_gpu_locale(self, valore):
            pass

        def set_contesto(self, lingue="it", soglia=5, ignora_eco=False):
            pass

        def set_cloud(self, token="", modello="", prompt=""):
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


def test_avvia_usa_job_id_del_diario(qapp, monkeypatch):
    from types import SimpleNamespace

    from PySide6.QtCore import QCoreApplication, QThreadPool

    from locallens.app import finestra as mod_finestra
    from locallens.core.orchestrator import OcrEngine

    catturati: dict = {}

    Reale = mod_finestra.OcrWorker

    def fabbrica(job_id, engine, immagini, diario):
        catturati["job_id"] = job_id
        catturati["diario"] = diario
        return Reale(job_id=job_id, engine=engine, immagini=immagini, diario=diario)

    monkeypatch.setattr(mod_finestra, "OcrWorker", fabbrica)
    diario = SimpleNamespace(
        job_id="jid-diario-1",
        registra_pagina=lambda *a, **k: None,
        chiudi=lambda *a, **k: None,
    )
    monkeypatch.setattr(MainWindow, "_nuovo_diario", lambda self, documento="": diario)
    w = MainWindow()
    eng = OcrEngine(infer=lambda p, i: (f"t{p}", "cuda"), fallback=lambda p, i: "fb")
    finiti: list = []
    orig_finito = w._on_finito
    w._on_finito = lambda jid: (finiti.append(jid), orig_finito(jid))
    w.avvia([b"a"], eng)
    assert QThreadPool.globalInstance().waitForDone(5000)
    QCoreApplication.processEvents()
    assert catturati["job_id"] == "jid-diario-1"
    assert finiti == ["jid-diario-1"]


def test_avvia_errore_riporta_job_id_del_diario(qapp, monkeypatch):
    from types import SimpleNamespace

    from PySide6.QtCore import QCoreApplication, QThreadPool

    from locallens.app import finestra as mod_finestra
    from locallens.core.orchestrator import OcrEngine

    catturati: dict = {}
    Reale = mod_finestra.OcrWorker

    def fabbrica(job_id, engine, immagini, diario):
        catturati["job_id"] = job_id
        return Reale(job_id=job_id, engine=engine, immagini=immagini, diario=diario)

    monkeypatch.setattr(mod_finestra, "OcrWorker", fabbrica)
    diario = SimpleNamespace(
        job_id="jid-errore-9",
        registra_pagina=lambda *a, **k: None,
        chiudi=lambda *a, **k: None,
    )
    monkeypatch.setattr(MainWindow, "_nuovo_diario", lambda self, documento="": diario)
    w = MainWindow()
    eng = OcrEngine(infer=lambda p, i: (f"t{p}", "cuda"), fallback=lambda p, i: "fb")
    eng.submit_document = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom-x"))
    errori: list = []
    orig_errore = w._on_errore
    w._on_errore = lambda jid, msg: (errori.append((jid, msg)), orig_errore(jid, msg))
    w.avvia([b"a"], eng)
    assert QThreadPool.globalInstance().waitForDone(5000)
    QCoreApplication.processEvents()
    assert catturati["job_id"] == "jid-errore-9"
    assert errori and errori[0][0] == "jid-errore-9"


def test_avvia_fallback_doc_senza_diario(qapp, monkeypatch):
    from PySide6.QtCore import QCoreApplication, QThreadPool

    from locallens.app import finestra as mod_finestra
    from locallens.core.orchestrator import OcrEngine

    catturati: dict = {}
    Reale = mod_finestra.OcrWorker

    def fabbrica(job_id, engine, immagini, diario):
        catturati["job_id"] = job_id
        return Reale(job_id=job_id, engine=engine, immagini=immagini, diario=diario)

    monkeypatch.setattr(mod_finestra, "OcrWorker", fabbrica)
    monkeypatch.setattr(MainWindow, "_nuovo_diario", lambda self, documento="": None)
    w = MainWindow()
    eng = OcrEngine(infer=lambda p, i: (f"t{p}", "cuda"), fallback=lambda p, i: "fb")
    w.avvia([b"a"], eng)
    assert QThreadPool.globalInstance().waitForDone(5000)
    QCoreApplication.processEvents()
    assert catturati["job_id"] == "doc"


def test_pill_mostra_gpu_locale(qapp):
    from locallens.app.finestra import ETICHETTE_SORGENTE, MainWindow

    assert ETICHETTE_SORGENTE["bundlato"] == "GPU locale"
    w = MainWindow()
    w.conf.update({"sorgente": "bundlato", "url_esterno": "http://127.0.0.1:10000", "lingua": "en"})
    w.aggiorna_intestazione()
    assert "Local GPU" in w.pill.text()
    assert "10000" in w.pill.text()


def test_chiusura_pulisce_token(qapp):
    from locallens.app.finestra import MainWindow

    w = MainWindow()
    w.conf["token_esterno"] = "tk-segreto"
    w.close()
    assert w.conf.get("token_esterno", "") == ""


def test_applica_lingua_commuta_pulsanti_en_it(qapp):
    from locallens.app.lingua import t

    w = MainWindow()
    w.conf["lingua"] = "en"
    w.applica_lingua()
    assert w.btn_apri.text() == t("en", "btn_apri")
    assert w.btn_incolla.text() == t("en", "btn_incolla")
    assert w.btn_schermo.text() == t("en", "btn_schermo")
    assert w.btn_annulla.text() == t("en", "btn_annulla")
    assert w.btn_copia.text() == t("en", "btn_copia")
    assert w.btn_salva.text() == t("en", "btn_salva")
    assert w.btn_setup.text() == t("en", "btn_impostazioni")
    assert w.btn_tema.text() == t("en", "btn_tema", nome=t("en", "tema_nome_chiaro"))
    assert w.testo.toPlainText() == t("en", "testo_vuoto")
    assert w.doc.text() == t("en", "nessun_documento")
    assert w.progress.format() == t("en", "progress_formato")
    assert w.statusBar().currentMessage() == t("en", "status_pronto")
    w.conf["lingua"] = "it"
    w.applica_lingua()
    assert w.btn_apri.text() == t("it", "btn_apri")
    assert w.btn_setup.text() == t("it", "btn_impostazioni")
    assert w.btn_tema.text() == t("it", "btn_tema", nome=t("it", "tema_nome_chiaro"))
    assert w.testo.toPlainText() == t("it", "testo_vuoto")


def test_tema_nome_display_en_e_config_invariato(qapp):
    from locallens.app.lingua import t

    w = MainWindow()
    w.conf["lingua"] = "en"
    w.applica_lingua()
    assert w.btn_tema.text() == t("en", "btn_tema", nome=t("en", "tema_nome_chiaro"))
    w.cambia_tema()
    assert w.tema_corrente == "scuro"
    assert w.conf["tema"] == "scuro"
    assert w.btn_tema.text() == t("en", "btn_tema", nome=t("en", "tema_nome_scuro"))
    w.conf["lingua"] = "it"
    w.applica_lingua()
    assert w.btn_tema.text() == t("it", "btn_tema", nome=t("it", "tema_nome_scuro"))


def test_applica_lingua_pill_inglese(qapp):
    from locallens.app.lingua import t

    w = MainWindow()
    w.conf.update(
        {"sorgente": "bundlato", "url_esterno": "http://127.0.0.1:10000", "lingua": "en"}
    )
    w.applica_lingua()
    assert t("en", "sorgente_bundlato") in w.pill.text()
    assert "10000" in w.pill.text()


def test_applica_lingua_ritraduce_lista(qapp):
    from locallens.app.lingua import t

    w = MainWindow()
    w.mostra_estrazioni(_estrazioni())
    w.conf["lingua"] = "en"
    w.applica_lingua()
    assert "Page 1" in w.lista.item(0).text()
    assert "riga due" in w.testo.toPlainText()
    assert "## Page" not in w.testo.toPlainText()
    assert "GPU" not in w.testo.toPlainText()
    assert "Local GPU" not in w.testo.toPlainText()
    assert t("en", "testo_vuoto") not in w.testo.toPlainText()


def test_banner_runtime_in_inglese(qapp):
    from locallens.app.lingua import t

    w = MainWindow()
    w.conf["lingua"] = "en"
    w._engine = None
    assert w._richiedi_engine() is None
    assert w.banner.text() == t("en", "banner_motore_non_pronto")

    class WorkerFinto:
        def annulla(self):
            pass

    w._worker = WorkerFinto()
    w.btn_annulla.setEnabled(True)
    w._annulla()
    assert w.banner.text() == t("en", "banner_annullamento")
    w.mostra_estrazioni(_estrazioni())
    assert w.banner.text() == t("en", "banner_fallback_cpu", id=2)


def test_avvia_pulisce_lista_pagine_precedenti(qapp, monkeypatch):
    from locallens.app import finestra as F
    from locallens.app.finestra import MainWindow

    monkeypatch.setattr(F.QThreadPool, "globalInstance", lambda: type("P", (), {"start": lambda self, w: None})())
    w = MainWindow()
    w.lista.addItem("Pagina 1 • bundlato • 37 s")
    w.avvia([b"x"], engine=object(), documento="nuovo.pdf")
    assert w.lista.count() == 0
