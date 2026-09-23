# Provider locale generico Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** L'utente incolla solo l'URL completo di un server locale OpenAI-compatibile (Ollama `/api/chat`, LM Studio/llama-server `/v1/chat/completions`) e l'app funziona, con health-check dialetto-aware e fallback CPU solo se il server non risponde.

**Architecture:** Generalizzare `verifica_health` in `rete.py` per dialetto, unificare il ramo `bundlato`/`esterno` in `fabbrica.py` come "server generico" verbatim, mantenere `Config` compatibile salvando l'URL su entrambi i campi, aggiornare `impostazioni.py` a campo URL unico e aggiornare docs. `HttpInferAdapter` resta verbatim.

**Tech Stack:** Python 3.11+, PySide6, urllib, pytest, ruff/mypy

**Spec:** `docs/superpowers/specs/2026-09-23-provider-locale-generico-design.md`

## Global Constraints

- `SorgenteModello` interno `bundlato`/`esterno`/`nessuno` invariato per compat (solo alias logico).
- `token_esterno` è `SEGRET` e mai scritto su disco (`src/locallens/config/settings.py:31`).
- `invia_chat` resta verbatim sull'URL (`src/locallens/core/client.py:86`), `HttpInferAdapter` distingue `ollama`/`openai` via `dialetto()`.
- Privacy: `is_url_privata` decide solo banner, non health.
- Comandi: `uv run --with pytest pytest tests/ -q`, `uv run --with ruff ruff check src tests`, `uv run --with mypy mypy src/locallens/`
- Un commit per task, solo file del task.

---

### Task 1: Health-check dialetto-aware

**Files:**
- Modify: `src/locallens/core/rete.py:40-48`
- Modify: `src/locallens/core/client.py` (import `dialetto` già presente, nessun cambio firma)
- Test: `tests/test_backend.py` (appendere) oppure `tests/test_rete_nuovo.py` (se non esiste `test_rete.py`, crearne uno nuovo)

**Interfaces:**
- Consumes: `dialetto(url)` da `src/locallens/core/client.py:53`, `urllib.request.urlopen`
- Produces: `verifica_health(url: str, timeout: float=2) -> bool` generica (stessa firma, nuova semantica: `ollama` → `/api/tags`, altrimenti `/v1/models` → `/health` → `""`)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_rete.py
def test_verifica_health_ollama_us_api_tags(monkeypatch):
    from locallens.core import rete
    chiamate = []
    def fake_urlopen(req, timeout=2):
        chiamate.append(req.full_url if hasattr(req, "full_url") else req)
        class Resp:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *a): return False
        # deve chiamare /api/tags, non /health
        assert "/api/tags" in chiamate[0]
        return Resp()
    monkeypatch.setattr(rete.urllib.request, "urlopen", fake_urlopen)
    assert rete.verifica_health("http://127.0.0.1:11434/api/chat") is True
    assert chiama_api_tags_non_health(chiamate)

def test_verifica_health_openai_prova_v1_models(monkeypatch):
    from locallens.core import rete
    # primo tentativo /v1/models → 404, secondo /health → 200
    import urllib.error
    def fake_urlopen(req, timeout=2):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if url.endswith("/v1/models"):
            raise urllib.error.HTTPError(url, 404, "not found", {}, None)
        class Resp:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *a): return False
        return Resp()
    monkeypatch.setattr(rete.urllib.request, "urlopen", fake_urlopen)
    assert rete.verifica_health("http://127.0.0.1:1234/v1/chat/completions") is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --with pytest pytest tests/test_rete.py -v`
Expected: FAIL — `verifica_health` chiama ancora `/health` e non `/api/tags`, quindi primo assert fallisce.

- [ ] **Step 3: Write minimal implementation**

```python
# src/locallens/core/rete.py
def verifica_health(base_url: str, timeout: float = 2) -> bool:
    """True se GET su endpoint dialetto-aware risponde 200. Mai eccezioni."""
    import urllib.request
    from locallens.core.client import dialetto
    def _get_ok(url: str) -> bool:
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                return r.status == 200
        except (OSError, ValueError):
            return False
        except Exception:
            return False
    d = dialetto(base_url)
    if d == "ollama":
        base = base_url.rstrip("/").removesuffix("/api/chat").rstrip("/")
        if not base:
            base = base_url.rstrip("/")
        return _get_ok(base + "/api/tags")
    # openai-compat: prova /v1/models → /health → base stessa
    base = base_url.rstrip("/")
    for suffix in ("/v1/models", "/health", ""):
        # evita doppio // quando base già contiene /v1/chat/completions
        cand = base + suffix if not base.endswith(suffix) or suffix == "" else base
        # per base verbatim con /v1/chat/completions, /v1/models è comunque distinto: ok
        if _get_ok(cand):
            return True
    return False
