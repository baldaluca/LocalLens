"""Impostazioni utente: TOML in path OS-standard. Vedi config.example.toml."""

import os
import sys
import tomllib
from dataclasses import asdict, dataclass, fields, replace
from pathlib import Path
from typing import Literal

DEFAULTS = {
    "lingua": "en",
    "sorgente": "bundlato",
    "url_esterno": "http://127.0.0.1:8011",
    "url_gpu_locale": "http://127.0.0.1:8011",
    "token_esterno": "",
    "modello_esterno": "",
    "prompt_esterno": "Transcribe the document text exactly. No commentary.",
    "preset_id": "lighton-ocr-q8_0",
    "backend_override": "",
    "porta": 8011,
    "dpi_pdf": 300,
    "max_side_px": 2048,
    "contrasto": False,
    "lingue_filtro": "it",
    "soglia_righe_loop": 5,
    "ignora_eco": False,
    "tema": "chiaro",
}

#: Chiavi mai scritte su disco (segreti di sessione).
SEGRET = ("token_esterno",)


def _scrivi_toml(dati: dict, path: Path) -> Path:
    """Helper DRY per Config.save/salva: serializza TOML con escape e filtro SEGRET."""
    path.parent.mkdir(parents=True, exist_ok=True)
    righe: list[str] = []
    for chiave, valore in dati.items():
        if chiave in SEGRET:
            continue
        if isinstance(valore, str):
            sicura = valore.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
            righe.append(f'{chiave} = "{sicura}"')
        elif isinstance(valore, bool):
            righe.append(f"{chiave} = {'true' if valore else 'false'}")
        else:
            righe.append(f"{chiave} = {valore}")
    path.write_text("\n".join(righe) + "\n", encoding="utf-8")
    return path


def percorso_config(
    piattaforma: str | None = None, home: str = "", appdata: str = ""
) -> Path:
    piattaforma = piattaforma or sys.platform
    if piattaforma == "win32":
        base = Path(appdata or os.environ.get("APPDATA", "")) / "LocalLens"
    else:
        base = Path(home or str(Path.home())) / ".config" / "locallens"
    return base / "config.toml"


@dataclass(frozen=True)
class Config:
    """Config typed: seam between dict TOML and dataclass (module settings)."""

    lingua: Literal["it", "en"] = "en"
    sorgente: Literal["bundlato", "esterno", "nessuno"] = "bundlato"
    url_esterno: str = "http://127.0.0.1:8011"
    url_gpu_locale: str = "http://127.0.0.1:8011"
    token_esterno: str = ""
    modello_esterno: str = ""
    prompt_esterno: str = "Transcribe the document text exactly. No commentary."
    preset_id: str = "lighton-ocr-q8_0"
    backend_override: str = ""
    porta: int = 8011
    dpi_pdf: int = 300
    max_side_px: int = 2048
    contrasto: bool = False
    lingue_filtro: str = "it"
    soglia_righe_loop: int = 5
    ignora_eco: bool = False
    tema: str = "chiaro"

    @classmethod
    def load(cls, path: Path | None = None) -> "Config":
        from locallens.app.lingua import LINGUE

        p = Path(path) if path is not None else percorso_config()
        if not p.is_file():
            return cls().validated()
        with open(p, "rb") as f:
            dati = tomllib.load(f)
        cfg_fields = {f.name for f in fields(cls)}
        filtrati = {k: v for k, v in dati.items() if k in cfg_fields and k not in SEGRET}
        base = asdict(cls())
        base.update(filtrati)
        # SEGRET mai da disco: resta default ""
        for chiave in SEGRET:
            base[chiave] = DEFAULTS.get(chiave, "")
        cfg = cls(**base)
        return cfg.validated()

    def save(self, path: Path | None = None) -> Path:
        p = Path(path) if path is not None else percorso_config()
        return _scrivi_toml(self.to_dict(), p)

    def validated(self) -> "Config":
        from locallens.app.lingua import LINGUE

        lingua = self.lingua if self.lingua in LINGUE else "en"
        sorgenti = ("bundlato", "esterno", "nessuno")
        sorgente = self.sorgente if self.sorgente in sorgenti else "bundlato"
        if lingua == self.lingua and sorgente == self.sorgente:
            return self
        return replace(self, lingua=lingua, sorgente=sorgente)

    def effective_url(self) -> str:
        return self.url_gpu_locale if self.sorgente == "bundlato" else self.url_esterno

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Config":
        cfg_fields = {f.name for f in fields(cls)}
        filtrati = {k: v for k, v in d.items() if k in cfg_fields}
        # SEGRET passato in dict è in memoria (sessione); se assente usa default
        base = asdict(cls())
        base.update(filtrati)
        cfg = cls(**base)
        return cfg.validated()


def as_dict(conf: "Config | dict") -> dict:
    """Seam Config: normalizza dict o Config a dict (single helper)."""
    if isinstance(conf, dict):
        return conf
    if hasattr(conf, "to_dict"):
        try:
            return conf.to_dict()  # type: ignore[attr-defined]
        except Exception:
            pass
    try:
        return dict(conf)  # type: ignore[arg-type]
    except Exception:
        return conf  # type: ignore[return-value]


def carica(path: Path | None = None) -> dict:
    return Config.load(path).to_dict()


def salva(conf: dict | Config, path: Path | None = None) -> Path:
    conf_dict = as_dict(conf)
    p = Path(path) if path is not None else percorso_config()
    return _scrivi_toml(conf_dict, p)
