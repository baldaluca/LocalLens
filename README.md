# LocalLens — OCR desktop interamente locale

Estrazione testo da immagini e PDF con inferenza GPU (NVIDIA/AMD/Intel via
`llama.cpp`: CUDA, HIP/ROCm, Vulkan) e fallback CPU (Tesseract). Nessun cloud.

## Requisiti

- Python ≥ 3.11, [uv](https://docs.astral.sh/uv/)
- Linux o Windows 10/11 (macOS rimandato a v2)
- GPU opzionale; senza GPU si usa solo Tesseract
- Tesseract di sistema per il fallback (`apt install tesseract-ocr tesseract-ocr-ita`)
- Pesi `ggml-org/GLM-OCR-GGUF` (scaricati al primo uso o riusati da `~/.cache/huggingface`)

## Avvio rapido (Linux)

```bash
uv sync
PYTHONPATH=src QT_QPA_PLATFORM=offscreen uv run --no-sync python -m locallens  # smoke headless
uv run --no-sync python -m locallens                                           # GUI
```

## Test

```bash
uv run --with pytest pytest -q                 # unit (live skippati di default)
uv run --with ruff ruff check src tests tools
uv run --with mypy mypy src/locallens/
```

Live (macchina di riferimento, server GLM-OCR su 8099):

```bash
LOCALLENS_LIVE=1 LOCALLENS_URL=http://127.0.0.1:8099 uv run --with pytest pytest tests/test_integrazione_ocr.py -q
TESSERACT_LIVE=1 uv run --with pytest pytest tests/test_fallback.py -q
```

## Binari llama-server (distribuzione)

```bash
python tools/fetch-binaries.py --list            # asset pinnati (llama.cpp b10995)
python tools/fetch-binaries.py --os linux --all  # scarica in bins/
```

Pinnatura aggiornata solo dopo test su entrambe le macchine di riferimento.

## Pacchetto

```bash
uv run --with pyinstaller pyinstaller locallens.spec
```

Un pacchetto per OS include tutti i binari `bins/<os>/*`; selezione a runtime.

## Layout

`src/locallens/{hwdetect,backend,config,core,preprocessing,fallback,app}` —
dettagli in `docs/architecture.md`, glossario in `CONTEXT.md`, decisioni in `docs/adr/`.
