"""Mapping PresetModello → argv di llama-server. Solo flag verificati su build 0.4.0-dev."""

from locallens.config.presets import PresetModello


def preset_to_argv(
    preset: PresetModello,
    binario: str,
    modello: str,
    mmproj: str,
    porta: int,
) -> list[str]:
    argv = [binario, "-m", modello, "--mmproj", mmproj]
    argv += ["-c", str(preset.ctx_size), "--port", str(porta)]
    ngl = preset.server_args.get("n_gpu_layers")
    if ngl is not None:
        argv += ["-ngl", str(ngl)]
    if preset.server_args.get("flash_attn") is True:
        argv += ["-fa", "on"]
    return argv
