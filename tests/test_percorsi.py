"""RED: path risorse dentro e fuori dal bundle PyInstaller."""

import sys

from locallens.config import percorsi


def test_fuori_bundle_cwd(monkeypatch):
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    monkeypatch.chdir("/tmp")
    assert str(percorsi.risorsa("presets", "x.toml")) == "/tmp/presets/x.toml"


def test_dentro_bundle_meipass(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert percorsi.risorsa("bins", "linux") == tmp_path / "bins" / "linux"
