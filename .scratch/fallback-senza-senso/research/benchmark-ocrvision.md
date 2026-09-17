# Benchmark synthetic OCR (`ocr_vision_test_document.pdf`)

Run 2026-09-17, 5 Pagine, tutte `esterno` (39-43 s). Check: 60 sequenze di
controllo esatte disegnate nel Documento (ID, importi, date, mail, accenti,
checkbox, simboli) — script `/tmp/bench_ocr.py`.

## Risultato: 60/60, filtro ok su tutte (corretto: nessuna da fallback)

- p1 10/10 · p2 10/10 (tabella markdown, numeri esatti) · p3 14/14
  (totali 1.316,49/289,63/1.606,12 e IBAN carattere per carattere) ·
  p4 8/8 (checkbox E-mail e 4-Buono corretti, firma vuota preservata) ·
  p5 18/18 (ordine lettura bicolonna A→F corretto).
- Refusi minori (2, entrambi nel footer boilerplate): `Campioni`/`Campiono`
  invece di `Campione` su p3/p4. Normalizzazione `Ωmega`→`Omega` su p5.
- Entrate nel banco come `ocrvision-p1..p5` (buone) → banco a 18 record.