```

Se `removesuffix` non disponibile su 3.11? È disponibile da 3.9 — ok. Altrimenti usa `if base_url.endswith("/api/chat"): base = base_url[:-9]`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --with pytest pytest tests/test_rete.py -v`
Expected: PASS

- [ ] **Step 5: Run existing related tests**

Run: `uv run --with pytest pytest tests/test_backend.py tests/test_fabbrica.py -q`
Expected: PASS (se `test_fabbrica` mocka `verifica`, non tocca rete reale)

- [ ] **Step 6: Commit**

```bash
git add src/locallens/core/rete.py tests/test_rete.py
git commit -m "feat(rete): verifica_health dialetto-aware per Ollama e OpenAI"
```

---

### Task 2: Unificare Factory su server generico

**Files:**
- Modify: `src/locallens/core/fabbrica.py:36-139` (disponibilita + costruisci) e `:181-261` (EngineFactory.rebuild)
- Test: `tests/test_fabbrica.py` (appendere 4 nuovi test)

**Interfaces:**
- Consumes: `verifica_health` (Task1), `HttpInferAdapter`, `preset_da_conf`, `dialetto`
- Produces: `costruisci(conf, info, preset, ...)` e `EngineFactory.rebuild(Config)` con unico ramo `server generico`

- [ ] **Step 1: Write the failing test**

```python
def test_bundlato_con_url_ollama_usa_health_generica(monkeypatch):
    from locallens.core.fabbrica import costruisci
    preset = load_preset("presets/glm-ocr-q8_0.toml")
    conf = {"sorgente": "bundlato", "url_gpu_locale": "http://127.0.0.1:11434/api/chat"}
    def verifica(url):
        assert "/api/tags" in url or url == "http://127.0.0.1:11434/api/chat" or "/api/tags" in url
        # simula che la nuova verifica_health sarebbe chiamata con /api/tags
        return True
    # Oggi verifica è chiamata con url verbatim + /health → fallirebbe per Ollama
    # Test fallisce perché costruisci non usa verifica_health_generica
    eng, stato, banner = costruisci(conf, _info(), preset, crea=lambda u,p,motore,**k: "engine", verifica=lambda u: True)
    assert eng == "engine"
```

Simpler real failing test:

```python
def test_esterno_locale_url_generico_senza_prefisso_health(monkeypatch):
    import locallens.core.fabbrica as fab
    preset = load_preset("presets/glm-ocr-q8_0.toml")
    conf = {"sorgente": "esterno", "url_esterno": "http://127.0.0.1:11434/api/chat", "modello_esterno": "dott", "token_esterno": "x"}
    # mock verifica_health_generica per vedere che viene chiamata con URL Ollama
    chiamate = {}
    def fake_verifica(url):
        chiamate["url"] = url
        return True
    monkeypatch.setattr(fab, "verifica_health", fake_verifica)
    from locallens.core.fabbrica import costruisci
    # se costruisci ignora verifica_health_generica e usa vecchia logica, test fallisce
    assert False, "da implementare unificazione"
```

Per TDD reale, scrivi:

```python
def test_url_generico_ollama_non_richiede_prefisso_health():
    from locallens.core.fabbrica import costruisci
    preset = load_preset("presets/glm-ocr-q8_0.toml")
    conf = {"sorgente": "bundlato", "url_gpu_locale": "http://127.0.0.1:11434/api/chat", "modello_esterno": "m", "preset_id": "glm-ocr-q8_0"}
    # Con implementazione attuale, bundlato con url Ollama e verifica=True passa, ma con verifica reale fallirebbe
    # Test atteso dopo fix: costruisci con verifica=lambda u: u.endswith("/api/tags") deve passare
    assert True
```

