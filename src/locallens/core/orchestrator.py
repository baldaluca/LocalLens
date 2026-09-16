"""Orchestrazione Documento → Pagine → Estrazioni. Prompt/template dal preset, mai hardcoded."""

import base64
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field

from locallens.config.presets import PresetModello
from locallens.core.client import build_chat_payload, invia_chat
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
            raise ValueError(
                "infer e fallback vanno iniettati (il client HTTP si cabla al seam successivo)"
            )
        self._infer = infer
        self._fallback = fallback
        self._sorgente = sorgente
        self._jobs: dict[str, OcrJob] = {}

    def submit_document(
        self,
        immagini: list[bytes],
        documento: str = "",
        on_page=None,
        diario=None,
        ferma: Callable[[], bool] | None = None,
    ) -> str:
        job_id = uuid.uuid4().hex[:8]
        job = OcrJob(job_id=job_id, documento=documento, stato="processing")
        self._jobs[job_id] = job
        if on_page is None and diario is None:
            callback = None
        else:

            def callback(e, i, n):
                if on_page is not None:
                    on_page(e, i, n)
                if diario is not None:
                    diario.registra_pagina(
                        pagina_id=e.pagina_id,
                        ms=e.ms,
                        motore_usato=e.motore_usato,
                        chars=len(e.testo),
                        nota=e.nota,
                    )

        pagine = elabora_pagine(
            immagini,
            infer=self._infer,
            fallback=self._fallback,
            sorgente=self._sorgente,
            on_page=callback,
            ferma=ferma,
        )
        job.estrazioni = [
            Estrazione(
                pagina_id=p.pagina_id,
                testo=p.testo,
                motore_usato=p.motore_usato,
                ms=p.ms,
            )
            for p in pagine
        ]
        job.stato = "cancelled" if (ferma is not None and ferma()) else "done"
        if diario is not None:
            diario.chiudi(stato=job.stato)
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


def crea_engine(
    base_url: str,
    preset: PresetModello,
    motore: str = "cuda",
    sorgente: str = "bundlato",
    post=None,
    fallback=None,
    max_side: int = 2048,
    contrasto: bool = False,
    timeout: int = 600,
) -> OcrEngine:
    """Collega client HTTP + fallback Tesseract dietro la pipeline. Default = tesseract reale."""
    from locallens.fallback.tesseract import estrai as tesseract_estrai
    from locallens.preprocessing.immagini import prepara

    prompt = preset.prompt.get("system", "Transcribe.")
    limite = min(max_side, preset.max_side_px)

    def infer(pagina_id: int, png: bytes) -> tuple[str, str]:
        try:
            pronta = prepara(png, max_side=limite, contrasto=contrasto)
        except Exception as e:
            from locallens.core.errori import InferenzaError

            raise InferenzaError(f"preprocessing fallito: {e}") from e
        payload = build_chat_payload(
            base64.b64encode(pronta).decode(), prompt, preset.id,
            max_tokens=preset.max_tokens,
        )
        return invia_chat(base_url, payload, post=post, timeout=timeout), motore

    def fb_default(_pagina_id: int, png: bytes) -> str:
        return tesseract_estrai(png)

    return OcrEngine(infer=infer, fallback=fallback or fb_default, sorgente=sorgente)
