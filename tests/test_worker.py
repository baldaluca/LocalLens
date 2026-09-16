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


def test_run_fallito_emette_errore():
    def boom(imgs, documento="", on_page=None):
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