Scegli il test più semplice che verifica unificazione: duplica `test_bundlato_usa_url_se_health_ok` ma con `url_gpu_locale` Ollama e `verifica` che controlla `/api/tags`:

```python
def test_bundlato_ollama_usa_api_tags(monkeypatch):
    import locallens.core.fabbrica as fab
    preset = load_preset("presets/glm-ocr-q8_0.toml")
    conf = {"sorgente": "bundlato", "url_gpu_locale": "http://127.0.0.1:11434/api/chat"}
    def verifica(url):
        # dopo fix, verifica_health sarà chiamata con base + /api/tags
        return url.endswith("/api/tags")
    # Oggi costruisci chiama verifica con url verbatim + /health, quindi questo verifica fallirà
    eng, _, _ = fab.costruisci(conf, _info(), preset, crea=lambda u,p,motore,**k: "engine", verifica=verifica, solo_cpu=lambda m: "cpu")
    assert eng == "engine"  # fallisce prima del fix
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --with pytest pytest tests/test_fabbrica.py::test_bundlato_ollama_usa_api_tags -v`
Expected: FAIL (engine == "cpu:...") perché verifica non matcha

- [ ] **Step 3: Write minimal implementation**

In `src/locallens/core/fabbrica.py`:
1. In alto, importa `dialetto` da `core.client` se non già.
2. Sostituisci `if sorgente=="bundlato"` + `if sorgente=="esterno"` in `costruisci()` con:

```python
if sorgente in ("bundlato", "esterno"):
    url = (d.get("url_gpu_locale") or d.get("url_esterno") or "http://127.0.0.1:8011").strip()
    from locallens.core.client import dialetto
    # health generica già in verifica (Task1), quindi basta chiamare verifica(url)
    # ma se verifica è la vecchia, ora è generica quindi ok
    # Mantieni logica token/modello solo se necessario per cloud? Per locale token opzionale
    modello = (d.get("modello_esterno") or "").strip()
    preset_id = d.get("preset_id", "")
    # se modello manca e preset presente, usa preset.id (per llama-server)
    if not modello and preset and getattr(preset, "id", ""):
        modello = preset.id
    if not modello:
        motivo = t(lingua, "motivo_esterno_manca_modello")
        return solo_cpu(motivo), t(lingua, "stato_esterno_non_configurato"), t(lingua, "banner_esterno_non_configurato")
    # token opzionale per locale: non bloccare se manca quando url è privata
    from locallens.core.rete import is_url_privata
    if not is_url_privata(url) and not (d.get("token_esterno") or "").strip():
        # cloud pubblico senza token → come prima, richiedi token
        motivo = t(lingua, "motivo_esterno_manca_token")
        return solo_cpu(motivo), t(lingua, "stato_esterno_non_configurato"), t(lingua, "banner_esterno_non_configurato")
    banner_priv = "" if is_url_privata(url) else t(lingua, "banner_privacy_url")
    if verifica(url):
        # usa crea_cloud se modello esplicito, altrimenti crea (preset)
        if d.get("modello_esterno"):
            if crea_cloud is None:
                from locallens.core.orchestrator import crea_engine_cloud as _cc
                crea_cloud = _cc
            engine = crea_cloud(url, modello=modello, prompt=d.get("prompt_esterno",""), token=(d.get("token_esterno") or "").strip(), max_side=d.get("max_side_px",2048), contrasto=d.get("contrasto",False), **_contesto(d))
            return engine, t(lingua, "stato_esterno", url=url), banner_priv
        return crea(url, preset, motore="bundlato", max_side=d.get("max_side_px",2048), contrasto=d.get("contrasto",False), **_contesto(d)), t(lingua, "stato_gpu_locale", url=url), banner_priv
    motivo = t(lingua, "motivo_gpu_non_raggiungibile", url=url)
    return solo_cpu(motivo), t(lingua, "stato_gpu_solo_cpu"), t(lingua, "banner_solo_cpu_assente", url=url)
```

In `EngineFactory.rebuild()` applica stessa unificazione: singolo `if sorgente in ("bundlato","esterno"):` e usa `self._verify` (che ora è `verifica_health` generica) + `self._make_infer` con `dialetto` check.

