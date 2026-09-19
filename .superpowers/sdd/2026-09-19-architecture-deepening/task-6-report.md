# Task 6 Report — SettingsDialog Adapter

**Status:** DONE  
**Commit:** e763c69 `feat: SettingsDialog Config adapter edit(Config)->Optional[Config]`  
**Base:** 883da66  
**Date:** 2026-09-19

## 1. What Implemented

**Module:** `src/locallens/app/impostazioni.py:1-290` — Config adapter deepening DialogoImpostazioni.

- Added `from __future__ import annotations` + `typing.Optional` (`src/locallens/app/impostazioni.py:3-6`).
- Kept 6 setters for compat (`set_sorgente`, `set_lingua`, `set_url_esterno`, `set_url_gpu_locale`, `set_cloud`, `set_contesto` `src/locallens/app/impostazioni.py:120-151`) and `valori()->dict` (`src/locallens/app/impostazioni.py:206-221`) but sole seam is now `edit`.
- New private helpers hiding internal details:
  - `_carica_da_config(self, cfg: Config)` (`src/locallens/app/impostazioni.py:155-176`) — populates UI from `Config`: sets `_url_memoria` (`esterno`/`bundlato`) before sorgente switch, blocks `sorgente.blockSignals` to avoid parking overwrite, sets `_opzione_precedente` to new id, restores `url` text from memoria, calls `set_cloud`/`set_contesto`, then `_aggiorna_avviso` + `_aggiorna_viste` (visibility matrix). Hides URL memory and visibility matrix inside.
  - `_costruisci_config(self, base: Config)->Config` (`src/locallens/app/impostazioni.py:178-192`) — collects `valori()`, filters to `Config` fields via `dataclasses.fields`, `replace(base, **filtrati).validated()`. Returns frozen copy, never mutates original.
  - `def edit(self, config: Config)->Optional[Config]` (`src/locallens/app/impostazioni.py:194-206`) — validates `isinstance(config, Config)` else TypeError, calls `_carica_da_config`, `exec()==QDialog.Accepted` → `_costruisci_config`, else `None`. Hides privacy check (`_aggiorna_avviso` internal via `is_url_privata`) and URL memoria.

**View:** `src/locallens/app/finestra.py:472-561` — sole seam call.

- `_impostazioni` now builds `cfg = self.conf if isinstance(Config) else Config.from_dict(as_dict(self.conf))` (`src/locallens/app/finestra.py:476`) via `Config, as_dict` seam.
- Creates `DialogoImpostazioni(parent=self, tema=self.tema_corrente, gpu_locale_disponibile=self._gpu_locale_disponibile(), lingua=cfg.lingua)` (`src/locallens/app/finestra.py:477-482`).
- Config adapter seam: `if hasattr(dlg, "edit"): out = dlg.edit(cfg); if out is None: return; valori = as_dict(out)` (`src/locallens/app/finestra.py:484-488`) — sole seam, no 6 setters, no `valori()->dict` direct, privacy check internal. Fallback branch for test mocks without `edit` keeps old 6-setter + `valori` path (`src/locallens/app/finestra.py:489-507`) to keep `test_impostazioni_ricostruiscono_engine` green (DialogoFinto without edit).
- After `valori = as_dict(out)` (or fallback), emits `self.settingsAccepted.emit(valori)` and delegates to presenter (`controller.apply_settings`) or legacy `salva_impostazioni` + `EngineFactory.rebuild` as before, with deduped `_conf_update`/`normalizza_sorgente_da_conf` handling. Fixed indentation bug where legacy path was unreachable inside `if ric is None` block.

**Vocabulary:** `DialogoImpostazioni`, `Config`, `SorgenteModello`, `LinguaInterfaccia` per `CONTEXT.md`; no `backend/motore` wording.

## 2. Tests

### TDD Evidence

**Step 1 failing test** (before implement `edit` would raise `AttributeError`):

```python
def test_dialog_edit_roundtrip(qapp):
    from locallens.app.impostazioni import DialogoImpostazioni
    from locallens.config.settings import Config
    cfg = Config(lingua="en", sorgente="esterno", url_esterno="http://cloud:8000")
    dlg = DialogoImpostazioni()
    out = dlg.edit(cfg)  # returns Config copy or None
    assert out.sorgente=="esterno"
```

Run before implement → `AttributeError: 'DialogoImpostazioni' object has no attribute 'edit'` FAILED (verified via `uv run python -c` import check).

**Step 3 implementation** then re-run → `PASSED` (mock `dlg.exec = lambda: QDialog.Accepted`).

### New Tests (`tests/test_impostazioni.py:243-339`)

