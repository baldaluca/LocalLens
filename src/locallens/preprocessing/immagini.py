"""Normalizzazione immagini prima dell'inferenza. Solo CPU (requisiti §8)."""

import io

from PIL import Image, ImageEnhance


def ridimensiona(png: bytes, max_side: int = 2048) -> bytes:
    """Downscale Lanczos se il lato lungo supera max_side; altrimenti invariata."""
    with Image.open(io.BytesIO(png)) as handle:
        rgb = handle.convert("RGB")
        w, h = rgb.size
        lungo = max(w, h)
        if lungo <= max_side:
            buf = io.BytesIO()
            rgb.save(buf, format="PNG")
            return buf.getvalue()
        fattore = max_side / lungo
        nuova = (round(w * fattore), round(h * fattore))
        rid = rgb.resize(nuova, Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        rid.save(buf, format="PNG")
        return buf.getvalue()


def prepara(png: bytes, max_side: int = 2048, contrasto: bool = False) -> bytes:
    """Pipeline pre-inferenza v1: resize anti-OOM + contrasto opzionale (RF2)."""
    if contrasto:
        with Image.open(io.BytesIO(png)) as handle:
            rgb = handle.convert("RGB")
            png = _a_png(ImageEnhance.Contrast(rgb).enhance(1.5))
    return ridimensiona(png, max_side=max_side)


def _a_png(immagine: Image.Image) -> bytes:
    buf = io.BytesIO()
    immagine.save(buf, format="PNG")
    return buf.getvalue()
