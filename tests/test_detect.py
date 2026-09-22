"""RED: detect() reale senza toccare hardware (probe finti)."""

from locallens.hwdetect.detector import detect


def _smi_ok(cmd):
    if cmd[0] == "nvidia-smi":
        return "4096"
    return None


def test_detect_nvidia_linux():
    info = detect(
        piattaforma="linux",
        esegui=_smi_ok,
        lspci=lambda: "00:02.0 VGA Intel HD Graphics",
        bins_presenti={"cuda", "vulkan", "cpu"},
    )
    assert info.gpu_vendor == "nvidia"
    assert info.vram_mb == 4096
    assert info.is_hybrid_optimus is True
    assert info.candidati == ("cuda", "vulkan", "cpu")


def test_detect_senza_nvidia_unknown():
    info = detect(
        piattaforma="linux",
        esegui=lambda cmd: None,
        lspci=lambda: "",
        bins_presenti={"vulkan", "cpu"},
    )
    assert info.gpu_vendor == "unknown"
    assert info.candidati == ("vulkan", "cpu")


def test_detect_senza_niente_solo_cpu():
    info = detect(
        piattaforma="win32",
        esegui=lambda cmd: None,
        lspci=lambda: "",
        bins_presenti=set(),
    )
    assert info.candidati == ("cpu",)


def test_detect_windows_wmic_nvidia():
    from locallens.hwdetect.detector import detect

    def esegui(cmd):
        if cmd[0] == "nvidia-smi":
            return None
        if cmd[0] == "wmic":
            return "Name\nNVIDIA GeForce RTX 4050 Laptop GPU\n"
        return None

    info = detect(
        piattaforma="win32",
        esegui=esegui,
        lspci=lambda: "",
        bins_presenti={"cuda", "vulkan", "cpu"},
    )
    assert info.gpu_vendor == "nvidia"
    assert info.candidati[0] == "cuda"


def test_detect_windows_powershell_amd():
    from locallens.hwdetect.detector import detect

    def esegui(cmd):
        if cmd[0] == "nvidia-smi":
            return None
        if cmd[0] == "wmic":
            return None
        if cmd[0] == "powershell":
            return "AMD Radeon Graphics"
        return None

    info = detect(
        piattaforma="win32",
        esegui=esegui,
        lspci=lambda: "",
        bins_presenti={"vulkan", "cpu"},
    )
    assert info.gpu_vendor == "amd"
    assert info.candidati == ("vulkan", "cpu")
