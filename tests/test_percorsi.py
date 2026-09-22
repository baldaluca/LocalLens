"""RED: path risorse dentro e fuori dal bundle PyInstaller."""

import sys

from locallens.config import percorsi


def test_fuori_bundle_cwd(monkeypatch, tmp_path):
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    monkeypatch.chdir(tmp_path)
    assert percorsi.risorsa("presets", "x.toml") == tmp_path / "presets" / "x.toml"


def test_dentro_bundle_meipass(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert percorsi.risorsa("bins", "linux") == tmp_path / "bins" / "linux"
