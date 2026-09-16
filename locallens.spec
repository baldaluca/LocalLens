# -*- mode: python ; coding: utf-8 -*-
"""Pacchetto unico per OS: app + presets + bins/<os>/* (selezione a runtime)."""

import sys
from pathlib import Path

ROOT = Path(SPEC).parent
OS = "win32" if sys.platform == "win32" else "linux"

a = Analysis(
    ["src/locallens/__main__.py"],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=[
        ("presets/*.toml", "presets"),
        (f"bins/{OS}", f"bins/{OS}"),
    ],
    hiddenimports=["locallens.app.finestra", "locallens.app.impostazioni"],
    excludes=["tkinter", "unittest"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="locallens",
    console=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    name="locallens",
)
