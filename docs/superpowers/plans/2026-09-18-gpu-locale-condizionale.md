# GPU locale condizionale Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** L'opzione GPU locale appare solo se binari+pesi rilevati, con label "GPU locale" e ripiego su esterno al boot.

**Architecture:** Rilevamento puro in `fabbrica.py` (binario via `resolve_binary` + snapshot via `snapshot_completo`); dialogo con flag e mappa label↔id; normalizzazione del config al boot e dopo il dialogo. Id interno `bundlato` invariato ovunque.

**Tech Stack:** Python, PySide6 (dialogo), pytest TDD, commit per task.

**Spec:** `docs/superpowers/specs/2026-09-18-gpu-locale-condizionale-design.md`

## Global Constraints

- Id interno `bundlato` invariato in config, diario, CONTEXT.md.
- Label UI "GPU locale" solo in dialogo, pill e banner.
- Comando test: `uv run --with pytest pytest tests/ -q`.
- Un commit per task, solo file del task.

---

### Task 1: Rilevamento disponibilità GPU locale

**Files:**
- Modify: `src/locallens/core/fabbrica.py` (appendere dopo `_contesto`)
- Test: `tests/test_fabbrica.py` (appendere)

**Interfaces:**
- Consumes: `resolve_binary(platform, backend_gpu, bins_root=None)` da `backend.manager`; `snapshot_completo(preset, cache_root=None)` da `config.pesi`; `HardwareInfo.candidati` (lista, primo = preferito).
- Produces: `disponibilita_gpu_locale(info, preset, piattaforma=None, bins_root=None, cache_root=None) -> bool` (usata dai Task 2, 3, 5).

- [ ] **Step 1: Write the failing test**

```python
def test_disponibilita_solo_se_binario_e_pesi(tmp_path):
    from locallens.core.fabbrica import disponibilita_gpu_locale

    preset = load_preset("presets/glm-ocr-q8_0.toml")
    (tmp_path / "linux" / "cuda").mkdir(parents=True)
    (tmp_path / "linux" / "cuda" / "llama-server").write_text("x")
    assert disponibilita_gpu_locale(_info(), preset) is False  # funzione non esiste ancora
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --with pytest pytest tests/test_fabbrica.py::test_disponibilita_solo_se_binario_e_pesi -q`
Expected: FAIL with ImportError (funzione non definita).

- [ ] **Step 3: Write minimal implementation**

```python
def disponibilita_gpu_locale(info, preset, piattaforma=None, bins_root=None, cache_root=None) -> bool:
    """True se la GPU locale è davvero usabile: binario + pesi presenti. Nessun download."""
    import sys

    from locallens.backend.manager import resolve_binary
    from locallens.config.pesi import snapshot_completo

    if not info.candidati:
        return False
    binario = resolve_binary(piattaforma or sys.platform, info.candidati[0], bins_root)
    return binario.is_file() and snapshot_completo(preset, cache_root) is not None
```

- [ ] **Step 4: Extend test to 4 combinazioni e run**

```python
def test_disponibilita_quattro_combinazioni(tmp_path, monkeypatch):
    import locallens.core.fabbrica as fab

    preset = load_preset("presets/glm-ocr-q8_0.toml")
    binario = tmp_path / "linux" / "cuda" / "llama-server"
    monkeypatch.setattr(fab.sys, "platform", "linux")
    casi = [
        (False, None, False),
        (True, None, False),
        (False, tmp_path / "snap", False),
        (True, tmp_path / "snap", True),
    ]
    for ha_binario, snap, atteso in casi:
        if ha_binario:
            binario.parent.mkdir(parents=True, exist_ok=True)
            binario.write_text("x")
        elif binario.is_file():
            binario.unlink()
        monkeypatch.setattr(
            "locallens.config.pesi.snapshot_completo", lambda p, c=None: snap
        )
        assert fab.disponibilita_gpu_locale(_info(), preset, bins_root=tmp_path) is atteso
```

Run: `uv run --with pytest pytest tests/test_fabbrica.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/locallens/core/fabbrica.py tests/test_fabbrica.py
git commit -m "Rilevamento disponibilita GPU locale (binario+pesi)"
```

### Task 2: Normalizzazione sorgente con ripiego

**Files:**
- Modify: `src/locallens/core/fabbrica.py`
- Test: `tests/test_fabbrica.py`

**Interfaces:**
- Consumes: `disponibilita_gpu_locale` (Task 1).
- Produces: `normalizza_sorgente(conf, info, preset, **rileva_kw) -> tuple[dict, str | None]` che ritorna (conf normalizzata, banner o None). Usata dai Task 3 e 5.

- [ ] **Step 1: Write the failing test**

```python
def test_normalizza_ripiega_su_esterno_se_gpu_assente(monkeypatch):
    import locallens.core.fabbrica as fab
    from locallens.core.fabbrica import normalizza_sorgente

    monkeypatch.setattr(fab, "disponibilita_gpu_locale", lambda *a, **k: False)
    preset = load_preset("presets/glm-ocr-q8_0.toml")
    conf = {"sorgente": "bundlato"}
    nuova, banner = normalizza_sorgente(conf, _info(), preset)
    assert nuova["sorgente"] == "esterno"
    assert "GPU locale non rilevata" in banner
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --with pytest pytest tests/test_fabbrica.py::test_normalizza_ripiega_su_esterno_se_gpu_assente -q`
Expected: FAIL with ImportError.

