"""Rendering PDF pagina-per-pagina via pypdfium2. Solo PNG, niente dipendenze di sistema."""

import pypdfium2 as pdfium  # type: ignore[import-untyped]


def render_pagine(pdf_bytes: bytes, dpi: int = 300) -> list[bytes]:
    """Ogni pagina → PNG bytes. Solleva ValueError su input non valido."""
    try:
        doc = pdfium.PdfDocument(pdf_bytes)
    except Exception as e:
        raise ValueError(f"PDF non valido: {e}") from e
    try:
        if len(doc) == 0:
            raise ValueError("PDF senza pagine")
        scala = dpi / 72.0
        out: list[bytes] = []
        for pagina in doc:
            bitmap = pagina.render(scale=scala)
            out.append(bitmap_to_png_bytes(bitmap))
        return out
    finally:
        try:
            doc.close()
        except Exception:  # noqa: BLE001 — chiusura best-effort, mai mascherare l'errore
            pass


def bitmap_to_png_bytes(bitmap) -> bytes:
    import io

    pil = bitmap.to_pil()
    buf = io.BytesIO()
    pil.save(buf, format="PNG")
    return buf.getvalue()
