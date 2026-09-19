"""Pipeline Documento → Pagine → Estrazioni. Deep: OcrPipeline con singola interfaccia submit."""

import re
import time
import unicodedata
import urllib.error
import uuid
import zlib
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field

from locallens.core.errori import InferenzaError

__all__ = ["EstrazionePagina", "Estrazione", "OcrConfig", "OcrJob", "OcrPipeline", "InferenzaError", "elabora_pagine"]


@dataclass(frozen=True)
class EstrazionePagina:
    pagina_id: int
    testo: str
    motore_usato: str
    ms: int = 0
    nota: str | None = None
    scartato: str | None = None  # output VLM rifiutato dal filtro (audit diario)


# Alias per compatibilità con orchestrator / finestra
Estrazione = EstrazionePagina


#: Tetto dello scartato conservato: il diario resta leggibile anche su loop lunghi.
MAX_SCARTATO = 2000


@dataclass(frozen=True)
class OcrConfig:
    """Config per OcrPipeline.submit: unione di sorgente + contesto filtro."""

    sorgente: str = "bundlato"
    lingue_attese: tuple[str, ...] = ("it",)
    soglia_righe_loop: int = 5
    ignora_eco: bool = False


@dataclass
class OcrJob:
    job_id: str
    documento: str
    stato: str = "queued"  # queued | processing | done | failed | cancelled
    estrazioni: list[EstrazionePagina] = field(default_factory=list)


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