- [ ] **Step 3: Write minimal implementation**

```python
def normalizza_sorgente(conf, info, preset, **rileva_kw) -> tuple[dict, str | None]:
    """Se il config chiede bundlato ma la GPU locale non è rilevata, ripiega su esterno."""
    if conf.get("sorgente", "bundlato") == "bundlato" and not disponibilita_gpu_locale(
        info, preset, **rileva_kw
    ):
        nuova = dict(conf, sorgente="esterno")
        return nuova, "GPU locale non rilevata (binari o pesi assenti): uso il server esterno."
    return conf, None
```

- [ ] **Step 4: Aggiungi test pass-through e run**

```python
def test_normalizza_lascia_esterno_e_nessuno():
    from locallens.core.fabbrica import normalizza_sorgente

    preset = load_preset("presets/glm-ocr-q8_0.toml")
    for sorg in ("esterno", "nessuno"):
        nuova, banner = normalizza_sorgente({"sorgente": sorg}, _info(), preset)
        assert nuova["sorgente"] == sorg
        assert banner is None
```

Run: `uv run --with pytest pytest tests/test_fabbrica.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/locallens/core/fabbrica.py tests/test_fabbrica.py
git commit -m "Normalizzazione sorgente con ripiego su esterno"
```

### Task 3: Normalizzazione al boot

**Files:**
- Modify: `src/locallens/__main__.py` (funzione `costruisci_da_conf`)
- Test: `tests/test_boot.py`

**Interfaces:**
- Consumes: `normalizza_sorgente` (Task 2); `costruisci_da_conf(conf)` esistente.
- Produces: boot che non tenta mai bundlato indisponibile.

- [ ] **Step 1: Write the failing test**

```python
def test_boot_bundlato_senza_pesi_va_su_esterno():
    from locallens.__main__ import costruisci_da_conf

    conf = dict(DEFAULTS, sorgente="bundlato", url_esterno="http://127.0.0.1:9")
    engine, stato, banner = costruisci_da_conf(conf)
    assert "esterno" in stato
    assert "GPU locale non rilevata" in banner
```

Nota: su macchine CON pesi+binari questo test fallirebbe; in tal caso
inietta `monkeypatch` su `disponibilita_gpu_locale` → False. Scrivilo
fin da subito con monkeypatch per renderlo deterministico:

```python
def test_boot_bundlato_senza_pesi_va_su_esterno(monkeypatch):
    import locallens.core.fabbrica as fab
    from locallens.__main__ import costruisci_da_conf

    monkeypatch.setattr(fab, "disponibilita_gpu_locale", lambda *a, **k: False)
    conf = dict(DEFAULTS, sorgente="bundlato")
    engine, stato, banner = costruisci_da_conf(conf)
    assert stato.startswith("esterno")
    assert "GPU locale non rilevata" in banner
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --with pytest pytest tests/test_boot.py::test_boot_bundlato_senza_pesi_va_su_esterno -q`
Expected: FAIL (stato "bundlato (solo CPU)" invece di "esterno").

- [ ] **Step 3: Write minimal implementation**

```python
def costruisci_da_conf(conf):
    """Boot completo: detect → preset → fabbrica. Ritorna (engine, stato, banner)."""
    from locallens.config.presets import seleziona_preset
    from locallens.core.fabbrica import costruisci, normalizza_sorgente
    from locallens.hwdetect.detector import detect

    info = detect()
    preset = _preset_da_conf(conf)
    conf = dict(conf, preset_id=preset.id)
    conf, avviso = normalizza_sorgente(conf, info, preset)
    engine, stato, banner = costruisci(conf, info, preset)
    atteso = seleziona_preset(info.vram_mb, [preset.id])
    banner = "; ".join(b for b in (avviso, banner) if b)
    return engine, f"{stato} • atteso={atteso}", banner
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --with pytest pytest tests/test_boot.py -q`
Expected: PASS (entrambi i test boot).

- [ ] **Step 5: Commit**

```bash
git add src/locallens/__main__.py tests/test_boot.py
git commit -m "Boot normalizza bundlato indisponibile su esterno"
```

### Task 4: Dialogo con label GPU locale e flag

**Files:**
- Modify: `src/locallens/app/impostazioni.py`
- Test: `tests/test_impostazioni.py`, `tests/test_finestra.py` (doppio `DialogoFinto`)

**Interfaces:**
- Consumes: niente di nuovo.
- Produces: `DialogoImpostazioni(preset_ids, parent=None, tema="chiaro", gpu_locale_disponibile=True)`; `VOCI_SORGENTE = (("GPU locale", "bundlato"), ("esterno", "esterno"), ("nessuno", "nessuno"))`; `valori()["sorgente"]` resta l'id interno.

- [ ] **Step 1: Write the failing tests**

