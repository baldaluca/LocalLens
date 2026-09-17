# Servizi esterni open e gratuiti di riserva — research

Ticket: `02-servizi-esterni-open` (effort fallback-senza-senso).
Domanda: se i segnali locali risultano insufficienti, quali servizi esterni
open-source e gratuiti (self-hostabili o pacchettizzabili offline, NIENTE a
pagamento) potrebbero giudicare se un'Estrazione è senza senso rispetto alla
Pagina?

Principio invariante (da `map.md`): il default resta tutto locale (segnali da
testo Estrazione + byte Pagina in millisecondi, politica dubbio→Tesseract).
Quanto sotto è solo riserva, da attivare soltanto se il locale risulta
insufficiente sul banco di 20-30 Pagine reali.

Metodo: sole fonti primarie (repo ufficiali, model card, docs di installazione).
Ogni affermazione di licenza/costo/peso cita la fonte.

## 1. SigLIP via Hugging Face `transformers` — punteggio di grounding Pagina↔Estrazione

Cosa fa qui: unico candidato cross-modale vero — misura la similarità
Pagina (byte immagine) ↔ testo Estrazione e segnala allucinazioni fluenti,
riassunti al posto di trascrizione e troncamenti che i segnali solo-testo non
vedono. Uso: `zero-shot-image-classification` / `SiglipModel` + soglia
tarata sul banco.

- Licenza: Apache-2.0 — frontmatter `license: apache-2.0` delle model card
  ufficiali `google/siglip-base-patch16-224`, `google/siglip-large-patch16-384`,
  `google/siglip-so400m-patch14-384`
  (fonte: https://huggingface.co/google/siglip-base-patch16-224/blob/main/README.md
  e omonime per large/so400m).
