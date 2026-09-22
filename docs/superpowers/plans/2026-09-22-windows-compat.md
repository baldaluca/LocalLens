# Windows Compatibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rendere LocalLens eseguibile su Windows reale (parità GPU a livello di codice) con build/test CI su runner Windows, senza dual-boot.

**Architecture:** Fix cross-platform mockabili da Ubuntu (kill/subprocess, hwdetect, Tesseract, HF cache) + workflow GitHub Actions matrix che builda l'exe sull'OS target; VM locale solo per click-test CPU; smoke cuda-windows rimandato a hardware reale.

**Tech Stack:** Python >=3.11, PySide6, PyInstaller onedir, llama.cpp b10995 (`llama-server.exe`), Tesseract (PSM 6, `ita+eng`), `mss`, `pypdfium2`, GitHub Actions (`ubuntu-latest` + `windows-latest`).

**Spec:** `docs/superpowers/specs/2026-09-22-windows-compat-design.md`

## Global Constraints

- Python `>=3.11`, ruff `target-version = "py311"`, `mypy` policy zero errori.
- `pytest -q` con live skippati senza `LOCALLENS_LIVE=1` / `TESSERACT_LIVE=1`.
- Tag binari pinnato `b10995`; asset win32: `win-cuda-12.4` / `win-vulkan` / `win-cpu` (zip).
- Token esterno mai su disco (`SEGRET = ("token_esterno",)`).
- Config Windows in `%APPDATA%\LocalLens\config.toml`, Linux in `~/.config/locallens/config.toml`.
- `locallens.spec`: `console=False`, icona `assets/icons/locallens.ico` (esiste, verificato).
- Linguaggio ubiquo: Documento / Pagina / Estrazione, BackendGpu, SorgenteModello (`bundlato|esterno|nessuno`), PresetModello, LinguaInterfaccia (`it|en`).
- Seams esistenti: `app → core/config` mai verso `backend`/`hwdetect`; runner/grabber iniettabili nei test.

## Scope Check

Spec con due sottosistemi (fix codice + infra CI). Tengo un solo piano perché i Task 1–4
(codice, testabili su Linux con `platform="win32"` mockato) sono prerequisiti del Task 5 (CI),
e il Task 6 (checklist VM + gate finale) è additivo. Ogni task è approvabile/rifiutabile da solo.

## File Structure

- `src/locallens/backend/manager.py` — Task 1: helper `uccidi_processo` + `creationflags=CREATE_NO_WINDOW` su win32.
- `src/locallens/hwdetect/detector.py` — Task 2: helper `rileva_vendor_windows` + fallback in `detect`.
- `src/locallens/fallback/tesseract.py` — Task 3: helper `trova_tesseract` + wiring in `verifica_disponibile`/`_ocr_default`.
- `src/locallens/config/pesi.py` — Task 4: `_cache_root` rispettoso di Windows/HF_HOME.
- `.github/workflows/ci.yml` — Task 5 (create): matrix test + package win/linux + smoke offscreen.
- `docs/windows-vm-checklist.md` — Task 6 (create): checklist click-test manuale CPU-only.
- Test: `tests/test_backend_manager.py`, `tests/test_detect.py`, `tests/test_fallback.py`, `tests/test_pesi.py` (modify, solo aggiunte).

---

### Task 1: BackendManager Windows (kill + console)

**Files:**
- Modify: `src/locallens/backend/manager.py`
- Test: `tests/test_backend_manager.py`

**Interfaces:**
- Consumes: `core.rete.resolve_binary(platform, backend_gpu, bins_root)` (esistente, già `.exe` su win32).
- Produces: `uccidi_processo(pid: int, piattaforma: str = "linux", esegui=None) -> None`; `BackendManager(platform="win32")` passa `creationflags=CREATE_NO_WINDOW` a `Popen` e usa `uccidi_processo` nel default `_uccidi`.

- [ ] **Step 1: Write the failing test**