```python
def test_label_gpu_locale_e_flag(qapp):
    d = DialogoImpostazioni(preset_ids=["glm-ocr-q8_0"])
    assert d.sorgente.itemText(0) == "GPU locale"
    assert d.valori()["sorgente"] == "bundlato"
    d2 = DialogoImpostazioni(preset_ids=["glm-ocr-q8_0"], gpu_locale_disponibile=False)
    voci = [d2.sorgente.itemText(i) for i in range(d2.sorgente.count())]
    assert voci == ["esterno", "nessuno"]
    d2.set_sorgente("esterno")
    assert d2.valori()["sorgente"] == "esterno"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --with pytest pytest tests/test_impostazioni.py -q -k "label_gpu_locale"`
Expected: FAIL (prima voce "bundlato", flag ignorato).

- [ ] **Step 3: Write minimal implementation**

```python
VOCI_SORGENTE = (("GPU locale", "bundlato"), ("esterno", "esterno"), ("nessuno", "nessuno"))


class DialogoImpostazioni(QDialog):
    def __init__(self, preset_ids, parent=None, tema="chiaro", gpu_locale_disponibile=True):
        ...
        voci = [v for v in VOCI_SORGENTE if v[1] != "bundlato" or gpu_locale_disponibile]
        self.sorgente = QComboBox()
        self.sorgente.addItems([etichetta for etichetta, _ in voci])
        ...
    def set_sorgente(self, valore: str) -> None:
        for etichetta, ident in VOCI_SORGENTE:
            if ident == valore and self.sorgente.findText(etichetta) >= 0:
                self.sorgente.setCurrentText(etichetta)
                return
    def valori(self) -> dict:
        scelta = self.sorgente.currentText()
        ident = next(ident for etichetta, ident in VOCI_SORGENTE if etichetta == scelta)
        return {
            "sorgente": ident,
            "url_esterno": self.url.text(),
            "preset_id": self.preset.currentText(),
            "lingue_filtro": self.lingue.text().strip() or "it",
            "soglia_righe_loop": self.soglia.value(),
            "ignora_eco": self.ignora_eco.isChecked(),
        }
```

- [ ] **Step 4: Aggiorna il doppio in test_finestra.py e run**

```python
def __init__(self, preset_ids=None, parent=None, tema="chiaro", gpu_locale_disponibile=True, **k):
```

Run: `uv run --with pytest pytest tests/test_impostazioni.py tests/test_finestra.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/locallens/app/impostazioni.py tests/test_impostazioni.py tests/test_finestra.py
git commit -m "Dialogo: label GPU locale condizionale al rilevamento"
```

### Task 5: Finestra passa flag, pill e post-dialogo

**Files:**
- Modify: `src/locallens/app/finestra.py`
- Test: `tests/test_finestra.py`

**Interfaces:**
- Consumes: `disponibilita_gpu_locale`, `normalizza_sorgente` (Task 1-2); flag del dialogo (Task 4).
- Produces: pill con "GPU locale" invece di "bundlato"; `_impostazioni` coerente.

- [ ] **Step 1: Write the failing test**

```python
def test_pill_mostra_gpu_locale(qapp):
    from locallens.app.finestra import ETICHETTE_SORGENTE, MainWindow

    assert ETICHETTE_SORGENTE["bundlato"] == "GPU locale"
    w = MainWindow()
    w.conf.update({"sorgente": "bundlato", "preset_id": "x"})
    w.aggiorna_intestazione()
    assert "GPU locale" in w.pill.text()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --with pytest pytest tests/test_finestra.py -q -k "pill_mostra"`
Expected: FAIL (ImportError: ETICHETTE_SORGENTE).

- [ ] **Step 3: Write minimal implementation**

```python
ETICHETTE_SORGENTE = {"bundlato": "GPU locale", "esterno": "esterno", "nessuno": "nessuno"}
```

In `aggiorna_intestazione`, sostituire `{sorgente}` con
`{ETICHETTE_SORGENTE.get(sorgente, sorgente)}`.

In `_impostazioni`, prima di creare il dialogo:

```python
from locallens.core.fabbrica import disponibilita_gpu_locale, normalizza_sorgente

def _preset_corrente(self):
    from locallens.__main__ import _preset_da_conf
    return _preset_da_conf(self.conf)

def _gpu_locale_disponibile(self) -> bool:
    from locallens.hwdetect.detector import detect
    try:
        return disponibilita_gpu_locale(detect(), self._preset_corrente())
    except Exception:
        return False
```

Passare `gpu_locale_disponibile=self._gpu_locale_disponibile()` al
dialogo; dopo `self.conf.update(dlg.valori())`, normalizzare:

```python
self.conf, avviso = normalizza_sorgente(self.conf, detect(), self._preset_corrente())
if avviso:
    self.mostra_banner(avviso)
```

- [ ] **Step 4: Run full suite**

Run: `uv run --with pytest pytest tests/ -q`
Expected: PASS tutto.

- [ ] **Step 5: Commit**

```bash
git add src/locallens/app/finestra.py tests/test_finestra.py
git commit -m "Finestra: flag GPU locale, pill e normalizzazione post-dialogo"
```
