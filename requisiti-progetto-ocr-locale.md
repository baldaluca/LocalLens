# Documento dei Requisiti di Progetto — LocalLens
## App OCR desktop multipiattaforma con inferenza locale GPU-accelerata

**Nome progetto:** LocalLens
**Versione:** 2.0
**Data:** 15 settembre 2026
**Piattaforme target:** Linux e Windows (prioritarie v1); macOS non nel perimetro v1

---

## 1. Obiettivo del progetto

Realizzare un'applicazione desktop **multipiattaforma**, con **Linux e Windows come piattaforme prioritarie per la v1** (macOS rimandato a una versione successiva), che esegua OCR (estrazione di testo da immagini/documenti) interamente in locale, sfruttando l'accelerazione GPU quando disponibile — **indipendentemente dal vendor** (NVIDIA, AMD, Intel, Apple Silicon) — con fallback automatico su CPU quando non lo è, senza mai dipendere da servizi cloud o API esterne.

---

## 2. Hardware/ambienti di riferimento

### 2.1 Macchina di riferimento Linux (sviluppo)

Usata come **riferimento empirico** per dimensionare i vincoli VRAM e validare il caso limite di GPU datata/a bassa memoria — non è l'unico target del progetto.

| Componente | Specifica |
|---|---|
| CPU | Intel Core i7-6700HQ |
| RAM | 16 GiB |
| Storage | SSD 1 TB |
| GPU dedicata | NVIDIA GeForce GTX 960M, 4 GB VRAM (architettura Maxwell, compute capability 5.2) |
| GPU integrata | Intel HD Graphics 530 (configurazione Optimus) |
| Driver NVIDIA | 580.178.04 (CUDA 13.0) |
| OS | Ubuntu 26.04.1 LTS |
| Stack LLM già presente | `llama-server` con modello Qwen3.5-4B-GGUF (Q4_K_M), validato e funzionante su questa GPU |

Nota: con Qwen2.5-Coder-7B-Instruct (Q4_K_M) a `--n-gpu-layers 24` si è già osservato **out-of-memory sulla GPU**. Questo è il riferimento empirico per la fascia "VRAM bassa" (vedi punto 9).

### 2.2 Macchina di riferimento Windows (test)

| Componente | Specifica |
|---|---|
| Dispositivo | Acer Nitro ANV15-51 |
| CPU | 13th Gen Intel Core i5-13420H, 2.10 GHz |
| RAM | 16 GB (15,7 GB utilizzabile) |
| GPU dedicata | NVIDIA GeForce RTX 4050 Laptop GPU, 6 GB VRAM (architettura Ada Lovelace, compute capability 8.9) |
| GPU integrata | Intel UHD Graphics (128 MB) |
| Storage | 477 GB (282 GB utilizzati) |
| OS | Windows |

Nota: con 6 GB di VRAM e un'architettura molto più recente della GTX 960M, questa macchina ricade al limite superiore della fascia "VRAM bassa" definita in sezione 9 (~2-6 GB). Nessun problema di compatibilità CUDA atteso: Ada Lovelace è pienamente supportata da tutte le build correnti.

---

## 3. Ambito (Scope)

### In ambito (v1)
- Estrazione testo da immagini e PDF, con accelerazione GPU quando disponibile
- Interfaccia desktop nativa per **Linux e Windows** (piattaforme prioritarie v1)
- Rilevamento automatico del backend GPU disponibile (CUDA/HIP/Metal/Vulkan) con fallback CPU (Tesseract) quando nessun backend GPU è utilizzabile
- Preset di modello OCR selezionabili in base alla VRAM rilevata a runtime
- Configurazione della sorgente del modello OCR: backend bundlato automatico (default), URL di un server `llama.cpp` esterno inserito manualmente, oppure nessun modello locale (solo fallback Tesseract)
- Salvataggio/copia del testo estratto

### Fuori ambito (v1)
- OCR tramite servizi cloud o API esterne (per qualunque motivo, anche come opzione)
- Training o fine-tuning di modelli
- Acceleratori non coperti da CUDA/HIP/Metal/Vulkan (NPU dedicate, TPU, ecc.) — valutabile in v2
- Versione mobile o web pubblica
- Editing avanzato del PDF di output (OCR searchable layer) — valutabile in v2
- Distribuzione tramite store applicativi (Microsoft Store, Mac App Store) — pacchetti installabili manualmente sufficienti per v1
- Supporto macOS (backend Metal) — rimandato a v2, non prioritario per v1

---

## 4. Requisiti funzionali (RF)