```python
def test_uccidi_windows_usa_taskkill():
    from locallens.backend.manager import uccidi_processo

    chiamate = []
    uccidi_processo(4242, piattaforma="win32", esegui=lambda cmd: chiamate.append(cmd))
    assert chiamate == [["taskkill", "/PID", "4242", "/F"]]


def test_lancio_win32_nasconde_console_e_usa_exe(monkeypatch):
    import subprocess

    from locallens.backend.manager import BackendManager

    chiamate = {}

    class ProcFinto:
        pid = 9999

        def __init__(self, cmd, **kw):
            chiamate["cmd"] = cmd
            chiamate.update(kw)

        def terminate(self):
            pass

        def wait(self, timeout=None):
            return 0

    monkeypatch.setattr(subprocess, "Popen", ProcFinto)
    mgr = BackendManager(
        platform="win32",
        bins_root="bins",
        esiste=lambda p: True,
        porte_occupate=lambda: set(),
        verifica=lambda url: True,
    )
    h = mgr.start("cpu")
    assert "llama-server.exe" in chiamate["cmd"][0]
    assert h.pid == 9999
    assert chiamate.get("creationflags", 0) == getattr(subprocess, "CREATE_NO_WINDOW", 0)
    assert chiamate.get("creationflags", 0) != 0 or hasattr(subprocess, "CREATE_NO_WINDOW") is False
    mgr.stop()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_backend_manager.py::test_uccidi_windows_usa_taskkill tests/test_backend_manager.py::test_lancio_win32_nasconde_console_e_usa_exe -v`
Expected: FAIL with "uccidi_processo not defined" / "creationflags" mismatch.

- [ ] **Step 3: Write minimal implementation**

```python
"""Avvio/supervisione llama-server bundlato come subprocess."""
import contextlib
import signal
from dataclasses import dataclass
from pathlib import Path


def uccidi_processo(pid: int, piattaforma: str = "linux", esegui=None) -> None:
    """Kill cross-platform. win32 → taskkill, altrimenti SIGTERM. Mai eccezioni."""
    if piattaforma == "win32":
        def _run(cmd: list[str]) -> None:
            import subprocess

            with contextlib.suppress(Exception):
                subprocess.run(cmd, capture_output=True, timeout=10, check=False)

        (esegui or _run)(["taskkill", "/PID", str(pid), "/F"])
        return
    with contextlib.suppress(OSError):
        import os

        os.kill(pid, signal.SIGTERM)
```

In `BackendManager.__init__`, catturare la piattaforma in closure e cambiare i default:

```python
        _piattaforma = platform

        def _lancia(cmd: list[str]) -> int:
            import subprocess

            extra: dict = {}
            if _piattaforma == "win32":
                flag = getattr(subprocess, "CREATE_NO_WINDOW", 0)
                if flag:
                    extra["creationflags"] = flag
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                **extra,
            )
            self._proc = proc
            return proc.pid
```

e il default `_uccidi`:

```python
        def _uccidi(pid: int) -> None:
            uccidi_processo(pid, _piattaforma)
```

Rimuovere il vecchio `_uccidi` con `os.kill` diretto e il vecchio `_lancia` senza `extra`.
Mantenere `_finalizza_proc` (terminate/wait/kill) invariato.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_backend_manager.py -q`
Expected: PASS (tutti, inclusi i vecchi).

- [ ] **Step 5: Commit**

```bash
git add src/locallens/backend/manager.py tests/test_backend_manager.py
git commit -m "feat(win): kill via taskkill e console nascosta per llama-server.exe"
```

---

### Task 2: hwdetect fallback Windows (niente lspci)

**Files:**
- Modify: `src/locallens/hwdetect/detector.py`
- Test: `tests/test_detect.py`

**Interfaces:**
- Consumes: `esegui(cmd: list[str]) -> str | None` (seam esistente di `detect`).
- Produces: `rileva_vendor_windows(esegui) -> str` (`"nvidia" | "amd" | "intel" | "none"`); `detect(piattaforma="win32", ...)` lo usa quando `nvidia-smi` non risponde.

- [ ] **Step 1: Write the failing test**

```python
def test_detect_windows_wmic_nvidia():
    from locallens.hwdetect.detector import detect

    def esegui(cmd):
        if cmd[0] == "nvidia-smi":
            return None
        if cmd[0] == "wmic":
            return "Name\nNVIDIA GeForce RTX 4050 Laptop GPU\n"
        return None

    info = detect(
        piattaforma="win32",
        esegui=esegui,
        lspci=lambda: "",
        bins_presenti={"cuda", "vulkan", "cpu"},
    )
    assert info.gpu_vendor == "nvidia"
    assert info.candidati[0] == "cuda"


