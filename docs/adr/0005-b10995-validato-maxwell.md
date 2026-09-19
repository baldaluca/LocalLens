# ADR 0005 — llama.cpp b10995 validated on Maxwell (GTX 960M)

The Maxwell/Pascal risk in the requirements referred to PyTorch builds.
Validation 2026-09-16: `llama-b10995-bin-ubuntu-cuda-12.8-x64` loads GLM-OCR-Q8_0
on GTX 960M (cc 5.2), `/health` 200, 1866 MiB VRAM on the dedicated GPU, OCR gold 4/4 lines.
Pin `TAG = b10995` in `backend/distro.py`; change only after testing on both reference machines.
