# Project Requirements — LocalLens
## Cross-platform desktop OCR app with GPU-accelerated local inference

**Project name:** LocalLens
**Version:** 2.2
**Date:** 2026-09-23 (rev: external/cloud via OpenRouter free vision models, session-only token, IT/EN interface)
**Target platforms:** Linux and Windows (v1 priority); macOS out of scope for v1

---

## 1. Project goal

Build a **cross-platform** desktop application, with **Linux and Windows as v1 priorities** (macOS deferred), that performs OCR (text extraction from images/documents) primarily locally, leveraging GPU acceleration when available — **regardless of vendor** (NVIDIA, AMD, Intel, Apple Silicon) — with automatic CPU fallback when not available. Since v2.1 an explicit external/cloud server is allowed (URL + model + prompt manually entered, token session-only never saved), with a privacy warning on non-local URLs. Since v2.2 this includes OpenRouter and other OpenAI-compatible cloud endpoints; recommended free vision models for OCR are documented in `README.md` (e.g. `inclusionai/ling-3.0-flash-vl:free`).

---

## 2. Reference hardware / environments

### 2.1 Linux reference machine (development)

Used as an **empirical reference** to size VRAM constraints and validate the low-memory / dated-GPU edge case — not the only target.

| Component | Spec |
|---|---|
| CPU | Intel Core i7-6700HQ |
| RAM | 16 GiB |
| Storage | SSD 1 TB |
| Dedicated GPU | NVIDIA GeForce GTX 960M, 4 GB VRAM (Maxwell, compute capability 5.2) |
| Integrated GPU | Intel HD Graphics 530 (Optimus) |
| NVIDIA driver | 580.178.04 (CUDA 13.0) |
| OS | Ubuntu 26.04.1 LTS |
| LLM stack present | `llama-server` with Qwen3.5-4B-GGUF (Q4_K_M), validated on this GPU |

Note: with Qwen2.5-Coder-7B-Instruct (Q4_K_M) at `--n-gpu-layers 24` an **out-of-memory** was already observed. This is the empirical reference for the "low VRAM" tier (see §9).

### 2.2 Windows reference machine (test)

| Component | Spec |
|---|---|
| Device | Acer Nitro ANV15-51 |
| CPU | 13th Gen Intel Core i5-13420H, 2.10 GHz |
| RAM | 16 GB (15.7 GB usable) |
| Dedicated GPU | NVIDIA GeForce RTX 4050 Laptop GPU, 6 GB VRAM (Ada Lovelace, cc 8.9) |
| Integrated GPU | Intel UHD Graphics (128 MB) |
| Storage | 477 GB (282 GB used) |
| OS | Windows |

Note: with 6 GB VRAM and a much newer architecture than the GTX 960M, this machine sits at the upper bound of the "low VRAM" tier (§9, ~2–6 GB). No CUDA compatibility issue expected: Ada Lovelace is fully supported by current builds.

---

## 3. Scope

### In scope (v1)
- Text extraction from images and PDFs, with GPU acceleration when available
- Native desktop UI for **Linux and Windows** (v1 priorities)
- Automatic detection of the available GPU backend (CUDA/HIP/Metal/Vulkan) with CPU fallback (Tesseract) when no GPU backend is usable
- Model presets selectable by VRAM detected at runtime
- Model source configuration: Local GPU (server at configured URL, entry shown only if binaries and weights detected, otherwise fallback to external), external/cloud server with manual URL + model + prompt (Ollama `/api/chat` dialect auto-detected from URL, OpenAI-compatible cloud such as `https://openrouter.ai/api/v1/chat/completions` with free vision models like `inclusionai/ling-3.0-flash-vl:free`, API token session-only never saved), or no local model (Tesseract-only)
- Save/copy extracted text
- Interface in Italian or English, hot-switchable from Settings

### Out of scope (v1)
- Training or fine-tuning models
- Accelerators not covered by CUDA/HIP/Metal/Vulkan (dedicated NPUs, TPUs, etc.) — possible in v2
- Mobile or public web version
- Advanced PDF output editing (searchable OCR layer) — possible in v2
- Distribution via app stores (Microsoft Store, Mac App Store) — manually installable packages are enough for v1
- macOS support (Metal backend) — deferred to v2, not a v1 priority

