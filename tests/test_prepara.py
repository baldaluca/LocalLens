"""RED: prepara() prima dell'inferenza. Deskew/crop fuori v1 (vedi ADR)."""

import io

from PIL import Image

from locallens.preprocessing.immagini import prepara, ridimensiona


def _png(w: int, h: int, grigio: int = 200) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (grigio, grigio, grigio)).save(buf, format="PNG")
    return buf.getvalue()


def _size(png: bytes) -> tuple[int, int]:
    with Image.open(io.BytesIO(png)) as im:
        return im.size


def test_prepara_resize_senza_contrasto():
    out = prepara(_png(4000, 2000), max_side=2048, contrasto=False)
    assert _size(out) == (2048, 1024)


def test_prepara_contrasto_aumenta_gamma():
    img = Image.new("RGB", (100, 100))
    px = img.load()
    for x in range(100):
        for y in range(100):
            v = 100 if x < 50 else 200
            px[x, y] = (v, v, v)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    dopo = prepara(buf.getvalue(), max_side=2048, contrasto=True)
    with Image.open(io.BytesIO(dopo)) as im:
        scuro = im.getpixel((25, 50))[0]
        chiaro = im.getpixel((75, 50))[0]
    assert chiaro - scuro > 100  # era 100, il contrasto allarga la forbice


def test_prepara_default_uguale_a_resize():
    png = _png(3000, 1500)
    assert prepara(png) == ridimensiona(png)


def test_crea_engine_prepara_immagini():
    import base64

    from locallens.config.presets import load_preset
    from locallens.core.orchestrator import crea_engine

    visti = {}

    def post_ok(url, payload):
        user = payload["messages"][1]["content"]
        b64 = next(p["image_url"]["url"] for p in user if p["type"] == "image_url")
        visti["png"] = base64.b64decode(b64.split(",", 1)[1])
        return {"choices": [{"message": {"content": "ok"}}]}

    eng = crea_engine(
        "http://x",
        load_preset("presets/glm-ocr-q8_0.toml"),
        post=post_ok,
        fallback=lambda p, i: "fb",
        max_side=2048,
    )
    eng.get_result(eng.submit_document([_png(4000, 2000)]))
    assert _size(visti["png"]) == (2048, 1024)
