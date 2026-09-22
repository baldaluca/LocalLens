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


def scarica(os: str, backend: str, bins_root: str = "bins", url: str | None = None) -> Path:
    url = url or download_url(os, backend)
    dest = Path(dest_dir(os, backend, bins_root))
    dest.mkdir(parents=True, exist_ok=True)
    import time
    import urllib.error

    with tempfile.NamedTemporaryFile(suffix=Path(url).suffix, delete=False) as tmp:
        archivio = tmp.name
        for tentativo in range(3):
            try:
                with urllib.request.urlopen(url, timeout=120) as r, open(archivio, "wb") as f:
                    shutil.copyfileobj(r, f)
                break
            except urllib.error.HTTPError as e:
                if e.code >= 500 and tentativo < 2:
                    time.sleep(2 * (tentativo + 1))
                    continue
                raise
            except OSError:
                if tentativo < 2:
                    time.sleep(2 * (tentativo + 1))
                    continue
                raise
    if archivio.endswith(".zip"):
        with zipfile.ZipFile(archivio) as z:
            z.extractall(dest)
    else:
        with tarfile.open(archivio) as t:
            t.extractall(dest, filter="data")
    for figlio in list(dest.iterdir()):
        if figlio.is_dir():  # release dentro singola cartella: appiattisci
            for elemento in figlio.iterdir():
                shutil.move(str(elemento), dest / elemento.name)
            figlio.rmdir()
    binario = dest / ("llama-server.exe" if os == "win32" else "llama-server")
    if not binario.is_file():
        raise FileNotFoundError(f"archivio senza binario atteso: {url} -> {dest}")
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
