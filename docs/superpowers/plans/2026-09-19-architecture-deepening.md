# Architecture Deepening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deepen 6 shallow modules into deep modules with strong seams for SorgenteModello, Config, LinguaInterfaccia, Pagina/Estrazione workflow.

**Architecture:** Introduce typed Config, EngineFactory, DocumentController Presenter, LinguaService, OcrPipeline merge, SettingsDialog adapter. Each module owns one interface, hides implementation, tested through interface. Phased: A (Config+Lingua) → B (Factory+Controller) → C (Pipeline+Dialog).

**Tech Stack:** Python 3.11+, PySide6, dataclasses, tomllib, pytest, Mermaid not needed in code

**Spec:** docs/superpowers/plans/2026-09-19-architecture-deepening.md (this plan) + CONTEXT.md seams + HTML report /tmp/architecture-review-1789808369.html

## Global Constraints

- Python >=3.11, no new runtime dependencies beyond stdlib
- Existing tests 238 passed must stay green; update tests that assert old shallow interfaces
- Domain terms per CONTEXT.md: SorgenteModello, BackendGpu, PresetModello, Documento, Pagina, Estrazione, LinguaInterfaccia
- No component/service/API wording — use module/interface/seam/adapter

---

## File Structure

**New files:**
- `src/locallens/config/typed.py` — Config dataclass (if split from settings.py) or extend settings.py in place
- `src/locallens/app/lingua_service.py` — LinguaService (or deepen lingua.py in place)
- `src/locallens/core/engine_factory.py` — EngineFactory (or deepen fabbrica.py)
- `src/locallens/app/controller.py` — DocumentController Presenter

**Modified:**
- `src/locallens/config/settings.py` — typed Config vs dict
- `src/locallens/app/lingua.py` — add enum + service
- `src/locallens/core/fabbrica.py` — collapse to factory
- `src/locallens/core/orchestrator.py` + `pipeline.py` → `pipeline.py` deep
- `src/locallens/app/finestra.py` — split View/Controller
- `src/locallens/app/impostazioni.py` — edit(Config) adapter

---

### Task 1: Typed Config Module (#5)

**Files:**
- Modify: `src/locallens/config/settings.py:1-76`
- Modify: `src/locallens/app/finestra.py:201,343,346`
- Modify: `src/locallens/core/fabbrica.py` — signature to accept Config
- Test: `tests/test_settings.py`

**Interfaces:**
- Consumes: `LINGUE`, `SorgenteModello` literals
- Produces: `@dataclass(frozen=True) class Config: lingua: Literal["it","en"]; sorgente: Literal["bundlato","esterno","nessuno"]; url_esterno: str; url_gpu_locale: str; token_esterno: SecretStr; modello_esterno: str; prompt_esterno: str; preset_id: str; max_side_px: int; contrasto: bool; lingue_filtro: str; soglia_righe_loop: int; ignora_eco: bool; tema: str` with `Config.load(path)->Config`, `Config.save(path)`, `Config.validated()->Config`, `Config.effective_url()->str`

- [ ] **Step 1: Write failing test for typed Config**

```python
def test_config_typed_load(tmp_path):
    from locallens.config.settings import Config
    p = tmp_path / "c.toml"
    p.write_text('lingua="en"\nsorgente="esterno"\n', encoding="utf-8")
    cfg = Config.load(p)
    assert cfg.lingua == "en"
    assert cfg.sorgente == "esterno"
    assert cfg.effective_url() == "http://127.0.0.1:8011"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_settings.py::test_config_typed_load -v`
Expected: FAIL with "Config not defined"

- [ ] **Step 3: Implement Config dataclass wrapping DEFAULTS**

```python
from dataclasses import dataclass
from typing import Literal
@dataclass(frozen=True)
class Config:
    lingua: Literal["it","en"] = "en"
    sorgente: Literal["bundlato","esterno","nessuno"] = "bundlato"
    # ... other fields
    @classmethod
    def load(cls, path=None)->"Config": ...
    def save(self, path=None): ...
    def validated(self): ...
    def effective_url(self): return self.url_gpu_locale if self.sorgente=="bundlato" else self.url_esterno
```

