# LocalLens

![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![Platform](https://img.shields.io/badge/platform-linux%20%7C%20windows-lightgrey)
![GUI](https://img.shields.io/badge/gui-PySide6-green)
![Tests](https://img.shields.io/badge/tests-233%20passed-brightgreen)

Desktop OCR app: extract text from images and PDFs using models you run locally, external token-based models, or plain CPU.

## Features

- 📄 OCR from **images and PDFs** (file, clipboard, screenshot)
- 🖥️ **GPU locale** — models you run yourself (llama.cpp, Ollama, LM Studio…), used at their own URL
- ☁️ **External** — models at an external URL requiring an API token; token lives **only in memory**, never saved, cleared on close
- 🔤 **CPU fallback** via Tesseract (PSM 6), with fail-fast on degenerate model output
- 🌍 UI in **Italian or English**, switchable live from Settings
- 🌓 Light / dark themes, per-page engine badge, JSONL run diary

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

> **GPU locale needs a server you start yourself.** If none answers at the
> configured URL you get CPU fallback with a banner telling you to start
> `llama-server` there and retry.

## Model sources

| Source | What it does |
|---|---|
| **GPU locale** | Models you run locally — via llama.cpp, Ollama, LM Studio, etc. Uses the server at its own URL (kept separate from the external one). Shown only if binaries + weights are detected, otherwise it falls back to external with a banner. |
| **External** | Models at an external URL that require an API token: URL (verbatim) + model + prompt + token (session-only, never saved). Privacy warning on non-local URLs. |
| **None** | Tesseract only. |

Presets (`presets/*.toml`) apply to local servers; cloud uses your manual model + prompt.

## Configuration

Settings persist to the user config (`XDG`/`APPDATA`) except the API token, which is never written to disk. Anti-self-hit filter (languages, loop threshold, prompt-echo ignore) is tunable from Settings.

## Development

```bash
uv run --with pytest pytest tests/ -q       # unit (live skipped by default)
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

- Glossary: [`CONTEXT.md`](CONTEXT.md)
- Architecture: [`docs/architecture.md`](docs/architecture.md)
- Decisions: [`docs/adr/`](docs/adr/)
- Requirements: [`requisiti-progetto-ocr-locale.md`](requisiti-progetto-ocr-locale.md)

## Out of scope

Windows smoke test on reference hardware, macOS/Metal, app stores, token persistence (deliberately session-only).
