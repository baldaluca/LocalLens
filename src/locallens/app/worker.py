"""Worker QRunnable: esegue OcrEngine fuori dal GUI thread, notifica via segnali."""

from PySide6.QtCore import QObject, QRunnable, Signal


class SegnaliWorker(QObject):
    pagina = Signal(object, int, int)  # EstrazionePagina, indice, totale
    finito = Signal(str)  # job_id
    errore = Signal(str, str)  # job_id, messaggio


class OcrWorker(QRunnable):
    def __init__(self, job_id: str, engine, immagini: list[bytes]) -> None:
        super().__init__()
        self.job_id = job_id
        self.engine = engine
        self.immagini = immagini
        self.segnali = SegnaliWorker()

    def run(self) -> None:
        try:
            self.engine.submit_document(
                self.immagini,
                on_page=lambda e, i, n: self.segnali.pagina.emit(e, i, n),
            )
        except Exception as e:  # noqa: BLE001 — frontiera worker/GUI: tutto diventa segnale (RNF4)
            self.segnali.errore.emit(self.job_id, str(e))
            return
        self.segnali.finito.emit(self.job_id)