| ID | Requisito |
|---|---|
| RF1 | L'utente deve poter fornire un'immagine o un PDF tramite: file da disco, drag&drop, incolla da clipboard, screenshot integrato |
| RF2 | Il sistema deve poter applicare un preprocessing opzionale (deskew, crop, aumento contrasto) prima dell'inferenza — v1: resize anti-OOM + contrasto (deskew/crop in v1.1, vedi ADR-0006) |
| RF3 | Il sistema deve rilevare automaticamente il backend GPU disponibile sulla piattaforma corrente (CUDA su NVIDIA, HIP/ROCm su AMD, Metal su Apple Silicon, Vulkan come fallback cross-vendor) e usarlo per l'inferenza tramite `llama.cpp`/`mtmd` |
| RF4 | Se nessun backend GPU è disponibile/supportato o l'inferenza GPU fallisce, il sistema deve ricadere su un motore OCR CPU-only (Tesseract) senza bloccare l'utente |
| RF5 | Il testo estratto deve essere copiabile negli appunti e salvabile su file (.txt/.md minimo) |
| RF6 | Il sistema deve selezionare (o proporre) un preset di modello OCR GGUF adeguato alla VRAM rilevata, tra più fasce predefinite (vedi punto 9), e permettere di cambiarlo manualmente |
| RF7 | L'interfaccia deve indicare chiaramente quale motore/backend (CUDA, HIP, Metal, Vulkan o CPU) ha elaborato ciascun documento |
| RF8 | Il sistema deve gestire in modo esplicito i documenti multi-pagina (elaborazione sequenziale pagina per pagina) |
| RF9 | L'app deve rimanere pienamente utilizzabile (via fallback CPU) anche su macchine prive di GPU dedicata o con GPU non coperta da alcun backend supportato |
| RF10 | L'utente deve poter scegliere la sorgente del modello OCR tra tre modalità: (a) backend bundlato gestito automaticamente dall'app (RF3/RF6), (b) URL di un server `llama.cpp` esterno già in esecuzione, inserito manualmente, (c) nessun modello locale — solo fallback Tesseract, come scelta esplicita e non solo come degradazione automatica |

---

## 5. Requisiti non funzionali (RNF)

| ID | Requisito |
|---|---|
| RNF1 | **Privacy**: nessun dato (immagine o testo estratto) lascia la macchina locale nella configurazione di default (backend bundlato). Se l'utente configura manualmente un URL di server esterno (RF10b), l'app deve mostrare un avviso esplicito quando l'URL non punta a `localhost`/rete privata, dato che a quel punto la garanzia dipende da dove l'utente ha scelto di puntare |
| RNF2 | **Portabilità**: l'app deve funzionare su Linux (distribuzioni principali) e Windows 10/11, con almeno un percorso funzionante — GPU o CPU — su ciascuna. Supporto macOS (Apple Silicon) rimandato a v2 |
| RNF3 | **Modularità**: il motore di inferenza (backend) deve essere disaccoppiato dalla GUI, comunicando via API HTTP locale, per poter sostituire/aggiornare modello e backend senza toccare l'interfaccia |
| RNF4 | **Degradazione controllata**: in caso di VRAM insufficiente o backend GPU non disponibile, l'app deve fallire in modo gestito (messaggio chiaro + fallback CPU), mai crash silenzioso |
| RNF5 | **Tempo di risposta**: nessun requisito hard uniforme tra piattaforme/hardware così eterogenei; va misurato per-preset e comunicato all'utente, non promesso a priori |

---

## 6. Vincoli hardware

- L'app deve funzionare su un ventaglio molto eterogeneo di configurazioni: da GPU datate a bassa VRAM (macchina di riferimento, 4 GB) a GPU moderne con VRAM abbondante, fino all'assenza totale di GPU dedicata.
- La VRAM disponibile **non può essere assunta a build-time**: va rilevata a runtime (query del backend GPU attivo) per scegliere il preset di modello (RF6).
- Baseline empirica nota (macchina di riferimento, 4 GB): OOM già osservato con un modello 7B Q4_K_M a 24 layer offloaded — fissa il limite superiore indicativo per la fascia "VRAM bassa".
- Su Linux con GPU ibrida (Optimus/PRIME), l'app deve gestire esplicitamente la selezione della GPU dedicata invece di affidarsi al comportamento di default del sistema (evitando di alterare il profilo prime-select globale, che in passato ha causato un loop di login sulla macchina di riferimento).
- Su macchine senza GPU supportata da nessun backend, l'app deve operare interamente su CPU (Tesseract, ed eventualmente `llama.cpp` CPU-only per modelli molto piccoli) senza richiedere intervento manuale.

---

## 7. Vincoli software / compatibilità

