"""Scarica i binari llama-server pinnati in bins/<os>/<backend>/ (stdlib only).

Uso:
    python tools/fetch-binaries.py --os linux --backend cuda
    python tools/fetch-binaries.py --os linux --all
    python tools/fetch-binaries.py --list
"""

import argparse
import shutil
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from locallens.backend.distro import TAG, asset_name, dest_dir, download_url, matrice_v1


def scarica(os: str, backend: str, bins_root: str = "bins") -> Path:
    url = download_url(os, backend)
    dest = Path(dest_dir(os, backend, bins_root))
    dest.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=Path(url).suffix, delete=False) as tmp:
        with urllib.request.urlopen(url, timeout=120) as r, open(tmp.name, "wb") as f:
            shutil.copyfileobj(r, f)
        archivio = tmp.name
    if archivio.endswith(".zip"):
        with zipfile.ZipFile(archivio) as z:
            z.extractall(dest)
    else:
        with tarfile.open(archivio) as t:
            t.extractall(dest, filter="data")
    print(f"{os}/{backend}: {asset_name(os, backend)} -> {dest}")
    return dest


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--os", choices=["linux", "win32"], default="linux")
    ap.add_argument("--backend", default="cpu")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--tag", default=TAG)
    args = ap.parse_args()
    if args.list:
        for os, backends in matrice_v1().items():
            for b in backends:
                print(f"{os}/{b}: {asset_name(os, b)}")
        return
    targets = matrice_v1()[args.os] if args.all else [args.backend]
    for b in targets:
        scarica(args.os, b)


if __name__ == "__main__":
    main()
