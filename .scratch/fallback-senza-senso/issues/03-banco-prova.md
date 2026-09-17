# Banco di prova con Pagine reali

Type: task
Status: resolved
Blocked by: —

## Question

Raccogliere il banco di 20-30 Pagine reali (buone + senza senso dai Documenti dell'utente, inclusi i casi già visti in `test`/`test2`) su cui contare quante Estrazioni difettose il nuovo controllo intercetta senza rovinare le buone: dove vivono i file, in che formato, e come si etichetta ogni Pagina (buona/cattiva + tipo di difetto)?

## Notes

Lavoro manuale prima di decidere soglie: niente da prototipare finché il banco non esiste. L'agente guida da solo dove può, altrimenti consegna una checklist precisa (quali Documenti, come anonimizzare, dove salvare). Risolto quando il banco esiste e i ticket successivi possono usarlo.

## Answer

Banco creato in `.scratch/fallback-senza-senso/banco/`: `pagine.jsonl` con 11 record
(10 da `test2` = run del Piano_Preparazione PDF verificato via confronto testo +
1 loop da `test` grezzo con `copying` ×1016), `png/` con le 10 Pagine a 300 dpi
(stesso renderer della pipeline, 6.5 MB), `SCHEMA.md` con vocabolario difetti e
checklist. Verifiche via script: eco confermata su p03/p06/p10; p01/p08/p09 già
fallback nella cattura. Resta da fare (checklist in SCHEMA.md, ~30 min): etichettare
gli 11 + aggiungere Pagine per classi mancanti (`lingua-sbagliata`, `riassunto`,
`troncamento`, `allucinazione-fluente`) fino a ~20-30. Il ticket 04 parte davvero
solo a banco etichettato e completo.

## Comments

2026-09-17 — etichettatura fatta dall'agente (testo + PNG p10 verificata a vista):
7 buone, 4 cattive in `pagine.jsonl` (dettagli in `banco/SCHEMA.md`). Classi senza
esempi (`lingua-sbagliata`, `riassunto`, `troncamento`, `allucinazione-fluente`)
richiedono nuove inferenze dall'app (1-2 min/Pagina, esito imprevedibile): non
forzabili in sessione, si aggiungono opportunisticamente o via `Consigli LLM locali.pdf`.
