"""RED: OcrEngine sincrono (la GUI lo threaderà). Job registry + cancel."""

import pytest

from locallens.core.orchestrator import OcrEngine


def _engine(infer=None, fallback=None, sorgente="bundlato"):
    infer = infer or (lambda pid, img: ("t", "cuda"))
    fallback = fallback or (lambda pid, img: "fb")
    return OcrEngine(infer=infer, fallback=fallback, sorgente=sorgente)


def test_submit_e_get_result():
    eng = _engine()
    jid = eng.submit_document([b"a", b"b"])
    job = eng.get_result(jid)
    assert job.stato == "done"
    assert [e.pagina_id for e in job.estrazioni] == [1, 2]
    assert all(e.motore_usato == "cuda" for e in job.estrazioni)


def test_submit_usa_fallback_su_errore():
    def infer(pid, img):
        from locallens.core.errori import InferenzaError

        raise InferenzaError("boom")

    eng = _engine(infer=infer)
    job = eng.get_result(eng.submit_document([b"a"]))
    assert job.stato == "done"
    assert job.estrazioni[0].motore_usato == "cpu-tesseract"


def test_cancel_su_job_fatto_noop_e_sconosciuto_errore():
    eng = _engine()
    jid = eng.submit_document([b"a"])
    eng.cancel(jid)  # done: nessun effetto, nessuna eccezione
    assert eng.get_result(jid).stato == "done"
    with pytest.raises(KeyError):
        eng.cancel("inesistente")
    with pytest.raises(KeyError):
        eng.get_result("inesistente")