---

## 4. Functional requirements (RF)

| ID | Requirement |
|---|---|
| RF1 | The user must be able to provide an image or PDF via: file from disk, drag&drop, clipboard paste, integrated screenshot |
| RF2 | The system must be able to apply optional preprocessing (deskew, crop, contrast boost) before inference — v1: anti-OOM resize + contrast (deskew/crop in v1.1, see ADR-0006) |
| RF3 | The system must automatically detect the GPU backend available on the current platform (CUDA on NVIDIA, HIP/ROCm on AMD, Metal on Apple Silicon, Vulkan as cross-vendor fallback) and use it via `llama.cpp`/`mtmd` |
| RF4 | If no GPU backend is available/supported or GPU inference fails, the system must fall back to a CPU-only OCR engine (Tesseract) without blocking the user |
| RF5 | Extracted text must be copyable to clipboard and savable to file (.txt/.md minimum) |
| RF6 | The system must select (or propose) a GGUF model preset suitable for the detected VRAM, among predefined tiers (see §9), and allow manual override |
| RF7 | The UI must clearly indicate which engine/backend (CUDA, HIP, Metal, Vulkan or CPU) processed each document |
| RF8 | The system must explicitly handle multi-page documents (sequential page-by-page processing) |
| RF9 | The app must remain fully usable (via CPU fallback) even on machines without a dedicated GPU or with a GPU not covered by any supported backend |
| RF10 | The user must be able to choose the OCR model source among three modes: (a) bundled backend managed by the app (RF3/RF6), (b) URL of an already-running external `llama.cpp` server or any OpenAI-compatible endpoint (e.g. `https://openrouter.ai/api/v1/chat/completions` with model `inclusionai/ling-3.0-flash-vl:free` — see `README.md` for recommended free VLMs) entered manually, (c) no local model — Tesseract-only, as an explicit choice not just automatic degradation |

---

## 5. Non-functional requirements (RNF)

| ID | Requirement |
|---|---|
| RNF1 | **Privacy**: no data (image or extracted text) leaves the local machine in the default configuration (bundled backend). If the user manually configures an external server URL (RF10b), the app must show an explicit warning when the URL does not point to `localhost`/private network, since the guarantee then depends on where the user chose to point |
| RNF2 | **Portability**: the app must work on Linux (major distros) and Windows 10/11, with at least one working path — GPU or CPU — on each. macOS (Apple Silicon) deferred to v2 |
| RNF3 | **Modularity**: the inference engine (backend) must be decoupled from the GUI, communicating via a local HTTP API, so model and backend can be replaced/updated without touching the UI |
| RNF4 | **Graceful degradation**: on insufficient VRAM or unavailable GPU backend, the app must fail in a managed way (clear message + CPU fallback), never a silent crash |
| RNF5 | **Response time**: no hard uniform requirement across such heterogeneous platforms/hardware; measure per-preset and communicate to the user, not promised upfront |

---

## 6. Hardware constraints

- The app must work across a very heterogeneous range of configs: from dated low-VRAM GPUs (reference machine, 4 GB) to modern GPUs with abundant VRAM, down to no dedicated GPU at all.
- Available VRAM **cannot be assumed at build time**: it must be detected at runtime (query of the active GPU backend) to choose the model preset (RF6).
- Known empirical baseline (reference machine, 4 GB): OOM already observed with a 7B Q4_K_M model at 24 offloaded layers — sets the indicative upper bound for the "low VRAM" tier.
- On Linux with hybrid GPU (Optimus/PRIME), the app must explicitly handle selection of the dedicated GPU instead of relying on the system default (avoiding altering the global prime-select profile, which previously caused a login loop on the reference machine).
- On machines without a GPU supported by any backend, the app must run entirely on CPU (Tesseract, and optionally CPU-only `llama.cpp` for very small models) without manual intervention.

---

## 7. Software / compatibility constraints

