"""Impostazioni utente: TOML in path OS-standard. Vedi config.example.toml."""

import os
import sys
import tomllib
from pathlib import Path

DEFAULTS = {
    "sorgente": "bundlato",
    "url_esterno": "http://127.0.0.1:8011",
    "preset_id": "glm-ocr-q8_0",
    "backend_override": "",
    "porta": 8011,
    "dpi_pdf": 300,
    "max_side_px": 2048,
    "deskew": False,
    "crop": False,
    "contrasto": False,
}


def percorso_config(
    piattaforma: str | None = None, home: str = "", appdata: str = ""
) -> Path:
    piattaforma = piattaforma or sys.platform
    if piattaforma == "win32":
        base = Path(appdata or os.environ.get("APPDATA", "")) / "LocalLens"
    else:
        base = Path(home or str(Path.home())) / ".config" / "locallens"
    return base / "config.toml"


def carica(path: Path | None = None) -> dict:
    path = path or percorso_config()
    if not path.is_file():
        return dict(DEFAULTS)
    with open(path, "rb") as f:
        dati = tomllib.load(f)
    conf = dict(DEFAULTS)
    conf.update({k: v for k, v in dati.items() if k in DEFAULTS})
    return conf


def salva(conf: dict, path: Path | None = None) -> Path:
    path = path or percorso_config()
    path.parent.mkdir(parents=True, exist_ok=True)
    righe = []
    for chiave, valore in conf.items():
        if isinstance(valore, str):
            righe.append(f'{chiave} = "{valore}"')
        elif isinstance(valore, bool):
            righe.append(f"{chiave} = {'true' if valore else 'false'}")
        else:
            righe.append(f"{chiave} = {valore}")
    path.write_text("\n".join(righe) + "\n", encoding="utf-8")
    return path
