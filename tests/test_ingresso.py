"""RED: ingressi RF1. Screenshot reale solo con display; nei test grabber finto."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from locallens.app import ingresso


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_carica_immagine_da_disco():
    pagine = ingresso.carica_documento("tests/assets/ocr-test-01.png")
    assert len(pagine) == 1
    assert pagine[0][:8] == b"\x89PNG\r\n\x1a\n"


def test_carica_pdf_chiama_render(monkeypatch, tmp_path):
    viste = {}
    monkeypatch.setattr(
        ingresso, "render_pagine", lambda pdf, dpi: (viste.update(dpi=dpi), [b"P1", b"P2"])[1]
    )
    f = tmp_path / "doc.pdf"
    f.write_bytes(b"%PDF-finto")
    assert ingresso.carica_documento(str(f), dpi=150) == [b"P1", b"P2"]
    assert viste["dpi"] == 150


def test_file_mancante_sollevato():
    with pytest.raises(FileNotFoundError):
        ingresso.carica_documento("tests/assets/inesistente.png")


def test_da_appunti(qapp):
    img = QImage(40, 20, QImage.Format_RGB888)
    img.fill(0xFFFFFF)
    QApplication.clipboard().setImage(img)
    png = ingresso.da_appunti(QApplication.clipboard())
    assert png is not None and png[:8] == b"\x89PNG\r\n\x1a\n"


def test_screenshot_con_grabber_finto():
    assert ingresso.cattura_schermo(grabber=lambda: b"PNG-FINTO") == b"PNG-FINTO"
