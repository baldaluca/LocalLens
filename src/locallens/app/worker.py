"""Worker QRunnable: esegue OcrEngine fuori dal GUI thread, notifica via segnali."""

import threading

from PySide6.QtCore import QObject, QRunnable, Signal


class SegnaliWorker(QObject):
    pagina = Signal(object, int, int)  # EstrazionePagina, indice, totale
    finito = Signal(str)  # job_id
    errore = Signal(str, str)  # job_id, messaggio


class OcrWorker(QRunnable):
    def __init__(self, job_id: str, engine, immagini: list[bytes], diario=None) -> None:
        super().__init__()
        self.job_id = job_id
        self.engine = engine
        self.immagini = immagini
        self.diario = diario
        self.segnali = SegnaliWorker()
        self._ferma = threading.Event()

    def annulla(self) -> None:
        """Segnala l'interruzione: la Pagina corrente finisce, le altre saltano."""
        self._ferma.set()

    def run(self) -> None:
        try:
            extra = {}
            if self.diario is not None:
                extra["diario"] = self.diario
            self.engine.submit_document(
                self.immagini,
                on_page=lambda e, i, n: self.segnali.pagina.emit(e, i, n),
                ferma=self._ferma.is_set,
                **extra,
            )
        except Exception as e:  # noqa: BLE001 — frontiera worker/GUI: tutto diventa segnale (RNF4)
            self.segnali.errore.emit(self.job_id, str(e))
            return
        self.segnali.finito.emit(self.job_id)
