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


def test_nuovi_token_e_regole():
    assert "fallback" in tema.TEMI["chiaro"]
    assert "link" in tema.TEMI["scuro"]
    qss = tema.qss("chiaro")
    assert "#1D4ED8" in qss  # primary_pressa interpolato
    assert "QLabel#titolo" in qss
    assert "QLabel#pill" in qss
    assert "QSplitter" in qss


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


def test_qss_dropdown_popup_a_tema():
    import locallens.app.tema as tema

    for nome in ("chiaro", "scuro"):
        foglio = tema.qss(nome)
        assert "QAbstractItemView" in foglio
        assert tema.TEMI[nome]["surface"] in foglio


def test_dropdown_freccia_a_tema(qapp):
    from PySide6.QtGui import QPalette

    from locallens.app.tema import applica_tavolozza

    for nome in ("chiaro", "scuro"):
        applica_tavolozza(nome)
        tav = QApplication.palette()
        assert tav.color(QPalette.ColorRole.ButtonText).name() == tema.TEMI[nome]["foreground"].lower()
        assert tav.color(QPalette.ColorRole.Highlight).name() == tema.TEMI[nome]["primary"].lower()
    foglio = tema.qss("scuro")
    assert "QComboBox::drop-down" in foglio
