"""RED: decisione backend/VRAM senza toccare hardware reale."""

from locallens.hwdetect.detector import HardwareInfo, decide


def test_nvidia_con_cuda_usa_cuda_primo():
    info = decide(
        platform="linux",
        gpu_vendor="nvidia",
        vram_mb=4096,
        is_hybrid_optimus=True,
        bins_disponibili={"cuda", "vulkan", "cpu"},
    )
    assert isinstance(info, HardwareInfo)
    assert info.candidati == ("cuda", "vulkan", "cpu")
    assert info.vram_mb == 4096
    assert info.is_hybrid_optimus is True


def test_nvidia_senza_bin_cuda_degrada_a_vulkan():
    info = decide(
        platform="linux",
        gpu_vendor="nvidia",
        vram_mb=4096,
        is_hybrid_optimus=False,
        bins_disponibili={"vulkan", "cpu"},
    )
    assert info.candidati == ("vulkan", "cpu")


def test_amd_con_hip_usa_hip_primo_su_linux():
    info = decide(
        platform="linux",
        gpu_vendor="amd",
        vram_mb=8192,
        is_hybrid_optimus=False,
        bins_disponibili={"hip", "vulkan", "cpu"},
    )
    assert info.candidati[0] == "hip"


def test_senza_gpu_solo_cpu():
    info = decide(
        platform="linux",
        gpu_vendor="none",
        vram_mb=None,
        is_hybrid_optimus=False,
        bins_disponibili={"cpu"},
    )
    assert info.candidati == ("cpu",)
    assert info.vram_mb is None


def test_cpu_sempre_ultima_spiaggia():
    info = decide(
        platform="win32",
        gpu_vendor="unknown",
        vram_mb=None,
        is_hybrid_optimus=False,
        bins_disponibili=set(),
    )
    assert info.candidati == ("cpu",)
