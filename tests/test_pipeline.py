"""RED: pipeline Pagina-per-Pagina con retry e fallback automatico."""

from locallens.core.pipeline import InferenzaError, elabora_pagine


def test_successo_backend_registra_motore():
    def infer(pagina_id, _img):
        return ("ciao", "cuda")

    def fallback(pagina_id, _img):
        raise AssertionError("fallback non deve scattare")

    out = elabora_pagine([b"img1"], infer=infer, fallback=fallback, sorgente="bundlato")
    assert len(out) == 1
    assert out[0].testo == "ciao"
    assert out[0].motore_usato == "cuda"
    assert out[0].pagina_id == 1


def test_un_fallimento_poi_retry_ok():
    chiamate = []

    def infer(pagina_id, _img):
        chiamate.append(pagina_id)
        if len(chiamate) == 1:
            raise InferenzaError("OOM simulato")
        return ("ok-dopo-retry", "cuda")

    def fallback(pagina_id, _img):
        raise AssertionError("fallback non deve scattare dopo retry riuscito")

    out = elabora_pagine([b"img1"], infer=infer, fallback=fallback, sorgente="bundlato")
    assert out[0].testo == "ok-dopo-retry"
    assert len(chiamate) == 2


def test_doppio_fallimento_va_in_fallback_con_badge():
    def infer(pagina_id, _img):
        raise InferenzaError("backend giu'")

    def fallback(pagina_id, _img):
        return "testo-cpu"

    out = elabora_pagine([b"img1"], infer=infer, fallback=fallback, sorgente="bundlato")
    assert out[0].testo == "testo-cpu"
    assert out[0].motore_usato == "cpu-tesseract"
    assert "backend giu" in (out[0].nota or "")


def test_output_vuoto_trattato_come_fallimento():
    def infer(pagina_id, _img):
        return ("   ", "vulkan")

    def fallback(pagina_id, _img):
        return "recuperato"

    out = elabora_pagine([b"img1"], infer=infer, fallback=fallback, sorgente="bundlato")
    assert out[0].motore_usato == "cpu-tesseract"
    assert out[0].testo == "recuperato"


def test_sorgente_nessuno_salata_backend():
    chiamate = []

    def infer(pagina_id, _img):
        chiamate.append(pagina_id)
        return ("mai", "cuda")

    def fallback(pagina_id, _img):
        return "solo-cpu"

    out = elabora_pagine([b"a", b"b"], infer=infer, fallback=fallback, sorgente="nessuno")
    assert chiamate == []
    assert [e.testo for e in out] == ["solo-cpu", "solo-cpu"]
    assert all(e.motore_usato == "cpu-tesseract" for e in out)


def test_timeout_non_ritentato():
    """Timeout >120s su 960M: ritentare raddoppia il danno e intasa il server."""
    from urllib.error import URLError

    chiamate = []

    def infer(pagina_id, _img):
        chiamate.append(pagina_id)
        raise InferenzaError("chiamata chat fallita: timed out") from URLError(
            TimeoutError()
        )

    def fallback(pagina_id, _img):
        return "fb-veloce"

    out = elabora_pagine([b"img1"], infer=infer, fallback=fallback, sorgente="bundlato")
    assert len(chiamate) == 1
    assert out[0].testo == "fb-veloce"
    assert out[0].motore_usato == "cpu-tesseract"
    assert "timed out" in (out[0].nota or "")


def test_ferma_interrompe_batch():
    chiamate = []

    def infer(pagina_id, _img):
        chiamate.append(pagina_id)
        return ("t", "cuda")

    out = elabora_pagine(
        [b"a", b"b", b"c"],
        infer=infer,
        fallback=lambda p, i: "fb",
        sorgente="bundlato",
        ferma=lambda: len(chiamate) >= 1,
    )
    assert [e.pagina_id for e in out] == [1]


def test_batch_non_si_interrompe_su_fallback():
    def infer(pagina_id, _img):
        if pagina_id == 1:
            raise InferenzaError("boom")
        return (f"p{pagina_id}", "cuda")

    def fallback(pagina_id, _img):
        return "fb1"

    out = elabora_pagine([b"a", b"b"], infer=infer, fallback=fallback, sorgente="bundlato")
    assert out[0].motore_usato == "cpu-tesseract"
    assert out[1].testo == "p2"


def test_loop_frase_breve_va_in_fallback():
    """REGRESSION test2/Pagina 3: 'No copying.' x N sfuggiva al filtro len>10."""
    loop = " ".join(["No copying."] * 200)

    def infer(pagina_id, _img):
        return (loop, "esterno")

    def fallback(pagina_id, _img):
        return "recuperato-tesseract"

    out = elabora_pagine([b"img1"], infer=infer, fallback=fallback, sorgente="bundlato")
    assert out[0].motore_usato == "cpu-tesseract"
    assert out[0].testo == "recuperato-tesseract"
    assert "loop" in (out[0].nota or "")


