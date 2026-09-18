# GPU locale condizionale — design

Data: 2026-09-18. Stato: approvato in chat, da rivedere su file.

## Obiettivo

L'opzione di inferenza su GPU di questa macchina appare nella UI solo
quando è davvero usabile (binario + pesi rilevati all'avvio), e si chiama
"GPU locale" invece di "bundlato". L'id interno `bundlato` non cambia:
diario, config.toml, CONTEXT.md e test restano stabili.

## Rilevamento

Nuova `disponibilita_gpu_locale(info, preset)` in
`src/locallens/core/fabbrica.py`, pura e testabile:

- vero se `resolve_binary(piattaforma, info.candidati[0])` esiste
  come file **e** `snapshot_completo(preset)` non è None;
- falso altrimenti. Nessun download, nessun avvio processo.

## Etichetta

Mappa solo UI: id `bundlato` ↔ label "GPU locale" nel dialogo
Impostazioni (combo, stati, banner). `SorgenteModello` in CONTEXT.md
invariato.

## Dialogo

`DialogoImpostazioni(..., gpu_locale_disponibile=True)`: con flag vero
le voci sono ["GPU locale", "esterno", "nessuno"], senza flag la prima
sparisce. `valori()` e `set_sorgente()` traducono label↔id interno.

## Boot

Se il config salvato dice `bundlato` ma il rilevamento fallisce,
`normalizza_sorgente()` in fabbrica ripiega su `"esterno"` e il banner
segnala "GPU locale non rilevata (binari o pesi assenti)". Chiamata in
`costruisci_da_conf` (`__main__.py`) e dopo la chiusura del dialogo.

Il degrado a runtime (avvio server fallito → engine solo CPU) resta
com'è: il rilevamento non garantisce il successo, solo la presenza.

## File toccati

`core/fabbrica.py` (rilevamento + normalizza), `app/impostazioni.py`
(flag + mappa label), `app/finestra.py` (passa flag, normalizza dopo
dialogo), `__main__.py` (normalizza al boot), test fabbrica /
impostazioni / boot.

## Test e accettazione

- Rilevamento sì/no con binari e pesi finti (4 combinazioni).
- Dialogo: voce presente/assente in base al flag; round-trip valori.
- Boot con config `bundlato` e pesi assenti → engine esterno + banner.
- Suite esistente verde, senza rinominare l'id interno.
