# ADR 0001 — llama.cpp as primary engine, not Python/PyTorch

`torch+CUDA/ROCm` builds narrow supported architectures over time (already happened
with Maxwell/Pascal) and tie compatibility to the exact installed combination.
`llama-server` exposes interchangeable native backends (CUDA/HIP/Vulkan/CPU) behind
the same OpenAI-compatible API, with per-backend pinned binaries and runtime selection.
