"""Normalizzazione immagini prima dell'inferenza. Solo CPU (requisiti §8)."""

import io

from PIL import Image


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
