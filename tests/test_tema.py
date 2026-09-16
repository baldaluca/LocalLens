"""RED: token semantici per tema, niente hex sparsi nei widget."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from locallens.app import tema


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_stesse_chiavi_nei_temi():
    assert set(tema.TEMI["chiaro"]) == set(tema.TEMI["scuro"])


def test_qss_contiene_token():
    qss = tema.qss("scuro")
    assert "#2563EB" in qss  # primary del design system
    assert "QPushButton" in qss and "QListWidget" in qss


def test_tema_ignoto_sollevato():
    try:
        tema.qss("neon")
        raise AssertionError("doveva sollevare")
    except ValueError:
        pass


def test_toggle_sulla_finestra(qapp):
    from locallens.app.finestra import MainWindow

    w = MainWindow()
    assert w.tema_corrente == "chiaro"
    w.cambia_tema()
    assert w.tema_corrente == "scuro"
    assert "#2563EB" in w.styleSheet() or "background" in w.styleSheet()
