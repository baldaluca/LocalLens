# ADR 0006 — RF2 partial in v1: resize + contrast, no deskew/crop or OpenCV

Deskew and crop would require OpenCV (~90 MB extra in the bundle) for marginal
gain on the gold image. v1 implements `prepare()` with Pillow (already a dependency):
Lanczos resize anti-OOM + optional contrast. `deskew`/`crop` flags were removed
from settings instead of remaining as silent no-ops.