def _motivo_anomalia(
    testo: str,
    *,
    lingue_attese: tuple[str, ...] = ("it",),
    soglia_righe_loop: int = 5,
    ignora_eco: bool = False,
) -> str | None:
    """Output del VLM andato storto: eco del prompt, loop, escape letterali.

    Somma pesi, fallback se >= 1 (dubbio → Tesseract): segnali forti = 1.0,
    deboli = 0.5 solo in combinazione. Vale a qualsiasi lunghezza, con pavimenti
    minimi per segnale: mai su trascrizioni brevi legittime o tabelle/codice.
    Contesto del Documento: lingue_attese dichiara le lingue legittime
    (es. ("it", "en") per Documenti bilingui), soglia_righe_loop alza il
    pavimento del loop su Pagine legittimamente ripetitive, ignora_eco salta
    il controllo eco quando le istruzioni sono stampate nella sorgente.
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
    if not ignora_eco and "transcribe the document" in minuscolo:
        _segnala("output anomalo: eco del prompt", 1.0)
    if testo.count("\\n") > 100:
        _segnala("output anomalo: escape eccessivi", 1.0)
    righe = [r.strip() for r in testo.splitlines() if r.strip()]
    if righe:
        comune, freq = Counter(righe).most_common(1)[0]
        if freq >= soglia_righe_loop and len(comune) > 20:
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
        if quota_en - quota_it > 0.10 and "en" not in lingue_attese:
            _segnala("output anomalo: lingua inattesa", 1.0)
        if quota_it - quota_en > 0.10 and "it" not in lingue_attese:
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


def _resolve_config(
    config,
    defaults: dict,
) -> dict:
    """Normalizza config (OcrConfig | Config | dict | None) a dict effettivo."""
    if config is None or config is Ellipsis:
        return dict(defaults)
    # dict
    if isinstance(config, dict):
        out = dict(defaults)
        # handle lingue_filtro → lingue_attese
        if "lingue_filtro" in config and "lingue_attese" not in config:
            lf = str(config.get("lingue_filtro", "") or "")
            lingue = tuple(s.strip() for s in lf.split(",") if s.strip()) or defaults.get("lingue_attese", ("it",))
            out["lingue_attese"] = lingue
            # still allow other keys
        for k in ("sorgente", "lingue_attese", "soglia_righe_loop", "ignora_eco"):
            if k in config:
                out[k] = config[k]
        # also allow explicit lingue_attese as string?
        if isinstance(out.get("lingue_attese"), str):
            out["lingue_attese"] = tuple(s.strip() for s in str(out["lingue_attese"]).split(",") if s.strip()) or ("it",)
        return out
    # object with attributes (OcrConfig, Config dataclass)
    out = dict(defaults)
    for k in ("sorgente", "lingue_attese", "soglia_righe_loop", "ignora_eco"):
        if hasattr(config, k):
            try:
                v = getattr(config, k)
                out[k] = v
            except Exception:
                pass
    # Config has lingue_filtro not lingue_attese
    if hasattr(config, "lingue_filtro") and not hasattr(config, "lingue_attese"):
        try:
            lf = str(getattr(config, "lingue_filtro"))
            lingue = tuple(s.strip() for s in lf.split(",") if s.strip()) or defaults.get("lingue_attese", ("it",))
            out["lingue_attese"] = lingue
        except Exception:
            pass
    if isinstance(out.get("lingue_attese"), str):
        out["lingue_attese"] = tuple(s.strip() for s in str(out["lingue_attese"]).split(",") if s.strip()) or ("it",)
    return out


class OcrPipeline:
    """Deep module: unica interfaccia submit owning retry, anomalia, fallback, diario."""

    def __init__(
        self,
        infer: Callable[[int, bytes], tuple[str, str]] | None = None,
        fallback: Callable[[int, bytes], str] | None = None,
        sorgente: str = "bundlato",
        lingue_attese: tuple[str, ...] = ("it",),
        soglia_righe_loop: int = 5,
        ignora_eco: bool = False,
    ) -> None:
        if infer is None or fallback is None:
            raise ValueError("infer e fallback vanno iniettati")
        self._infer = infer
        self._fallback = fallback
        self._sorgente = sorgente
        self._lingue_attese = tuple(lingue_attese)
        self._soglia_righe_loop = soglia_righe_loop
        self._ignora_eco = ignora_eco
        self._jobs: dict[str, OcrJob] = {}

    def submit(
        self,
        immagini: list[bytes],
        config: OcrConfig | dict | object | None = None,
        ferma: Callable[[], bool] | None = None,
        diario=None,
        on_page: Callable[[EstrazionePagina, int, int], None] | None = None,
    ) -> list[EstrazionePagina]:
        """Singola interfaccia: per ogni Pagina infer→retry/anomalia→fallback con audit diario."""
        defaults = {
            "sorgente": self._sorgente,
            "lingue_attese": self._lingue_attese,
            "soglia_righe_loop": self._soglia_righe_loop,
            "ignora_eco": self._ignora_eco,
        }
        cfg = _resolve_config(config, defaults)
        sorgente: str = cfg.get("sorgente", self._sorgente)
        lingue_attese: tuple[str, ...] = tuple(cfg.get("lingue_attese", self._lingue_attese))
        soglia_righe_loop: int = int(cfg.get("soglia_righe_loop", self._soglia_righe_loop))
        ignora_eco: bool = bool(cfg.get("ignora_eco", self._ignora_eco))

        out: list[EstrazionePagina] = []
        totale = len(immagini)
        for i, img in enumerate(immagini, start=1):
            if ferma is not None and ferma():
                break
            t0 = time.monotonic()
            if sorgente == "nessuno":
                testo = self._fallback(i, img)
                nota = "sorgente=nessuno"
                if not testo.strip():
                    nota += "; fallback vuoto"
                estrazione = EstrazionePagina(i, testo, "cpu-tesseract", _ms(t0), nota)
                out.append(estrazione)
                if on_page is not None:
                    on_page(estrazione, i, totale)
                if diario is not None:
                    diario.registra_pagina(
                        pagina_id=estrazione.pagina_id,
                        ms=estrazione.ms,
                        motore_usato=estrazione.motore_usato,
                        chars=len(estrazione.testo),
                        nota=estrazione.nota,
                        extra={"scartato": estrazione.scartato} if estrazione.scartato else None,
                    )
                continue
            ultimo_errore: str | None = None
            respinto: str | None = None
            riuscito: EstrazionePagina | None = None
            for _ in range(2):
                try:
                    testo, motore = self._infer(i, img)
                    if not testo.strip():
                        ultimo_errore = "output vuoto/anomalo"
                        continue
                    motivo = _motivo_anomalia(
                        testo,
                        lingue_attese=lingue_attese,
                        soglia_righe_loop=soglia_righe_loop,
                        ignora_eco=ignora_eco,
                    )
                    if motivo is not None:
                        ultimo_errore = motivo + "; fail-fast (senza retry)"
                        respinto = testo[:MAX_SCARTATO]
                        break
                    riuscito = EstrazionePagina(i, testo, motore, _ms(t0))
                    break
                except InferenzaError as e:
                    ultimo_errore = str(e)
                    if _è_timeout(e):
                        break
                    continue
            if riuscito is None:
                testo = self._fallback(i, img)
                nota_fallback: str | None = ultimo_errore
                corpo = testo.strip()
                if not corpo:
                    nota_fallback = ((ultimo_errore + "; ") if ultimo_errore else "") + "fallback vuoto"
                elif len(corpo) < 20:
                    nota_fallback = ((ultimo_errore + "; ") if ultimo_errore else "") + (
                        f"fallback debole ({len(corpo)} char)"
                    )
                riuscito = EstrazionePagina(i, testo, "cpu-tesseract", _ms(t0), nota_fallback, respinto)
            out.append(riuscito)
            if on_page is not None:
                on_page(riuscito, i, totale)
            if diario is not None:
                diario.registra_pagina(
                    pagina_id=riuscito.pagina_id,
                    ms=riuscito.ms,
                    motore_usato=riuscito.motore_usato,
                    chars=len(riuscito.testo),
                    nota=riuscito.nota,
                    extra={"scartato": riuscito.scartato} if riuscito.scartato else None,
                )
        if diario is not None:
            stato = "cancelled" if (ferma is not None and ferma()) else "done"
            try:
                diario.chiudi(stato=stato)
            except Exception:
                pass
        return out

    # --- Compatibilità orchestrator (job registry) ---
    def submit_document(
        self,
        immagini: list[bytes],
        documento: str = "",
        on_page=None,
        diario=None,
        ferma: Callable[[], bool] | None = None,
        config=None,
    ) -> str:
        job_id = uuid.uuid4().hex[:8]
        job = OcrJob(job_id=job_id, documento=documento, stato="processing")
        self._jobs[job_id] = job
        # callback merging già gestito da submit; costruiamo on_page combinato se necessario via submit direttamente
        # Per compatibilità, lasciamo che submit gestisca diario/on_page
        pagine = self.submit(immagini, config=config, ferma=ferma, diario=diario, on_page=on_page)
        job.estrazioni = [
            EstrazionePagina(p.pagina_id, p.testo, p.motore_usato, p.ms, p.nota, p.scartato)
            for p in pagine
        ]
        # Estrazione alias for job.estrazioni compatibility (tests use job.estrazioni[].motore_usato etc)
        # Need to also keep Estrazione type compatible: job.estrazioni uses same field names
        job.stato = "cancelled" if (ferma is not None and ferma()) else "done"
        # diario chiudi già fatto in submit; se non c'era diario, submit already handled none
        # Ma se submit ha già chiuso, una seconda chiudi sarebbe duplicata: submit già chiude se diario != None, quindi non richiamare
        return job_id

    def cancel(self, job_id: str) -> None:
        job = self._jobs.get(job_id)
        if job is None:
            raise KeyError(job_id)
        if job.stato in ("queued", "processing"):
            job.stato = "cancelled"

    def get_result(self, job_id: str) -> OcrJob:
        try:
            return self._jobs[job_id]
        except KeyError:
            raise KeyError(job_id) from None


def elabora_pagine(
    immagini: list[bytes],
    infer: Callable[[int, bytes], tuple[str, str]],
    fallback: Callable[[int, bytes], str],
    sorgente: str = "bundlato",
    on_page: Callable[[EstrazionePagina, int, int], None] | None = None,
    ferma: Callable[[], bool] | None = None,
    lingue_attese: tuple[str, ...] = ("it",),
    soglia_righe_loop: int = 5,
    ignora_eco: bool = False,
) -> list[EstrazionePagina]:
    """Compat: delega a OcrPipeline.submit (mantiene firma originale)."""
    p = OcrPipeline(
        infer=infer,
        fallback=fallback,
        sorgente=sorgente,
        lingue_attese=lingue_attese,
        soglia_righe_loop=soglia_righe_loop,
        ignora_eco=ignora_eco,
    )
    return p.submit(immagini, ferma=ferma, on_page=on_page)


def _ms(t0: float) -> int:
    return int((time.monotonic() - t0) * 1000)
