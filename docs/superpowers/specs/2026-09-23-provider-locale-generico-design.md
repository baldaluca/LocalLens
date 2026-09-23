# Design: Provider locale generico (OpenAI-compatibile, URL-only)

**Data:** 2026-09-23  
**Stato:** approvato (brainstorming architectural)  
**Approccio scelto:** 1 — Minimal URL-generico (estende `esterno`/`bundlato` come alias)

## 1. Contesto e problema

L'ultima esecuzione (`~/.config/locallens/esecuzioni/5e614c50.jsonl`) è caduta in `cpu-tesseract` nonostante `Config.sorgente=bundlato` e `HardwareInfo(candidati=cuda,vulkan,cpu, vram=4096, snapshot presente)` perché `verifica_health("http://127.0.0.1:11434/api/chat")` fa `GET /health → 404` su Ollama. `EngineFactory.rebuild()` (`src/locallens/core/fabbrica.py:247`) considera il server assente e crea `solo_cpu`.

Obiettivo: l'utente incolla **solo l'URL** del server locale self-managed (Ollama `http://127.0.0.1:11434/api/chat`, LM Studio `http://127.0.0.1:1234/v1/chat/completions`, `llama-server` `http://127.0.0.1:8011/v1/chat/completions` o base `http://127.0.0.1:8011`) e l'app funziona, auto-rilevando il dialetto. Nessun `BackendManager.start()`.

Ambito v1: solo provider OpenAI-compatibili locali (scelta A). Cloud resta su `esterno` con token.

## 2. Architettura target

```
Config (url_gpu_locale/url_esterno + modello_esterno + prompt_esterno + preset_id facoltativo)
  → normalizza_sorgente (bundlato/esterno → alias "server generico", compat)
  → verifica_health_generica(url) // dialetto-aware
  → HttpInferAdapter(base_url=url verbatim, preset?, modello, prompt)
  → OcrPipeline → Estrazione
```

- `app/finestra.py → controller → EngineFactory.rebuild(Config)` invariato.
- `HttpInferAdapter` resta unico seam HTTP (`src/locallens/core/client.py:116`), `dialetto()` già distingue `ollama` vs `openai` (`:53`), `invia_chat` è verbatim (`:86`).
- `BackendManager` resta nel repo ma non è invocato per provider generico; `is_url_privata` decide solo il banner privacy, non la salute.
- Invariante: per URL generico l'URL è **verbatim** (come già per `esterno`). Il ramo legacy `bundlato` che aggiungeva `/v1/chat/completions` in `HttpInferAdapter:173` è deprecato — documentato come “incolla l'URL completo come lo testi con `curl`”.

## 3. Config (`src/locallens/config/settings.py:64`)

- Mantiene `sorgente: Literal["bundlato","esterno","nessuno"]` per compat; `validated()` non rompe file esistenti. `bundlato` e `esterno` mappano sullo stesso ramo “server generico” in `fabbrica.py`.
- `url_gpu_locale` e `url_esterno` restano entrambi; `effective_url()` ritorna il primo non vuoto. Il dialogo salva il valore su **entrambi** per compat con `~/.config/locallens/config.toml` esistente.
- `preset_id` opzionale: se URL è `llama-server` e preset presente, `preset_da_conf` (`src/locallens/config/presets.py:49`) fornisce `prompt`/`max_side`; per Ollama/LM Studio `preset=None` e si usa `prompt_esterno` + `modello_esterno` (già previsto in `fabbrica._make_infer` `:154`).
- `token_esterno` resta `SEGRET` non scritto su disco (`:31`); per locali è `""`.

## 4. Health generica (`src/locallens/core/rete.py:40`)

```python
def verifica_health_generica(base_url: str) -> bool:
    d = dialetto(base_url)
    if d == "ollama":
        base = base_url.rstrip("/").removesuffix("/api/chat").rstrip("/")
        return _get_ok(base + "/api/tags")
    for suffix in ("/v1/models", "/health", ""):
        if _get_ok(base_url.rstrip("/") + suffix):
            return True
    return False
```
`_get_ok` = `urllib.request.urlopen(..., timeout=2).status == 200`. Mantiene firma `verifica_health(url)->bool` così `EngineFactory` e `BackendManager.health()` non cambiano interfaccia. `is_url_privata` resta solo per `banner_privacy_url` (`src/locallens/core/fabbrica.py:94`).

