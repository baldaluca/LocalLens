# Test live dietro flag env + bundle via _MEIPASS

I test che toccano hardware/rete (`test_integrazione_ocr`, live Tesseract) girano
solo con `LOCALLENS_LIVE=1` / `TESSERACT_LIVE=1`: la CI resta pura e veloce,
la validazione reale è esplicita e documentata. Il bundle PyInstaller risolve
`presets/` e `bins/` via `sys._MEIPASS` (`config/percorsi.py`), CWD in sviluppo:
un solo codice per entrambi, verificato con boot offscreen del binario pacchettizzato.
