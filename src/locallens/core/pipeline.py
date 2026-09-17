"""Pipeline Documento → Pagine → Estrazioni. Sequenziale, 1 retry, poi fallback CPU."""
import re
import time
import unicodedata
import urllib.error
import zlib
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


_STOP_IT = frozenset(
    (
        "di", "e", "che", "la", "il", "lo", "i", "gli", "le", "un", "uno",
        "una", "in", "con", "su", "per", "tra", "fra", "non", "si", "come",
        "anche", "dal", "dei", "delle", "alla", "questo", "questa", "sono",
        "molto", "tutto", "quando", "sempre",
    )
)
_STOP_EN = frozenset(
    (
        "the", "and", "of", "to", "in", "is", "that", "for", "with", "as",
        "on", "are", "was", "were", "be", "by", "from", "this", "have",
        "has", "not", "but", "they", "their", "you", "your", "can", "will",
        "would", "all", "more", "than",
    )
)
_MARCATORI_FORTI = (
    "in sintesi",
    "in conclusione",
    "riassunto",
    "il documento tratta di",
    "the document shows",
    "as an ai",
    "as a language model",
    "i can't",
    "mi dispiace",
    "non riesco a leggere",
    "ecco la trascrizione",
)
_MARCATORI_DEBOLI = ("il documento", "conclusione")
_CONNETTIVI_FINALI = frozenset(
    ("e", "ed", "di", "a", "da", "in", "con", "su", "per", "tra", "fra", "che", "the", "and", "or", "to", "of")
)
_SCRIPT_INATTESI = (
    "CJK",
    "CYRILLIC",
    "ARABIC",
    "HEBREW",
    "THAI",
    "DEVANAGARI",
    "HANGUL",
    "HIRAGANA",
    "KATAKANA",
    "ARMENIAN",
    "GEORGIAN",
)


def _motivo_anomalia(testo: str) -> str | None:
    """Output del VLM andato storto: eco del prompt, loop, escape letterali.

    Somma pesi, fallback se >= 1 (dubbio → Tesseract): segnali forti = 1.0,
    deboli = 0.5 solo in combinazione. Vale a qualsiasi lunghezza, con pavimenti
    minimi per segnale: mai su trascrizioni brevi legittime o tabelle/codice.
    Ritorna il motivo (per nota/diario) oppure None se il testo è accettabile.
    """
    motivi: list[str] = []
    punteggio = 0.0

    def _segnala(motivo: str, peso: float) -> None:
        nonlocal punteggio
        motivi.append(motivo)
        punteggio += peso

    n = len(testo)
    minuscolo = testo.lower()
    if "transcribe the document" in minuscolo:
        _segnala("output anomalo: eco del prompt", 1.0)
    if testo.count("\\n") > 100:
        _segnala("output anomalo: escape eccessivi", 1.0)
    righe = [r.strip() for r in testo.splitlines() if r.strip()]
    if righe:
        comune, freq = Counter(righe).most_common(1)[0]
        if freq >= 5 and len(comune) > 20:
            _segnala("output anomalo: ripetizione in loop", 1.0)
    frasi = [s.strip() for s in testo.replace("\n", " ").split(".") if len(s.strip()) >= 4]
    if len(frasi) >= 30:
        _top, freq = Counter(frasi).most_common(1)[0]
        if freq >= 10 or (len(frasi) >= 50 and len(set(frasi)) / len(frasi) < 0.25):
            _segnala("output anomalo: ripetizione in loop", 1.0)
    parole = [w for w in "".join(c.lower() if c.isalnum() else " " for c in testo).split() if w]
    if len(parole) >= 50:
        _top, freq = Counter(parole).most_common(1)[0]
        if freq / len(parole) > 0.30:
            _segnala("output anomalo: ripetizione in loop", 1.0)
    compatti = "".join(testo.split())
    if compatti:
        alnum = sum(c.isalnum() for c in compatti)
        if alnum / len(compatti) < 0.10:
            _segnala("output anomalo: testo senza contenuto", 1.0)
    if n >= 200 and len(zlib.compress(testo.encode())) / n < 0.20:
        _segnala("output anomalo: compressione anomala (loop)", 1.0)
    parole_alpha = re.findall(r"[a-zà-ÿ]+", minuscolo)
    if len(parole_alpha) >= 50:
        _top, freq = Counter(parole_alpha).most_common(1)[0]
        if freq / len(parole_alpha) > 0.25:
            _segnala("output anomalo: ripetizione in loop (parola dominante)", 1.0)
    trigrammi = [" ".join(parole_alpha[i : i + 3]) for i in range(len(parole_alpha) - 2)]
    if len(trigrammi) >= 100 and len(set(trigrammi)) / len(trigrammi) < 0.5:
        _segnala("output anomalo: ripetizione in loop (frasi uguali)", 1.0)
    if len(parole_alpha) >= 30:
        quota_it = sum(1 for w in parole_alpha if w in _STOP_IT) / len(parole_alpha)
        quota_en = sum(1 for w in parole_alpha if w in _STOP_EN) / len(parole_alpha)
        if quota_en - quota_it > 0.10:
            _segnala("output anomalo: lingua inattesa", 1.0)
    for marcatore in _MARCATORI_FORTI:
        if marcatore in minuscolo:
            _segnala(f"output anomalo: meta-discorso ({marcatore})", 1.0)
            break
    for marcatore in _MARCATORI_DEBOLI:
        if marcatore in minuscolo:
            _segnala(f"segnale debole ({marcatore})", 0.5)
    if _finale_monco(testo):
        _segnala("output anomalo: troncamento (finale monco)", 0.5)
    if n >= 100 and _quota_simboli_inattesi(testo) > 0.05:
        _segnala("output anomalo: simboli inattesi", 0.5)
    if punteggio >= 1.0:
        return "; ".join(motivi)
    return None


def _finale_monco(testo: str) -> bool:
    """Finale troncato: parola a metà o connettivo, ignorando footer e recinzioni."""
    s = testo.strip().rstrip("`").rstrip()
    s = re.sub(r"(pagina|page)\s+\d+\s+(di|of)\s+\d+\s*$", "", s, flags=re.IGNORECASE).rstrip()
    if not s or s[-1] in ".:;!?\"»)'’”":
        return False
    if s.endswith((",", "-")):
        return True
    ultime = re.findall(r"[a-zà-ÿ]+", s.lower())
    return bool(ultime) and ultime[-1] in _CONNETTIVI_FINALI


def _quota_simboli_inattesi(testo: str) -> float:
    """Quota di caratteri fuori dallo script atteso (CJK/cirillico/emoji/...)."""
    strani = 0
    for c in testo:
        if unicodedata.category(c) == "So":
            strani += 1
        elif c.isalpha() and ord(c) > 0x052F:
            try:
                nome = unicodedata.name(c)
            except ValueError:
                continue
            if any(script in nome for script in _SCRIPT_INATTESI):
                strani += 1
    return strani / len(testo) if testo else 0.0


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
            nota = "sorgente=nessuno"
            if not testo.strip():
                nota += "; fallback vuoto"
            estrazione = EstrazionePagina(i, testo, "cpu-tesseract", _ms(t0), nota)
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
            nota = ultimo_errore
            if not testo.strip():
                nota = ((ultimo_errore + "; ") if ultimo_errore else "") + "fallback vuoto"
            riuscito = EstrazionePagina(i, testo, "cpu-tesseract", _ms(t0), nota)
        out.append(riuscito)
        if on_page:
            on_page(riuscito, i, totale)
    return out


def _ms(t0: float) -> int:
    return int((time.monotonic() - t0) * 1000)
