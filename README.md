# LocalLens

![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![Platform](https://img.shields.io/badge/platform-linux%20%7C%20windows-lightgrey)
![GUI](https://img.shields.io/badge/gui-PySide6-green)
![Tests](https://img.shields.io/badge/tests-255%20passed-brightgreen)

Desktop OCR app: extract text from images and PDFs using local GPU inference when available, an optional external/cloud server, and CPU fallback.

## Features

- 📄 OCR from **images and PDFs** (file, clipboard, screenshot) — see `Documento` / `Pagina` in `CONTEXT.md`
- 🖥️ **Local GPU** (`bundlato`) — models you run yourself (llama.cpp, Ollama, LM Studio) at a dedicated local URL
- ☁️ **External** (`esterno`) — models at an external URL requiring an API token; token lives **only in memory**, never written to disk, cleared on close
- 🔤 **CPU fallback** via Tesseract (PSM 6), with fail-fast on degenerate model output
- 🌍 UI in **Italian or English**, hot-switchable from Settings (`LinguaInterfaccia`, default `en`)
- 🌓 Light / dark themes, per-page engine badge, single-page filtering, Markdown output (copy / Save .md), JSONL run diary

## Quickstart (Linux)

```bash
uv sync
uv run python -m locallens        # GUI (or: uv run locallens)
```

Smoke test without a display:

```bash
QT_QPA_PLATFORM=offscreen timeout 12 uv run python -m locallens
```

Requirements: Python ≥ 3.11, [uv](https://docs.astral.sh/uv/), Tesseract (`apt install tesseract-ocr tesseract-ocr-ita`).

> **Local GPU needs a server you start yourself.** If no server answers at the configured URL you get CPU fallback with a banner telling you to start `llama-server` there and retry.

## Model sources

| Source | What it does |
|---|---|
| **Local GPU** (`bundlato`) | Server at the Local GPU URL. Entry shown only if binaries + weights are detected, otherwise it automatically falls back to External with a banner. |
| **External** (`esterno`) | Server at an external URL with URL (verbatim) + model + prompt + token (session-only, never saved). Privacy warning on non-local URLs. |
| **None** (`nessuno`) | Tesseract only. |

Presets (`presets/*.toml`) apply to local servers; external/cloud uses your manual model + prompt. See `PresetModello` in `CONTEXT.md`.

## Configuration

Settings persist to the user config (`XDG`/`APPDATA`) except the API token, which is never written to disk. The typed `Config` module (`src/locallens/config/settings.py:64`) owns `lingua | sorgente | url_esterno | url_gpu_locale | preset_id | max_side_px | contrasto | lingue_filtro | soglia_righe_loop | ignora_eco | tema`. The anti-self-hit filter (languages, loop threshold, prompt-echo ignore) is tunable from Settings. See `config.example.toml`.

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

`BackendGpu` (`cuda | hip | vulkan | cpu`) is chosen at runtime via `hwdetect/detector.py`. `app` talks only to `core`/`config`; never directly to `backend` or a remote URL.

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
```

## Packaging

```bash
python tools/fetch-binaries.py --os linux --all  # llama-server builds into bins/
uv run --with pyinstaller pyinstaller -y locallens.spec
./dist/locallens/locallens
```

## Docs

- Glossary (ubiquitous language): [`CONTEXT.md`](CONTEXT.md)
- Architecture (as-built): [`docs/architecture.md`](docs/architecture.md)
- Decisions: [`docs/adr/`](docs/adr/)
- Requirements: [`requisiti-progetto-ocr-locale.md`](requisiti-progetto-ocr-locale.md) (full spec, now in English)

## Out of scope

Windows smoke test on reference hardware, macOS/Metal, app stores, token persistence (deliberately session-only).
