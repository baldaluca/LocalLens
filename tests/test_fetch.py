"""RED: scarica() con URL qualsiasi (file:// nei test) + verifica binario."""

import importlib.util
import zipfile
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("fetch", "tools/fetch-binaries.py")
fetch = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fetch)


def _zip_finto(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("llama-b9999/llama-server", "#!/bin/sh\necho finto")


def test_scarica_file_zip_appiattisce_e_verifica(tmp_path):
    archivio = tmp_path / "finto.zip"
    _zip_finto(archivio)
    dest = fetch.scarica("linux", "cpu", bins_root=str(tmp_path / "bins"), url=archivio.as_uri())
    assert (dest / "llama-server").is_file()


def test_scarica_senza_binario_sollevato(tmp_path):
    archivio = tmp_path / "vuoto.zip"
    with zipfile.ZipFile(archivio, "w") as z:
        z.writestr("readme.txt", "niente binario")
    try:
        fetch.scarica("linux", "cpu", bins_root=str(tmp_path / "b2"), url=archivio.as_uri())
        raise AssertionError("doveva sollevare")
    except FileNotFoundError:
        pass
