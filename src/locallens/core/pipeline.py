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
    on_page: Callable[[EstrazionePagina, int, int], None] | None = None,
) -> list[EstrazionePagina]:
    """Per ogni Pagina: infer (max 2 tentativi) → fallback Tesseract. Mai interruzione batch."""
    out: list[EstrazionePagina] = []
    totale = len(immagini)
    for i, img in enumerate(immagini, start=1):
        t0 = time.monotonic()
        if sorgente == "nessuno":
            testo = fallback(i, img)
            estrazione = EstrazionePagina(i, testo, "cpu-tesseract", _ms(t0), "sorgente=nessuno")
            out.append(estrazione)
            if on_page:
                on_page(estrazione, i, totale)
            continue
        ultimo_errore: str | None = None
        riuscito: EstrazionePagina | None = None
        for _ in range(2):
            try:
                testo, motore = infer(i, img)
                if not testo.strip():
                    ultimo_errore = "output vuoto/anomalo"
                    continue
                riuscito = EstrazionePagina(i, testo, motore, _ms(t0))
                break
            except InferenzaError as e:
                ultimo_errore = str(e)
                continue
        if riuscito is None:
            testo = fallback(i, img)
            riuscito = EstrazionePagina(i, testo, "cpu-tesseract", _ms(t0), ultimo_errore)
        out.append(riuscito)
        if on_page:
            on_page(riuscito, i, totale)
    return out


def _ms(t0: float) -> int:
    return int((time.monotonic() - t0) * 1000)
