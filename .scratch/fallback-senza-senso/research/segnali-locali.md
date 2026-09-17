# Research: segnali locali per Estrazioni senza senso

Ticket: `.scratch/fallback-senza-senso/issues/01-segnali-locali.md` · effort `fallback-senza-senso`
Branch throwaway: `research/segnali-locali` (da HEAD `7a011aa`) · main NON toccato
Vincoli (da `map.md`): solo testo Estrazione + byte Pagina, millisecondi, niente rete,
niente secondo modello pesante; dubbio → `cpu-tesseract`; termini da `CONTEXT.md`.
Stato attuale codice: `_motivo_anomalia` in `src/locallens/core/pipeline.py:22`
copre solo Estrazioni ≥ 500 char (eco prompt, loop righe/frasi/parole, escape, non-alfanumerico);
sotto i 500 char non scatta mai → buco noto della degenerazione corta.

## Metodo

- Fonti primarie: paper EACL 2023 su euristiche di allucinazione NMT (Dale et al.),
  README CLD3 (Google), docs fastText LID, docs Python (`zlib`, `re`, `unicodedata`),
  docs Pillow (`resize`, `histogram`); codice locale (`pipeline.py`, `test_pipeline.py`).
- Misure locali (CPython 3.14, Pillow 12.1.1, testi ~5 KB / Pagine 1700×2200):
  segnali testo ~0,1–2 ms/chiamata; ink-ratio Pagina ~19 ms a 340×440
  (riducibile a ~5 ms scendendo a ~200 px di lato).

## Segnali candidati (tutti stdlib + Pillow, già dipendenze di progetto)

### 1. Rapporto di compressione zlib (loop / degenerazione ripetitiva)

- Cosa: `len(zlib.compress(testo)) / len(testo)`; testo ripetitivo collassa (< 0,15),
  trascrizione naturale sta ~0,3–0,5. Generalizza i tre controlli loop attuali
  (righe/frasi/parole) in un unico numero O(n).
- Costo: ~1 ms su 5 KB (misurato dentro il totale 1,9 ms del blocco segnali testo).
- Soglia di partenza: `ratio < 0,20` E `len ≥ 200 char` → sospetta.
  Da tarare sul banco: i testi sintetici ripetitivi danno 0,08 anche quando "buoni".
- Falsi positivi: tabelle con molte celle identiche, moduli a caselle, codice
  sorgente trascritto, Pagine con una sola frase ripetuta come intestazione.
- Copre: loop/oscillazioni (cfr. euristica TNG in Dale et al., EACL 2023:
  top-n-gram count anomalo = firma delle "oscillatory hallucinations").
- NON copre: allucinazione fluente non ripetitiva (ratio normale).

### 2. Top-n-gram normalizzato / TTR (type-token ratio)

- Cosa: quota di trigrammi di parole distinti + `parole distinte / parole totali`.
  Misurato: loop "No copying."×200 → top1-ratio 0,50 / TTR 0,005 / top-trigramma ×199;
  testo variato → top1-ratio 0,08. Attenzione: su testo sintetico da template anche
  il "buono" riusa trigrammi (×60) → usare la quota di distinti, non il conteggio grezzo.
- Costo: stesso passaggio del punto 1, ~0 ms aggiuntivi (un solo `Counter`).
- Soglia di partenza: `top1-ratio > 0,25` con `n_parole ≥ 50`, oppure
  `trigrammi distinti / totali < 0,5` con `n_parole ≥ 100` → sospetta.
- Falsi positivi: elenchi puntati ripetitivi, tabelle, formule, testo breve
  (sotto 50 parole il segnale è instabile → non applicare).
- NON copre: allucinazione fluente varia, riassunti ben scritti.

### 3. Punteggio stopword IT/EN (lingua sbagliata)

- Cosa: due liste statiche (~20 stopword IT + ~20 EN, in codice, zero dipendenze),
  quota di occorrenze sul totale parole. Misurato: IT 0,26/0,00 – EN 0,00/0,22,
  separazione netta. CLD3/fastText (Google / Meta) confermano che n-grammi di
  caratteri e stopword bastano per IT↔EN, ma sono modelli esterni: qui basta
  la versione minimale perché le lingue da distinguere sono due, note a priori.
