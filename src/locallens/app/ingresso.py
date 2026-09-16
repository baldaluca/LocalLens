"""Ingressi RF1: file, PDF, appunti, screenshot. Solo bytes, niente logica OCR."""

from pathlib import Path

from locallens.preprocessing.pdf import render_pagine


def carica_documento(percorso: str, dpi: int = 300) -> list[bytes]:
    """Immagine → [bytes]; PDF → una PNG per pagina."""
    p = Path(percorso)
    if not p.is_file():
        raise FileNotFoundError(percorso)
    if p.suffix.lower() == ".pdf":
        return render_pagine(p.read_bytes(), dpi=dpi)
    return [p.read_bytes()]


def da_appunti(clipboard) -> bytes | None:
    """QImage dagli appunti → PNG bytes; None se vuoti."""
    from PySide6.QtCore import QBuffer, QIODeviceBase

    img = clipboard.image()
    if img.isNull():
        return None
    buf = QBuffer()
    buf.open(QIODeviceBase.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    return bytes(buf.data().data())


def cattura_schermo(grabber=None) -> bytes:
    """Screenshot → PNG bytes. Grabber iniettabile per i test."""
    if grabber is not None:
        return grabber()
    import mss

    with mss.mss() as sct:
        shot = sct.grab(sct.monitors[0])
        from PIL import Image

        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        import io

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
