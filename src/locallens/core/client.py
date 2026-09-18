"""Client HTTP per /v1/chat/completions. Prompt/modello dal preset, mai hardcoded."""
import json
import urllib.request
from collections.abc import Callable

from locallens.core.errori import InferenzaError


def build_chat_payload(
    immagine_b64: str, prompt_system: str, modello: str, max_tokens: int = 2048
) -> dict:
    return {
        "model": modello,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": prompt_system},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_system},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{immagine_b64}"},
                    },
                ],
            },
        ],
    }


def parse_chat_text(risposta: dict) -> str:
    try:
        content = risposta["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise InferenzaError(f"risposta chat non valida: {e}") from e
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(p.get("text", "") for p in content if isinstance(p, dict))
    raise InferenzaError("content non testuale")


def invia_chat(
    url: str,
    payload: dict,
    post: Callable[[str, dict], dict] | None = None,
    timeout: int = 600,
    token: str | None = None,
) -> str:
    """POST all'URL così com'è: nessuna desinenza aggiunta (vale per cloud e locali)."""
    try:
        if post is None:
            headers = {"Content-Type": "application/json"}
            if token:
                headers["Authorization"] = f"Bearer {token}"
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode(),
                headers=headers,
            )
            with urllib.request.urlopen(req, timeout=timeout) as r:
                risposta = json.load(r)
        else:
            risposta = post(url, payload)
    except InferenzaError:
        raise
    except Exception as e:
        raise InferenzaError(f"chiamata chat fallita: {e}") from e
    return parse_chat_text(risposta)