def test_eco_prompt_va_in_fallback():
    """REGRESSION test2/Pagine 6,10: eco 'Transcribe the document...'."""
    eco = "Transcribe the document text exactly. No commentary. Career Prep " + " ".join(
        f"frase diversa numero {i} con parole varie." for i in range(60)
    )

    def infer(pagina_id, _img):
        return (eco, "esterno")

    def fallback(pagina_id, _img):
        return "recuperato-tesseract"

    out = elabora_pagine([b"img1"], infer=infer, fallback=fallback, sorgente="bundlato")
    assert out[0].motore_usato == "cpu-tesseract"
    assert out[0].testo == "recuperato-tesseract"
    assert "eco del prompt" in (out[0].nota or "")


def test_loop_corto_sotto_500_va_in_fallback():
    """Buco guardia n<500: loop di 360 char sfuggiva a tutti i controlli."""
    loop = " ".join(["No copying."] * 30)
    assert len(loop) < 500

    def infer(pagina_id, _img):
        return (loop, "esterno")

    def fallback(pagina_id, _img):
        return "recuperato-tesseract"

    out = elabora_pagine([b"img1"], infer=infer, fallback=fallback, sorgente="bundlato")
    assert out[0].motore_usato == "cpu-tesseract"
    assert "loop" in (out[0].nota or "")


def test_lingua_inattesa_va_in_fallback():
    """Estrazione in inglese su Documento italiano: segnale stopword EN-IT."""
    inglese = (
        "The quarterly report shows revenue growth across all regions. "
        "The board approved the budget for the next fiscal year. "
        "Operating costs remained stable while hiring continued in engineering and sales. "
        "The company expects stronger demand in the second half of the year. "
        "Cash flow from operations covered capital expenditure and debt repayment. "
        "Management will present updated guidance during the next earnings call with analysts and investors."
    )

    def infer(pagina_id, _img):
        return (inglese, "esterno")

    def fallback(pagina_id, _img):
        return "recuperato-tesseract"

    out = elabora_pagine([b"img1"], infer=infer, fallback=fallback, sorgente="bundlato")
    assert out[0].motore_usato == "cpu-tesseract"
    assert "lingua" in (out[0].nota or "")


def test_marcatore_forte_riassunto_va_in_fallback():
    """Riassunto invece di trascrizione: 'In sintesi' da solo basta."""
    testo = (
        "In sintesi, il documento descrive un percorso di carriera con tabelle "
        "e sezioni tecniche. Il contenuto copre streaming, governance e domande "
        "per il colloquio finale con il team della piattaforma dati."
    )

    def infer(pagina_id, _img):
        return (testo, "esterno")

    def fallback(pagina_id, _img):
        return "recuperato-tesseract"

    out = elabora_pagine([b"img1"], infer=infer, fallback=fallback, sorgente="bundlato")
    assert out[0].motore_usato == "cpu-tesseract"


def test_marcatore_debole_solo_non_scarta():
    """'il documento' isolato in testo buono: 0.5 punti, sotto soglia."""
    testo = (
        "Career Prep — Piano di preparazione al colloquio. La tabella mostra "
        "le competenze richieste per il ruolo e il documento illustra il percorso previsto."
    )

    def infer(pagina_id, _img):
        return (testo, "esterno")

    def fallback(pagina_id, _img):
        raise AssertionError("fallback non deve scattare su segnale debole isolato")

    out = elabora_pagine([b"img1"], infer=infer, fallback=fallback, sorgente="bundlato")
    assert out[0].motore_usato == "esterno"


def test_troncamento_solo_non_scarta_ma_con_debole_si():
    """Finale monco (0.5) da solo non basta; con marcatore debole (0.5+0.5) sì."""
    base = (
        "Career Prep — Piano di preparazione al colloquio. La tabella mostra "
        "le competenze richieste per il ruolo e il documento illustra il percorso"
    )
    solo_monco = base.replace("il documento illustra", "la guida descrive") + " e"

    def infer_solo(pagina_id, _img):
        return (solo_monco, "esterno")

    out = elabora_pagine(
        [b"img1"],
        infer=infer_solo,
        fallback=lambda p, i: (_ for _ in ()).throw(AssertionError("no fallback")),
        sorgente="bundlato",
    )
    assert out[0].motore_usato == "esterno"

    con_debole = base + " e"

    def infer_combo(pagina_id, _img):
        return (con_debole, "esterno")

    def fallback(pagina_id, _img):
        return "recuperato-tesseract"

    out = elabora_pagine([b"img1"], infer=infer_combo, fallback=fallback, sorgente="bundlato")
    assert out[0].motore_usato == "cpu-tesseract"
    assert "tronca" in (out[0].nota or "")


