"""Pipeline Documento → Pagine → Estrazioni. Sequenziale, 1 retry, poi fallback CPU."""
import time
from collections.abc import Callable
from dataclasses import dataclass

from locallens.core.errori import InferenzaError

__all__ = ["EstrazionePagina", "InferenzaError", "elabora_pagine"]


@dataclass(frozen=True)
class EstrazionePagina:
    pagina_id: int
    testo: str
    motore_usato: str
    ms: int = 0
    nota: str | None = None


def elabora_pagine(
    immagini: list[bytes],
    infer: Callable[[int, bytes], tuple[str, str]],
    fallback: Callable[[int, bytes], str],
    sorgente: str = "bundlato",
) -> list[EstrazionePagina]:
    """Per ogni Pagina: infer (max 2 tentativi) → fallback Tesseract. Mai interruzione batch."""
    out: list[EstrazionePagina] = []
    for i, img in enumerate(immagini, start=1):
        t0 = time.monotonic()
        if sorgente == "nessuno":
            testo = fallback(i, img)
            out.append(
                EstrazionePagina(i, testo, "cpu-tesseract", _ms(t0), "sorgente=nessuno")
            )
            continue
        ultimo_errore: str | None = None
        riuscito = False
        for _ in range(2):
            try:
                testo, motore = infer(i, img)
                if not testo.strip():
                    ultimo_errore = "output vuoto/anomalo"
                    continue
                out.append(EstrazionePagina(i, testo, motore, _ms(t0)))
                riuscito = True
                break
            except InferenzaError as e:
                ultimo_errore = str(e)
                continue
        if not riuscito:
            testo = fallback(i, img)
            out.append(
                EstrazionePagina(i, testo, "cpu-tesseract", _ms(t0), ultimo_errore)
            )
    return out


def _ms(t0: float) -> int:
    return int((time.monotonic() - t0) * 1000)
