# ADR 0007 — Live tests behind env flags + bundle via _MEIPASS

Tests touching hardware/network (`test_integrazione_ocr`, live Tesseract) run only
with `LOCALLENS_LIVE=1` / `TESSERACT_LIVE=1`: CI stays pure and fast, real
validation is explicit and documented. The PyInstaller bundle resolves `presets/`
and `bins/` via `sys._MEIPASS` (`config/paths.py`), CWD in development: one
codepath for both, verified with an offscreen boot of the packaged binary.
