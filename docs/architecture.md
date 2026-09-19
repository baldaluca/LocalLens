# LocalLens Architecture (v1, as-built)

Target: Linux + Windows. macOS deferred to v2. Canonical terms in `CONTEXT.md`.

## 1. Layout

```
src/locallens/
├── __main__.py         → boot: load() settings → detect() → preset → factory → MainWindow
├── hwdetect/detector.py→ decide() pure + detect() (nvidia-smi, lspci, binary scan). No Qt.
├── backend/
│   ├── manager.py      → BackendManager (subprocess, ports 8011-8020, /health),
│   │                     resolve_binary, find_free_port, is_url_private (RNF1)
│   ├── cli.py          → preset_to_argv: only flags verified on build 0.4.0-dev
│   └── distro.py       → pinned tag b10995 + asset names verified via GitHub API
├── config/
│   ├── presets.py      → PresetModello + load_preset + select_preset (local servers only)
│   ├── weights.py      → HF-Hub cache reuse, download only on explicit request
│   ├── settings.py     → Config (frozen dataclass, LinguaService-aware validation);
│   │                     TOML in XDG/APPDATA; SEGRET never on disk (token);
│   │                     lingua validated on it/en; distinct URLs url_esterno/url_gpu_locale
│   └── paths.py        → _MEIPASS in bundle, CWD in development
├── preprocessing/
│   ├── pdf.py          → pypdfium2, 300 DPI, one PNG per page
│   └── images.py       → prepare(): Lanczos resize anti-OOM + optional contrast (RF2)
├── fallback/tesseract.py → extract() via pytesseract (lang ita+eng, PSM 6), injectable runner
├── core/
│   ├── errors.py       → InferenceError shared (server body truncated to 500)
│   ├── client.py       → HttpInferAdapter + build_chat_payload / build_ollama_payload
│   │                     (dialect auto from URL) / parse_chat_text / send_chat
│   │                     (verbatim URL; suffix only for local servers)
│   ├── pipeline.py     → OcrPipeline: filter context (languages/threshold/echo), anomaly
│   │                     fail-fast on 1st attempt, discarded truncated to 2000, quality-gate <20 char
│   ├── orchestrator.py → OcrEngine sync + thin re-export (create_engine / create_engine_cloud)
│   ├── factory.py      → EngineFactory.rebuild(Config) → (OcrEngine, status, banner);
│   │                     local GPU availability (binary+weights, no download),
│   │                     normalize_source (bundlato→esterno with banner), build()
│   └── diary.py        → JSONL per run, extra{discarded} for discarded outputs
└── app/                → GUI PySide6, talks only to core/config
    ├── controller.py   → DocumentController (Presenter, owns Document/Page/Extraction flow)
    ├── window.py       → MainWindow View (thin: signals openRequested/settingsAccepted,
    │                     apply_lingua() hot, engine pill, banner, copy/save, filtered text)
    ├── worker.py       → QRunnable + page/finished/error signals (RNF4)
    ├── input.py        → RF1: file, PDF, clipboard, screenshot (mss, injectable grabber)
    ├── settings.py     → source (Local GPU/external/none), URL with per-option memory +
    │                     privacy warning, cloud (token/model/prompt),
    │                     filter context, InterfaceLanguage; '?' expandable per row
    ├── lingua.py       → LinguaService (STRINGS it/en + t(key)), key parity via test
    ├── theme.py        → qss light/dark + apply_palette
    └── icons.py        → icons + combo/spin arrows per theme
presets/                 → glm-ocr-q8_0.toml (default) + placeholder-high.toml (disabled, §12)
tools/fetch-binaries.py  → download pinned assets into bins/<os>/<backend>/ (flattened)
locallens.spec           → PyInstaller onedir: app + presets + bins/<os>
```

Forbidden: `app → backend`, `app → hwdetect`, `app → __main__`; `core → __main__`. Hardcoded prompt/template in `core` forbidden.

## 2. Contracts

- **BackendGpu** `cuda | hip | vulkan | cpu`: order from `decide()`, CPU always last.
- **ModelSource** `bundlato | esterno | nessuno` (UI labels: Local GPU / External / None):
  `bundlato` = server at Local GPU URL if `verify_health` responds, without spawning
  binaries (binary+weight detection only controls visibility and automatic fallback
  to external); `esterno` = manual local or cloud server
  (verbatim URL, model+prompt, Bearer token session-only, Ollama dialect
  auto on `/api/chat` URL); `nessuno` = direct fallback; non-local URL = banner (RNF1).
- **ModelPreset**: GGUF + mmproj + documented chat-template + constraints; never hardcoded;
  used only for local servers, not for cloud.
- **Document / Page / Extraction**: `Extraction{..., engine_used, ms, note}`; `note`
  explains fallback (basis for badge and banner, RF7).

## 3. Verified flows

**Boot.** `load()` (token never from disk, language validated) → `detect()` →
preset → `normalize_source` (Local GPU not detected → external with banner) →
`build()` → `MainWindow` with `apply_lingua()` from config.

**Inference.** Input → `prepare()` (max side from preset, default 2048) → chat with
base64 image → `Extraction`; anomaly fail-fast on 1st attempt, 1 retry only
for errors/empty output, then Tesseract; batch never crashes. Synchronous in `core`,
threaded in GUI (`OcrWorker` via `DocumentController`). Discarded outputs in diary (`extra.discarded`,
max 2000 chars); Extractions <20 chars flagged as "weak fallback".

**Validated 2026-09-16 (GTX 960M):** server b10995+cuda-12.8 → `/health` 200,
1866 MiB VRAM on dedicated GPU; gold image 4/4 exact lines in ~7 s, also via pinned binary.
Details and live commands in `*_LIVE` tests.

## 4. Build and test

- `uv sync`; `pytest -q` (live skipped without `LOCALLENS_LIVE`/`TESSERACT_LIVE`);
  `ruff check`, `mypy` clean (policy: zero errors).
- `tools/fetch-binaries.py --os linux --all` then `pyinstaller locallens.spec`;
  `dist/locallens/locallens` tested with offscreen boot.
- Pinning updated only after tests on both reference machines (§10 in requirements).

## 5. Out of scope for v1 (honest)

Deskew/crop (RF2 partial: only resize+contrast), Windows RTX 4050 smoke test,
medium/high VRAM preset (§12), app stores, macOS/Metal.
Deliberately out: API Token persistence (session-only for security).
