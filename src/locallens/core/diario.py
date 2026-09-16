"""Diario esecuzioni: un file JSONL per job, un evento per riga.

Eventi: job_avviato → pagina* → job_chiuso. Leggibile con qualsiasi
parser JSONL, senza l'app. I tempi/token server (quando disponibili)
viaggiano nel campo `extra` senza rompere lo schema.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

__all__ = ["Diario", "avvia_job", "percorso_diario"]


def percorso_diario(job_id: str, base: Path | str | None = None) -> Path:
    """`~/.config/locallens/esecuzioni/<job_id>.jsonl` (o %APPDATA% su win32)."""
    if base is None:
        from locallens.config.settings import percorso_config

        base = percorso_config().parent
    return Path(base) / "esecuzioni" / f"{job_id}.jsonl"


def _ts() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class Diario:
    def __init__(self, percorso: Path, job_id: str) -> None:
        self.percorso = percorso
        self.job_id = job_id

    def _scrivi(self, evento: dict) -> None:
        riga = json.dumps(evento, ensure_ascii=False)
        with open(self.percorso, "a", encoding="utf-8") as f:
            f.write(riga + "\n")

    def registra_pagina(
        self,
        pagina_id: int,
        ms: int,
        motore_usato: str,
        chars: int,
        nota: str | None = None,
        extra: dict | None = None,
    ) -> None:
        evento: dict = {
            "evento": "pagina",
            "ts": _ts(),
            "job_id": self.job_id,
            "pagina_id": pagina_id,
            "ms": ms,
            "motore_usato": motore_usato,
            "chars": chars,
        }
        if nota is not None:
            evento["nota"] = nota
        if extra:
            evento["extra"] = dict(extra)
        self._scrivi(evento)

    def chiudi(self, stato: str = "done") -> None:
        self._scrivi(
            {"evento": "job_chiuso", "ts": _ts(), "job_id": self.job_id, "stato": stato}
        )


def avvia_job(
    base: Path | str | None,
    *,
    job_id: str | None = None,
    documento: str = "",
    modello: str = "",
    sorgente: str = "",
    motore: str = "",
    preset_id: str = "",
    server_args: dict | None = None,
) -> Diario:
    jid = job_id or uuid.uuid4().hex[:8]
    percorso = percorso_diario(jid, base)
    percorso.parent.mkdir(parents=True, exist_ok=True)
    diario = Diario(percorso, jid)
    diario._scrivi(
        {
            "evento": "job_avviato",
            "ts": _ts(),
            "job_id": jid,
            "documento": documento,
            "modello": modello,
            "sorgente": sorgente,
            "motore": motore,
            "preset_id": preset_id,
            "server_args": dict(server_args or {}),
        }
    )
    return diario
