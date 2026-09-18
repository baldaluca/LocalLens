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
│   ├── presets.py      → PresetModello + load_preset + seleziona_preset (solo server locali)
│   ├── pesi.py         → riuso cache HF-Hub, download solo su richiesta esplicita
│   ├── settings.py     → TOML utente (XDG/APPDATA); SEGRET mai su disco (token);
│   │                     `lingua` validata su it/en; URL distinti url_esterno/url_gpu_locale
│   └── percorsi.py     → _MEIPASS nel bundle, CWD in sviluppo
├── preprocessing/
│   ├── pdf.py          → pypdfium2, 300 DPI, una PNG per pagina
│   └── immagini.py     → prepara(): resize Lanczos anti-OOM + contrasto opzionale (RF2)
├── fallback/tesseract.py → estrai() via pytesseract (lang ita+eng, PSM 6), runner iniettabile
├── core/
│   ├── errori.py       → InferenzaError condiviso (con corpo server troncato a 500)
│   ├── client.py       → build_chat_payload / build_ollama_payload (dialetto auto da URL) /
│   │                     parse_chat_text / invia_chat (URL verbatim; suffisso solo locali)
│   ├── pipeline.py     → elabora_pagine: contesto filtro (lingue/soglia/eco), anomalia
│   │                     fail-fast al 1° tentativo, scartato troncato a 2000, quality-gate <20 char
│   ├── orchestrator.py → OcrEngine sync + crea_engine / crea_engine_cloud (token Bearer)
│   ├── fabbrica.py     → disponibilita_gpu_locale (binario+pesi, no download),
│   │                     normalizza_sorgente (bundlato→esterno con banner), costruisci()
│   └── diario.py       → JSONL per esecuzione, extra{scartato} per output scartati
└── app/                → GUI PySide6, parla solo con core
    ├── finestra.py     → applica_lingua() a caldo, pill motore, banner, copia/salva,
    │                     Apri/Incolla/Screenshot, ricostruttore; closeEvent pulisce il token
    ├── worker.py       → QRunnable + segnali pagina/finito/errore (RNF4)
    ├── ingresso.py     → RF1: file, PDF, appunti, screenshot (mss, grabber iniettabile)
    ├── impostazioni.py → sorgente (GPU locale/esterno/nessuno), URL con memoria per
    │                     opzione + avviso privacy, cloud (token/modello/prompt),
    │                     contesto filtro, LinguaInterfaccia; '?' espandibile per riga
    ├── lingua.py       → STRINGS it/en + t(lingua, chiave); parità chiavi via test
    ├── tema.py         → qss chiaro/scuro + applica_tavolozza
    └── icone.py        → icone + frecce combo/spin per tema
presets/                 → glm-ocr-q8_0.toml (default) + placeholder-alta.toml (disabilitato, §12)
tools/fetch-binaries.py  → download asset pinnati in bins/<os>/<backend>/ (appiattiti)
locallens.spec           → PyInstaller onedir: app + presets + bins/<os>
```

Vietato: `app → backend`, `app → hwdetect`, template/prompt hardcoded in `core`.

## 2. Contratti

- **BackendGpu** `cuda | hip | vulkan | cpu`: ordine da `decide()`, CPU sempre ultima.
- **SorgenteModello** `bundlato | esterno | nessuno` (label UI: GPU locale/esterno/nessuno):
  `bundlato` = server all'URL GPU locale se `verifica_health` risponde, senza avviare
  binari (rilevamento binario+pesi solo per mostrare/nascondere la voce e per il
  ripiego automatico su esterno); `esterno` = server locale o cloud tutto a mano
  (URL verbatim, modello+prompt, token Bearer solo in sessione, dialetto Ollama
  auto su URL `/api/chat`); `nessuno` = fallback diretto; URL non-locale = banner (RNF1).
- **PresetModello**: GGUF + mmproj + chat-template documentati + vincoli; mai hardcoded;
  usato solo per i server locali, non per il cloud.
- **Documento / Pagina / Estrazione**: `Estrazione{..., motore_usato, ms, nota}`; `nota`
  spiega il fallback (base di badge e banner, RF7).

## 3. Flussi verificati

**Boot.** `carica()` (token mai dal disco, lingua validata) → `detect()` →
preset → `normalizza_sorgente` (GPU locale non rilevata → esterno con banner) →
`costruisci()` → `MainWindow` con `applica_lingua()` dal config.

**Inferenza.** Ingresso → `prepara()` (lato max da preset, default 2048) → chat con
immagine base64 → `Estrazione`; anomalia fail-fast al 1° tentativo, 1 retry solo
per errori/output vuoto, poi Tesseract; mai crash del batch. Sincrona in `core`,
threadata in GUI (`OcrWorker`). Output scartati nel diario (`extra.scartato`,
max 2000 char); Estrazioni <20 char marcate "fallback debole".

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
Volontariamente fuori: persistenza del Token API (solo sessione, per sicurezza).