def test_footer_pagina_non_e_troncamento():
    """'Pagina 2 di 10' finale non è un troncamento: nessuna parola a metà."""
    testo = (
        "Sezione 2 — Diagnosi della posizione e pilastri chiave. "
        "Il ruolo richiede esperienza su pipeline ETL e modellazione dati.\n\nPagina 2 di 10"
    )

    def infer(pagina_id, _img):
        return (testo, "esterno")

    def fallback(pagina_id, _img):
        raise AssertionError("il footer non deve scattare come troncamento")

    out = elabora_pagine([b"img1"], infer=infer, fallback=fallback, sorgente="bundlato")
    assert out[0].motore_usato == "esterno"


def test_fallback_vuoto_segnalato_in_nota():
    """Se anche Tesseract non legge nulla, la nota lo dice (mai silenzio)."""

    def infer(pagina_id, _img):
        raise InferenzaError("backend giu'")

    def fallback(pagina_id, _img):
        return "   "

    out = elabora_pagine([b"img1"], infer=infer, fallback=fallback, sorgente="bundlato")
    assert out[0].motore_usato == "cpu-tesseract"
    assert "fallback vuoto" in (out[0].nota or "")


def test_contesto_bilingue_non_scarta_inglese_fedele():
    """Crisi-2 P3: inglese sorgente con attese it+en resta esterno."""
    inglese = (
        "Supply contract n. 88 between Gamma Trasporti and Paolo Riva. "
        "The quarterly report shows revenue growth across all regions. "
        "The board approved the budget for the next fiscal year. "
        "Cash flow from operations covered capital expenditure and debt repayment. "
        "The company expects stronger demand in the second half of the year."
    )

    def infer(pagina_id, _img):
        return (inglese, "esterno")

    def fallback(pagina_id, _img):
        raise AssertionError("fedele bilingue non deve scattare")

    out = elabora_pagine(
        [b"img1"], infer=infer, fallback=fallback,
        sorgente="bundlato", lingue_attese=("it", "en"),
    )
    assert out[0].motore_usato == "esterno"


def test_contesto_soglia_loop_accetta_righe_legittime():
    """Crisi-2 P2: 8 righe identiche legittime con soglia 9 restano esterno."""
    righe = ["Verbale seggio n. 14, apertura ore 8:00."]
    righe += ["Presente - delega verificata - documento valido - scheda consegnata."] * 8
    righe += ["Chiusura ore 19:00, schede scrutinate 214."]
    testo = "\n".join(righe)

    def infer(pagina_id, _img):
        return (testo, "esterno")

    def fallback(pagina_id, _img):
        raise AssertionError("ripetizione legittima non deve scattare")

    out = elabora_pagine(
        [b"img1"], infer=infer, fallback=fallback,
        sorgente="bundlato", soglia_righe_loop=9,
    )
    assert out[0].motore_usato == "esterno"


def test_contesto_ignora_eco_istruzioni_stampate():
    """Crisi-2 P1: eco stampata nella sorgente con ignora_eco resta esterno."""
    testo = (
        "Transcribe the document text exactly. No commentary. "
        "Il sottoscritto Mario Rossi chiede il certificato di residenza storica. "
        "Allega documento di identita e marca da bollo da sedici euro."
    )

    def infer(pagina_id, _img):
        return (testo, "esterno")

    def fallback(pagina_id, _img):
        raise AssertionError("eco stampata nota non deve scattare")

    out = elabora_pagine(
        [b"img1"], infer=infer, fallback=fallback,
        sorgente="bundlato", ignora_eco=True,
    )
    assert out[0].motore_usato == "esterno"


def test_anomalia_fail_fast_senza_retry():
    """P4 densa: loop al 1° tentativo → fallback diretto, 1 sola infer (no 2° retry)."""
    chiamate = []
    loop = " ".join(["No copying."] * 200)

    def infer(pagina_id, _img):
        chiamate.append(pagina_id)
        return (loop, "esterno")

    def fallback(pagina_id, _img):
        return "recuperato-tesseract"

    out = elabora_pagine([b"img1"], infer=infer, fallback=fallback, sorgente="bundlato")
    assert out[0].motore_usato == "cpu-tesseract"
    assert len(chiamate) == 1
    assert "fail-fast" in (out[0].nota or "")


def test_output_vuoto_mantiene_retry():
    """Vuoto forse transitorio: retry conservato, 2 infer prima del fallback."""
    chiamate = []

    def infer(pagina_id, _img):
        chiamate.append(pagina_id)
        if len(chiamate) == 1:
            return ("   ", "esterno")
        return ("ok-dopo-retry", "esterno")

    def fallback(pagina_id, _img):
        raise AssertionError("retry riuscito, fallback non deve scattare")

    out = elabora_pagine([b"img1"], infer=infer, fallback=fallback, sorgente="bundlato")
    assert out[0].testo == "ok-dopo-retry"
    assert len(chiamate) == 2