def test_detect_windows_powershell_amd():
    from locallens.hwdetect.detector import detect

    def esegui(cmd):
        if cmd[0] == "nvidia-smi":
            return None
        if cmd[0] == "wmic":
            return None
        if cmd[0] == "powershell":
            return "AMD Radeon Graphics"
        return None

    info = detect(
        piattaforma="win32",
        esegui=esegui,
        lspci=lambda: "",
        bins_presenti={"vulkan", "cpu"},
    )
    assert info.gpu_vendor == "amd"
    assert info.candidati == ("vulkan", "cpu")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_detect.py::test_detect_windows_wmic_nvidia tests/test_detect.py::test_detect_windows_powershell_amd -v`
Expected: FAIL (vendor `unknown` invece di `nvidia`/`amd`).

- [ ] **Step 3: Write minimal implementation**

```python
def rileva_vendor_windows(esegui) -> str:
    """Fallback Windows senza lspci: wmic → powershell. Ritorna nvidia|amd|intel|none."""
    for cmd in (
        ["wmic", "path", "win32_VideoController", "get", "name"],
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name",
        ],
    ):
        try:
            out = (esegui(cmd) or "").lower()
        except Exception:
            continue
        if "nvidia" in out:
            return "nvidia"
        if "amd" in out or "radeon" in out:
            return "amd"
        if "intel" in out:
            return "intel"
    return "none"
```

In `detect`, dopo il blocco `smi`, prima del calcolo `bins_presenti`, inserire:

```python
    if vendor == "none" and os == "win32":
        vendor = rileva_vendor_windows(esegui)
```

`decide` resta invariata (hip mai su win32, cpu sempre ultima).

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_detect.py tests/test_hwdetect.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/locallens/hwdetect/detector.py tests/test_detect.py
git commit -m "feat(win): rilevamento GPU via wmic/powershell senza lspci"
```

---

### Task 3: Tesseract su Windows (PATH + Program Files)

**Files:**
- Modify: `src/locallens/fallback/tesseract.py`
- Test: `tests/test_fallback.py`

**Interfaces:**
- Consumes: env `TESSERACT_CMD`, `shutil.which`, path default Windows.
- Produces: `trova_tesseract(cmd_env=None, which=None, esiste=None) -> str | None`; `verifica_disponibile()` e `_ocr_default` lo usano; firma `estrai(png, lang, psm, ocr)` invariata.

- [ ] **Step 1: Write the failing test**

```python
def test_trova_tesseract_program_files(monkeypatch):
    from locallens.fallback import tesseract as tess

    monkeypatch.setattr(tess.shutil, "which", lambda _: None)
    monkeypatch.setenv("TESSERACT_CMD", "")
    monkeypatch.setattr(
        tess.Path, "is_file", lambda self: str(self).endswith("tesseract.exe")
    )
    trovato = tess.trova_tesseract()
    assert trovato is not None and str(trovato).endswith("tesseract.exe")


def test_trova_tesseract_env Vince(monkeypatch):
    from locallens.fallback import tesseract as tess

    monkeypatch.setenv("TESSERACT_CMD", r"D:\tools\tesseract.exe")
    assert tess.trova_tesseract() == r"D:\tools\tesseract.exe"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_fallback.py::test_trova_tesseract_program_files tests/test_fallback.py::test_trova_tesseract_env -v`
Expected: FAIL with "trova_tesseract not defined".

- [ ] **Step 3: Write minimal implementation**

```python
"""Fallback CPU via Tesseract. Nessun vincolo GPU (requisiti §7)."""

import io
import os
import shutil
from collections.abc import Callable
from pathlib import Path

from PIL import Image

LANG_DEFAULT = "ita+eng"
PSM_DEFAULT = 6

CANDIDATI_WINDOWS = (
    Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
    Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
)


def trova_tesseract(cmd_env=None, which=None, esiste=None) -> str | None:
    """Percorso binario tesseract: env TESSERACT_CMD → PATH → path default Windows."""
    env = cmd_env if cmd_env is not None else os.environ.get("TESSERACT_CMD", "")
    if env:
        return env
    cerca = which or shutil.which
    if cerca("tesseract"):
        return cerca("tesseract")
    is_file = esiste or (lambda p: Path(p).is_file())
    for candidato in CANDIDATI_WINDOWS:
        if is_file(candidato):
            return str(candidato)
    return None


def verifica_disponibile() -> bool:
    """True se il binario tesseract è nel PATH o nei path default Windows."""
    return trova_tesseract() is not None
```