- **Motivazione generale (non solo per la GPU di riferimento)**: gli stack Python/PyTorch legano la compatibilità GPU alla combinazione precisa di torch+CUDA/ROCm installata, e le build ufficiali riducono nel tempo il ventaglio di architetture supportate (è già successo con Maxwell/Pascal nelle build CUDA 12.8+/13.0). Per un'app pensata per girare su hardware eterogeneo e restare compatibile nel tempo, questo è un rischio di manutenzione **non accettabile come dipendenza critica** per il motore OCR primario.
- Il motore di inferenza primario **deve** essere `llama.cpp`/`llama-server` (via `mtmd` per i modelli OCR), che espone più backend nativi intercambiabili:

  | Backend | Vendor GPU | Piattaforme |
  |---|---|---|
  | CUDA | NVIDIA | Windows, Linux |
  | HIP / ROCm | AMD | Linux (principalmente) |
  | Metal | Apple Silicon | macOS |
  | Vulkan | NVIDIA / AMD / Intel (cross-vendor) | Windows, Linux |
  | CPU | — | Windows, macOS, Linux |

- **Vulkan va trattato come fallback GPU universale** quando il backend vendor-specifico non è disponibile o non è stato compilato per quella combinazione piattaforma/GPU.
- Per le piattaforme prioritarie v1 (Linux, Windows), i backend rilevanti sono: CUDA, HIP/ROCm (solo Linux), Vulkan, CPU. Metal (macOS) non richiede build in v1.
- **Strategia di distribuzione confermata**: pacchetto unico per piattaforma (Linux, Windows) che include tutti i binari `llama-server` rilevanti per quell'OS (CUDA, HIP/ROCm dove pertinente, Vulkan, CPU), con **selezione automatica a runtime** del binario corretto in base al backend rilevato — non installer separati per backend. Questa scelta riusa la stessa logica di rilevamento già richiesta da RF3, evita l'errore di selezione manuale del pacchetto sbagliato, e permette all'app di adattarsi da sola se l'hardware della macchina cambia, senza reinstallazione.
- Modelli OCR: distribuiti in GGUF con `mmproj` compatibile (es. dalla collezione `ggml-org` su Hugging Face: DeepSeek-OCR, PaddleOCR-VL, GLM-OCR, Dots.OCR, HunyuanOCR).
- **Template di prompt specifico per modello**: ogni modello OCR GGUF ha una struttura di prompt/chat-template propria (es. `--chat-template deepseek-ocr`). Il layer `core` deve trattarlo come configurazione per-modello, non come costante hardcoded.
- Il backend deve esporre un'API compatibile OpenAI (`/v1/chat/completions`), coerente col pattern già in uso per il server Qwen, su una **porta dedicata** separata da altri server LLM eventualmente in esecuzione.
- Tesseract (fallback CPU) non ha vincoli di compatibilità GPU: dipendenza a basso rischio, uguale su tutte le piattaforme.
- **Libreria per estrazione/rendering PDF confermata: `pypdfium2`** (binding Python per PDFium, il motore di rendering PDF di Chrome). Preferita a `pdf2image`/Poppler perché quest'ultimo richiede un binario di sistema esterno — su Windows va scaricato manualmente e aggiunto al PATH, una delle cause più comuni di errore in fase di setup/runtime. `pypdfium2` è invece un pacchetto pip auto-contenuto (nessuna dipendenza esterna) con wheel precompilate per Linux e Windows. Preferita anche a `PyMuPDF` (tecnicamente equivalente e anch'esso auto-contenuto) per la licenza: PDFium è permissiva, mentre PyMuPDF è AGPL-3.0 o a pagamento — meno compatibile con un'eventuale distribuzione non-AGPL dell'app.

---

## 8. Vincoli architetturali

Architettura a livelli, con l'aggiunta del rilevamento hardware/backend:

```
/backend        → istanza llama-server, con binario/backend selezionato
                  in base a piattaforma+GPU rilevata (CUDA/HIP/Metal/Vulkan/CPU)
/core           → orchestrazione: rilevamento hardware, scelta preset modello,
                  prompt/template per-modello, chiamata HTTP, parsing output
/preprocessing  → OpenCV, solo CPU (deskew, crop, contrasto)
/app            → GUI desktop (PyQt6/PySide6)
/fallback       → integrazione Tesseract via pytesseract
```

- La logica di rilevamento GPU/backend/VRAM deve vivere in `/core` (o in un modulo dedicato `/hwdetect`), **mai nella GUI**, per restare testabile e sostituibile.
- `/core` deve astrarre la **sorgente del modello OCR** in tre modalità intercambiabili dietro la stessa interfaccia client HTTP (RF10): backend bundlato (avviato/gestito da `/backend`), URL esterno inserito dall'utente, o nessuna sorgente (solo `/fallback`). La differenza tra le tre è solo *dove* punta il client, non il protocollo: essendo tutte API compatibili OpenAI, `/core` non necessita di logica diversa per modalità.
- `/core` non deve avere dipendenze dirette da un modello OCR specifico: i template di prompt sono dati esterni (config), non codice.
- `/app` comunica solo con `/core`, mai direttamente con `/backend` né con un URL esterno, per mantenere sostituibile motore, backend e sorgente di inferenza.