- Costo: 0,09 ms/chiamata (regex + set lookup).
- Soglia di partenza: se la Pagina è attesa in italiano e
  `quota_EN − quota_IT > 0,10` con `n_parole ≥ 30` → sospetta (lingua sbagliata).
  Sotto 30 parole: segnale inaffidabile → astenersi.
- Falsi positivi: Documenti legittimamente in inglese o misti IT/EN (fatture con
  termini inglesi, manuali bilingue), Documenti con poco testo funzionale.
  Mitigazione: applicare solo quando il contesto si aspetta italiano, mai da solo
  ma in OR con altri segnali deboli.
- NON copre: allucinazione fluente nella lingua giusta (caso più insidioso).

### 4. Marcatori meta-discorsivi (riassunto invece di trascrizione, rifiuti)

- Cosa: lista statica di frasi-regola (case-insensitive, ~30 voci IT/EN):
  `in sintesi`, `in conclusione`, `riassunto`, `il documento tratta di`,
  `the document shows`, `as an ai`, `as a language model`, `i can't`,
  `mi dispiace`, `non riesco a leggere`, `transcribe the document`
  (quest'ultima già coperta da `_motivo_anomalia`), `commentary`, `ecco la trascrizione:`
  solo se seguita da testo corto. Un riassunto si riconosce dal(frame)linguaggio,
  non dalla statistica.
- Costo: ~0,05 ms (ricerca sottostringhe su testo breve).
- Soglia di partenza: ≥ 1 marcatore "forte" (rifiuto, `as an ai`, `in sintesi`,
  `riassunto`) → sospetta immediata; marcatori "deboli" (`il documento`,
  `mostra`, markdown `##`/`**` diffuso) → sospetta solo con altro segnale.
- Falsi positivi: il Documento reale contiene quelle parole (es. Pagina di un
  libro che parla di riassunti; intestazioni markdown trascritte fedelmente).
  Mitigazione: i marcatori forti quasi mai appaiono in trascrizioni fedeli;
  pesare forte = 1, debole = 0,5.
- NON copre: riassunto senza frasi-segnale, allucinazione che imita la forma.

### 5. Troncamento parziale (finale monco + rapporto char/inchistro)

- Cosa: (a) l'Estrazione non termina con punteggiatura di chiusura (`. : ; ! ? " » )`)
  ma con parola a metà o connettivo (`e`, `di`, `che`, `the`, `and`, `,`);
  (b) rapporto `char Estrazione / ink-ratio Pagina`: Pagina piena di inchiostro
  con Estrazione cortissima = contenuto perso.
- Costo: (a) ~0 ms; (b) un resize+istogramma Pillow, ~19 ms a 340×440,
  ~5 ms stimati a ~200 px lato (da verificare sul banco).
- Soglia di partenza: (a) finale monco → segnale debole (0,5);
  (b) `ink-ratio > 0,05` E `len(Estrazione) < 200 char` → sospetta.
  Misurato: Pagina con righe → ink 0,17; Pagina bianca → 0,00.
- Falsi positivi: (a) Pagine che finiscono legittimamente senza punto
  (titoli, tabelle, elenchi, ultima riga di tabella); (b) Pagine con foto/grafici
  (molto inchiostro, poco testo), timbri, firme, Pagine quasi bianche.
  Mitigazione: (b) solo come conferma di Estrazione corta, mai da solo.
- NON copre: troncamento a metà Documento che capita di finire con un punto.

### 6. Degenerazione corta (< 500 char, il buco attuale)

- Cosa: rimuovere/abbassare la guardia `n < 500: return None` di
  `pipeline.py:30` applicando i segnali 1–4 anche sotto i 500 char, con la
  combinazione del punto 5b per le Estrazioni brevissime (< 100 char).
  Le regressioni esistenti (`test_pipeline.py:131-162`) restano valide: i nuovi
  controlli si aggiungono, non sostituiscono.
- Costo: invariato (stessi segnali, testi più corti = più veloci).
- Soglia di partenza: sotto 100 char decide solo marcatore forte o finale
  monco + ink alto; tra 100 e 500 char valgono tutti i segnali con soglie
  piene; politica dubbio → Tesseract invariata.
- Falsi positivi: Pagine legittimamente corte (biglietti da visita, etichette,
  timbri, singole righe) → rischio fallback inutile ma innocuo (Tesseract su
  testo corto è veloce e spesso corretto). È il falso positivo più tollerabile.
- NON copre: Estrazione corta ma plausibile e completa (indistinguibile senza
  confronto con i byte Pagina; il segnale 5b è l'unico appiglio).

### 7. Charset/script inatteso (segnale ausiliario, quasi gratis)

- Cosa: quota di caratteri fuori dallo script atteso via `unicodedata.name`
  (es. CJK/cirillico/arabo in Documento italiano), quota emoji, quota
  punteggiatura/simboli > 40 %. Una riga di Python, stdlib pura.
- Costo: ~0,1 ms. Soglia: `quota script-inatteso > 0,05` con `len ≥ 100` →
  segnale debole (0,5). Falsi positivi: Documenti multilingua legittimi,
  formule matematiche, codice. NON copre: quasi nulla da solo, solo conferma.

## Combinazione proposta (da validare sul banco, non implementata qui)

Punteggio somma-pesi: loop/compressione = 1, lingua = 1, marcatore forte = 1,
marcatore debole / finale monco / charset / ink = 0,5 ciascuno.
Fallback `cpu-tesseract` se somma ≥ 1 (politica dubbio → Tesseract da `map.md`).
Stima costo totale per Pagina: ~2 ms (solo testo) + ~5 ms (ink solo se
Estrazione < 500 char) — tre ordini di grandezza sotto una chiamata di inferenza.

## Cosa NON coprono (limiti onesti)

1. Allucinazione fluente nella lingua giusta, ben formattata, di lunghezza
   plausibile: indistinguibile da testo+byte senza modello giudice o
   confronto incrociato — fuori scope per decisione (`map.md` esclude il
   secondo modello pesante). Solo mitigazione parziale: rapporto char/ink (5b).
2. Errori di trascrizione puntuali (cifre, nomi, date sbagliate): nessun segnale
   statistico li vede; li vede solo la revisione umana o il confronto tra motori.
3. Lingua del Documento legittimamente diversa/mista dall'atteso: richiede
   metadato "lingua attesa" per Pagina, oggi non specificato (v. `map.md`,
   "not yet specified").
4. Soglie sopra sono stimate su testi sintetici + 2 Pagine sintetiche: vanno
   tarate sul banco di 20–30 Pagine reali prima di qualsiasi default attivo.

## Fonti

- Dale et al., "Looking for a Needle in a Haystack" (EACL 2023, ACL Anthology
  `2023.eacl-main.75`): tassonomia allucinazioni NMT (oscillatory vs fluent/detached)
  ed euristiche TNG/RT — base dei segnali 1–2.
- Google CLD3 README (`github.com/google/cld3`): LID con n-grammi di caratteri —
  giustifica il segnale 3 minimale (2 lingue note, niente rete neurale).
- fastText LID docs (`fasttext.cc/docs/en/language-identification.html`,
  Joulin et al. 2016/2017): classificatore lineare + n-grammi, migliaia di
  doc/s, modello compresso 917 kB — alternativa open-source solo se il segnale 3
  risultasse insufficiente (preferenza locale-first da `map.md`).
- Python docs: `zlib`, `re`, `unicodedata`; Pillow docs: `Image.resize`,
  `Image.histogram` — costi e disponibilità dei segnali 1/3/5/7.
- Repo: `src/locallens/core/pipeline.py:22-57`, `tests/test_pipeline.py:131-162`,
  `.scratch/fallback-senza-senso/map.md`, `CONTEXT.md`.
- Misure riportate verificate in locale il 2026-09-17 (script throwaway, non committati).