e in `_ocr_default`, prima di `pytesseract.image_to_string`:

```python
def _ocr_default(immagine: Image.Image, lang: str, psm: int) -> str:
    import pytesseract  # type: ignore[import-untyped]

    binario = trova_tesseract()
    if binario:
        pytesseract.pytesseract.tesseract_cmd = binario
    return pytesseract.image_to_string(immagine, lang=lang, config=f"--psm {psm}")
```

`estrai` resta invariata (runner `ocr` iniettabile come prima).

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_fallback.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/locallens/fallback/tesseract.py tests/test_fallback.py
git commit -m "feat(win): ricerca tesseract in Program Files e TESSERACT_CMD"
```

---

### Task 4: Cache pesi HF su Windows

**Files:**
- Modify: `src/locallens/config/pesi.py`
- Test: `tests/test_pesi.py`

**Interfaces:**
- Consumes: env `HF_HOME` / `HUGGINGFACE_HUB_CACHE`, default di `huggingface_hub` se importabile.
- Produces: `_cache_root(env=None) -> Path`; `snapshot_completo`/`risolvi_pesi` invariati (usano `cache_root` esplicito nei test).

- [ ] **Step 1: Write the failing test**

```python
def test_cache_root_rispetta_hf_home(monkeypatch, tmp_path):
    from locallens.config import pesi

    monkeypatch.setenv("HF_HOME", str(tmp_path / "hf"))
    monkeypatch.delenv("HUGGINGFACE_HUB_CACHE", raising=False)
    assert pesi._cache_root() == tmp_path / "hf"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_pesi.py::test_cache_root_rispetta_hf_home -v`
Expected: FAIL (ritorna `~/.cache/huggingface/hub` invece di `HF_HOME`).

- [ ] **Step 3: Write minimal implementation**

```python
def _cache_root(env=None) -> Path:
    Ambiente = env if env is not None else os.environ
    override = Ambiente.get("HF_HOME") or Ambiente.get("HUGGINGFACE_HUB_CACHE")
    if override:
        return Path(override)
    try:
        from huggingface_hub.constants import HF_HUB_CACHE as _default

        return Path(_default)
    except Exception:
        return Path.home() / ".cache" / "huggingface" / "hub"
```

Sostituire il vecchio `_cache_root()` senza parametri. `snapshot_completo`/`risolvi_pesi` invariati.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_pesi.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/locallens/config/pesi.py tests/test_pesi.py
git commit -m "fix(win): cache pesi via HF_HOME e default huggingface_hub"
```

---

### Task 5: CI matrix Windows+Linux con packaging

**Files:**
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: `tools/fetch-binaries.py --os <os> --all`, `locallens.spec`, `assets/icons/locallens.ico`.
- Produces: artefatti `dist/locallens/` per OS + smoke offscreen verde su entrambi.

- [ ] **Step 1: Write the workflow file**

```yaml
name: ci
on: [push, pull_request]
jobs:
  test:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install uv
        run: pip install uv
      - name: Sync
        run: uv sync
      - name: Tesseract (linux)
        if: runner.os == 'Linux'
        run: sudo apt-get update && sudo apt-get install -y tesseract-ocr tesseract-ocr-ita
      - name: Tesseract (windows)
        if: runner.os == 'Windows'
        run: choco install tesseract -y
      - name: Unit
        run: uv run pytest -q
      - name: Ruff
        run: uv run --with ruff ruff check src tests tools
      - name: Mypy
        run: uv run --with mypy mypy src/locallens/
  package:
    needs: test
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install uv
        run: pip install uv
      - name: Sync
        run: uv sync
      - name: Fetch binaries (linux)
        if: runner.os == 'Linux'
        run: uv run python tools/fetch-binaries.py --os linux --all
      - name: Fetch binaries (windows)
        if: runner.os == 'Windows'
        run: uv run python tools/fetch-binaries.py --os win32 --all
      - name: Build
        run: uv run --with pyinstaller pyinstaller -y locallens.spec
      - name: Smoke offscreen (linux)
        if: runner.os == 'Linux'
        run: QT_QPA_PLATFORM=offscreen timeout 20 ./dist/locallens/locallens
      - name: Smoke offscreen (windows)
        if: runner.os == 'Windows'
        run: $env:QT_QPA_PLATFORM = "offscreen"; Start-Sleep -Seconds 2; ./dist/locallens/locallens.exe
        timeout-minutes: 2
      - uses: actions/upload-artifact@v4
        with:
          name: locallens-${{ runner.os }}
          path: dist/locallens/
```

