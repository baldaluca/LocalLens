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
    motore_usato: str  # cuda | hip | vulkan | cpu-llama | cpu-tesseract | esterno | bundlato
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
        lingue_attese: tuple[str, ...] = ("it",),
        soglia_righe_loop: int = 5,
        ignora_eco: bool = False,
    ) -> None:
        if infer is None or fallback is None:
            raise ValueError(
                "infer e fallback vanno iniettati (il client HTTP si cabla al seam successivo)"
            )
        self._infer = infer
        self._fallback = fallback
        self._sorgente = sorgente
        self._lingue_attese = lingue_attese
        self._soglia_righe_loop = soglia_righe_loop
        self._ignora_eco = ignora_eco
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
                        extra={"scartato": e.scartato} if e.scartato else None,
                    )

        pagine = elabora_pagine(
            immagini,
            infer=self._infer,
            fallback=self._fallback,
            sorgente=self._sorgente,
            on_page=callback,
            ferma=ferma,
            lingue_attese=self._lingue_attese,
            soglia_righe_loop=self._soglia_righe_loop,
            ignora_eco=self._ignora_eco,
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


def solo_cpu(motivo: str) -> OcrEngine:
    """Engine CPU-only: infer solleva sempre, fallback Tesseract reale."""
    from locallens.core.errori import InferenzaError
    from locallens.fallback.tesseract import estrai

    def infer(pagina_id: int, png: bytes):
        raise InferenzaError(motivo)

    return OcrEngine(infer=infer, fallback=lambda p, i: estrai(i), sorgente="nessuno")


def _make_infer(sorgente: str, base_url: str, preset, modello: str, prompt: str, token: str, max_side: int, contrasto: bool, timeout: int, post, motore: str, max_tokens: int = 2048):
    """Unified prepara→build_payload→invia_chat closure for both sorgenti."""
    from locallens.preprocessing.immagini import prepara

    if sorgente == "esterno":
        def infer(pagina_id: int, png: bytes) -> tuple[str, str]:
            try:
                pronta = prepara(png, max_side=max_side, contrasto=contrasto)
            except Exception as e:
                from locallens.core.errori import InferenzaError

                raise InferenzaError(f"preprocessing fallito: {e}") from e
            from locallens.core.client import build_ollama_payload, dialetto

            b64 = base64.b64encode(pronta).decode()
            if dialetto(base_url) == "ollama":
                payload = build_ollama_payload(b64, prompt, modello, max_tokens=max_tokens)
            else:
                payload = build_chat_payload(b64, prompt, modello, max_tokens=max_tokens)
            testo = invia_chat(base_url, payload, post=post, timeout=timeout, token=token or None)
            return testo, "esterno"

        return infer

    # bundlato / locale
    prompt_local = preset.prompt.get("system", "Transcribe.") if preset else prompt
    limite = min(max_side, preset.max_side_px) if preset else max_side

    def infer(pagina_id: int, png: bytes) -> tuple[str, str]:
        try:
            pronta = prepara(png, max_side=limite, contrasto=contrasto)
        except Exception as e:
            from locallens.core.errori import InferenzaError

            raise InferenzaError(f"preprocessing fallito: {e}") from e
        payload = build_chat_payload(
            base64.b64encode(pronta).decode(), prompt_local, preset.id,
            max_tokens=preset.max_tokens,
        )
        endpoint = base_url.rstrip("/") + "/v1/chat/completions"
        return invia_chat(endpoint, payload, post=post, timeout=timeout), motore

    return infer


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
    lingue_attese: tuple[str, ...] = ("it",),
    soglia_righe_loop: int = 5,
    ignora_eco: bool = False,
) -> OcrEngine:
    """Collega client HTTP + fallback Tesseract dietro la pipeline. Default = tesseract reale."""
    from locallens.fallback.tesseract import estrai as tesseract_estrai

    infer = _make_infer(
        sorgente="bundlato",
        base_url=base_url,
        preset=preset,
        modello=preset.id,
        prompt=preset.prompt.get("system", "Transcribe."),
        token="",
        max_side=max_side,
        contrasto=contrasto,
        timeout=timeout,
        post=post,
        motore=motore,
    )

    def fb_default(_pagina_id: int, png: bytes) -> str:
        return tesseract_estrai(png)

    return OcrEngine(
        infer=infer, fallback=fallback or fb_default, sorgente=sorgente,
        lingue_attese=lingue_attese, soglia_righe_loop=soglia_righe_loop,
        ignora_eco=ignora_eco,
    )


def crea_engine_cloud(
    base_url: str,
    modello: str,
    prompt: str,
    token: str = "",
    sorgente: str = "esterno",
    post=None,
    fallback=None,
    max_side: int = 2048,
    max_tokens: int = 2048,
    contrasto: bool = False,
    timeout: int = 600,
    lingue_attese: tuple[str, ...] = ("it",),
    soglia_righe_loop: int = 5,
    ignora_eco: bool = False,
) -> OcrEngine:
    """Engine per servizio cloud OpenAI-compatibile: tutto a mano, nessun preset."""
    from locallens.fallback.tesseract import estrai as tesseract_estrai

    infer = _make_infer(
        sorgente="esterno",
        base_url=base_url,
        preset=None,
        modello=modello,
        prompt=prompt,
        token=token,
        max_side=max_side,
        contrasto=contrasto,
        timeout=timeout,
        post=post,
        motore="esterno",
        max_tokens=max_tokens,
    )

    def fb_default(_pagina_id: int, png: bytes) -> str:
        return tesseract_estrai(png)

    return OcrEngine(
        infer=infer, fallback=fallback or fb_default, sorgente=sorgente,
        lingue_attese=lingue_attese, soglia_righe_loop=soglia_righe_loop,
        ignora_eco=ignora_eco,
    )
