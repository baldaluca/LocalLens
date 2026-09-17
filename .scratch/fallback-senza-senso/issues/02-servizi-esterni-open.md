# Servizi esterni open e gratuiti di riserva

Type: research
Status: resolved
Blocked by: —

## Question

Se i segnali locali risultano insufficienti, quali servizi esterni open-source e gratuiti (self-hostabili o offline-packaged, niente a pagamento) potrebbero giudicare se un'Estrazione è senza senso rispetto alla Pagina, e con quali costi (privacy Documento, latenza batch, peso integrazione)?

## Notes

Risolto da subagente AFK con skill `research`, su branch throwaway `research/servizi-esterni-open`; restano opzione di riserva: il default resta tutto locale.

## Answer

4 riserve open e gratuite, solo se il locale non basta sul banco: SigLIP via `transformers` (Apache-2.0, unica cross-modale Pagina↔Estrazione, prima riserva sui soli dubbi), fastText LID (MIT+CC-BY-SA pesi, ~1 MB, quasi-locale per lingua sbagliata), LanguageTool self-hosted (LGPL-2.1+, batch fuori dal path veloce), PaddleOCR (Apache-2.0, secondo lettore, pesante da isolare). Surya OCR scartata (pesi Rail-M con soglia commerciale). Default resta locale, dubbio persistente → Tesseract.

Context pointer: `.scratch/fallback-senza-senso/research/servizi-esterni-open.md` (branch `research/servizi-esterni-open`, file uncommitted recuperato su `main`).
