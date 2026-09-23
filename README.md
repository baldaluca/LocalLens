# LocalLens

![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![Platform](https://img.shields.io/badge/platform-linux%20%7C%20windows-lightgrey)
![GUI](https://img.shields.io/badge/gui-PySide6-green)
![Tests](https://img.shields.io/badge/tests-255%20passed-brightgreen)

Desktop OCR app: extract text from images and PDFs using local GPU inference when available, an optional external/cloud server (including free OpenRouter vision models), and CPU fallback.

## Features

- 📄 OCR from **images and PDFs** (file, clipboard, screenshot) — see `Documento` / `Pagina` in `CONTEXT.md`
- 🖥️ **Local GPU** (`bundlato`) — models you run yourself (llama.cpp, Ollama, LM Studio) at a dedicated local URL
- ☁️ **External** (`esterno`) — any OpenAI-compatible server: self-hosted `llama-server`, **OpenRouter** (free tier), or other cloud; token lives **only in memory**, never written to disk, cleared on close
- 🔤 **CPU fallback** via Tesseract (PSM 6), with fail-fast on degenerate model output
- 🌍 UI in **Italian or English**, hot-switchable from Settings (`LinguaInterfaccia`, default `en`)
- 🌓 Light / dark themes, per-page engine badge, single-page filtering, Markdown output (copy / Save .md), JSONL run diary

## Quickstart

### Linux

```bash
uv sync
uv run python -m locallens        # GUI (or: uv run locallens)
```

Smoke test without a display:

```bash
QT_QPA_PLATFORM=offscreen timeout 12 uv run python -m locallens
```

Requirements: Python ≥ 3.11, [uv](https://docs.astral.sh/uv/), Tesseract (`apt install tesseract-ocr tesseract-ocr-ita`).

### Windows

```powershell
pip install uv
uv sync
uv run python -m locallens
```

Requirements: Python ≥ 3.11, [uv](https://docs.astral.sh/uv/), Tesseract (`choco install tesseract -y` or installer from [UB-Mannheim](https://github.com/UB-Mannheim/tesseract/wiki) with `ita` language data).

> **Local GPU needs a server you start yourself.** If no server answers at the configured URL you get CPU fallback with a banner telling you to start `llama-server` there and retry. In a VM with a virtual VGA, `bundlato/cuda` always fails by design — use `esterno` or `nessuno`.

## Model sources

| Source | What it does |
|---|---|
| **Local GPU** (`bundlato`) | Server at the Local GPU URL. Entry shown only if binaries + weights are detected, otherwise it automatically falls back to External with a banner. |
| **External** (`esterno`) | Any OpenAI-compatible server at an external URL (verbatim) + model + prompt + token (session-only, never saved). Includes self-hosted servers and cloud providers like OpenRouter. Privacy warning on non-local URLs. |
| **None** (`nessuno`) | Tesseract only. |

Presets (`presets/*.toml`) apply to local servers; external/cloud uses your manual model + prompt. See `PresetModello` in `CONTEXT.md`.

## External models via OpenRouter (free tier)

`SorgenteModello = esterno` works with any OpenAI-compatible endpoint. The easiest way to try cloud OCR without a local GPU is [OpenRouter](https://openrouter.ai/models?max_price=0) — it proxies many providers behind `https://openrouter.ai/api/v1/chat/completions`.

### Setup in LocalLens

1.  Create an API key at `https://openrouter.ai/settings/keys`
2.  In LocalLens: `Settings → Source = External`
3.  Set:
    * **URL** = `https://openrouter.ai/api/v1/chat/completions`
    * **Model** = one of the IDs below (with `:free` suffix)
    * **Prompt** = `Transcribe the document text exactly. No commentary.`
    * **Token** = your `sk-or-v1-...` key (kept only in memory, never written to disk — `src/locallens/config/settings.py:31`)

The app sends the image as `base64` + prompt using the standard `build_chat_payload` (`src/locallens/core/client.py:14`) — no extra configuration needed. Non-local URL banner (`RNF1`) is expected for OpenRouter.

### Recommended free vision models (verified 2026-09-23 via `openrouter.ai/api/v1/models`)

Free models rotate monthly; verify live at `https://openrouter.ai/models?max_price=0`. All below have `input_modalities` including `image` and `pricing.prompt = 0`:

| Model ID | Notes | Context |
|---|---|---|
| `inclusionai/ling-3.0-flash-vl:free` | **Recommended for OCR** — 124B MoE, explicitly vision-capable (`image+video → text`), best document-text fidelity | 262K |
| `thinkingmachines/inkling-small:free` | Smaller Inkling variant, 1M context multimodal | 1M |
| `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` | Omni-modal `image+video+audio → text`, reasoning | 256K |

Other free text-only models (e.g. `nvidia/nemotron-3-ultra-550b-a55b:free`, `poolside/laguna-*`) are **not** suitable for OCR — they lack vision input.

> **Limits:** free tier is rate-limited (429) and may log prompts per provider. For production, use a paid OpenRouter model or a self-hosted `llama-server`. `openrouter/free` router (`openrouter/free:free`) auto-picks a random free model but is not deterministic — prefer an explicit ID.

Example `curl` (same payload LocalLens sends):

```bash
curl -X POST https://openrouter.ai/api/v1/chat/completions \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "inclusionai/ling-3.0-flash-vl:free",
    "messages": [
      {"role": "system", "content": "Transcribe the document text exactly. No commentary."},
      {"role": "user", "content": [
        {"type": "text", "text": "Transcribe the document text exactly. No commentary."},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
      ]}
    ]
  }'
```

## Configuration

Settings persist to the user config (`XDG`/`APPDATA`) except the API token, which is never written to disk. The typed `Config` module (`src/locallens/config/settings.py:64`) owns `lingua | sorgente | url_esterno | url_gpu_locale | preset_id | max_side_px | contrasto | lingue_filtro | soglia_righe_loop | ignora_eco | tema`. The anti-self-hit filter (languages, loop threshold, prompt-echo ignore) is tunable from Settings. See `config.example.toml` (includes OpenRouter example).

## Architecture

Deep modules with narrow seams (see `docs/architecture.md` and `CONTEXT.md` for the ubiquitous language):

```
src/locallens/
├── config/settings.py   → Config (frozen dataclass, load/save/validated/effective_url)
├── app/lingua.py        → LinguaService (t() + set_lingua, single SORGENTE_LABELS source)
├── core/fabbrica.py     → EngineFactory (rebuild(Config) → OcrEngine, owns ModelSource)
├── app/controller.py    → DocumentController (Presenter, owns Pagina/Estrazione workflow)
├── core/pipeline.py     → OcrPipeline + core/client.py HttpInferAdapter (single Page seam)
├── app/impostazioni.py  → Dialog.edit(Config) → Optional[Config] adapter
└── app/finestra.py      → View (thin, signals only: openRequested / settingsAccepted)
```

`BackendGpu` (`cuda | hip | vulkan | cpu`) is chosen at runtime via `hwdetect/detector.py`. `app` talks only to `core`/`config`; never directly to `backend` or a remote URL. External URLs are used verbatim (`src/locallens/core/client.py:86` — `invia_chat` adds no suffix; for `bundlato` the suffix `/v1/chat/completions` is added in `HttpInferAdapter:173`).

## Development

```bash
uv run pytest -q                           # unit (live skipped by default)
uv run --with ruff ruff check src tests tools
uv run --with mypy mypy src/locallens/
```

Live tests against a real server:

```bash
LOCALLENS_LIVE=1 LOCALLENS_URL=http://127.0.0.1:8099 uv run --with pytest pytest tests/test_integrazione_ocr.py -q
TESSERACT_LIVE=1 uv run --with pytest pytest tests/test_fallback.py -q
# OpenRouter live (uses token from env, never saved):
LOCALLENS_LIVE=1 LOCALLENS_URL=https://openrouter.ai/api/v1/chat/completions OPENROUTER_API_KEY=sk-or-... uv run --with pytest pytest tests/test_integrazione_ocr.py -q
```

## Packaging

```bash
python tools/fetch-binaries.py --os linux --all  # llama-server builds into bins/
# or: python tools/fetch-binaries.py --os win32 --all  # on/for Windows
uv run --with pyinstaller pyinstaller -y locallens.spec
./dist/locallens/locallens              # Linux
./dist/locallens/locallens.exe          # Windows
```

## Docs

- Glossary (ubiquitous language): [`CONTEXT.md`](CONTEXT.md)
- Architecture (as-built): [`docs/architecture.md`](docs/architecture.md)
- Decisions: [`docs/adr/`](docs/adr/)
- Requirements: [`requisiti-progetto-ocr-locale.md`](requisiti-progetto-ocr-locale.md) (full spec)
- Windows VM checklist: [`docs/windows-vm-checklist.md`](docs/windows-vm-checklist.md)

## Out of scope

macOS/Metal, app stores, token persistence (deliberately session-only). Windows smoke on physical RTX 4050 is documented but not gated on every CI run.
