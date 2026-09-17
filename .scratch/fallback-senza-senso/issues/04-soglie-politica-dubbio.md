# Soglie e politica dubbio-Tesseract

Type: grilling
Status: resolved
Blocked by: 01, 03

## Question

Con i segnali locali noti e il banco pronto, quali soglie e quale politica dubbio→Tesseract adottiamo in `elabora_pagine` (dove vive il controllo, cosa finisce in `nota`/diario/banner, quanti falsi positivi su Estrazioni buone tolleriamo per intercettare quasi tutte le cattive)?

## Notes

Ticket HITL: si risolve solo con scambio live (grilling + domain-modeling). Non partire finché i ticket bloccanti non sono chiusi. Prerequisito concreto: banco in `banco/pagine.jsonl` etichettato e completo a ~20-30 record con classi mancanti coperte (vedi `banco/SCHEMA.md`); oggi è a 11 non etichettati.

## Answer

Grilling chiuso 2026-09-17: utente accetta tutte le raccomandazioni. Decisioni:

1. **Combinazione somma-pesi, fallback se ≥ 1** (dubbio→Tesseract). Pesi 1:
   compressione zlib < 0.20 (len ≥ 200), top1-parola > 0.25 (≥ 50 parole),
   trigrammi-distinti < 0.5 (≥ 100 parole), lingua EN−IT > 0.10 (≥ 30 parole),
   marcatore forte (eco inclusa). Pesi 0.5 solo in combinazione: marcatori deboli,
   finale monco ridefinito, charset inatteso, ink-ratio. Misurato sul banco:
   4/4 cattive, 0 falsi positivi (script `research/misura-segnali-banco.py`).
2. **Finale monco ridefinito**: scatta solo su parola a metà o connettivo finale
   (`e/di/che/the/and`, virgola), ignorando footer e recinzioni markdown.
   La versione "ultimo char non è punteggiatura" è rumore (11/11 sul banco).
3. **Marcatori deboli 0.5 mai da soli**; `mostra` esclusa dalla lista (scatta su
   3/7 buone); restano `il documento`, `conclusione`.
4. **Guardia `n < 500` rimossa**: segnali a qualsiasi lunghezza con i pavimenti
   minimi sopra; Pagine corte legittime in Tesseract = falso positivo tollerabile.
5. **Estendere `_motivo_anomalia` nello stesso seam** (stessa firma, stessa `nota`,
   stesso diario/banner); in più, `nota` segnala anche quando il fallback
   Tesseract stesso è vuoto (oggi silenzioso).

Resta fog (non bloccante per implementare): taratura su classi senza esempi
(lingua, riassunto, troncamento, allucinazione fluente) quando arriveranno Pagine
reali; impatto retry/timeout/batch da verificare in implementazione.
