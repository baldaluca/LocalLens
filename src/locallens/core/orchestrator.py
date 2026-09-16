"""Orchestrazione Documento → Pagine → Estrazioni. Prompt/template dal preset, mai hardcoded."""
from dataclasses import dataclass, field


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
    def submit_document(self, path: str) -> str:
        """Accoda un Documento, elaborazione sequenziale per Pagina. Da implementare."""
        raise NotImplementedError

    def cancel(self, job_id: str) -> None:
        raise NotImplementedError

    def get_result(self, job_id: str) -> OcrJob:
        raise NotImplementedError
