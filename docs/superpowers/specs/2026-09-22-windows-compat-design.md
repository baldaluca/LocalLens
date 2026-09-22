# Windows Compatibility Design — LocalLens (2026-09-22)

Path: architectural (cross-cutting: BackendGpu, hwdetect, fallback, packaging, CI).
Decisione: approccio A — CI-first Windows. Scopo v1: parità completa GPU a livello di
codice; smoke `win32/cuda` solo su hardware reale/cloud GPU quando disponibile.
Distribuzione v1: zip `onedir` da CI, niente installer. Test locali: Ubuntu + VM Windows CPU-only.

## Contesto (as-is verificato)

- `backend/distro.py`: matrice v1 con asset `win32` (cuda 12.4 / vulkan / cpu), tag pinnato b10995.
- `core/rete.py:resolve_binary`: ritorna `llama-server.exe` su `win32`; `verifica_health`/`is_url_privata` stdlib-only.
- `config/settings.py:percorso_config`: `APPDATA/LocalLens` su win32, `~/.config/locallens` su Linux.
- `hwdetect/detector.py:decide`: `hip` solo su Linux, `vulkan` per nvidia/amd/intel/unknown, `cpu` sempre ultima.
- `locallens.spec`: switch `OS = win32 | linux`, include `bins/<os>`, `presets`, icone; `console=False`.
- `tools/fetch-binaries.py`: `--os linux|win32`, zip/tar.gz — gira su qualunque host.
- Manca: `.github/workflows/` (nessuna CI), fix kill/subprocess Windows, fallback `lspci`, path Tesseract Windows, HF cache Windows.

## Sezione 1 — Fix codice cross-platform (tutto mockabile da Ubuntu)

1. `backend/manager.py` — `_lancia`: aggiungere `creationflags=CREATE_NO_WINDOW` solo su win32
   (evita console popup per ogni `llama-server.exe`); `_uccidi`: via `proc.terminate()` quando
   esiste Popen registrato, fallback `taskkill /PID` per pid orfani (niente `os.kill+SIGTERM`
   Linux-centrico). `resolve_binary` invariato (già `.exe`). Errori invariati:
   `FileNotFoundError` binario assente, `RuntimeError` healthcheck ko con cleanup anti-zombie
   (`_finalizza_proc` terminate/wait/kill resta cross-platform).
2. `hwdetect/detector.py:detect` — `decide` invariata. Solo `detect`: fallback iniettabile
   `nvidia-smi` → `wmic path win32_VideoController get name` / `powershell Get-CimInstance
   Win32_VideoController`, mapping NVIDIA/AMD/Intel → `unknown` se binari presenti.
   Check Optimus resta guardato da `startswith("linux")`; `lspci` assente su Windows ritorna `""`.
3. `fallback/tesseract.py` — ricerca binario: `shutil.which` → `C:\Program Files\Tesseract-OCR\...`
   → env `TESSERACT_CMD`, runner `ocr` resta iniettabile; documentare language pack `ita`
   (default `ita+eng`, PSM 6 invariato).
4. `config/pesi.py:_cache_root` — rispettare `HF_HOME`/`HUGGINGFACE_HUB_CACHE`, altrimenti default
   di `huggingface_hub` (su Windows `%USERPROFILE%\.cache\...`), mai forzare `~/.cache` manuale;
   `cache_root` resta iniettabile.
5. Invariati: `config/percorsi.py` (`_MEIPASS`/CWD), `core/rete.py`, screenshot `mss`
   (`monitors[0]` combinato ok), `pypdfium2`, `settings.percorso_config`, `locallens.spec`
   (verificare esistenza `assets/icons/locallens.ico` in CI).
- Test: estendere `test_backend_manager.py` (win32 `.exe` + `CREATE_NO_WINDOW` + kill mock),
  `test_hwdetect.py`/`test_detect.py` (output WMIC finto via `esegui` iniettato),
  tesseract/pesi (PATH/env con `monkeypatch`). Tutto gira su Linux con `platform="win32"`.

## Sezione 2 — Packaging e test senza dual-boot

- `.github/workflows/ci.yml` — job `test` matrix `ubuntu-latest + windows-latest`:
  `uv sync`, `ruff check`, `mypy` (policy zero errori), `pytest -q` (live skippati senza
  `LOCALLENS_LIVE`/`TESSERACT_LIVE`); Tesseract via `apt` / `choco install tesseract`.
  Job `package`: `fetch-binaries --os <runner-os> --all` + `pyinstaller locallens.spec`
  **sul runner corrispondente** (PyInstaller non cross-builda); smoke `QT_QPA_PLATFORM=offscreen`
  con timeout su entrambi; artefatto `dist/locallens/` zippato per OS; cache `bins/`
  via `actions/cache`. Exe non firmato → warning SmartScreen documentato.
- VM locale (KVM/VirtualBox, ISO Win 10/11 anche evaluation, 60 GB / 4 GB RAM, VGA virtuale):
  solo click-test manuale `sorgente=nessuno|esterno` (Tesseract + server esterno in LAN),
  Documento immagine + PDF, appunti, screenshot, hot-switch LinguaInterfaccia it/en, temi.
  Fallimento `cuda` in VM è atteso, non un bug.
- Smoke `win32/cuda-12.4` (protocollo validazione GTX 960M 2026-09-16: `/health` 200, VRAM,
  gold image 4/4): solo su hardware fisico Windows+NVIDIA (es. RTX 4050 di riferimento)
  o cloud GPU Windows a ore; sbloccato dalla sezione 1, non blocca la release cpu/vulkan/esterno.

## Sezione 3 — Fuori v1 (YAGNI)

Installer Inno Setup/NSIS, firma codice, smoke RTX 4050 su hardware fisico, HIP/Optimus su
Windows, macOS/Metal, app store, persistenza token (resta session-only per sicurezza),
deskew/crop oltre resize+contrasto.

## Contratti invariati

SorgenteModello `bundlato|esterno|nessuno`, BackendGpu `cuda|hip|vulkan|cpu` (hip mai su win32),
Estrazione `{engine_used, ms, nota}`, `app → core/config` mai verso `backend`/`hwdetect` diretto.
