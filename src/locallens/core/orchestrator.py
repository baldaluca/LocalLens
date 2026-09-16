"""Orchestrazione Documento → Pagine → Estrazioni. Prompt/template dal preset, mai hardcoded."""
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field

from locallens.core.pipeline import elabora_pagine


@dataclass(frozen=True)
class Estrazione:
    pagina_id: int
    testo: str
    motore_usato: str  # cuda | hip | vulkan | cpu-llama | cpu-tesseract | esterno
    ms: int = 0


@dataclass
class OcrJob:
    job_id: str
    documento: str
    stato: str = "queued"  # queued | processing | done | failed | cancelled
    estrazioni: list[Estrazione] = field(default_factory=list)


class OcrEngine:
    """Sincrono (la GUI lo esegue in worker thread). Funzioni iniettabili per i test."""

    def __init__(
        self,
        infer: Callable[[int, bytes], tuple[str, str]] | None = None,
        fallback: Callable[[int, bytes], str] | None = None,
        sorgente: str = "bundlato",
    ) -> None:
        if infer is None or fallback is None:
            raise ValueError("infer e fallback vanno iniettati (il client HTTP si cabla al seam successivo)")
        self._infer = infer
        self._fallback = fallback
        self._sorgente = sorgente
        self._jobs: dict[str, OcrJob] = {}

    def submit_document(self, immagini: list[bytes], documento: str = "") -> str:
        job_id = uuid.uuid4().hex[:8]
        job = OcrJob(job_id=job_id, documento=documento, stato="processing")
        self._jobs[job_id] = job
        pagine = elabora_pagine(
            immagini, infer=self._infer, fallback=self._fallback, sorgente=self._sorgente
        )
        job.estrazioni = [
            Estrazione(pagina_id=p.pagina_id, testo=p.testo, motore_usato=p.motore_usato, ms=p.ms)
            for p in pagine
        ]
        job.stato = "done"
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
