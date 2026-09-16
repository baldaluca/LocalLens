# Architettura LocalLens (v1)

Target: Linux + Windows. macOS rimandato a v2. Termini canonici in `CONTEXT.md`.

## 1. Layout

```
src/locallens/
├── hwdetect/       → rilevamento GPU/backend/VRAM. Nessuna dipendenza Qt. Testabile.
├── backend/        → BackendManager: sceglie il binario, avvia/supervisiona llama-server.
├── config/         → paths, settings.toml utente, loader presets/*.toml, validazione.
├── preprocessing/  → rendering PDF (pypdfium2) + resize/normalizzazione (OpenCV, CPU).
├── fallback/       → Tesseract via pytesseract. Nessun vincolo GPU.
├── core/           → OcrEngine: pipeline Documento→Pagine→Estrazioni via HTTP OpenAI-compatibile.
└── app/            → GUI PySide6. Parla solo con core. Mai con backend/URL direttamente.
presets/             → un TOML per PresetModello, shipped con l'app.
tools/fetch-binaries.py → scarica i binari llama-server pinnati per OS/backend in bins/.
bins/<os>/<backend>/llama-server[.exe] → incluso nel pacchetto PyInstaller onedir.
```

Dipendenze consentite: `app → core → {hwdetect, backend, preprocessing, fallback, config}`.
Vietato: `app → backend`, `app → hwdetect`, `core → <modello specifico>`.

## 2. Concetti e contratti

- **BackendGpu**: `cuda | hip | vulkan | cpu`. Scelto a runtime da `hwdetect.detect()` + verifica
  che il binario esista in `bins/`. Ordine: vendor-specifico → vulkan → cpu.
- **SorgenteModello**: `bundlato | esterno | nessuno`. Cambia solo il `base_url` del client HTTP
  in `core`; stesso protocollo `/v1/chat/completions`, stessa pipeline. (RF10)
- **PresetModello** (TOML, vedi `presets/glm-ocr-q8_0.toml`): repo/file GGUF, mmproj,
  `chat_template`, `vram_min_mb`, `ctx`, `max_side_px`, args server (`n_gpu_layers`, …).
  `core` non hardcodizza mai template/prompt: li legge dal preset.
- **Documento / Pagina / Estrazione**: `Documento` = file input; `Pagina` = unità di inferenza;
  `Estrazione` = `{pagina_id, testo, motore_usato, ms}` dove `motore_usato` ∈
  `{cuda, hip, vulkan, cpu-llama, cpu-tesseract, esterno}`. (RF7)

Interfaccia minima `core` (usata dalla GUI via QThreadPool, mai bloccante):

```python
job_id = engine.submit_document(path | qimage, settings)  # → OcrJob
engine.cancel(job_id)
result = engine.get_result(job_id)  # {pagine: [Estrazione], stato}
# segnali Qt: progress(job_id, i, n), page_done(Estrazione), finished, failed(msg)
```

## 3. Flussi

**Avvio.** `hwdetect.detect()` (nvidia-smi / hipinfo / vulkaninfo + probe binario) →
VRAM runtime → selezione `PresetModello` (default fascia bassa `glm-ocr-q8_0`) →
se `sorgente=bundlato`: `BackendManager.start(binario, preset, porta)` con default `8011`
+ scan 8011→8020 se occupata → `GET /health` → UI pronta con status
`BackendGpu • VRAM • preset`. Se fallisce: banner + degradazione a CPU, mai crash. (RNF4)
Su Optimus/PRIME: verifica esplicita che il server usi la dedicata
(`nvidia-smi` / log server), senza toccare `prime-select` globale.

**Inferenza (sequenziale per Pagina, RF8).** Split (`pypdfium2` a 300 DPI per PDF,
immagine diretta altrimenti) → `preprocessing` (default: tutto OFF, solo
downscale Lanczos a lato max 2048, limite da preset; deskew/crop/contrasto su richiesta, RF2)
→ `POST /v1/chat/completions` con immagine base64 + prompt dal preset →
parsing testo → `Estrazione`. Su eccezione/OOM/output anomalo: **1 retry**,
poi fallback Tesseract automatico sulla Pagina + badge giallo con motivazione.
Batch non interrotto, nessun modale. (RF4)

**Sorgente esterna (RF10b).** L'utente inserisce URL; stesso client, nessuno start locale.
Se host ∉ {localhost, 127.*, 10/8, 172.16/12, 192.168/16, [::1]} → avviso privacy
esplicito (RNF1). `nessuno` = skip diretto al fallback.

## 4. GUI (PySide6)

MainWindow: dropzone (file/drag&drop/clipboard/mss-screenshot, RF1) → lista Pagine con
anteprima + badge `motore_usato` → pannello testo con copia/salva .txt/.md (RF5) →
status bar (BackendGpu, preset, porta) + banner fallback. Dialog impostazioni:
SorgenteModello, URL esterno, preset override (RF6), DPI/lato-max.
Nessun rilevamento hardware in GUI.

## 5. Build, config, dati

- Python ≥3.11, `uv` + lockfile; GUI PySide6; `mss` per screenshot; `pypdfium2`,
  `opencv-python`, `pytesseract` (+ binario Tesseract bundlato o di sistema).
- `tools/fetch-binaries.py --os <linux|win> --llama <ver>` scarica release pinnate
  (CUDA, HIP solo Linux, Vulkan, CPU) in `bins/`. PyInstaller onedir le include.
  Aggiornamento backend solo dopo test (pinning, §10 requisiti).
- Config utente TOML: `~/.config/locallens/config.toml` (Linux),
  `%APPDATA%/LocalLens/config.toml` (Win). Pesi GGUF in cache HF-Hub condivisa.
- RNF5: nessun tempo promesso; misurato per-preset e mostrato (ms/pagina in `Estrazione`).

## 6. Test (v1)

Unit: hwdetect con probe mockati; loader preset; pipeline core con fake HTTP server;
fallback mock. Integrazione: immagine gold → `glm-ocr-q8_0` via server reale su
Linux+CUDA (macchina riferimento); smoke Win+CUDA RTX4050; smoke CPU-only
(Tesseract senza GPU). Nessuna rete esterna durante i test (RNF1).

## 7. Tracciabilità requisiti

RF1 app/dropzone · RF2 preprocessing · RF3 hwdetect+BackendManager · RF4 fallback auto ·
RF5 copia/salva · RF6 preset per VRAM + override · RF7 badge motore · RF8 pipeline
sequenziale · RF9 CPU-only funzionante · RF10 SorgenteModello a 3 vie.
RNF1 avviso URL non-locale · RNF2 Linux/Win · RNF3 disaccoppiamento HTTP ·
RNF4 degradazione gestita · RNF5 tempi misurati, non promessi.
Punto aperto §12: fascia media/alta = preset placeholder disabilitato, solo TOML futuro.