def test_fallback_dopo_anomalia_conserva_testo_scartato():
    """Audit: il testo VLM scartato resta sull'Estrazione per il diario."""
    loop = "riga ripetuta identica per il loop del modello\n" * 6

    def infer(pagina_id, _img):
        return (loop, "esterno")

    def fallback(pagina_id, _img):
        return "recuperato-tesseract"

    out = elabora_pagine([b"img1"], infer=infer, fallback=fallback, sorgente="bundlato")
    assert out[0].motore_usato == "cpu-tesseract"
    assert out[0].scartato == loop


def test_testo_scartato_troncato_a_2000():
    """Il diario non si gonfia: scartato troncato a 2000 char."""
    loop = "riga ripetuta identica per il loop del modello\n" * 200

    def infer(pagina_id, _img):
        return (loop, "esterno")

    def fallback(pagina_id, _img):
        return "recuperato-tesseract"

    out = elabora_pagine([b"img1"], infer=infer, fallback=fallback, sorgente="bundlato")
    assert len(out[0].scartato) == 2000
    assert loop.startswith(out[0].scartato)


def test_successo_non_ha_scartato():
    def infer(pagina_id, _img):
        return ("testo pulito di trascrizione", "cuda")

    def fallback(pagina_id, _img):
        raise AssertionError("fallback non deve scattare")

    out = elabora_pagine([b"img1"], infer=infer, fallback=fallback, sorgente="bundlato")
    assert out[0].scartato is None


def test_fallback_debole_segnalato_in_nota():
    """Quality-gate: Tesseract quasi vuoto (ma non vuoto) → avviso in nota."""
    def infer(pagina_id, _img):
        raise InferenzaError("backend giu'")

    def fallback(pagina_id, _img):
        return "  ab  "

    out = elabora_pagine([b"img1"], infer=infer, fallback=fallback, sorgente="bundlato")
    assert out[0].testo == "  ab  "
    assert "fallback debole" in (out[0].nota or "")


def test_fallback_sostanzioso_nessun_avviso():
    def infer(pagina_id, _img):
        raise InferenzaError("backend giu'")

    def fallback(pagina_id, _img):
        return "una trascrizione decente di parecchie parole vere"

    out = elabora_pagine([b"img1"], infer=infer, fallback=fallback, sorgente="bundlato")
    assert "debole" not in (out[0].nota or "")


def test_lingua_italiana_inattesa_con_attesa_en_va_in_fallback():
    """FIX 7: testo tutto-italiano con lingue_attese=('en',) deve essere anomalo."""
    italiano = (
        "La relazione trimestrale mostra la crescita dei ricavi con una distribuzione capillare. "
        "Il consiglio ha approvato il bilancio per il prossimo esercizio con il voto dei presenti. "
        "I costi operativi sono rimasti stabili mentre le assunzioni sono continuate con regolarita. "
        "La societa prevede una domanda piu sostenuta nella seconda parte quando il mercato riparte. "
        "Il flusso di cassa copre gli investimenti con margini solidi e riduce il debito. "
        "La direzione presentera le nuove linee guida durante il prossimo incontro con gli analisti e gli investitori."
    )

    def infer(pagina_id, _img):
        return (italiano, "esterno")

    def fallback(pagina_id, _img):
        return "recuperato-tesseract"

    out = elabora_pagine(
        [b"img1"], infer=infer, fallback=fallback,
        sorgente="bundlato", lingue_attese=("en",),
    )
    assert out[0].motore_usato == "cpu-tesseract"
    assert "lingua" in (out[0].nota or "")


def test_lingua_inglese_inattesa_con_attesa_it_esplicita_va_in_fallback():
    """FIX 7 simmetrico: testo inglese con lingue_attese=('it',) esplicita resta anomalo."""
    inglese = (
        "The quarterly report shows revenue growth across all regions. "
        "The board approved the budget for the next fiscal year. "
        "Operating costs remained stable while hiring continued in engineering and sales. "
        "The company expects stronger demand in the second half of the year. "
        "Cash flow from operations covered capital expenditure and debt repayment. "
        "Management will present updated guidance during the next earnings call with analysts and investors."
    )

    def infer(pagina_id, _img):
        return (inglese, "esterno")

    def fallback(pagina_id, _img):
        return "recuperato-tesseract"

    out = elabora_pagine(
        [b"img1"], infer=infer, fallback=fallback,
        sorgente="bundlato", lingue_attese=("it",),
    )
    assert out[0].motore_usato == "cpu-tesseract"
    assert "lingua" in (out[0].nota or "")
