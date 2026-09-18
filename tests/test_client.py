"""RED: client HTTP OpenAI-compatibile. Prompt dal preset, mai hardcoded."""

import pytest

from locallens.core.client import (
    InferenzaError,
    build_chat_payload,
    invia_chat,
    parse_chat_text,
)


def test_payload_contiene_immagine_e_prompt_preset():
    p = build_chat_payload(immagine_b64="QUJD", prompt_system="Trascrici.", modello="glm-ocr")
    assert p["model"] == "glm-ocr"
    assert p["max_tokens"] == 2048  # cap anti-runaway: mai generazione illimitata
    msgs = p["messages"]
    assert msgs[0] == {"role": "system", "content": "Trascrici."}
    user_parts = msgs[1]["content"]
    assert {"type": "text", "text": "Trascrici."} in user_parts
    assert {
        "type": "image_url",
        "image_url": {"url": "data:image/png;base64,QUJD"},
    } in user_parts


def test_payload_cap_override():
    p = build_chat_payload(
        immagine_b64="QUJD", prompt_system="x", modello="m", max_tokens=512
    )
    assert p["max_tokens"] == 512


def test_timeout_default_600():
    import inspect

    assert inspect.signature(invia_chat).parameters["timeout"].default == 600


def test_parse_content_stringa():
    resp = {"choices": [{"message": {"content": " testo "}}]}
    assert parse_chat_text(resp) == " testo "


def test_parse_content_a_parti():
    resp = {
        "choices": [
            {"message": {"content": [{"type": "text", "text": "a"}, {"type": "text", "text": "b"}]}}
        ]
    }
    assert parse_chat_text(resp) == "ab"


def test_parse_choices_vuote_sollevato():
    with pytest.raises(InferenzaError):
        parse_chat_text({"choices": []})


def test_invia_mappa_errore_http():
    def post_fallita(url, payload):
        raise OSError("conn refused")

    with pytest.raises(InferenzaError):
        invia_chat("http://127.0.0.1:8011", {"model": "x"}, post=post_fallita)


def test_invia_ok():
    def post_ok(url, payload):
        assert url.endswith("/v1/chat/completions")
        return {"choices": [{"message": {"content": "ok"}}]}

    assert invia_chat("http://127.0.0.1:8011", {"model": "x"}, post=post_ok) == "ok"


def test_invia_chat_con_token_mette_bearer(monkeypatch):
    import json
    import locallens.core.client as client

    viste = {}

    class Risposta:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode()

    def urlopen_finto(req, timeout=None):
        viste["auth"] = req.get_header("Authorization")
        return Risposta()

    monkeypatch.setattr("urllib.request.urlopen", urlopen_finto)
    assert client.invia_chat("http://x", {"model": "m"}, token="segreto") == "ok"
    assert viste["auth"] == "Bearer segreto"


def test_invia_chat_senza_token_nessun_header(monkeypatch):
    import json
    import locallens.core.client as client

    viste = {}

    class Risposta:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode()

    def urlopen_finto(req, timeout=None):
        viste["auth"] = req.get_header("Authorization")
        return Risposta()

    monkeypatch.setattr("urllib.request.urlopen", urlopen_finto)
    client.invia_chat("http://x", {"model": "m"})
    assert viste["auth"] is None
