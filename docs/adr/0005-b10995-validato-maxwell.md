# llama.cpp b10995 convalidato su Maxwell (GTX 960M)

Il rischio Maxwell/Pascal documentato nei requisiti si riferiva a build PyTorch.
Verifica del 2026-09-16: `llama-b10995-bin-ubuntu-cuda-12.8-x64` carica GLM-OCR-Q8_0
su GTX 960M (cc 5.2), `/health` 200, 1866 MiB VRAM su dedicata, OCR gold 4/4 righe.
Pin `TAG = b10995` in `backend/distro.py`; cambio solo dopo test su entrambe le macchine.
