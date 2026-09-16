"""Integrazione live: immagine gold → GLM-OCR via llama-server. Solo con LOCALLENS_LIVE=1.

Esecuzione manuale sulla macchina di riferimento:
    (avvia llama-server con GLM-OCR su 8099)
    LOCALLENS_LIVE=1 LOCALLENS_URL=http://127.0.0.1:8099 \
        uv run --with pytest pytest tests/test_integrazione_ocr.py -q

Verificato il 2026-09-16 su GTX 960M: 4/4 righe esatte in ~7 s.
"""

import base64
import os

import pytest

Richiede = pytest.mark.skipif(
    os.environ.get("LOCALLENS_LIVE") != "1", reason="solo live esplicito"
)


@Richiede
def test_ocr_immagine_gold():
    from locallens.config.presets import load_preset
    from locallens.core.client import build_chat_payload, invia_chat

    url = os.environ.get("LOCALLENS_URL", "http://127.0.0.1:8099")
    preset = load_preset("presets/glm-ocr-q8_0.toml")
    with open("tests/assets/ocr-test-01.png", "rb") as f:
        img = f.read()
    payload = build_chat_payload(
        base64.b64encode(img).decode(),
        preset.prompt.get("system", "Transcribe."),
        preset.id,
    )
    testo = invia_chat(url, payload)
    assert "LocalLens OCR test" in testo
    assert "1234567890" in testo
    assert "42,00 euro" in testo