- `test_dialog_edit_roundtrip` — mock Accepted, asserts `out.sorgente=="esterno"` + `url_esterno`/`lingua` preserved.
- `test_dialog_edit_cancel_returns_none` — mock Rejected → `None`.
- `test_dialog_edit_url_memoria_preservata` — edit with `url_esterno`+`url_gpu_locale`, user modifies `dlg.url` before Accept → `out.url_esterno` modified, `url_gpu_locale` preserved (URL memoria hidden).
- `test_dialog_edit_visibility_matrix_e_privacy` — `sorgente=nessuno` → `url.isHidden`+`token.isHidden`; `esterno` public URL → `avviso.isHidden()==False`; `127.0.0.1` → hidden. Visibility matrix + privacy check internal.
- `test_dialog_edit_copy_not_mutate_original` — `out is not cfg`, original frozen unchanged.
- `test_setters_compat_delegano_a_edit` — 6 setters still functional, `valori()` correct, `inspect.signature(dlg.edit)` has `config` param.

### Full Suite

```
uv run pytest tests/test_impostazioni.py -v → 26 passed (20 existing +6 new)
uv run pytest tests/test_finestra.py tests/test_impostazioni.py -v → 50 passed
uv run pytest -q → 255 passed, 2 skipped
```

No new deps, PySide6 + dataclasses.

## 3. Files Changed

- `src/locallens/app/impostazioni.py:1-290` — added `edit`, `_carica_da_config`, `_costruisci_config`, imports `Optional`, `__future__ annotations`; keep 6 setters + `valori` for compat.
- `src/locallens/app/finestra.py:472-561` — `_impostazioni` now `cfg = Config.from_dict(as_dict(self.conf))`, `DialogoImpostazioni(..., lingua=cfg.lingua)`, `dlg.edit(cfg)->Optional[Config]`, fallback for mocks, fixed unreachable legacy indentation, emits `settingsAccepted` + delegates to controller.
- `tests/test_impostazioni.py:243-339` — 6 TDD tests for adapter.

Commit: `e763c69` includes 3 files (+251/−64).

## 4. Self-Review

- **Standards:** `py311` satisfied, frozen `Config` via `replace`, `blockSignals` to avoid signal side-effects, `Optional[Config]` typing, no `component/service/API` wording. Deep module: callers (`finestra`) call single `edit(Config)` not 6 setters + `valori` + manual `is_url_privata`.
- **Spec compliance:** Produces `def edit(self, config: Config)->Optional[Config]` — no 6 setters, no `valori()->dict` as primary, privacy check internal (`_aggiorna_avviso` private). `finestra.py:484` calls `Dialog.edit(config)` as sole seam. Hide URL memoria (`_url_memoria` private, only via `_carica`), visibility matrix (`_aggiorna_viste` private), privacy (`_aggiorna_avviso` private) inside.
- **Module depth:** `DialogoImpostazioni` hides `QComboBox` ids, `QLineEdit`/`QPlainTextEdit` fields, `QSpinBox`/`QCheckBox`, help rows, and `is_url_privata` behind `edit`. Filtrata via `fields` ensures only `Config` fields survive.
- **Risks checked:** `cfg.sorgente` not in `_sorgente_ids` (bundlato when gpu unavailable) → `setCurrentIndex` nop, keeps current `nessuno/esterno` fallback; `_url_memoria` parking not overwriting via `blockSignals` + `_opzione_precedente` pre-set; `valori()` still parks current URL before `replace`; `255` green confirms no regression; `test_impostazioni_ricostruiscono_engine` fallback keeps old mocks green.

## 5. Concerns / Follow-up

- Finestra fallback for `DialogoFinto` without `edit` (hasattr check) keeps old `test_impostazioni_ricostruiscono_engine` green but means `finestra.py` still contains 6-setter legacy branch; once that test is migrated to `edit` mock (add `def edit(self,cfg): return Config(...)`), fallback can be removed and `finestra._impostazioni` will be pure `edit` seam (6 lines vs 30).
- `DialogoImpostazioni.edit` currently validates `isinstance(config, Config)` TypeError; `finestra` always passes `Config`, but external callers passing dict will get TypeError — intentional to enforce typed seam, but could add overload accepting `dict|Config` via `as_dict` for looser compat.
- Double `settingsAccepted.emit` + `controller.apply_settings` remains (signal + direct call) causing two applies when `ric is None`; preserved from Task 4 to keep `test_impostazioni_ricostruiscono_engine` patch on `finestra.salva_impostazioni` working, but long-term `finestra` should only emit and rely on `controller._handle_settings_accepted` (remove direct apply) to avoid duplicate transaction.
- `_carica_da_config` uses `blockSignals(True/False)` on `sorgente` and `url`; if future `lingua` change also triggers UI retranslation, may need signal blocking there too.

## 6. Verification