## 5. Adapter & Factory

**`src/locallens/core/client.py:116` HttpInferAdapter**
- Unifica `esterno`/`bundlato` in unico `__call__`: `prepara()` → `b64` → `dialetto` switch tra `build_ollama_payload` e `build_chat_payload` (`:156`). `invia_chat` verbatim; documentato che l'utente incolla URL completo (con `/api/chat` o `/v1/chat/completions`).
- Nessun nuovo template; `build_chat_payload`/`build_ollama_payload` invariati.

**`src/locallens/core/fabbrica.py:181` EngineFactory.rebuild**
- Singolo ramo `if sorgente in ("bundlato","esterno"):`:
  ```
  url = d.get("url_gpu_locale") or d.get("url_esterno") or "http://127.0.0.1:8011"
  if not verifica_health_generica(url): return solo_cpu(motivo_gpu_non_raggiungibile), stato_solo_cpu, banner
  modello = (d.get("modello_esterno") or "").strip() or (preset.id if preset and preset.id else "")
  if not modello.strip(): return solo_cpu(motivo_manca_modello), stato_non_config, banner
  infer = HttpInferAdapter(base_url=url, preset=preset, modello=modello, ...)
  ```
- `disponibilita_gpu_locale` (`:26`) diventa indicatore (badge) non gate, perché server è self-managed.
- Error handling: `invia_chat` solleva `InferenzaError` con `HTTP code + corpo` (`:108`), `OcrPipeline.submit` (`src/locallens/core/pipeline.py:359`) fa 1 retry poi fallback Tesseract con `nota` + `scartato` in diario — invariato.

## 6. UI & Docs

**`src/locallens/app/impostazioni.py`**
- Unico campo “URL server locale” (placeholder con esempi Ollama/LM Studio/llama-server). Salva su entrambi `url_gpu_locale` e `url_esterno`. Mantiene `modello_esterno` (obbligatorio se preset assente) + `prompt_esterno`.
- Rimuove gating `gpu_locale_disponibile` che nascondeva `bundlato` (`src/locallens/app/finestra.py:646` → solo indicatore).
- Validazione live al Salva: `verifica_health_generica` con banner inline, non blocca.

**`src/locallens/app/finestra.py` + `lingua.py`**
- `SORGENTE_LABELS` mantiene alias per traduzioni; pill mostra `● Locale • {url}` per entrambi.

**Docs:** `README.md` tabella Model sources → `Locale (qualsiasi server OpenAI-compatibile, URL completo)` + esempi curl; `docs/architecture.md` + `CONTEXT.md` aggiornati (SorgenteModello alias).

## 7. Testing

- Unit (mock): `tests/test_rete.py` parametrizza `verifica_health_generica` su `/api/tags` vs `/v1/models` vs `/health`; `tests/test_client.py` verifica `dialetto()` + `HttpInferAdapter` con `post` finto su URL con/senza suffix; `tests/test_fabbrica.py` verifica `rebuild` con `verify=False/True` e modello mancante.
- Live opzionale: `LOCALLENS_LIVE=1 LOCALLENS_URL=http://127.0.0.1:11434/api/chat` e `...1234/v1/chat/completions` riusa `tests/test_integrazione_ocr.py`.

## 8. Rischi e non-obiettivi

- Non tocca `bins/`, `BackendManager.start`, download pesi, `pypdfium2`, `preprocessing`; rollback = revert di `rete.py:verifica_health` + `fabbrica.rebuild`.
- Fuori scope v1: provider non-OpenAI, discovery automatico porte, registro plugin estensibile (Approccio 3 rimandato).

## 9. Checklist implementazione

- [ ] `src/locallens/core/rete.py` — `verifica_health_generica` dialetto-aware
- [ ] `src/locallens/core/fabbrica.py` — unifica ramo bundlato/esterno, usa health generica
- [ ] `src/locallens/core/client.py` — doc verbatim URL, eventuale helper `_endpoint` se base nuda
- [ ] `src/locallens/config/settings.py` — `effective_url` + save su entrambi URL
- [ ] `src/locallens/app/impostazioni.py` + `lingua.py` + `finestra.py` — UI URL unico
- [ ] `tests/test_rete.py`, `test_client.py`, `test_fabbrica.py` — unit
- [ ] `README.md`, `docs/architecture.md`, `CONTEXT.md` — docs
