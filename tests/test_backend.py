"""RED: logica pura BackendManager senza avviare processi reali."""

from locallens.backend.manager import trova_porta_libera
from locallens.core.rete import is_url_privata, resolve_binary


def test_resolve_binary_linux_cuda():
    p = resolve_binary(platform="linux", backend_gpu="cuda", bins_root="bins")
    assert str(p).endswith("bins/linux/cuda/llama-server")


def test_resolve_binary_win_exe():
    p = resolve_binary(platform="win32", backend_gpu="vulkan", bins_root="bins")
    assert str(p).endswith("bins/win32/vulkan/llama-server.exe")


def test_trova_porta_libera_saluta_occupata():
    occupate = {8011, 8012}
    porta = trova_porta_libera(partenza=8011, occupate=occupate)
    assert porta == 8013


def test_url_privata():
    assert is_url_privata("http://127.0.0.1:8011") is True
    assert is_url_privata("http://192.168.1.10:8080") is True
    assert is_url_privata("http://10.0.0.5:8011") is True
    assert is_url_privata("http://localhost:8011") is True


def test_url_pubblica_richiede_avviso():
    assert is_url_privata("http://203.0.113.10:8011") is False
    assert is_url_privata("https://example.com:443") is False