---

## 9. Vincoli sulla scelta del modello OCR

Invece di un budget VRAM fisso, si definiscono almeno tre fasce:

| Fascia | VRAM indicativa | Modello |
|---|---|---|
| CPU-only | GPU assente/non supportata | Nessun modello GPU: solo Tesseract |
| VRAM bassa | ~2–6 GB (es. macchina di riferimento) | Modello OCR dedicato 1B–4B, Q4_K_M o più aggressivo |
| VRAM media/alta | >6 GB | Modello OCR più grande o quantizzazione meno aggressiva, se disponibile |

**Modello di test/default confermato per la fascia VRAM bassa:** `ggml-org/GLM-OCR-GGUF:Q8_0` — 0,9B parametri, pesi Q8_0 ~950 MB + `mmproj` ~484 MB (~1,4 GB totali). Rientra ampiamente nel budget dei 4 GB della macchina di riferimento anche contando la KV cache.

Un modello è idoneo per qualunque fascia GPU solo se rispetta **tutti** i seguenti punti:
1. Disponibile in formato GGUF con `mmproj` per `llama.cpp`/`mtmd`
2. È un modello OCR dedicato, non una VLM general-purpose di grandi dimensioni (specialmente per la fascia bassa)
3. Ha una configurazione di prompt/chat-template documentata (non dedotta per analogia)
4. Rientra nel budget VRAM della fascia target, mmproj incluso

---

## 10. Rischi e mitigazioni

| Rischio | Mitigazione |
|---|---|
| OOM su immagini/pagine ad alta risoluzione | Resize/tiling dell'immagine in `/preprocessing` prima dell'invio, con limite massimo configurabile |
| GPU non utilizzata per errata configurazione Optimus (Linux) | Verifica esplicita all'avvio che `llama-server` stia usando la GPU dedicata attesa, non quella integrata |
| Superficie di test comunque ampia (2 OS prioritari × fino a 4 backend GPU: CUDA, HIP, Vulkan, CPU) | Build/matrice automatizzata dove possibile; test manuale approfondito solo sulla macchina di riferimento (Linux + CUDA) in v1, resto trattato come "best effort" (vedi punti aperti) |
| Driver Vulkan/HIP meno maturi di CUDA su alcune configurazioni | Fallback esplicito a CPU se l'inferenza GPU fallisce silenziosamente o produce output anomalo, mai un errore non gestito |
| Latenza alta su fallback CPU con documenti complessi | RF7 (indicare motore usato) + gestione aspettative, nessuna promessa di tempo di risposta uniforme |
| Aggiornamenti driver/CUDA/ROCm che rompono compatibilità | Pinning esplicito della versione di `llama.cpp` validata per ciascun backend, aggiornamento solo dopo test |

---

## 11. Criteri di accettazione (v1)

Stato verificato il 2026-09-16 (dettagli in `docs/architecture.md` §3):

- [x] L'app rileva automaticamente il backend GPU disponibile (o la sua assenza) e seleziona un preset di modello coerente con la VRAM rilevata
- [x] L'app estrae testo leggibile da almeno un'immagine di test tramite `ggml-org/GLM-OCR-GGUF:Q8_0` via `llama-server`, su almeno una combinazione piattaforma/backend verificata (macchina di riferimento: Linux + CUDA)
- [ ] La stessa estrazione funziona anche su Windows (macchina di riferimento: Acer Nitro ANV15-51, RTX 4050 Laptop GPU) con backend CUDA — best effort, non verificato in questa sessione
- [x] Su GPU assente o non supportata, l'estrazione avviene automaticamente via Tesseract senza intervento manuale — pipeline verificata via test; live Tesseract richiede il binario di sistema (`TESSERACT_LIVE=1`)
- [x] Nessuna chiamata di rete esterna viene effettuata durante l'elaborazione
- [x] Il sistema non va in crash su OOM o backend non disponibile: mostra un errore gestito e propone il fallback CPU
- [x] Il testo estratto è copiabile e salvabile su file
- [x] L'utente può scegliere tra backend bundlato, URL di server `llama.cpp` esterno, o nessun modello locale (solo Tesseract), e l'app avvisa esplicitamente se l'URL esterno non punta a `localhost`/rete privata
- [x] Il PDF in input viene gestito (rendering pagina-per-pagina) secondo l'approccio scelto (vedi punti aperti)

---

## 12. Punti aperti da chiarire prima dello sviluppo

- Modello di default per la fascia VRAM media/alta (quella bassa è coperta da `GLM-OCR-GGUF:Q8_0`, vedi punto 9)
