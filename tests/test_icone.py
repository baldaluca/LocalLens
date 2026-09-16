"""RED: helper icona + wiring finestra."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from locallens.app.icone import percorso_icona


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_percorso_icona_esiste():
    import os

    assert os.path.isfile(percorso_icona())
    assert percorso_icona(999).endswith("locallens-256.png")


def test_finestra_ha_icona(qapp):
    from locallens.app.finestra import MainWindow

    w = MainWindow()
    assert not w.windowIcon().isNull()
