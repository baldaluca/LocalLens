# ADR 0003 — Single package per OS with multi-binary and runtime selection

Instead of separate installers per backend, each OS package bundles all pertinent
`llama-server` binaries (CUDA, HIP on Linux only, Vulkan, CPU). The same
detection logic from RF3 picks the binary, avoiding a wrong-package error and
adapting to hardware changes without reinstalling.
