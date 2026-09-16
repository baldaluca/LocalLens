"""RED: worker asincrono. GUI non blocca mai su OCR multi-pagina (RF8)."""

from locallens.app.worker import OcrWorker
from locallens.core.orchestrator import OcrEngine


def _engine_ok():
    return OcrEngine(infer=lambda p, i: (f"t{p}", "cuda"), fallback=lambda p, i: "fb")


def test_run_ok_emette_pagine_e_finished():
    eng = _engine_ok()
    w = OcrWorker(job_id="j1", engine=eng, immagini=[b"a", b"b"])
    pagine, avanzamenti, finiti, errori = [], [], [], []
    w.segnali.pagina.connect(lambda e, i, n: (pagine.append(e), avanzamenti.append((i, n))))
    w.segnali.finito.connect(finiti.append)
    w.segnali.errore.connect(errori.append)
    w.run()
    assert [e.pagina_id for e in pagine] == [1, 2]
    assert avanzamenti == [(1, 2), (2, 2)]
    assert finiti == ["j1"]
    assert errori == []


def test_annulla_interrompe_run():
    import threading

    from PySide6.QtCore import QCoreApplication

    app = QCoreApplication.instance() or QCoreApplication([])
    iniziato = threading.Event()
    sblocca = threading.Event()

    def infer(p, i):
        iniziato.set()
        sblocca.wait(10)
        return ("t", "cuda")

    eng = OcrEngine(infer=infer, fallback=lambda p, i: "fb")
    w = OcrWorker(job_id="j", engine=eng, immagini=[b"a", b"b"])
    pagine, finiti = [], []
    w.segnali.pagina.connect(lambda e, i, n: pagine.append(e))
    w.segnali.finito.connect(finiti.append)
    t = threading.Thread(target=w.run)
    t.start()
    assert iniziato.wait(10)
    w.annulla()
    sblocca.set()
    t.join(10)
    app.processEvents()
    assert finiti == ["j"]
    assert [e.pagina_id for e in pagine] == [1]
    stati = {j.stato for j in eng._jobs.values()}
    assert stati == {"cancelled"}


def test_run_fallito_emette_errore():
    def boom(imgs, documento="", on_page=None, **k):
        raise RuntimeError("gpu esplosa")

    eng = _engine_ok()
    eng.submit_document = boom  # type: ignore[method-assign]
    w = OcrWorker(job_id="j9", engine=eng, immagini=[b"a"])
    errori, finiti = [], []
    w.segnali.errore.connect(lambda j, m: errori.append((j, m)))
    w.segnali.finito.connect(finiti.append)
    w.run()
    assert errori == [("j9", "gpu esplosa")]
    assert finiti == []
