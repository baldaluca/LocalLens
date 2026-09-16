"""Pipeline Documento → Pagine → Estrazioni. Sequenziale, 1 retry, poi fallback CPU."""
import time
import urllib.error
from collections import Counter
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


def _motivo_anomalia(testo: str) -> str | None:
    """Output del VLM andato storto: eco del prompt, loop, escape letterali.

    Ritorna il motivo (per nota/diario) oppure None se il testo è accettabile.
    Soglie conservative: scatta solo su output lunghi e marcatamente degeneri,
    mai su trascrizioni brevi o tabelle/codice legittimi.
    """
    n = len(testo)
    if n < 500:
        return None
    if testo.count("\\n") > 100:
        return "output anomalo: escape eccessivi"
    righe = [r.strip() for r in testo.splitlines() if r.strip()]
    if righe:
        comune, freq = Counter(righe).most_common(1)[0]
        if freq >= 5 and len(comune) > 20:
            return "output anomalo: ripetizione in loop"
    frasi = [s.strip() for s in testo.replace("\n", " ").split(".") if len(s.strip()) > 10]
    if len(frasi) >= 30:
        _top, freq = Counter(frasi).most_common(1)[0]
        if freq >= 10 or (len(frasi) >= 50 and len(set(frasi)) / len(frasi) < 0.25):
            return "output anomalo: ripetizione in loop"
    compatti = "".join(testo.split())
    if compatti:
        alnum = sum(c.isalnum() for c in compatti)
        if alnum / len(compatti) < 0.10:
            return "output anomalo: testo senza contenuto"
    return None


def _è_timeout(e: InferenzaError) -> bool:
    """Timeout socket (diretto o dentro URLError): ritentare raddoppia il danno."""
    causa = e.__cause__
    if isinstance(causa, TimeoutError):
        return True
    return isinstance(causa, urllib.error.URLError) and isinstance(
        causa.reason, TimeoutError
    )


def elabora_pagine(
    immagini: list[bytes],
    infer: Callable[[int, bytes], tuple[str, str]],
    fallback: Callable[[int, bytes], str],
    sorgente: str = "bundlato",
    on_page: Callable[[EstrazionePagina, int, int], None] | None = None,
    ferma: Callable[[], bool] | None = None,
) -> list[EstrazionePagina]:
    """Per ogni Pagina: infer (max 2 tentativi) → fallback Tesseract. Mai interruzione batch."""
    out: list[EstrazionePagina] = []
    totale = len(immagini)
    for i, img in enumerate(immagini, start=1):
        if ferma is not None and ferma():
            break
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
                motivo = _motivo_anomalia(testo)
                if motivo is not None:
                    ultimo_errore = motivo
                    continue
                riuscito = EstrazionePagina(i, testo, motore, _ms(t0))
                break
            except InferenzaError as e:
                ultimo_errore = str(e)
                if _è_timeout(e):
                    break
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
