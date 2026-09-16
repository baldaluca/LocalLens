"""RED: pipeline Pagina-per-Pagina con retry e fallback automatico."""

from locallens.core.pipeline import InferenzaError, elabora_pagine


def test_successo_backend_registra_motore():
    def infer(pagina_id, _img):
        return ("ciao", "cuda")

    def fallback(pagina_id, _img):
        raise AssertionError("fallback non deve scattare")

    out = elabora_pagine([b"img1"], infer=infer, fallback=fallback, sorgente="bundlato")
    assert len(out) == 1
    assert out[0].testo == "ciao"
    assert out[0].motore_usato == "cuda"
    assert out[0].pagina_id == 1


def test_un_fallimento_poi_retry_ok():
    chiamate = []

    def infer(pagina_id, _img):
        chiamate.append(pagina_id)
        if len(chiamate) == 1:
            raise InferenzaError("OOM simulato")
        return ("ok-dopo-retry", "cuda")

    def fallback(pagina_id, _img):
        raise AssertionError("fallback non deve scattare dopo retry riuscito")

    out = elabora_pagine([b"img1"], infer=infer, fallback=fallback, sorgente="bundlato")
    assert out[0].testo == "ok-dopo-retry"
    assert len(chiamate) == 2


def test_doppio_fallimento_va_in_fallback_con_badge():
    def infer(pagina_id, _img):
        raise InferenzaError("backend giu'")

    def fallback(pagina_id, _img):
        return "testo-cpu"

    out = elabora_pagine([b"img1"], infer=infer, fallback=fallback, sorgente="bundlato")
    assert out[0].testo == "testo-cpu"
    assert out[0].motore_usato == "cpu-tesseract"
    assert "backend giu" in (out[0].nota or "")


def test_output_vuoto_trattato_come_fallimento():
    def infer(pagina_id, _img):
        return ("   ", "vulkan")

    def fallback(pagina_id, _img):
        return "recuperato"

    out = elabora_pagine([b"img1"], infer=infer, fallback=fallback, sorgente="bundlato")
    assert out[0].motore_usato == "cpu-tesseract"
    assert out[0].testo == "recuperato"


def test_sorgente_nessuno_salata_backend():
    chiamate = []

    def infer(pagina_id, _img):
        chiamate.append(pagina_id)
        return ("mai", "cuda")

    def fallback(pagina_id, _img):
        return "solo-cpu"

    out = elabora_pagine([b"a", b"b"], infer=infer, fallback=fallback, sorgente="nessuno")
    assert chiamate == []
    assert [e.testo for e in out] == ["solo-cpu", "solo-cpu"]
    assert all(e.motore_usato == "cpu-tesseract" for e in out)


def test_timeout_non_ritentato():
    """Timeout >120s su 960M: ritentare raddoppia il danno e intasa il server."""
    from urllib.error import URLError

    chiamate = []

    def infer(pagina_id, _img):
        chiamate.append(pagina_id)
        raise InferenzaError("chiamata chat fallita: timed out") from URLError(
            TimeoutError()
        )

    def fallback(pagina_id, _img):
        return "fb-veloce"

    out = elabora_pagine([b"img1"], infer=infer, fallback=fallback, sorgente="bundlato")
    assert len(chiamate) == 1
    assert out[0].testo == "fb-veloce"
    assert out[0].motore_usato == "cpu-tesseract"
    assert "timed out" in (out[0].nota or "")


def test_batch_non_si_interrompe_su_fallback():
    def infer(pagina_id, _img):
        if pagina_id == 1:
            raise InferenzaError("boom")
        return (f"p{pagina_id}", "cuda")

    def fallback(pagina_id, _img):
        return "fb1"

    out = elabora_pagine([b"a", b"b"], infer=infer, fallback=fallback, sorgente="bundlato")
    assert out[0].motore_usato == "cpu-tesseract"
    assert out[1].testo == "p2"