- **General rationale (not only for the reference GPU)**: Python/PyTorch stacks tie GPU compatibility to the exact torch+CUDA/ROCm combination installed, and official builds narrow the supported architectures over time (already happened with Maxwell/Pascal on CUDA 12.8+/13.0). For an app meant to run on heterogeneous hardware and stay compatible over time, this is an **unacceptable maintenance risk as a critical dependency** for the primary OCR engine.
- The primary inference engine **must** be `llama.cpp`/`llama-server` (via `mtmd` for OCR models), exposing multiple interchangeable native backends:

  | Backend | GPU vendor | Platforms |
  |---|---|---|
  | CUDA | NVIDIA | Windows, Linux |
  | HIP / ROCm | AMD | Linux (mainly) |
  | Metal | Apple Silicon | macOS |
  | Vulkan | NVIDIA / AMD / Intel (cross-vendor) | Windows, Linux |
  | CPU | — | Windows, macOS, Linux |

- **Vulkan is the universal GPU fallback** when the vendor-specific backend is unavailable or not built for that platform/GPU combination.
- For v1 priorities (Linux, Windows), the relevant backends are: CUDA, HIP/ROCm (Linux only), Vulkan, CPU. Metal (macOS) needs no build in v1.
- **Distribution strategy (confirmed)**: single package per platform (Linux, Windows) bundling all relevant `llama-server` binaries for that OS (CUDA, HIP/ROCm where relevant, Vulkan, CPU), with **automatic runtime selection** of the correct binary based on detected backend — not separate installers per backend. This reuses the same detection logic already required by RF3, avoids picking the wrong package, and lets the app adapt if the machine's hardware changes without reinstalling.
- OCR models: distributed as GGUF with compatible `mmproj` for local inference (e.g. from the `ggml-org` collection on Hugging Face: DeepSeek-OCR, PaddleOCR-VL, GLM-OCR, Dots.OCR, HunyuanOCR). For external/cloud (`esterno`), any OpenAI-compatible vision model is valid — recommended free options via OpenRouter (`inclusionai/ling-3.0-flash-vl:free`, `nex-agi/nex-n2.5-pro:free`, `qwen/qwen3.8-27b:free`, `google/gemma-4-31b-it:free`, etc. — full list in `README.md`, verified 2026-09-23).
- **Per-model prompt template**: each GGUF OCR model has its own prompt/chat-template structure (e.g. `--chat-template deepseek-ocr`). The `core` layer must treat it as per-model configuration, not a hardcoded constant.
- The backend must expose an OpenAI-compatible API (`/v1/chat/completions`), consistent with the existing Qwen server pattern, on a **dedicated port** separate from other running LLM servers. The same interface is used for external/cloud providers (OpenRouter `https://openrouter.ai/api/v1/chat/completions` is verbatim OpenAI-compatible — `src/locallens/core/client.py:86`).
- Tesseract (CPU fallback) has no GPU compatibility constraints: low-risk dependency, identical on all platforms.
- **PDF extraction/rendering library (confirmed): `pypdfium2`** (Python binding for PDFium, Chrome's PDF engine). Preferred over `pdf2image`/Poppler because Poppler requires an external system binary — on Windows it must be downloaded manually and added to PATH, a common source of setup/runtime errors. `pypdfium2` is a self-contained pip package (no external dependency) with prebuilt wheels for Linux and Windows. Also preferred over `PyMuPDF` (technically equivalent and also self-contained) for licensing: PDFium is permissive, while PyMuPDF is AGPL-3.0 or paid — less compatible with a non-AGPL distribution.

---

## 8. Architecture constraints

Layered architecture, with hardware/backend detection:

```
/backend        → llama-server instance, with binary/backend selected
                   by platform+GPU detection (CUDA/HIP/Metal/Vulkan/CPU)
/core           → orchestration: hardware detection, model preset choice,
                   per-model prompt/template, HTTP call, output parsing
/preprocessing  → OpenCV, CPU only (deskew, crop, contrast)
/app            → desktop GUI (PyQt6/PySide6)
/fallback       → Tesseract integration via pytesseract
```

- GPU/backend/VRAM detection must live in `/core` (or a dedicated `/hwdetect` module), **never in the GUI**, to stay testable and replaceable.
- `/core` must abstract the **OCR model source** into three interchangeable modes behind the same HTTP client interface (RF10): bundled backend (started/managed by `/backend`), external URL entered by the user, or no source (`/fallback` only). The difference is only *where* the client points, not the protocol: since all are OpenAI-compatible APIs, `/core` needs no per-mode branching.
- `/core` must not have direct dependencies on a specific OCR model: prompt templates are external data (config), not code.
- `/app` communicates only with `/core`, never directly with `/backend` nor an external URL, to keep engine, backend and inference source replaceable.

---

## 9. Constraints on OCR model selection

Instead of a fixed VRAM budget, at least three tiers are defined:

| Tier | Indicative VRAM | Model |
|---|---|---|
| CPU-only | GPU absent/unsupported | No GPU model: Tesseract only |
| Low VRAM | ~2–6 GB (e.g. reference machine) | Dedicated OCR model 1B–4B, Q4_K_M or more aggressive |
| Medium/high VRAM | >6 GB | Larger model or less aggressive quantization, if available |

**Default model for the low-VRAM tier (confirmed):** `ggml-org/GLM-OCR-GGUF:Q8_0` — 0.9B params, Q8_0 weights ~950 MB + `mmproj` ~484 MB (~1.4 GB total). Well within the 4 GB budget of the reference machine including KV cache.

A model is eligible for any GPU tier only if it meets **all** of:

1. Available as GGUF with `mmproj` for `llama.cpp`/`mtmd`
2. It is a dedicated OCR model, not a large general-purpose VLM (especially for the low tier)
3. It has a documented prompt/chat-template configuration (not deduced by analogy)
4. It fits the target tier's VRAM budget, mmproj included

---

## 10. Risks and mitigations

| Risk | Mitigation |
|---|---|
| OOM on high-resolution images/pages | Resize/tiling in `/preprocessing` before sending, with configurable max limit |
| GPU not used due to Optimus misconfiguration (Linux) | Explicit check at startup that `llama-server` is using the expected dedicated GPU, not the integrated one |
| Still broad test surface (2 priority OS × up to 4 GPU backends: CUDA, HIP, Vulkan, CPU) | Automated build/matrix where possible; in-depth manual testing only on reference machine (Linux + CUDA) in v1, rest as "best effort" (see open issues) |
| Vulkan/HIP drivers less mature than CUDA on some configs | Explicit CPU fallback if GPU inference fails silently or produces anomalous output, never an unhandled error |
| High latency on CPU fallback with complex documents | RF7 (indicate engine used) + expectation management, no uniform response-time promise |
| Driver/CUDA/ROCm updates breaking compatibility | Explicit pinning of the validated `llama.cpp` version per backend, update only after testing |

---

## 11. Acceptance criteria (v1)

Verified 2026-09-16 (details in `docs/architecture.md` §3):

- [x] The app automatically detects the available GPU backend (or its absence) and selects a model preset consistent with detected VRAM
- [x] The app extracts readable text from at least one test image via `ggml-org/GLM-OCR-GGUF:Q8_0` through `llama-server`, on at least one verified platform/backend (reference: Linux + CUDA)
- [ ] The same extraction works on Windows (reference: Acer Nitro ANV15-51, RTX 4050 Laptop) with CUDA backend — best effort, not verified in this session
- [x] With absent or unsupported GPU, extraction happens automatically via Tesseract with no manual step — pipeline verified via tests; live Tesseract requires system binary (`TESSERACT_LIVE=1`)
- [x] No external network call is made during processing
- [x] The system does not crash on OOM or unavailable backend: shows a managed error and offers CPU fallback
- [x] Extracted text is copyable and savable to file
- [x] The user can choose among bundled backend, external `llama.cpp` server URL, or no local model (Tesseract-only), and the app warns explicitly if the external URL does not point to `localhost`/private network
- [x] Input PDF is handled (page-by-page rendering) per the chosen approach (see open issues)

---

## 12. Open issues before development

- Default model for the medium/high VRAM tier (low tier covered by `GLM-OCR-GGUF:Q8_0`, see §9)
