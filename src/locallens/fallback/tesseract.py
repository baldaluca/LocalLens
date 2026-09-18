"""Fallback CPU via Tesseract. Nessun vincolo GPU (requisiti §7)."""

import io
import shutil
from collections.abc import Callable

from PIL import Image

LANG_DEFAULT = "ita+eng"
# Blocco uniforme di testo (niente foto/scene): misurato su P4 densa
# crisi-reale-2 (F1 0.84 → 1.00, 7s → 5s contro psm 3 a 300dpi).
PSM_DEFAULT = 6


def _ocr_default(immagine: Image.Image, lang: str, psm: int) -> str:
    import pytesseract  # type: ignore[import-untyped]

    return pytesseract.image_to_string(immagine, lang=lang, config=f"--psm {psm}")


def verifica_disponibile() -> bool:
    """True se il binario tesseract è nel PATH."""
    return shutil.which("tesseract") is not None


def estrai(
    png: bytes,
    lang: str = LANG_DEFAULT,
    psm: int = PSM_DEFAULT,
    ocr: Callable[[Image.Image, str], str] | None = None,
) -> str:
    """PNG bytes → testo. `psm` vale solo per il binario reale; il runner
    iniettato (test) riceve (immagine, lang) come prima."""
    with Image.open(io.BytesIO(png)) as handle:
        rgb = handle.convert("RGB")
        if ocr is not None:
            return ocr(rgb, lang)
        return _ocr_default(rgb, lang, psm)
