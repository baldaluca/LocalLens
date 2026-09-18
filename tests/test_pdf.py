"""RED: rendering PDF pagina-per-pagina via pypdfium2."""

import pytest

from locallens.preprocessing.pdf import render_pagine


def _pdf_minimo(pagine: int = 2) -> bytes:
    """PDF valido con N pagine bianche Letter + testo Helvetica."""
    oggetti = []
    n = 1
    kids = " ".join(f"{3 + i} 0 R" for i in range(pagine))
    oggetti.append(f"{n} 0 obj<</Type/Catalog/Pages 2 0 R>>endobj")
    n = 2
    oggetti.append(f"{n} 0 obj<</Type/Pages/Kids[{kids}]/Count {pagine}>>endobj")
    for i in range(pagine):
        n = 3 + i
        c = 3 + pagine + i
        stream = f"BT /F1 24 Tf 72 720 Td (Pagina {i + 1}) Tj ET"
        oggetti.append(
            f"{n} 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
            f"/Resources<</Font<</F1<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>>>>>>"
            f"/Contents {c} 0 R>>endobj"
        )
    for i in range(pagine):
        stream = f"BT /F1 24 Tf 72 720 Td (Pagina {i + 1}) Tj ET"
        oggetti.append(f"{3 + pagine + i} 0 obj<</Length {len(stream)}>>stream\n{stream}\nendstream endobj")
    out = ["%PDF-1.4"]
    offsets = []
    for o in oggetti:
        offsets.append(sum(len(x) + 1 for x in out))
        out.append(o)
    start = sum(len(x) + 1 for x in out)
    out.append(f"xref\n0 {len(oggetti) + 1}\n0000000000 65535 f ")
    for off in offsets:
        out.append(f"{off:010d} 00000 n ")
    out.append(f"trailer<</Size {len(oggetti) + 1}/Root 1 0 R>>\nstartxref\n{start}\n%%EOF")
    return "\n".join(out).encode("latin-1")


def test_render_due_pagine_letter_a_300dpi():
    pdf = _pdf_minimo(2)
    pagine = render_pagine(pdf, dpi=300)
    assert len(pagine) == 2
    from PIL import Image

    for png in pagine:
        assert png[:8] == b"\x89PNG\r\n\x1a\n"
        with Image.open(__import__("io").BytesIO(png)) as im:
            w, h = im.size
            assert abs(w - 2550) <= 1 and abs(h - 3300) <= 1


def test_pdf_vuoto_sollevato():
    with pytest.raises(ValueError):
        render_pagine(b"non-un-pdf", dpi=300)


def test_chiude_documento_a_fine_render(monkeypatch):
    import locallens.preprocessing.pdf as mod_pdf

    chiusure = []

    class PaginaFinta:
        def render(self, scale=1.0):
            class Bitmap:
                def to_pil(self):
                    from PIL import Image

                    return Image.new("RGB", (8, 8))
            return Bitmap()

    class DocFinto:
        def __init__(self, *a, **k):
            self.chiuso = False

        def __len__(self):
            return 1

        def __iter__(self):
            yield PaginaFinta()

        def close(self):
            self.chiuso = True
            chiusure.append(True)

    creati: list = []

    def fabbrica(*a, **k):
        d = DocFinto(*a, **k)
        creati.append(d)
        return d

    monkeypatch.setattr(mod_pdf.pdfium, "PdfDocument", fabbrica)
    out = render_pagine(b"finto", dpi=72)
    assert len(out) == 1 and out[0][:8] == b"\x89PNG\r\n\x1a\n"
    assert creati and creati[0].chiuso is True


def test_chiude_documento_anche_su_eccezione_pagina(monkeypatch):
    import locallens.preprocessing.pdf as mod_pdf

    class PaginaRotta:
        def render(self, scale=1.0):
            raise RuntimeError("render esploso")

    class DocFinto:
        def __init__(self, *a, **k):
            self.chiuso = False

        def __len__(self):
            return 1

        def __iter__(self):
            yield PaginaRotta()

        def close(self):
            self.chiuso = True

    creati: list = []

    def fabbrica(*a, **k):
        d = DocFinto(*a, **k)
        creati.append(d)
        return d

    monkeypatch.setattr(mod_pdf.pdfium, "PdfDocument", fabbrica)
    with pytest.raises(RuntimeError, match="render esploso"):
        render_pagine(b"finto", dpi=72)
    assert creati and creati[0].chiuso is True
