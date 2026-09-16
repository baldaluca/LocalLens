"""RED: tabella asset pinnati per tools/fetch-binaries.py."""

import pytest

from locallens.backend.distro import asset_name, dest_dir, download_url, matrice_v1


def test_asset_linux_cuda_pinnato():
    assert asset_name("linux", "cuda") == "llama-b10995-bin-ubuntu-cuda-12.8-x64.tar.gz"


def test_asset_linux_hip_rocm():
    assert asset_name("linux", "hip") == "llama-b10995-bin-ubuntu-rocm-10.0-x64.tar.gz"


def test_asset_vulkan_cpu():
    assert asset_name("linux", "vulkan") == "llama-b10995-bin-ubuntu-vulkan-x64.tar.gz"
    assert asset_name("linux", "cpu") == "llama-b10995-bin-ubuntu-x64.tar.gz"
    assert asset_name("win32", "cuda") == "llama-b10995-bin-win-cuda-12.4-x64.zip"
    assert asset_name("win32", "vulkan") == "llama-b10995-bin-win-vulkan-x64.zip"
    assert asset_name("win32", "cpu") == "llama-b10995-bin-win-cpu-x64.zip"


def test_backend_ignoto_sollevato():
    with pytest.raises(ValueError):
        asset_name("linux", "metal")


def test_url_e_dest():
    url = download_url("linux", "cpu")
    assert url.startswith("https://github.com/ggml-org/llama.cpp/releases/download/b10995/")
    assert url.endswith(".tar.gz")
    assert str(dest_dir("linux", "cpu")) == "bins/linux/cpu"


def test_matrice_v1_copre_requisiti():
    m = matrice_v1()
    assert set(m["linux"]) == {"cuda", "hip", "vulkan", "cpu"}
    assert set(m["win32"]) == {"cuda", "vulkan", "cpu"}
