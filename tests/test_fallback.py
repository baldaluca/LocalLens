"""RED: fallback CPU via Tesseract. Runner iniettabile (binario assente in CI)."""

import os

import pytest

from locallens.fallback.tesseract import LANG_DEFAULT, estrai, verifica_disponibile


def _png_bianco() -> bytes:
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (100, 30), "white").save(buf, format="PNG")
    return buf.getvalue()


def test_estrai_usa_runner_iniettato():
    viste = {}

    def fake_ocr(immagine, lang):
        viste["lang"] = lang
        viste["size"] = immagine.size
        return "testo-fake"

    assert estrai(_png_bianco(), ocr=fake_ocr) == "testo-fake"
    assert viste["lang"] == LANG_DEFAULT
    assert viste["size"] == (100, 30)


def test_lang_default_ita_eng():
    assert LANG_DEFAULT == "ita+eng"


def test_verifica_disponibile_bool():
    assert isinstance(verifica_disponibile(), bool)


@pytest.mark.skipif(os.environ.get("TESSERACT_LIVE") != "1", reason="solo live esplicito")
def test_live_immagine_gold():
    with open("tests/assets/ocr-test-01.png", "rb") as f:
        testo = estrai(f.read())
    assert "LocalLens" in testo
    assert "1234567890" in testo
