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


def test_crea_engine_collega_client_e_fallback():
    from locallens.config.presets import load_preset
    from locallens.core.orchestrator import crea_engine

    def post_ok(url, payload):
        assert payload["model"] == "glm-ocr-q8_0"
        return {"choices": [{"message": {"content": "dal-server"}}]}

    preset = load_preset("presets/glm-ocr-q8_0.toml")
    eng = crea_engine(
        "http://127.0.0.1:8011", preset, motore="cuda", post=post_ok, fallback=lambda p, i: "fb"
    )
    with open("tests/assets/ocr-test-01.png", "rb") as f:
        job = eng.get_result(eng.submit_document([f.read()]))
    assert job.estrazioni[0].testo == "dal-server"
    assert job.estrazioni[0].motore_usato == "cuda"


def test_immagine_corrotta_va_in_fallback():
    from locallens.config.presets import load_preset
    from locallens.core.orchestrator import crea_engine

    eng = crea_engine(
        "http://127.0.0.1:8011",
        load_preset("presets/glm-ocr-q8_0.toml"),
        post=lambda u, p: {"choices": [{"message": {"content": "x"}}]},
        fallback=lambda p, i: "fb-caduta",
    )
    job = eng.get_result(eng.submit_document([b"non-una-immagine"]))
    assert job.estrazioni[0].motore_usato == "cpu-tesseract"
    assert job.estrazioni[0].testo == "fb-caduta"


def test_cancel_su_job_fatto_noop_e_sconosciuto_errore():
    eng = _engine()
    jid = eng.submit_document([b"a"])
    eng.cancel(jid)  # done: nessun effetto, nessuna eccezione
    assert eng.get_result(jid).stato == "done"
    with pytest.raises(KeyError):
        eng.cancel("inesistente")
    with pytest.raises(KeyError):
        eng.get_result("inesistente")