- [ ] **Step 2: Validate locally without a Windows host**

Run: `uv run python tools/fetch-binaries.py --list`
Expected: lista con `linux/cuda,hip,vulkan,cpu` e `win32/cuda,vulkan,cpu` (asset b10995).

Run: `uv run pytest -q`
Expected: PASS (il workflow non rompe i test locali).

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci(win): matrix ubuntu+windows con package e smoke offscreen"
```

---

### Task 6: Checklist VM + gate finale

**Files:**
- Create: `docs/windows-vm-checklist.md`

**Interfaces:**
- Consumes: exe `locallens.exe` dall'artefatto CI (job `package`, runner Windows).
- Produces: esito manuale CPU-only documentato; gate `pytest+ruff+mypy` verde su Linux.

- [ ] **Step 1: Write the checklist file**

```markdown
# Windows VM checklist (CPU-only, niente GPU)

VM: KVM/VirtualBox, Win 10/11 (anche evaluation), 60 GB disco, 4 GB RAM, VGA virtuale.
Exe: `locallens.exe` dallo zip dell'artefatto CI `locallens-Windows`.

1. [ ] Avvio senza console popup, finestra visibile, nessun traceback.
2. [ ] Apri Documento immagine → Estrazione con `sorgente=nessuno` (Tesseract).
3. [ ] Apri PDF 2 pagine → 2 Pagine, badge engine `tesseract` su entrambe.
4. [ ] `sorgente=esterno` verso server Linux in LAN → Estrazione via rete, banner privacy se URL non-locale.
5. [ ] Appunti (screenshot negli appunti) → Pagina importata; screenshot `mss` → PNG valida.
6. [ ] Hot-switch LinguaInterfaccia it/en + tema chiaro/scuro senza riavvio.
7. [ ] Config salvata in `%APPDATA%\LocalLens\config.toml`, token mai su disco.
8. [ ] `bundlato/cuda` in VM FALLISCE per disegno (VGA virtuale) → banner fallback, non un bug.

Smoke `win32/cuda-12.4` reale (hardware fisico Windows+NVIDIA o cloud GPU a ore):
`/health` 200, VRAM dedicata, gold image 4/4 linee esatte — protocollo validazione GTX 960M 2026-09-16.
```

- [ ] **Step 2: Run the full local gate**

Run: `uv run pytest -q`
Expected: PASS.

Run: `uv run --with ruff ruff check src tests tools`
Expected: PASS, zero errori.

Run: `uv run --with mypy mypy src/locallens/`
Expected: PASS, zero errori.

- [ ] **Step 3: Commit**

```bash
git add docs/windows-vm-checklist.md
git commit -m "docs(win): checklist click-test VM CPU-only"
```

---

## Self-Review

1. Spec coverage: §1.1 manager→Task 1; §1.2 hwdetect→Task 2; §1.3 tesseract→Task 3; §1.4 pesi→Task 4; §2 CI/package/smoke→Task 5; §2 VM + §3 YAGNI→Task 6. Icona/APPADATA/contratti invariati verificati nel testo dei task.
2. Placeholder scan: nessun TBD/TODO/"appropriate handling"; ogni step ha codice, comando e atteso espliciti.
3. Type consistency: `uccidi_processo(pid, piattaforma, esegui)`, `rileva_vendor_windows(esegui)`, `trova_tesseract(cmd_env, which, esiste)`, `_cache_root(env)` usati con gli stessi nomi in test e implementazione; `estrai/snapshot_completo/risolvi_pesi/decide` invariati.