Mantieni `disponibilita_gpu_locale` come indicatore non gate: rimuovi il blocco che forza `d["sorgente"]="esterno"` con `banner_gpu_non_rilevata` se `disponibilita` false — trasforma in solo `avviso` senza cambiare sorgente (o rimuovilo del tutto per locale self-managed). Per compat, lascia `avviso` ma non cambia `sorgente`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --with pytest pytest tests/test_fabbrica.py -v`
Expected: PASS (tutti i vecchi + nuovo)

- [ ] **Step 5: Commit**

```bash
git add src/locallens/core/fabbrica.py tests/test_fabbrica.py
git commit -m "feat(fabbrica): unifica bundlato/esterno su URL generico verbatim"
```

---

### Task 3: Adapter verbatim e docs

**Files:**
- Modify: `src/locallens/core/client.py:116-174` (commento + eventuale helper `_endpoint` se base nuda)
- Modify: `README.md:46-55` (Model sources), `docs/architecture.md`, `CONTEXT.md`

**Interfaces:**
- Consumes: Task1 health, Task2 factory
- Produces: `HttpInferAdapter` documentato come verbatim per URL generico

- [ ] **Step 1: Write the failing test**

```python
def test_adapter_usa_url_verbatim_ollama():
    from locallens.core.client import HttpInferAdapter
    adapter = HttpInferAdapter(base_url="http://127.0.0.1:11434/api/chat", modello="dott", prompt="p", sorgente="esterno")
    # mock post per catturare url
    chiamate = {}
    def fake_post(url, payload):
        chiamate["url"] = url
        return {"message": {"content": "ok"}}
    adapter.post = fake_post
    # prepara png finto 1x1
    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (10,10), "white").save(buf, format="PNG")
    testo, motore = adapter(1, buf.getvalue())
    assert chiamate["url"] == "http://127.0.0.1:11434/api/chat"  # verbatim
    assert motore == "esterno"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --with pytest pytest tests/test_client.py::test_adapter_usa_url_verbatim_ollama -v`
Expected: FAIL se adapter appende `/v1/chat/completions`

- [ ] **Step 3: Write minimal implementation**

In `src/locallens/core/client.py` `HttpInferAdapter.__call__`:
- Assicura ramo `sorgente=="esterno"` usi `self.base_url` verbatim (già fa) e aggiungi commento.
- Rimuovi/ depreca ramo `bundlato` che appende `/v1/chat/completions` se `base_url` contiene già `/api/chat` o `/v1/chat/completions`; altrimenti per compat con base nuda `http://127.0.0.1:8011` mantieni append per retrocompat.

```python
endpoint = self.base_url.rstrip("/")
if endpoint.endswith("/api/chat") or endpoint.endswith("/v1/chat/completions"):
    url_chat = endpoint
else:
    # base nuda: default openai
    url_chat = endpoint + "/v1/chat/completions"
```

Per `sorgente=="bundlato"` usa stessa logica verbatim (non più sempre append).

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --with pytest pytest tests/test_client.py -v`
Expected: PASS

- [ ] **Step 5: Update docs**

In `README.md` e `docs/architecture.md`: tabella Model sources → `Locale (qualsiasi server OpenAI-compatibile, URL completo)` + esempi `curl` per Ollama/LM Studio.

- [ ] **Step 6: Commit**

```bash
git add src/locallens/core/client.py README.md docs/architecture.md CONTEXT.md
git commit -m "feat(client): URL generico verbatim e docs provider locale"
```

---

### Task 4: Config effective_url e persistenza

**Files:**
- Modify: `src/locallens/config/settings.py:118-133` (`effective_url`, `save`)
- Test: `tests/test_settings.py`

**Interfaces:**
- Consumes: Task2
- Produces: `Config.effective_url()` ritorna primo non vuoto tra `url_gpu_locale`/`url_esterno`

- [ ] **Step 1: Write the failing test**

```python
def test_effective_url_preferisci_gpu_locale():
    from locallens.config.settings import Config
    c = Config(url_gpu_locale="http://127.0.0.1:11434/api/chat", url_esterno="http://127.0.0.1:8011")
    assert c.effective_url() == "http://127.0.0.1:11434/api/chat"

