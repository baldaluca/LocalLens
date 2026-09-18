"""Layering: app parla solo con core; core mai con __main__.

Controllo statico via AST sui soli statement import: fallisce se qualcuno
reintroduce `app -> __main__ / hwdetect` o `core/fabbrica -> __main__`
(`finestra.py` inoltre non deve importare `backend`).

Eccezione nota fuori scope (non toccare: finding parcheggiati):
`app/impostazioni.py` importa `locallens.backend.manager.is_url_privata`.
"""

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
APP_DIR = REPO / "src" / "locallens" / "app"
FABBRICA = REPO / "src" / "locallens" / "core" / "fabbrica.py"
FINESTRA = APP_DIR / "finestra.py"

# Fuori scope di questo finding (parcheggiato): non far fallire la suite,
# ma impedisci che ALTRI file app importino backend.
ECCEZIONI_BACKEND_NOTE = {"impostazioni.py"}


def _moduli_importati(path: Path) -> set[str]:
    albero = ast.parse(path.read_text(encoding="utf-8"))
    moduli: set[str] = set()
    for nodo in ast.walk(albero):
        if isinstance(nodo, ast.Import):
            moduli.update(a.name for a in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            moduli.add(nodo.module)
    return moduli


def test_app_non_importa_main_né_hwdetect():
    violazioni = []
    for f in sorted(APP_DIR.glob("*.py")):
        vietati = [
            mod
            for mod in _moduli_importati(f)
            if mod == "locallens.__main__" or mod.startswith("locallens.hwdetect")
        ]
        if vietati:
            violazioni.append(f"{f.name} importa {vietati}")
    assert violazioni == [], f"inversione layer in app: {violazioni}"


def test_finestra_non_importa_backend():
    moduli = _moduli_importati(FINESTRA)
    vietati = [m for m in moduli if m == "locallens.backend" or m.startswith("locallens.backend.")]
    assert vietati == [], f"finestra.py importa backend: {vietati}"


def test_backend_in_app_solo_eccezione_nota():
    oltre = []
    for f in sorted(APP_DIR.glob("*.py")):
        if f.name in ECCEZIONI_BACKEND_NOTE:
            continue
        vietati = [
            mod
            for mod in _moduli_importati(f)
            if mod == "locallens.backend" or mod.startswith("locallens.backend.")
        ]
        if vietati:
            oltre.append(f"{f.name} importa {vietati}")
    assert oltre == [], f"nuovo import backend in app: {oltre}"


def test_fabbrica_non_importa_main():
    moduli = _moduli_importati(FABBRICA)
    vietati = [m for m in moduli if m == "locallens.__main__"]
    assert vietati == [], f"inversione layer in core/fabbrica: {vietati}"


def test_solo_cpu_vive_in_orchestrator():
    import pytest

    from locallens.core.errori import InferenzaError
    from locallens.core.orchestrator import solo_cpu

    eng = solo_cpu("motivo-prova")
    assert hasattr(eng, "submit_document")
    assert eng._sorgente == "nessuno"
    with pytest.raises(InferenzaError, match="motivo-prova"):
        eng._infer(1, b"x")


def test_preset_da_conf_vive_in_presets():
    from locallens.config.presets import preset_da_conf

    p = preset_da_conf({"preset_id": "lighton-ocr-q8_0"})
    assert p.id == "lighton-ocr-q8_0"
    # id ignoto → fallback al default shipped
    p2 = preset_da_conf({"preset_id": "inesistente-xyz"})
    assert p2.id == "lighton-ocr-q8_0"


def test_disponibilita_gpu_locale_da_conf():
    from locallens.core.fabbrica import disponibilita_gpu_locale_da_conf

    # Nessun download, mai eccezioni: False se detect fallisce o GPU assente.
    assert disponibilita_gpu_locale_da_conf({}, None) in (True, False)
