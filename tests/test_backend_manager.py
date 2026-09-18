"""RED: BackendManager avvia/supervisiona senza processi reali (fakes iniettati)."""

import pytest

from locallens.backend.manager import BackendManager


def _manager(esiste=True, occupate=None, health_ok=True):
    lanci = []
    uccisi = []
    occupate = set() if occupate is None else set(occupate)
    mgr = BackendManager(
        platform="linux",
        bins_root="bins",
        esiste=lambda p: esiste,
        porte_occupate=lambda: set(occupate),
        lancia=lambda cmd: (lanci.append(cmd), 4242)[1],
        verifica=lambda url: health_ok,
        uccidi=lambda pid: uccisi.append(pid),
    )
    return mgr, lanci, uccisi


def test_start_ok_sceglie_porta_libera():
    mgr, lanci, _ = _manager(occupate={8011})
    h = mgr.start("cuda", porta=8011)
    assert h.porta == 8012
    assert h.base_url == "http://127.0.0.1:8012"
    assert h.backend_gpu == "cuda"
    assert h.pid == 4242
    assert "bins/linux/cuda/llama-server" in lanci[0][0]


def test_start_con_preset_usa_argv_reali():
    from locallens.config.presets import load_preset

    mgr, lanci, _ = _manager()
    preset = load_preset("presets/glm-ocr-q8_0.toml")
    mgr.start("cuda", preset=preset, modello="/m/g.gguf", mmproj="/m/p.gguf")
    cmd = lanci[0]
    assert "--preset" not in cmd
    assert "-m" in cmd and "--mmproj" in cmd
    assert cmd[cmd.index("-m") + 1] == "/m/g.gguf"


def test_start_fallisce_se_binario_manca():
    mgr, lanci, _ = _manager(esiste=False)
    with pytest.raises(FileNotFoundError):
        mgr.start("cuda")
    assert lanci == []


def test_start_fallisce_se_health_ko_e_uccide():
    mgr, _lanci, uccisi = _manager(health_ok=False)
    with pytest.raises(RuntimeError):
        mgr.start("vulkan")
    assert uccisi == [4242]


def test_stop_uccide_e_pulisce():
    mgr, _, uccisi = _manager()
    mgr.start("cpu")
    mgr.stop()
    assert uccisi == [4242]
    assert mgr.handle is None


def test_stop_senza_start_noop():
    mgr, _, uccisi = _manager()
    mgr.stop()
    assert uccisi == []


def test_health_delega_a_verifica():
    mgr, _, _ = _manager()
    mgr.start("cpu")
    assert mgr.health() is True
    mgr2, _, _ = _manager(health_ok=False)
    # senza start: health False invece di eccezione (UI resta usabile via CPU)
    assert mgr2.health() is False
