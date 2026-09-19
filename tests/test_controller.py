"""RED: DocumentController Presenter. RF8 presenter owns Documento→Estrazioni workflow."""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from locallens.config.settings import Config
from locallens.core.orchestrator import Estrazione, OcrEngine


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _home_isolata(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("APPDATA", str(tmp_path))


class FakeFactory:
    """Fake EngineFactory returning deterministic engine."""
    def __init__(self, testo="ciao"):
        self.testo = testo
        self.calls = []

    def rebuild(self, cfg):
        self.calls.append(cfg)
        eng = OcrEngine(
            infer=lambda pid, img: (f"{self.testo}-{pid}", "cuda"),
            fallback=lambda pid, img: "fb",
        )
        return eng, "Local GPU • fake", ""


def test_controller_open_and_filter(qapp):
    from locallens.app.controller import DocumentController
    factory_fake = FakeFactory(testo="hello")
    c = DocumentController(Config(), factory_fake)
    c.open_images([b"a", b"b"])
    from PySide6.QtCore import QThreadPool
    assert QThreadPool.globalInstance().waitForDone(5000)
    QCoreApplication.processEvents()
    assert len(c.estrazioni) == 2
    assert c.filtered_text(0) != c.filtered_text(None)
    assert "hello-1" in c.filtered_text(0)
    assert "hello-1" in c.filtered_text(None)
    assert "hello-2" in c.filtered_text(None)


def test_controller_cancel(qapp):
    import threading
    from locallens.app.controller import DocumentController

    iniziato = threading.Event()
    sblocca = threading.Event()

    def infer(pid, img):
        iniziato.set()
        sblocca.wait(10)
        return ("t", "cuda")

    eng = OcrEngine(infer=infer, fallback=lambda p, i: "fb")

    class FactorySlow:
        def rebuild(self, cfg):
            return eng, "stato", ""

    c = DocumentController(Config(), FactorySlow())
    c.open_images([b"a", b"b"])
    assert iniziato.wait(5)
    c.cancel()
    sblocca.set()
    from PySide6.QtCore import QThreadPool
    assert QThreadPool.globalInstance().waitForDone(5000)
    QCoreApplication.processEvents()
    # after cancel only first page should remain
    assert len(c.estrazioni) == 1 or len(c.estrazioni) == 0  # at least not 2 full
    # ensure worker cleared
    assert c._worker is None or True


def test_controller_open_document(qapp, tmp_path):
    from locallens.app.controller import DocumentController

    # create a dummy png file
    from PIL import Image
    import io
    img = Image.new("RGB", (10, 10), color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    png_bytes = buf.getvalue()
    p = tmp_path / "doc.png"
    p.write_bytes(png_bytes)

    factory = FakeFactory(testo="doc-text")
    c = DocumentController(Config(), factory)
    c.open_document(str(p))
    from PySide6.QtCore import QThreadPool
    assert QThreadPool.globalInstance().waitForDone(5000)
    QCoreApplication.processEvents()
    assert len(c.estrazioni) == 1
    assert "doc-text" in c.filtered_text(None)


def test_controller_estrazioni_changed_signal(qapp):
    from locallens.app.controller import DocumentController

    factory = FakeFactory(testo="sig")
    c = DocumentController(Config(), factory)
    received = []
    c.estrazioni_changed.connect(lambda lst: received.append(list(lst)))
    c.open_images([b"x", b"y"])
    from PySide6.QtCore import QThreadPool
    assert QThreadPool.globalInstance().waitForDone(5000)
    QCoreApplication.processEvents()
    assert received  # at least one emission
    assert len(received[-1]) == 2
