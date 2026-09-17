# Banco di prova — schema e checklist

11 Pagine reali in `pagine.jsonl` (una per riga) + PNG in `png/` (solo fonte certa).
Resta fuori da git (`.scratch/` non tracciato): contiene testo dei tuoi Documenti.

## Record

| campo | significato |
|---|---|
| `id` | stabile: `test2-pNN` o `test-grezzo-loop` |
| `fonte_documento` / `fonte_pagina` | da quale Documento/Pagina viene |
| `png` | Pagina renderizzata a 300 dpi (stesso renderer della pipeline); `null` se fonte ignota |
| `testo` / `motore_osservato` / `tempo_osservato` | Estrazione catturata e come fu prodotta |
| `etichetta` | `buona` \| `cattiva` — da compilare a mano |
| `tipo_difetto` | uno o più, separati da `+` — da compilare se `cattiva` |
| `note` | libero |

## Vocabolario `tipo_difetto`

`eco-prompt` · `loop` · `escape` · `vuoto` · `allucinazione-fluente` ·
`troncamento` · `lingua-sbagliata` · `riassunto` · `degenerazione-corta` · `altro`

## Stato — etichettato 2026-09-17 (da validare: 2 min di rilettura)

7 buone · 4 cattive. Dettaglio per record nel campo `note` di `pagine.jsonl`.
Aggiunta serale: `colloquio-p1/p2` (run `colloquio Prima.pdf`, entrambe `esterno`,
F1 0.98/0.97, filtro ok) → banco a **13 record: 9 buone, 4 cattive**.
Aggiunta 2026-09-17 notte: `ocrvision-p1..p5` (synthetic benchmark
`ocr_vision_test_document.pdf`, tutte `esterno`, controlli 60/60, filtro ok)
→ banco a **18 record: 14 buone, 4 cattive**.
Aggiunta 2026-09-17: `stress-p1/p5/p6` (buone `esterno` da `stress-fallback.pdf`;
p1 prova che 4 punti quasi-identici non flaggano, p5 le tabelle, p6 il testo corto)
→ banco a **21 record: 17 buone, 4 cattive**. Le p2/p3/p4 stress (fallback corretto)
non entrano: l'output VLM scartato non è loggato, resta solo il Tesseract.

- `test2-p3`: cattiva `eco-prompt+loop` (eco + No copying ×677).
- `test2-p6`: cattiva `eco-prompt` (eco in testa + contenuto reale).
- `test2-p10`: cattiva `eco-prompt` (eco in testa; resto fedele — verificato sul
  PNG: la Pagina contiene solo le domande 9-12; footer reso `Page 10 of 10`
  invece di `Pagina 10 di 10`).
- `test-grezzo-loop`: cattiva `loop+escape+eco-prompt`, tenuto come regressione
  pura (fonte ignota, senza PNG).
- `test2-p1/p8/p9` (fallback Tesseract): buone; p1 ha una riga di rumore OCR.
- `test2-p2/p4/p5/p7` (esterno): buone; p6/p7 hanno recinzione markdown residua
  in coda, tollerabile.
- Classi **ancora senza esempi**: `lingua-sbagliata`, `riassunto`, `troncamento`,
  `allucinazione-fluente`, `degenerazione-corta`, `vuoto`. Si aggiungono solo con
  nuove inferenze (1-2 min/Pagina, esito imprevedibile): via `Consigli LLM locali.pdf`
  (58 Pagine) o segnalando i prossimi fallimenti visti nell'uso reale.

## Checklist residua (tu)

1. Rileggi le 11 etichette (`etichetta`/`tipo_difetto`/`note` in `pagine.jsonl`):
   basta dissentire su una riga per farmelo sapere.
2. Facoltativo: aggiungi Pagine per le classi mancanti (procedura al punto 3
   precedente) oppure lascia il banco a 11 per partire — il ticket soglie può
   lavorare su eco/loop/escape/buone e registrare le altre come fog.
3. Dimmi quando posso partire con [Soglie e politica dubbio-Tesseract](../issues/04-soglie-politica-dubbio.md).