- Integrazione: `transformers` (`SiglipModel`, `AutoProcessor`, pipeline
  `zero-shot-image-classification`; supporto `device_map="auto"`,
  quantizzazione bitsandbytes, `attn_implementation`)
  (fonte: https://huggingface.co/docs/transformers/main/model_doc/siglip).
  Pacchettizzabile offline: checkpoint scaricato una volta, poi
  `from_pretrained` da path locale (pattern documentato per i pesi CLIP-like;
  fonte: README `mlfoundations/open_clip`).
- Costo: 0 €, nessun canone, nessun invio a terzi se eseguito in locale.
- Privacy Documento: ottima in configurazione self-hosted/offline — la Pagina
  non lascia il PC. (Rischio solo se si usano Inference Provider remoti di
  Hugging Face: per questo ticket restano esclusi.)
- Latenza batch: decine–centinaia di ms per Pagina su GPU, ~1 s su CPU con
  variante base (224px); la variante 384px/so400m è più accurata ma più pesante.
  Stima dimensionata sul banco, non da fonte primaria — da misurare.
- Peso integrazione: medio-basso se `transformers`+torch è già nel progetto;
  medio-alto altrimenti (torch (~GB), pesi ~400 MB–1 GB a seconda del checkpoint).
  Alternativa equivalente: OpenCLIP (codice con licenza permissiva stile MIT —
  fonte: https://github.com/mlfoundations/open_clip/blob/main/LICENSE) o
  CLIP originale OpenAI (MIT — fonte: https://github.com/openai/CLIP/).
  SigLIP è preferito per licenza Apache-2.0 esplicita per checkpoint e supporto
  nativo in `transformers`.
- Verdetto: **prima riserva se il locale non basta**, perché è l'unica che
  confronta davvero Estrazione e Pagina. Attivazione consigliata: solo sui casi
  dubbi del giudizio locale (non su ogni Pagina), con soglia tarata sul banco.

## 2. fastText Language Identification (`lid.176`) — segnale lingua sbagliata

Cosa fa qui: rileva la lingua dell'Estrazione in millisecondi; Estrazione in
lingua diversa da quella attesa della Pagina = anomalia (una delle classi
target del ticket).

- Licenza codice: MIT — fonte: https://github.com/facebookresearch/fastText/blob/master/LICENSE
  (`Copyright (c) 2016-present, Facebook, Inc.` + testo MIT).
- Licenza pesi `lid.176.bin` / `lid.176.ftz`: Creative Commons
  Attribuzione-CondividiAlloStessoModo 3.0; due varianti: `lid.176.bin`
  (126 MB, più accurato) e `lid.176.ftz` (917 kB compresso)
  (fonte: https://github.com/facebookresearch/fastText/blob/master/docs/language-identification.md).
  Attribuzione richiesta se ridistribuito — verificare con il vincolo di
  bundling del progetto.
- Stato progetto: repository archiviato in sola lettura il 19 mar 2024
  (fonte: banner sulla pagina LICENSE di cui sopra) — nessun fix futuro;
  wrapper community attivi ma da validare (es. `zafercavdar/fasttext-langdetect`,
  MIT). In alternativa il binario `fasttext` si compila dai sorgenti.
- Costo: 0 €. Privacy: ottima — inferenza interamente offline sul testo
  Estrazione (mai la Pagina, mai rete).
- Latenza batch: millisecondi per Estrazione, anche con `.ftz`; throughput
  migliaia di testi/min su CPU. (Ordine di grandezza noto dal design
  fastText; tarare sul banco.)
- Peso integrazione: minimo — una dipendenza nativa o un wrapper + file modello
  da ~1 MB (`.ftz`) a 126 MB (`.bin`).
- Verdetto: **riserva quasi-locale ideale** — così leggera da poter diventare
  segnale stabile (non solo riserva) per la classe "lingua sbagliata". Usarla
  quando il giudizio locale non distingue codici lingua simili o testi corti.

## 3. LanguageTool core self-hosted — segnale fluenza/nonsenso grammaticale

Cosa fa qui:server locale di proofreading (`/v2/check`) che conta
errori ortografici/grammaticali per carattere; densità di errori anomala =
Estrazione degenere o senza senso (allucinazione fluente esclusa — resta
coperta da SigLIP, §1).

- Licenza: LanguageTool core sotto LGPL 2.1 o successiva
  (fonte: campo License `GNU Lesser General Public License v2.1` + README di
  https://github.com/languagetool-org/languagetool/ — "freely available under
  the LGPL 2.1 or later"). Implica obblighi di copyleft debole (dynamic
  linking + distribuzione sorgenti modifiche alla libreria): da validare con i
  vincoli di distribuzione di LocalLens prima di bundlare.
- Self-hosting: immagini Docker community (`meyayl/docker-languagetool`,
  `erikvl87/docker-languagetool`, entrambe LGPL-2.1 — fonte: rispettive pagine
  GitHub); server su `localhost:8081/8010`, nessuna UI né autenticazione
  inclusa di default. Richiede Java 17 + Maven per build da sorgenti
  (fonte: README LanguageTool).
- Costo: 0 € in self-hosting (il modello freemium/premium del sito
  https://languagetool.org/ riguarda il servizio cloud, escluso da questo ticket).
- Privacy Documento: buona in configurazione localhost — viaggia solo il testo
  Estrazione verso `127.0.0.1`, mai la Pagina, mai rete esterna. (Il cloud
  languagetool.org è escluso proprio per privacy.)
- Latenza batch: decine–centinaia di ms per Estrazione via HTTP locale;
  container con heap di default `-Xmx2G`, immagine ~1–2 GB
  (fonte: setup community `loglux/languagetool-docker` — valori da confermare
  sul banco perché non ufficiali).
- Peso integrazione: medio-alto — runtime Java + container/daemon accanto
  all'app desktop; sforzo giustificato solo come riserva batch, non nel path
  veloce per-Pagina.
- Verdetto: **riserva batch/offline** per testi lunghi dove i segnali locali
  (ripetizioni, entropia) sono inconcludenti. Non usarla nel path interattivo;
  in dubbio resta dubbio→Tesseract.

## 4. PaddleOCR (PP-OCRv5) — secondo lettore indipendente

Cosa fa qui: seconda Estrazione indipendente dalla stessa Pagina; disaccordo
forte tra Estrazione VLM e Estrazione PaddleOCR (similarità testuale bassa a
fronte di confidenza OCR alta) = segnale di allucinazione/riassunto. È la
riserva più vicina concettualmente al fallback `cpu-tesseract` già previsto.

- Licenza: Apache 2.0 per il progetto
  (fonte: campo License + sezione `## 📄 License` di
  https://github.com/PaddlePaddle/PaddleOCR?tab=readme-ov-file e testo in
  https://github.com/paddlepaddle/paddleocr/blob/HEAD/LICENSE).
  Modelli distribuiti su Hugging Face e ModelScope, tier tiny (1.5M) / small
  (7.7M) / medium (34.5M…) per scenari edge/mobile
  (fonte: stessa README). Da verificare per singolo checkpoint prima di bundlare.
- Integrazione: `pip install paddleocr` / da sorgenti, deployment locale
  documentato per serie PP-OCR / PaddleOCR-VL / PP-StructureV3
  (fonte: https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/installation.en.md
  e README — Step 2 Local Deployment). Pacchettizzabile offline dopo primo
  download pesi.
- Costo: 0 € self-hosted. (L'API gratuita fino a 20.000 pagine/giorno citata su
  https://www.paddleocr.ai/main/en/index.html è servizio remoto: esclusa per
  privacy in questo ticket.)
- Privacy Documento: ottima in locale — la Pagina resta sul PC. Solo testo e
  punteggi lasciano eventualmente il processo, mai la rete.
- Latenza batch: secondi per Pagina su CPU, decine–centinaia di ms su GPU con
  modelli tiny/small; più lenta di Tesseract ma più accurata su layout difficili.
  (Ordini di grandezza da confermare sul banco; la documentazione promette
  supporto CUDA e upgrade PP-OCRv5 — fonte: README.)
- Peso integrazione: alto — framework PaddlePaddle + pesi; conflitti di
  dipendenze possibili con ambienti torch/transformers (la stessa guida
  installazione raccomanda env pulito). Da isolare in processo/servizio opzionale.
- Verdetto: **riserva di seconda opinione** quando SigLIP (§1) non è disponibile
  o il disaccordo va spiegato all'utente con testo alternativo mostrabile.
  Non sostituisce Tesseract come fallback di default (più leggero); la si usa in
  batch sui soli casi dubbi.

## 5. Surya OCR — valutata e SCARTATA (licenza pesi non open)

- Codice: Apache 2.0, MA pesi sotto "modified AI Pubs Open Rail-M license
  (free for research, personal use, and startups under $5M funding/revenue);
  For broader commercial licensing … visit our pricing page"
  (fonte: https://github.com/datalab-to/surya e
  https://pypi.org/project/surya-ocr/). Non è open-source piena né gratuita
  senza condizioni commerciali → viola il vincolo del ticket ("NIENTE a
  pagamento", open-source). **Non usarla** finché i pesi restano sotto Rail-M
  con soglia commerciale; rivalutare solo a cambio licenza.

## Raccomandazione operativa (riserva, non default)

1. Se il banco mostra che il locale non copre allucinazioni fluenti/riassunti:
   attivare **SigLIP §1 solo sui dubbi**, soglia tarata sul banco.
2. **fastText §2** come segnale lingua quasi-gratuito (unico con peso ~1 MB).
3. **LanguageTool §3** e **PaddleOCR §4** solo batch sui dubbi residui,
   fuori dal path veloce; dubbio persistente → Tesseract (politica invariata).
4. **Surya esclusa** per licenza pesi.

Fonti primarie consultate: model card HF `google/siglip-*-*` (licenza Apache-2.0);
docs `transformers` SigLIP; `open_clip` LICENSE + README; `openai/CLIP` (MIT);
`facebookresearch/fastText` LICENSE (MIT) + `docs/language-identification.md`
(CC-BY-SA 3.0, pesi 126 MB/917 kB, repo archiviato); `languagetool-org/languagetool`
(LGPL-2.1+, Docker community, requisiti Java 17); `PaddlePaddle/PaddleOCR`
LICENSE Apache-2.0 + docs installazione + homepage API/limiti; `datalab-to/surya`
README + PyPI (licenza pesi Rail-M con soglia $5M) — tutti link citati sopra.
