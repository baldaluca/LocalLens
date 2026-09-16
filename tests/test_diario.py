"""RED: Diario esecuzioni JSONL — un evento per riga, leggibile senza l'app."""

import json

from locallens.core.diario import avvia_job, percorso_diario


def _eventi(percorso):
    with open(percorso, encoding="utf-8") as f:
        return [json.loads(riga) for riga in f if riga.strip()]


def test_job_scrive_avvio_pagine_e_chiusura(tmp_path):
    diario = avvia_job(
        tmp_path,
        job_id="abc123",
        documento="Consigli LLM locali.pdf",
        modello="ggml-org/LightOnOCR-1B-1025-GGUF",
        sorgente="esterno",
        motore="esterno",
        preset_id="lighton-ocr-q8_0",
    )
    diario.registra_pagina(pagina_id=1, ms=40300, motore_usato="esterno", chars=1045)
    diario.registra_pagina(
        pagina_id=7,
        ms=31700,
        motore_usato="esterno",
        chars=159,
        nota="solo-boilerplate?",
    )
    diario.chiudi(stato="done")

    eventi = _eventi(diario.percorso)
    assert [e["evento"] for e in eventi] == [
        "job_avviato",
        "pagina",
        "pagina",
        "job_chiuso",
    ]
    assert eventi[0]["job_id"] == "abc123"
    assert eventi[0]["modello"] == "ggml-org/LightOnOCR-1B-1025-GGUF"
    assert eventi[1]["pagina_id"] == 1
    assert eventi[1]["ms"] == 40300
    assert eventi[1]["motore_usato"] == "esterno"
    assert eventi[1]["chars"] == 1045
    assert eventi[2]["nota"] == "solo-boilerplate?"
    assert eventi[-1]["stato"] == "done"
    assert all("ts" in e for e in eventi)


def test_engine_con_diario_registra_pagine_e_chiude(tmp_path):
    import json

    from locallens.core.diario import avvia_job
    from locallens.core.orchestrator import OcrEngine

    diario = avvia_job(tmp_path, job_id="eng1", documento="doc.pdf")
    eng = OcrEngine(
        infer=lambda pid, img: ("testo-pagina", "esterno"),
        fallback=lambda pid, img: "fb",
        sorgente="bundlato",
    )
    eng.submit_document([b"a", b"b"], diario=diario)
    with open(diario.percorso, encoding="utf-8") as f:
        eventi = [json.loads(r) for r in f if r.strip()]
    assert [e["evento"] for e in eventi] == [
        "job_avviato",
        "pagina",
        "pagina",
        "job_chiuso",
    ]
    assert eventi[1]["chars"] == len("testo-pagina")
    assert eventi[1]["motore_usato"] == "esterno"


def test_percorso_default_sotto_config_parent(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    p = percorso_diario("job9")
    assert p.parent.name == "esecuzioni"
    assert p.name == "job9.jsonl"
