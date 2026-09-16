# Architettura LocalLens (v1, as-built)

Target: Linux + Windows. macOS rimandato a v2. Termini canonici in `CONTEXT.md`.

## 1. Layout

```
src/locallens/
├── __main__.py         → boot: carica() settings → detect() → preset → fabbrica → MainWindow
├── hwdetect/detector.py→ decide() pura + detect() (nvidia-smi, lspci, scan binari). No Qt.
├── backend/
│   ├── manager.py      → BackendManager (subprocess, porte 8011-8020, /health),
│   │                     resolve_binary, trova_porta_libera, is_url_privata (RNF1)
│   ├── cli.py          → preset_to_argv: solo flag verificati su build 0.4.0-dev
│   └── distro.py       → tag pinnato b10995 + nomi asset verificati via GitHub API
├── config/
│   ├── presets.py      → PresetModello + load_preset + seleziona_preset
│   ├── pesi.py         → riuso cache HF-Hub, download solo su richiesta esplicita
│   ├── settings.py     → TOML utente (XDG/APPDATA), DEFAULTS senza parti non implementate
│   └── percorsi.py     → _MEIPASS nel bundle, CWD in sviluppo
├── preprocessing/
│   ├── pdf.py          → pypdfium2, 300 DPI, una PNG per pagina
│   └── immagini.py     → prepara(): resize Lanczos anti-OOM + contrasto opzionale (RF2)
├── fallback/tesseract.py → estrai() via pytesseract (lang ita+eng), runner iniettabile
├── core/
│   ├── errori.py       → InferenzaError condiviso
│   ├── client.py       → build_chat_payload / parse_chat_text / invia_chat (/v1/chat/completions)
│   ├── pipeline.py     → elabora_pagine sequenziale: 2 tentativi → fallback, on_page, mai stop batch
│   ├── orchestrator.py → OcrEngine sync + crea_engine (prepara dentro infer, errori → fallback)
│   └── fabbrica.py     → costruisci(): SorgenteModello dietro stessa interfaccia (RF10)
└── app/                → GUI PySide6, parla solo con core
    ├── finestra.py     → badge motore, banner, copia/salva, Apri/Incolla/Screenshot, ricostruttore
    ├── worker.py       → QRunnable + segnali pagina/finito/errore (RNF4)
    ├── ingresso.py     → RF1: file, PDF, appunti, screenshot (mss, grabber iniettabile)
    └── impostazioni.py → RF10/RNF1: sorgente, URL con avviso, preset (persistenti via settings)
presets/                 → glm-ocr-q8_0.toml (default) + placeholder-alta.toml (disabilitato, §12)
tools/fetch-binaries.py  → download asset pinnati in bins/<os>/<backend>/ (appiattiti)
locallens.spec           → PyInstaller onedir: app + presets + bins/<os>
```

Vietato: `app → backend`, `app → hwdetect`, template/prompt hardcoded in `core`.

## 2. Contratti

- **BackendGpu** `cuda | hip | vulkan | cpu`: ordine da `decide()`, CPU sempre ultima.
- **SorgenteModello** `bundlato | esterno | nessuno`: `fabbrica.costruisci()` cambia solo
  dove punta il client; `nessuno` = fallback diretto; `esterno` non-locale = banner (RNF1).
- **PresetModello**: GGUF + mmproj + chat-template documentati + vincoli; mai hardcoded.
- **Documento / Pagina / Estrazione**: `Estrazione{..., motore_usato, ms, nota}`; `nota`
  spiega il fallback (base di badge e banner, RF7).

## 3. Flussi verificati

**Boot.** `carica()` → `detect()` (su GTX 960M: nvidia/4096/optimus) → preset →
`risolvi_pesi` (solo cache; niente download silenziosi) → `BackendManager.start`
oppure `_solo_cpu` con banner. Bundle: stessi path via `_MEIPASS`.

**Inferenza.** Ingresso → `prepara()` (lato max da preset, default 2048) → chat con
immagine base64 → `Estrazione`; 1 retry, poi Tesseract; immagini corrotte → fallback,
mai crash del batch. Sincrona in `core`, threadata in GUI (`OcrWorker`).

**Validato il 2026-09-16 (GTX 960M):** server b10995+cuda-12.8 → `/health` 200,
1866 MiB VRAM su dedicata; immagine gold 4/4 righe esatte in ~7 s, anche via binario
pinnato. Dettagli e comandi live nei test `*_LIVE`.

## 4. Build e test

- `uv sync`; `pytest -q` (live skippati senza `LOCALLENS_LIVE`/`TESSERACT_LIVE`);
  `ruff check`, `mypy` puliti (policy: zero errori).
- `tools/fetch-binaries.py --os linux --all` poi `pyinstaller locallens.spec`;
  `dist/locallens/locallens` testato in boot offscreen.
- Pinning aggiornato solo dopo test su entrambe le macchine (§10 requisiti).

## 5. Fuori v1 (onesto)

Deskew/crop (RF2 parziale: solo resize+contrasto), smoke Windows RTX 4050,
preset fascia media/alta (§12), store applicativi, macOS/Metal.
