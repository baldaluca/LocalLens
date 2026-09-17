# Benchmark stress-fallback.pdf (avversariale per costruzione)

Run 2026-09-17, 6 Pagine. Routing osservato: fallback su 2,3,4 — 6/6 come disegnato.

## Dettaglio segnali (verifica post-hoc)

- p2: output Tesseract contiene l'eco → VLM fedele ⇒ regola eco. Self-hit confermato.
- p4: output inglese ⇒ `lingua inattesa`. Self-hit confermato.
- p3: ambiguo (loop VLM o trascrizione fedele di 8 righe identiche, che flagga
  comunque con `ripetizione in loop` + `compressione anomala`). Fallback corretto per disegno.
- p1/p5/p6 `esterno`, filtro `ok`: 4 punti quasi-identici (freq 4<5), tabella,
  testo corto non generano falsi positivi.
- Entrate nel banco come `stress-p1/p5/p6` (buone). p2/p3/p4 escluse: output VLM
  scartato non loggato (solo Tesseract disponibile) — possibile miglioramento futuro:
  salvare nel diario il testo scartato che ha triggerato il fallback.
