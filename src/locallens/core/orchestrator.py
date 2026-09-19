"""Orchestrazione sottile: HttpInferAdapter + OcrPipeline. Prompt/template dal preset, mai hardcoded."""

from locallens.core.client import HttpInferAdapter
from locallens.core.pipeline import EstrazionePagina, InferenzaError, OcrJob, OcrPipeline

# Alias compatibilità: Estrazione = EstrazionePagina, OcrEngine = OcrPipeline
Estrazione = EstrazionePagina
OcrEngine = OcrPipeline

__all__ = ["Estrazione", "EstrazionePagina", "OcrJob", "OcrEngine", "OcrPipeline", "HttpInferAdapter", "solo_cpu", "crea_engine", "crea_engine_cloud"]


def solo_cpu(motivo: str) -> OcrPipeline:
    """Engine CPU-only: infer solleva sempre, fallback Tesseract reale."""
    from locallens.fallback.tesseract import estrai

    def infer(pagina_id: int, png: bytes):
        raise InferenzaError(motivo)

    return OcrPipeline(infer=infer, fallback=lambda p, i: estrai(i), sorgente="nessuno")


def _make_infer(sorgente: str, base_url: str, preset, modello: str, prompt: str, token: str, max_side: int, contrasto: bool, timeout: int, post, motore: str, max_tokens: int = 2048):
    """Compat: restituisce callable infer via HttpInferAdapter."""
    return HttpInferAdapter(
        base_url=base_url,
        preset=preset if sorgente != "esterno" else None,
        modello=modello,
        prompt=prompt,
        token=token,
        max_side=max_side,
        contrasto=contrasto,
        timeout=timeout,
        post=post,
        motore=motore,
        max_tokens=max_tokens,
        sorgente=sorgente,
    )


def crea_engine(
    base_url: str,
    preset,
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
) -> OcrPipeline:
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

    return OcrPipeline(
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
) -> OcrPipeline:
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

    return OcrPipeline(
        infer=infer, fallback=fallback or fb_default, sorgente=sorgente,
        lingue_attese=lingue_attese, soglia_righe_loop=soglia_righe_loop,
        ignora_eco=ignora_eco,
    )