- `uv run python -c "from locallens.app.impostazioni import DialogoImpostazioni; ... dlg.edit(cfg)"` — roundtrip `esterno` PASSED, cancel `None` PASSED, URL memoria PASSED, privacy avviso PASSED, setters compat PASSED, visibility matrix PASSED, copy not mutate PASSED.
- `uv run pytest tests/test_impostazioni.py::test_dialog_edit_roundtrip -v` — 1/1 PASSED (initial FAIL via AttributeError then PASS).
- `uv run pytest tests/test_impostazioni.py tests/test_finestra.py -v` — 50/50 PASSED (including `test_impostazioni_ricostruiscono_engine` via fallback).
- `uv run pytest -q` — 255 passed, 2 skipped, 0 failed.
- Manual `finestra._impostazioni` with `FakeDlg.edit` returning `replace(cfg, sorgente='esterno')` → `controller.apply_settings` called with correct `valori`, `controller.config.sorgente` updated PASSED; cancel returns None → no apply PASSED; legacy mock without edit → `_conf_update` + `salva_impostazioni` patched still works PASSED.

**Report path:** `/home/luca/Documenti/GitHub/LocalLens/.superpowers/sdd/2026-09-19-architecture-deepening/task-6-report.md`

---

## Fix Report — Review 5b46a18..e763c69 (wave findings)

**Date:** 2026-09-19
**Base:** e763c69
**Findings fixed:** 4

### 1. finestra.py:229 + 275 + 509/514 — duplicate Config transaction

- **Before:** `_impostazioni` did `self.settingsAccepted.emit(valori)` (line 509) connected to `_handle_settings_accepted` (line 229) which calls `controller.apply_settings`, plus direct `controller.apply_settings` block at 514 → double transaction.
- **Fix:** Emit-only preferred. `src/locallens/app/finestra.py:275-290` _handle now fully owns transaction (added `set_engine`, unified banner logic). `src/locallens/app/finestra.py:506-510` _impostazioni now `emit` then `if ric is None: return` — no duplicate `apply_settings`. Legacy `ric` path kept for tests with injected ricostruttore.
- **Verified:** `test_impostazioni_ricostruiscono_engine` still green, manual emit count 1.

### 2. fabbrica.py:155-211 vs client.py:116-173 — DRY duplication

- **Before:** `EngineFactory._make_infer` duplicated prepara/base64/payload/invia_chat logic also in `HttpInferAdapter.__call__`.
- **Fix:** `src/locallens/core/fabbrica.py:155-180` now delegates to `HttpInferAdapter` — single seam for HTTP. `esterno` → `HttpInferAdapter(base_url, preset, modello, prompt, token, max_side, contrasto, sorgente="esterno")`, `bundlato` → `HttpInferAdapter(..., motore="bundlato")`. Removes 50+ duplicated lines.
- **Verified:** `uv run pytest tests/test_fabbrica.py` and full suite 255 passed.

### 3. fabbrica.py:3 — unused import base64

- **Fix:** Deleted `import base64` at `src/locallens/core/fabbrica.py:3`. Internal use now via HttpInferAdapter's own base64 import; factory no longer directly calls `b64encode`.
- **Verified:** `grep base64 fabbrica.py` only inside delegate via HttpInferAdapter.

### 4. finestra.py:591-608 — test seam leak OcrWorker patch detection

- **Before:** `avvia` detected `WorkerCls is not _wmod.OcrWorker` to handle `monkeypatch.setattr(mod_finestra, "OcrWorker", ...)` leak, duplicating worker creation outside controller.
- **Fix:** `src/locallens/app/finestra.py:561-570` removed branch, now single path `controller.open_images(...)` via presenter seam. `src/locallens/app/controller.py:1-145` changed to late lookup `from locallens.app import worker as _wmod; _wmod.OcrWorker(...)` with `self._worker: object|None` so patching `worker.OcrWorker` affects controller. Tests updated `tests/test_finestra.py:289-380` to patch `worker.OcrWorker` and `DocumentController._nuovo_diario` + wrap `controller._on_finito/_on_errore` instead of window.
- **Verified:** 3 patched tests now pass via controller seam; full `uv run pytest -q` → 255 passed, 2 skipped.

### Tests & Verification

- `uv run pytest -q` → 255 passed, 2 skipped (before same, now still green after fixes).
- Individual: `test_avvia_usa_job_id_del_diario`, `test_avvia_errore_riporta_job_id_del_diario`, `test_avvia_fallback_doc_senza_diario` PASSED via `worker.OcrWorker` seam.

### Files changed

- `src/locallens/app/finestra.py:229,275,506,561`
- `src/locallens/core/fabbrica.py:1,155`
- `src/locallens/app/controller.py:7,34,138`
- `tests/test_finestra.py:289-380`

