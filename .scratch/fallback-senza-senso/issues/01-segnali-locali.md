# Segnali locali per Estrazioni senza senso

Type: research
Status: resolved
Blocked by: —

## Question

Quali segnali calcolabili in locale e in millisecondi (solo da testo dell'Estrazione + byte della Pagina, senza rete e senza secondo modello pesante) distinguono un'Estrazione senza senso — allucinazione fluente, troncamento parziale, lingua sbagliata, riassunto invece di trascrizione, degenerazione corta < 500 caratteri — da una trascrizione buona?

## Notes

Risolto da subagente AFK con skill `research`, su branch throwaway `research/segnali-locali`; i risultati vanno linkati al ticket, non incollati.

## Answer

7 segnali solo stdlib+Pillow (≤2 ms testo + ~5 ms ink-ratio solo se Estrazione < 500 char): rapporto compressione zlib, top-n-gram/TTR, stopword IT/EN, marcatori meta-discorsivi, finale monco + char/ink-ratio, estensione sotto i 500 char, charset inatteso. Combinazione somma-pesi ≥ 1 → `cpu-tesseract`. Limite onesto: allucinazione fluente in lingua giusta e lunghezza plausibile resta invisibile senza giudice cross-modale. Soglie stimate su sintetico: taratura obbligatoria sul banco reale.

Context pointer: `.scratch/fallback-senza-senso/research/segnali-locali.md` (commit `935ec0d` su branch `research/segnali-locali`).
