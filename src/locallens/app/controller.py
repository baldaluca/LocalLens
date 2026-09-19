"""DocumentController Presenter: owns Documento → Pagine → Estrazioni workflow, Config transaction, Worker."""

from __future__ import annotations

from PySide6.QtCore import QObject, QThreadPool, Signal

from locallens.config.settings import Config, as_dict, salva as salva_impostazioni
from locallens.core.orchestrator import Estrazione


class DocumentController(QObject):
    """Presenter owning estrazioni state, Config transaction, Worker lifecycle.

    Consumes: Config, EngineFactory, OcrEngine (via factory.rebuild).
    Produces: estrazioni list, filtered_text, open_document/open_images, cancel, estrazioni_changed signal.
    """

    estrazioni_changed = Signal(list)
    stato_changed = Signal(str)
    banner_changed = Signal(str)
    errore = Signal(str, str)  # job_id, messaggio
    progresso = Signal(int, int)  # i, n

    def __init__(self, config: Config, factory) -> None:
        super().__init__()
        # Config seam: accept Config or dict, normalize to Config typed frozen
        if isinstance(config, dict):
            self._config: Config = Config.from_dict(config)
        else:
            self._config = config
        self._factory = factory
        self._estrazioni: list[Estrazione] = []
        self._worker: object | None = None
        self._engine = None
        self._filtrata: int | None = None
        # Build initial engine if factory provided
        if factory is not None:
            try:
                eng, stato, banner = self._rebuild_engine(self._config)
                self._engine = eng
                # emit initial stato/banner if needed (view may bind)
                # we store last stato/banner for view sync
                self._last_stato = stato
                self._last_banner = banner
            except Exception:
                self._engine = None
                self._last_stato = ""
                self._last_banner = ""
        else:
            self._last_stato = ""
            self._last_banner = ""

    # --- config/engine access ---
    @property
    def config(self) -> Config:
        return self._config

    @config.setter
    def config(self, value: Config | dict) -> None:
        if isinstance(value, dict):
            self._config = Config.from_dict(value)
        else:
            self._config = value

    @property
    def engine(self):
        return self._engine

    def set_engine(self, engine) -> None:
        self._engine = engine

    def _rebuild_engine(self, cfg: Config):
        """Delegate to factory rebuild; handles factory returning tuple or engine."""
        if self._factory is None:
            return None, "", ""
        # Factory conforming to EngineFactory interface: rebuild(config)->(engine,stato,banner)
        if hasattr(self._factory, "rebuild"):
            return self._factory.rebuild(cfg)
        # callable fallback
        if callable(self._factory):
            res = self._factory(cfg)
            if isinstance(res, tuple) and len(res) == 3:
                return res
            return res, "", ""
        return None, "", ""

    def _engine_or_rebuild(self):
        if self._engine is not None:
            return self._engine
        eng, stato, banner = self._rebuild_engine(self._config)
        self._engine = eng
        self._last_stato = stato
        self._last_banner = banner
        return eng

    # --- estrazioni / filtered ---
    @property
    def estrazioni(self) -> list[Estrazione]:
        return list(self._estrazioni)

    def filtered_text(self, row: int | None) -> str:
        if not self._estrazioni:
            return ""
        if row is None:
            return "\n\n".join(e.testo for e in self._estrazioni)
        if 0 <= row < len(self._estrazioni):
            return self._estrazioni[row].testo
        return "\n\n".join(e.testo for e in self._estrazioni)

    # --- diario helper (moved from finestra._nuovo_diario) ---
    def _nuovo_diario(self, documento: str):
        try:
            from locallens.core.diario import avvia_job

            return avvia_job(
                None,
                documento=documento,
                sorgente=as_dict(self._config).get("sorgente", ""),
                preset_id=as_dict(self._config).get("preset_id", ""),
            )
        except OSError:
            return None

    # --- open / cancel ---
    def open_images(self, immagini: list[bytes], documento: str = "") -> None:
        """Elabora in background: crea OcrWorker e notifica via segnali."""
        # reset state
        self._estrazioni = []
        self._filtrata = None
        # lazy engine
        engine = self._engine_or_rebuild()
        if engine is None:
            # no engine available: emit error banner and empty result
            self.errore.emit("doc", "Engine non pronto")
            self.estrazioni_changed.emit([])
            return
        diario = self._nuovo_diario(documento)
        job_id = getattr(diario, "job_id", None) or "doc"
        from locallens.app import worker as _wmod

        worker = _wmod.OcrWorker(job_id=job_id, engine=engine, immagini=immagini, diario=diario)
        worker.segnali.pagina.connect(self._on_pagina)
        worker.segnali.finito.connect(self._on_finito)
        worker.segnali.errore.connect(self._on_errore)
        self._worker = worker
        QThreadPool.globalInstance().start(worker)

    def open_document(self, path: str) -> None:
        """Carica Documento (immagine o PDF) e delega a open_images."""
        from locallens.app.ingresso import carica_documento

        immagini = carica_documento(path)
        self.open_images(immagini, documento=path)

    def cancel(self) -> None:
        if self._worker is not None:
            self._worker.annulla()

    # --- signal handlers (moved from finestra._on_pagina/_on_finito/_on_errore) ---
    def _on_pagina(self, estrazione, i: int, n: int) -> None:
        self._estrazioni.append(estrazione)
        self.progresso.emit(i, n)

    def _on_finito(self, job_id: str) -> None:
        # emit final list
        self.estrazioni_changed.emit(list(self._estrazioni))
        self._worker = None

    def _on_errore(self, job_id: str, messaggio: str) -> None:
        self.errore.emit(job_id, messaggio)
        self.estrazioni_changed.emit(list(self._estrazioni))
        self._worker = None

    # --- settings transaction (salva_impostazioni) ---
    def apply_settings(self, valori: dict) -> tuple[str, str, str | None]:
        """Transazione Config: merge valori, normalizza, salva, rebuild engine.

        Ritorna (stato, banner, avviso_normalizza).
        """
        from dataclasses import fields, replace

        from locallens.core.fabbrica import normalizza_sorgente_da_conf
        from locallens.config.presets import preset_da_conf

        # merge valori into Config (frozen via replace), filtrando chiavi ignote
        cfg_fields = {f.name for f in fields(self._config)}
        filtrati = {k: v for k, v in valori.items() if k in cfg_fields}
        # handle url_gpu_locale / url_esterno che esistono in Config, già filtrati
        # merge
        nuova_cfg = replace(self._config, **filtrati) if filtrati else self._config
        # normalizza sorgente (bundlato→esterno se GPU assente)
        conf_dict = as_dict(nuova_cfg)
        try:
            preset = preset_da_conf(conf_dict)
        except Exception:
            preset = None
        nuovo_dict, avviso = normalizza_sorgente_da_conf(conf_dict, preset) if preset else (conf_dict, None)
        # normalize dict back to Config
        nuova_cfg = Config.from_dict(nuovo_dict)
        self._config = nuova_cfg
        # salva su disco (esclude SEGRET)
        try:
            salva_impostazioni(self._config)
        except Exception:
            pass
        # rebuild engine
        try:
            engine, stato, banner = self._rebuild_engine(self._config)
        except Exception as e:
            from locallens.core.orchestrator import solo_cpu

            engine = solo_cpu(str(e))
            stato = "errore"
            banner = str(e)
        self._engine = engine
        # merge avviso normalizza con banner rebuilt
        banner_finale = "; ".join(b for b in (avviso, banner) if b)
        self._last_stato = stato
        self._last_banner = banner_finale
        self.stato_changed.emit(stato)
        if banner_finale:
            self.banner_changed.emit(banner_finale)
        return stato, banner_finale, avviso

    # compatibility alias for spec that may call save_settings
    def save_settings(self, valori: dict):
        return self.apply_settings(valori)