Keep `DEFAULTS` dict for compat, add `to_dict()` and `from_dict()` helpers; `carica()` remains but delegates to `Config.load().to_dict()` for old callers.

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_settings.py -v` Expected: PASS (update test_lingua_default_it etc.)

- [ ] **Step 5: Commit**

```bash
git add src/locallens/config/settings.py tests/test_settings.py
git commit -m "feat: typed Config module deepens settings seam"
```

---

### Task 2: LinguaService (#3)

**Files:**
- Modify: `src/locallens/app/lingua.py:1-162`
- Modify: `src/locallens/app/finestra.py:34-52` — remove duplicated maps
- Modify: `src/locallens/app/impostazioni.py:24-25` — remove duplicate
- Test: `tests/test_lingua.py`

**Interfaces:**
- Consumes: `STRINGS` dict, `LINGUE`
- Produces: `class LinguaService: def __init__(self, lingua: str); def t(self, chiave: Chiave, **fmt)->str; def set_lingua(self, l: str); @property def lingua(self)->str` and `Chiave = Literal[...]` or Enum generated from STRINGS keys

- [ ] **Step 1: Write failing test**

```python
def test_lingua_service_typed():
    from locallens.app.lingua import LinguaService
    s = LinguaService("it")
    assert s.t("btn_apri") == "Apri file/PDF"
    s.set_lingua("en")
    assert s.t("btn_apri") == "Open file/PDF"
    # missing key should raise at type-check, at runtime KeyError
    import pytest
    with pytest.raises(KeyError):
        s.t("chiave_che_non_esiste")
```

- [ ] **Step 2: Run test fails**

Run: `uv run pytest tests/test_lingua.py::test_lingua_service_typed -v` Expected FAIL

- [ ] **Step 3: Implement service, keep t() compat shim**

```python
class LinguaService:
    def __init__(self, lingua="en"): self._lingua=lingua
    def t(self, chiave, **fmt): return STRINGS.get(self._lingua, STRINGS["en"])[chiave].format(**fmt)
    def set_lingua(self, l): ...
# keep def t(lingua, chiave, **fmt): return LinguaService(lingua).t(chiave, **fmt) for compat
# Add SORGENTE_LABELS = {"bundlato": "sorgente_bundlato", ...} single source
```

Remove `_CHIAVE_SORGENTE` duplicates in finestra/impostazioni, import from lingua.

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_lingua.py tests/test_finestra.py::test_applica_lingua_ritraduce_lista -v` PASS

- [ ] **Step 5: Commit**

```bash
git add src/locallens/app/lingua.py src/locallens/app/finestra.py src/locallens/app/impostazioni.py
git commit -m "feat: LinguaService deepens LinguaInterfaccia seam"
```

---

### Task 3: EngineFactory Deep (#1)

**Files:**
- Modify: `src/locallens/core/fabbrica.py:134`
- Modify: `src/locallens/core/orchestrator.py:131-220`
- Modify: `src/locallens/__main__.py:8-19` — use factory
- Modify: `src/locallens/app/finestra.py:336-375` — use factory
- Test: `tests/test_fabbrica.py`

**Interfaces:**
- Consumes: `Config`, `HardwareInfo`, `PresetModello`
- Produces: `class EngineFactory: def __init__(self, config: Config, verify=verifica_health); def rebuild(self, config: Config)->tuple[OcrEngine,str,str]`

- [ ] **Step 1: Write failing test**

```python
def test_factory_rebuild_bundlato(monkeypatch):
    from locallens.config.settings import Config
    from locallens.core.fabbrica import EngineFactory
    cfg = Config(lingua="en", sorgente="bundlato", url_gpu_locale="http://127.0.0.1:8011")
    f = EngineFactory(cfg, verify=lambda url: True)
    engine, stato, banner = f.rebuild(cfg)
    assert "Local GPU" in stato or "GPU locale" in stato
```

- [ ] **Step 2: Run fails**

`uv run pytest tests/test_fabbrica.py::test_factory_rebuild_bundlato -v` FAIL

- [ ] **Step 3: Implement factory collapsing crea_engine / crea_engine_cloud**

Merge `prepara→build_payload→invia_chat` into one `make_infer(sorgente)` closure; hide `verifica_health`, `resolve_binary`, `snapshot_completo` inside factory implementation; expose only `rebuild`.

