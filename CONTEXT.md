# LocalLens

Estrazione OCR desktop con inferenza su GPU locale quando disponibile, server esterno o cloud opzionale, e fallback CPU.

## Language

### Inferenza

**BackendGpu**:
Flavor del binario llama-server selezionato a runtime in base a piattaforma e GPU.
_Avoid_: backend generico

**SorgenteModello**:
Dove punta il client di inferenza: bundlato, esterno oppure nessuno (solo fallback CPU).
_Avoid_: backend, motore

**PresetModello**:
Configurazione per-modello: repo GGUF, mmproj, chat-template, VRAM minima e limiti di resize.
_Avoid_: modello generico

### Documento

**Documento**:
File in input fornito dall'utente: un'immagine singola o un PDF.
_Avoid_: file, input

**Pagina**:
Unità atomica di inferenza: un'immagine oppure una singola pagina renderizzata di un PDF.
_Avoid_: immagine, foglio

**Estrazione**:
Testo risultato dell'inferenza su una singola Pagina, con indicazione del motore usato.
_Avoid_: OCR, output, risultato

### Applicazione

**LinguaInterfaccia**:
Lingua dei testi dell'interfaccia, italiano oppure inglese, commutabile a caldo dalle Impostazioni.
_Avoid_: locale, lingue filtro
