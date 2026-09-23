"""Task1: verifica_health dialetto-aware — TDD."""

import urllib.error


def _chiama_api_tags_non_health(chiamate: list[str]) -> bool:
    return any("/api/tags" in c for c in chiamate) and not any(c.rstrip("/").endswith("/health") for c in chiamate)


def chiama_api_tags_non_health(chiamate: list[str]) -> bool:
    return _chiama_api_tags_non_health(chiamate)


def test_verifica_health_ollama_us_api_tags(monkeypatch):
    from locallens.core import rete

    chiamate = []

    def fake_urlopen(req, timeout=2):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if isinstance(req, str):
            url = req
        elif hasattr(req, "full_url"):
            url = req.full_url
        else:
            url = str(req)
        chiamate.append(url)
        # deve chiamare /api/tags, non /health
        assert "/api/tags" in chiamate[0], f"atteso /api/tags in {chiamate[0]}"
        assert "/health" not in chiamate[0], f"non deve chiamare /health: {chiamate[0]}"

        class Resp:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        return Resp()

    monkeypatch.setattr(rete.urllib.request, "urlopen", fake_urlopen)
    assert rete.verifica_health("http://127.0.0.1:11434/api/chat") is True
    assert chiama_api_tags_non_health(chiamate)


def test_verifica_health_openai_prova_v1_models(monkeypatch):
    from locallens.core import rete

    def fake_urlopen(req, timeout=2):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if isinstance(req, str):
            url = req
        elif hasattr(req, "full_url"):
            try:
                url = req.full_url
            except Exception:
                url = str(req)
        else:
            url = str(req)
        if url.endswith("/v1/models"):
            raise urllib.error.HTTPError(url, 404, "not found", {}, None)

        class Resp:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        return Resp()

    monkeypatch.setattr(rete.urllib.request, "urlopen", fake_urlopen)
    assert rete.verifica_health("http://127.0.0.1:1234/v1/chat/completions") is True
