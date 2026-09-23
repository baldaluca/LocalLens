# Windows VM checklist (CPU-only, niente GPU)

VM: KVM/VirtualBox, Win 10/11 (anche evaluation), 60 GB disco, 4 GB RAM, VGA virtuale.
Exe: `locallens.exe` dallo zip dell'artefatto CI `locallens-Windows`.

1. [ ] Avvio senza console popup, finestra visibile, nessun traceback.
2. [ ] Apri Documento immagine → Estrazione con `sorgente=nessuno` (Tesseract).
3. [ ] Apri PDF 2 pagine → 2 Pagine, badge engine `tesseract` su entrambe.
4. [ ] `sorgente=esterno` verso server Linux in LAN → Estrazione via rete, banner privacy se URL non-locale.
5. [ ] `sorgente=esterno` verso cloud (OpenRouter: URL `https://openrouter.ai/api/v1/chat/completions`, modello `inclusionai/ling-3.0-flash-vl:free`, token session-only) → Estrazione via rete, banner privacy atteso. Vedi `README.md` per altri modelli free.
6. [ ] Appunti (screenshot negli appunti) → Pagina importata; screenshot `mss` → PNG valida.
7. [ ] Hot-switch LinguaInterfaccia it/en + tema chiaro/scuro senza riavvio.
8. [ ] Config salvata in `%APPDATA%\LocalLens\config.toml`, token mai su disco.
9. [ ] `bundlato/cuda` in VM FALLISCE per disegno (VGA virtuale) → banner fallback, non un bug.

Smoke `win32/cuda-12.4` reale (hardware fisico Windows+NVIDIA o cloud GPU a ore):
`/health` 200, VRAM dedicata, gold image 4/4 linee esatte — protocollo validazione GTX 960M 2026-09-16.
Per validazione cloud, basta la checklist 5 sopra con un modello vision free.
