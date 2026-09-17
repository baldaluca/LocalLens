# Benchmark run file3 (nuovo filtro attivo)

Run reale del 2026-09-17 sullo stesso Documento del banco
(`Piano_Preparazione_...pdf`, 10 Pagine). Routing osservato:
Tesseract su 1,3,6,8,9,10 — LLM locale su 2,4,5,7.

Metodo (`/tmp/bench_file3.py`, score in `banco/file3-score.json`):
fedeltà = F1 su token contro text-layer PDF (ground truth);
routing confrontato con cattura `test2` (codice precedente).

## Routing: 3/3 degeneri intercettate, 0 cambi sulle buone

| Pagina | prima (test2) | ora (file3) | esito |
|---|---|---|---|
| 3 (loop+eco) | esterno | cpu-tesseract | ✅ intercettata |
| 6 (eco) | esterno | cpu-tesseract | ✅ intercettata |
| 10 (eco) | esterno | cpu-tesseract | ✅ intercettata |
| 1,8,9 (già fallback) | cpu-tesseract | cpu-tesseract | invariato |
| 2,4,5,7 (buone) | esterno | esterno | invariato, nessun falso positivo |

## Fedeltà output finali (F1 vs GT): 0.97–1.00 ovunque

p1 0.977 · p2 0.987 · p3 0.980 · p4 1.000 · p5 0.988 ·
p6 0.987 · p7 0.970 · p8 0.999 · p9 0.998 · p10 0.995.
Nuovo filtro sugli output finali: nessun flag (corretto — sono tutti fedeli;
rumore OCR residuo su p1/p3 non abbassa F1 in modo significativo).

## Tempi (osservazione, non regressione del filtro)

Fallback 124–153 s (p6 41 s, p10 16 s) vs LLM 14–98 s: il costo del fallback
resta nei tentativi VLM precedenti (retry/timeout invariati). p10 veloce (16 s)
= VLM fallito in fretta, fallback immediato.

## Limiti

Text-layer PDF come GT: ignora layout/formule; F1 lessicale non vede errori
puntuali (cifre/nomi). Classi senza esempi restano fuori benchmark.
