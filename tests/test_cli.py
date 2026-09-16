"""RED: mapping PresetModello → argv reali di llama-server (build 0.4.0-dev)."""

from locallens.backend.cli import preset_to_argv
from locallens.config.presets import load_preset


def test_argv_preset_fascia_bassa():
    preset = load_preset("presets/glm-ocr-q8_0.toml")
    argv = preset_to_argv(
        preset,
        binario="bins/linux/cuda/llama-server",
        modello="/m/GLM-OCR-Q8_0.gguf",
        mmproj="/m/mmproj.gguf",
        porta=8011,
    )
    assert argv[0] == "bins/linux/cuda/llama-server"
    assert "--preset" not in argv
    assert "--chat-template" not in argv
    assert ["-m", "/m/GLM-OCR-Q8_0.gguf"] == argv[1:3]
    assert ["--mmproj", "/m/mmproj.gguf"] in [argv[i : i + 2] for i in range(len(argv))]
    assert ["--port", "8011"] in [argv[i : i + 2] for i in range(len(argv))]
    assert ["-c", "4096"] in [argv[i : i + 2] for i in range(len(argv))]
    assert ["-ngl", "99"] in [argv[i : i + 2] for i in range(len(argv))]
    assert ["-fa", "on"] in [argv[i : i + 2] for i in range(len(argv))]
