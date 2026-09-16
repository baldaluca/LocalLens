"""RED: downscale Lanczos sopra il lato massimo (mitigazione OOM §10)."""

import io

from PIL import Image

from locallens.preprocessing.immagini import ridimensiona


def _png(w: int, h: int) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), "white").save(buf, format="PNG")
    return buf.getvalue()


def _size(png: bytes) -> tuple[int, int]:
    with Image.open(io.BytesIO(png)) as im:
        return im.size


def test_sotto_limite_invariata():
    png = _png(800, 600)
    assert _size(ridimensiona(png, max_side=2048)) == (800, 600)


def test_sopra_limite_scala_lato_lungo():
    out = ridimensiona(_png(4000, 2000), max_side=2048)
    assert _size(out) == (2048, 1024)


def test_verticale_scala_altezza():
    out = ridimensiona(_png(1000, 3000), max_side=2048)
    w, h = _size(out)
    assert h == 2048
    assert w == 682 or w == 683


def test_output_sempre_png():
    assert ridimensiona(_png(3000, 3000), max_side=100)[:8] == b"\x89PNG\r\n\x1a\n"
