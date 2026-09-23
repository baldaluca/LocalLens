# LocalLens

Desktop OCR extraction with local GPU inference when available, optional external/cloud server, and CPU fallback.

## Language

### Inference

**BackendGpu**:
Flavor of the llama-server binary selected at runtime based on platform and GPU.
_Avoid_: generic backend

**SorgenteModello (ModelSource)**:
Where the inference client points: `bundlato` (bundled/local GPU server), `esterno` (external server/cloud — self-hosted or OpenAI-compatible cloud such as OpenRouter `https://openrouter.ai/api/v1/chat/completions` with model `inclusionai/ling-3.0-flash-vl:free`), or `nessuno` (no local model — CPU fallback only).
_Avoid_: backend, engine

**PresetModello (ModelPreset)**:
Per-model configuration: GGUF repo, mmproj, chat template, minimum VRAM and resize limits.
_Avoid_: generic model

### Document

**Documento (Document)**:
User-provided input file: a single image or a PDF.
_Avoid_: file, input

**Pagina (Page)**:
Atomic unit of inference: one image or a single rendered PDF page.
_Avoid_: image, sheet

**Estrazione (Extraction)**:
Text result of inference on a single Pagina, with the engine used and timing; `nota` explains fallback.
_Avoid_: OCR, output, result

### Application

**LinguaInterfaccia (InterfaceLanguage)**:
Language of the UI strings, Italian or English, hot-switchable from Settings. Validated `it | en`.
_Avoid_: locale, filter languages