- [ ] **Step 4: Run tests**

`uv run pytest tests/test_fabbrica.py -q` PASS

- [ ] **Step 5: Commit**

```bash
git add src/locallens/core/fabbrica.py src/locallens/core/orchestrator.py
git commit -m "feat: deep EngineFactory owns SorgenteModello"
```

---

### Task 4: DocumentController Presenter (#2)

**Files:**
- Create: `src/locallens/app/controller.py`
- Modify: `src/locallens/app/finestra.py:605` — strip to View, delegate to controller
- Modify: `src/locallens/app/worker.py` — consumed by controller
- Test: `tests/test_finestra.py` + new `tests/test_controller.py`

**Interfaces:**
- Consumes: `Config`, `EngineFactory`, `OcrEngine`
- Produces: `class DocumentController: def __init__(self, config: Config, factory: EngineFactory); def open_document(self, path:str); def open_images(self, imgs:list[bytes]); def cancel(self); @property def estrazioni(self)->list[Estrazione]; def filtered_text(self, row:int|None)->str`

- [ ] **Step 1: Write failing test**

```python
def test_controller_open_and_filter(qapp):
    from locallens.app.controller import DocumentController
    c = DocumentController(Config(), factory_fake)
    c.open_images([b"a", b"b"])
    # wait?
    assert len(c.estrazioni)==2
    assert c.filtered_text(0) != c.filtered_text(None)
```

- [ ] **Step 2: Run fails**

`uv run pytest tests/test_controller.py::test_controller_open_and_filter -v` FAIL

- [ ] **Step 3: Implement controller moving avvia/_on_pagina/_on_finito/_annulla/_nuovo_diario, salva_impostazioni transaction**

View `finestra.py` only emits `openRequested`, `settingsAccepted` signals and binds `controller.estrazioni_changed -> mostra_estrazioni`.

- [ ] **Step 4: Run tests**

`uv run pytest tests/test_finestra.py tests/test_controller.py -q` PASS

- [ ] **Step 5: Commit**

```bash
git add src/locallens/app/controller.py src/locallens/app/finestra.py
git commit -m "feat: split MainWindow into Presenter+View"
```

---

### Task 5: OcrPipeline Merge (#4)

**Files:**
- Modify: `src/locallens/core/orchestrator.py`, `src/locallens/core/pipeline.py` → `src/locallens/core/pipeline.py` deep
- Modify: `src/locallens/core/client.py` — HttpInferAdapter
- Test: `tests/test_pipeline.py` `tests/test_ocr_engine.py`

**Interfaces:**
- Produces: `class OcrPipeline: def submit(self, immagini:list[bytes], config: OcrConfig, ferma)->list[EstrazionePagina]` owning retry, _motivo_anomalia, _è_timeout, Tesseract fallback, diario audit

- [ ] **Step 1: Failing test for single interface**

```python
def test_pipeline_single_interface():
    from locallens.core.pipeline import OcrPipeline
    p = OcrPipeline(infer=lambda i,b: ("hello","cuda"), fallback=lambda i,b: "fb")
    res = p.submit([b"a"], config=...) 
    assert res[0].testo=="hello"
```

- [ ] **Step 2-5: Standard TDD, commit**

---

### Task 6: SettingsDialog Adapter (#6)

**Files:**
- Modify: `src/locallens/app/impostazioni.py`
- Modify: `src/locallens/app/finestra.py:336` — call `Dialog.edit(config)`
- Test: `tests/test_impostazioni.py`

**Interfaces:**
- Produces: `def edit(self, config: Config)->Optional[Config]` — no 6 setters, no valori()->dict, privacy check internal

- [ ] **Step 1: Failing test**

```python
def test_dialog_edit_roundtrip(qapp):
    from locallens.app.impostazioni import DialogoImpostazioni
    from locallens.config.settings import Config
    cfg = Config(lingua="en", sorgente="esterno", url_esterno="http://cloud:8000")
    dlg = DialogoImpostazioni()
    out = dlg.edit(cfg)  # returns Config copy or None
    assert out.sorgente=="esterno"
```

- [ ] **Step 2-5: TDD, commit**

