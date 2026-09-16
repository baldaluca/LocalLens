"""Fallback CPU via Tesseract. Nessun vincolo GPU (requisiti §7)."""

import io
import shutil
from collections.abc import Callable

from PIL import Image

LANG_DEFAULT = "ita+eng"


def _ocr_default(immagine: Image.Image, lang: str) -> str:
    import pytesseract  # type: ignore[import-untyped]

    return pytesseract.image_to_string(immagine, lang=lang)


def verifica_disponibile() -> bool:
    """True se il binario tesseract è nel PATH."""
    return shutil.which("tesseract") is not None


def estrai(
    png: bytes,
    lang: str = LANG_DEFAULT,
    ocr: Callable[[Image.Image, str], str] | None = None,
) -> str:
    """PNG bytes → testo. Solleva RuntimeError se il binario manca (uso reale)."""
    ocr = ocr or _ocr_default
    with Image.open(io.BytesIO(png)) as handle:
        return ocr(handle.convert("RGB"), lang)
