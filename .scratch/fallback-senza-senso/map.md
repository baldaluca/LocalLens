## Destination

Nuovo controllo in `elabora_pagine` attivo di default, tutto locale, che manda in `cpu-tesseract` la maggioranza delle Estrazioni senza senso del modello locale (allucinazione fluente, troncamento parziale, lingua sbagliata, riassunto al posto di trascrizione, degenerazione corta), con politica dubbio→Tesseract, validato su un banco di 20-30 Pagine reali.

## Notes

- Dominio: LocalLens; usare i termini di `CONTEXT.md`: Documento, Pagina, Estrazione, SorgenteModello, PresetModello, BackendGpu. Mai "output/file" per Estrazione/Documento.
- Skills per ogni sessione: `grilling` + `domain-modeling` per le decisioni; `research` per i ticket research; `prototype` quando si alza la fedeltà dello stub.
- Preferenze stabili: locale-first e veloce (solo segnali da testo Estrazione + byte Pagina in millisecondi); servizi esterni solo open-source e gratuiti, solo se il locale risulta insufficiente; nel dubbio si va in Tesseract (falso fallback ok, allucinazione mostrata no).
- Codice interessato: `src/locallens/core/pipeline.py` (`_motivo_anomalia`, `elabora_pagine`), `tests/test_pipeline.py`.

## Decisions so far

<!-- una riga per ticket chiuso: gist + link; la decisione vive nel ticket -->

- [Segnali locali per Estrazioni senza senso](issues/01-segnali-locali.md): 7 segnali stdlib+Pillow in millisecondi, somma-pesi ≥ 1 → `cpu-tesseract`; allucinazione fluente plausibile resta invisibile senza giudice cross-modale.
- [Servizi esterni open e gratuiti di riserva](issues/02-servizi-esterni-open.md): prima riserva SigLIP sui soli dubbi, poi fastText/LanguageTool/PaddleOCR; Surya scartata per licenza pesi; default resta locale.
- [Banco di prova con Pagine reali](issues/03-banco-prova.md): `banco/` con 21 record
  (17 buone, 4 cattive) + PNG + schema; classi senza esempi (riassunto, troncamento,
  allucinazione fluente) solo via nuove inferenze; `lingua` coperta da stress-p4 (self-hit).
- [Soglie e politica dubbio-Tesseract](issues/04-soglie-politica-dubbio.md): somma-pesi ≥ 1 con soglie misurate (4/4, 0 FP); monco ridefinito; deboli 0.5 mai soli senza `mostra`; guardia 500 rimossa; estendere `_motivo_anomalia`, `nota` anche su fallback vuoto.

## Not yet specified

- Taratura su classi senza esempi (lingua-sbagliata, riassunto, troncamento,
  allucinazione-fluente): si aggiunge quando arrivano Pagine reali, senza
  bloccare l'implementazione.
- Impatto su retry/timeout/batch e performance: da verificare in implementazione
  (nessuna decisione attesa, solo misura).

La via è tracciata ed è stata percorsa: implementato il 2026-09-17 in
`src/locallens/core/pipeline.py` (TDD, 7 test nuovi) + benchmark verdi:
file3 10 Pagine (3/3 degeneri intercettate), ocrvision 60/60, stress 6/6,
banco 21 record TP=4 FP=0. Dettagli in `research/benchmark-*.md`.

## Out of scope

- Servizi a pagamento o cloud di default con invio delle Pagine fuori dal PC.
- Cambio di BackendGpu, PresetModello o SorgenteModello.
- Secondo modello giudice pesante/lento in pipeline.