def test_effective_url_fallback_esterno():
    from locallens.config.settings import Config
    c = Config(url_gpu_locale="", url_esterno="http://127.0.0.1:8011/v1/chat/completions")
    assert c.effective_url() == "http://127.0.0.1:8011/v1/chat/completions"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --with pytest pytest tests/test_settings.py::test_effective_url_preferisci_gpu_locale -v`
Expected: FAIL (effective_url ritorna solo url_gpu_locale senza fallback)

- [ ] **Step 3: Write minimal implementation**

```python
def effective_url(self) -> str:
    return (self.url_gpu_locale or "").strip() or (self.url_esterno or "").strip() or "http://127.0.0.1:8011"
```

In `salva()`/`_scrivi_toml` assicurati che se uno dei due URL è vuoto ma l'altro valorizzato, entrambi vengano scritti uguali per compat (opzionale, nel dialogo si fa).

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --with pytest pytest tests/test_settings.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/locallens/config/settings.py tests/test_settings.py
git commit -m "feat(config): effective_url fallback generico"
```

---

### Task 5: UI URL unico

**Files:**
- Modify: `src/locallens/app/impostazioni.py:33-180` (DialogoImpostazioni)
- Modify: `src/locallens/app/lingua.py` (etichette)
- Modify: `src/locallens/app/finestra.py:646-660` (gpu_locale_disponibile → indicatore)
- Test: `tests/test_impostazioni.py`, `tests/test_finestra.py`

**Interfaces:**
- Consumes: Task4 Config
- Produces: Dialogo con singolo campo URL server locale

- [ ] **Step 1: Write the failing test**

```python
def test_dialogo_url_unico_sincronizza_entrambi(qapp):
    from locallens.app.impostazioni import DialogoImpostazioni
    d = DialogoImpostazioni()
    d.set_url_server("http://127.0.0.1:11434/api/chat")
    v = d.valori()
    assert v["url_gpu_locale"] == "http://127.0.0.1:11434/api/chat"
    assert v["url_esterno"] == "http://127.0.0.1:11434/api/chat"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --with pytest pytest tests/test_impostazioni.py::test_dialogo_url_unico_sincronizza_entrambi -v`
Expected: FAIL (metodo non esiste)

- [ ] **Step 3: Write minimal implementation**

In `DialogoImpostazioni`:
- Aggiungi `self.url_server = QLineEdit()` con placeholder con 3 esempi.
- `set_url_server(v)` imposta `self.url.setText(v)` e sync; `valori()` ritorna `{"url_gpu_locale": url, "url_esterno": url, ...}`.
- Mantieni `set_url_esterno`/`set_url_gpu_locale` come alias per test vecchi (chiamano `set_url_server`).
- Rimuovi gating che nasconde campi bundlato; mostra sempre URL + modello + prompt.

In `finestra.py` `_gpu_locale_disponibile()` torna sempre `True` o mostra badge “Server self-managed” invece di “GPU non rilevata”.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --with pytest pytest tests/test_impostazioni.py tests/test_finestra.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/locallens/app/impostazioni.py src/locallens/app/lingua.py src/locallens/app/finestra.py tests/test_impostazioni.py
git commit -m "feat(ui): dialogo URL server locale unico"
```

---

### Task 6: Verifica end-to-end (opzionale live)

**Files:**
- Test: `tests/test_integrazione_ocr.py` (nessuna modifica codice, solo verifica)
- Docs: `docs/superpowers/specs/2026-09-23-provider-locale-generico-design.md` checklist

- [ ] **Step 1: Run all unit tests**

Run: `uv run --with pytest pytest tests/ -q`
Expected: PASS (255+)

- [ ] **Step 2: Manual smoke (se Ollama/LM Studio in esecuzione)**

Run: `LOCALLENS_LIVE=1 LOCALLENS_URL=http://127.0.0.1:11434/api/chat uv run --with pytest pytest tests/test_integrazione_ocr.py -q`
Expected: PASS su 1 pagina

- [ ] **Step 3: Commit docs checklist**

```bash
git add docs/superpowers/specs/2026-09-23-provider-locale-generico-design.md
git commit -m "docs: checklist provider locale completata" --allow-empty
```
