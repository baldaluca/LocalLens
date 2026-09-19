"""Loader PresetModello da TOML. Nessun template hardcoded in core."""
import tomllib
from dataclasses import dataclass, field


@dataclass(frozen=True)
class PresetModello:
    id: str
    display_name: str = ""
    hf_repo: str = ""
    gguf_file: str = ""
    mmproj_file: str = ""
    chat_template: str = ""
    vram_min_mb: int = 0
    ctx_size: int = 4096
    max_side_px: int = 2048
    max_tokens: int = 2048
    enabled: bool = True
    server_args: dict = field(default_factory=dict)
    prompt: dict = field(default_factory=dict)


_OBBLIGATORI = ("gguf_file", "mmproj_file", "chat_template", "vram_min_mb", "ctx_size", "max_side_px", "max_tokens")


def load_preset(path: str) -> PresetModello:
    with open(path, "rb") as f:
        d = tomllib.load(f)
    mancanti = [k for k in _OBBLIGATORI if not d.get(k)]
    if not d.get("id") or mancanti:
        raise ValueError(f"preset non valido {path}: mancano {mancanti}")
    return PresetModello(
        id=d["id"],
        display_name=d.get("display_name", ""),
        hf_repo=d.get("hf_repo", ""),
        gguf_file=d["gguf_file"],
        mmproj_file=d["mmproj_file"],
        chat_template=d["chat_template"],
        vram_min_mb=int(d["vram_min_mb"]),
        ctx_size=int(d["ctx_size"]),
        max_side_px=int(d["max_side_px"]),
        max_tokens=int(d["max_tokens"]),
        enabled=bool(d.get("enabled", True)),
        server_args=dict(d.get("server_args", {})),
        prompt=dict(d.get("prompt", {})),
    )


def preset_da_conf(conf) -> PresetModello:
    """Preset da conf['preset_id'], con fallback al default shipped."""
    from locallens.config.percorsi import risorsa

    # seam Config: accetta dict o Config
    if not isinstance(conf, dict):
        try:
            conf = conf.to_dict()  # type: ignore[union-attr]
        except AttributeError:
            conf = dict(conf)  # type: ignore[arg-type]
    pid = conf.get("preset_id", "") or "lighton-ocr-q8_0"
    try:
        return load_preset(str(risorsa("presets", f"{pid}.toml")))
    except (ValueError, OSError):
        return load_preset(str(risorsa("presets", "lighton-ocr-q8_0.toml")))


def seleziona_preset(vram_mb: int | None, candidati: list[str]) -> str:
    """Scelta preset per VRAM. vram None = CPU-only: ritorna default shipped (nessun modello GPU usato)."""
    if not candidati:
        raise ValueError("nessun candidato")
    return candidati[0]


def elenco_preset(cartelle: list) -> list[str]:
    """Id dei preset trovati come *.toml nelle cartelle (ordinati, unici).

    Tollerante: salta file non TOML o senza id. Usato dal dialogo
    Impostazioni per offrire tutti i PresetModello disponibili.
    """
    from pathlib import Path

    trovati: list[str] = []
    for cartella in cartelle:
        base = Path(cartella)
        if not base.is_dir():
            continue
        for f in sorted(base.glob("*.toml")):
            try:
                with open(f, "rb") as fh:
                    pid = tomllib.load(fh).get("id")
            except (OSError, ValueError):
                continue
            pid = pid or f.stem
            if pid not in trovati:
                trovati.append(pid)
    return sorted(trovati)
