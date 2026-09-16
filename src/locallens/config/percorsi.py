"""Risoluzione risorse: _MEIPASS nel bundle, CWD in sviluppo."""

import sys
from pathlib import Path


def base() -> Path:
    bundle = getattr(sys, "_MEIPASS", None)
    return Path(bundle) if bundle else Path.cwd()


def risorsa(*parti: str) -> Path:
    return base().joinpath(*parti)
