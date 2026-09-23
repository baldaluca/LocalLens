"""Client HTTP per /v1/chat/completions. Prompt/modello dal preset, mai hardcoded."""
import base64
import json
import urllib.error
import urllib.request
from collections.abc import Callable

from locallens.core.errori import InferenzaError

#: Quanti caratteri del body d'errore finiscono in nota/diario.
MAX_CORPO_ERRORE = 500


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
    if isinstance(risposta.get("message"), dict):
        content = risposta["message"].get("content", "")
        if isinstance(content, str):
            return content
        raise InferenzaError("content non testuale")
    try:
        content = risposta["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise InferenzaError(f"risposta chat non valida: {e}") from e
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(p.get("text", "") for p in content if isinstance(p, dict))
    raise InferenzaError("content non testuale")


def dialetto(url: str) -> str:
    """'ollama' se il path dell'URL è /api/chat, altrimenti 'openai'."""
    from urllib.parse import urlparse

    try:
        percorso = urlparse(url).path.rstrip("/")
    except (ValueError, TypeError):
        # URL non parsabile: dialetto default, mai bloccare la chiamata.
        return "openai"
    return "ollama" if percorso == "/api/chat" else "openai"


def build_ollama_payload(
    immagine_b64: str, prompt_system: str, modello: str, max_tokens: int = 2048
) -> dict:
    return {
        "model": modello,
        "stream": False,
        "options": {"num_predict": max_tokens},
        "messages": [
            {"role": "system", "content": prompt_system},
            {"role": "user", "content": prompt_system, "images": [immagine_b64]},
        ],
    }


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
    except urllib.error.HTTPError as e:
        try:
            corpo = e.read().decode("utf-8", "replace")[:MAX_CORPO_ERRORE]
        except (OSError, ValueError):
            # Corpo best-effort: l'HTTP code basta per la diagnosi.
            corpo = ""
        dettaglio = corpo or e.reason
        raise InferenzaError(f"chiamata chat fallita: HTTP {e.code}: {dettaglio}") from e
    except InferenzaError:
        raise
    except Exception as e:
        raise InferenzaError(f"chiamata chat fallita: {e}") from e
    return parse_chat_text(risposta)


class HttpInferAdapter:
    """Adapter HTTP: prepara immagine → payload → invia_chat. Unico seam HTTP."""

    def __init__(
        self,
        base_url: str,
        preset=None,
        modello: str = "",
        prompt: str = "",
        token: str = "",
        max_side: int = 2048,
        contrasto: bool = False,
        timeout: int = 600,
        post: Callable[[str, dict], dict] | None = None,
        motore: str = "cuda",
        max_tokens: int = 2048,
        sorgente: str = "bundlato",
    ) -> None:
        self.base_url = base_url
        self.preset = preset
        self.modello = modello
        self.prompt = prompt
        self.token = token
        self.max_side = max_side
        self.contrasto = contrasto
        self.timeout = timeout
        self.post = post
        self.motore = motore
        self.max_tokens = max_tokens
        self.sorgente = sorgente

    def __call__(self, pagina_id: int, png: bytes) -> tuple[str, str]:
        from locallens.preprocessing.immagini import prepara

        if self.sorgente == "esterno":
            try:
                pronta = prepara(png, max_side=self.max_side, contrasto=self.contrasto)
            except Exception as e:
                raise InferenzaError(f"preprocessing fallito: {e}") from e
            b64 = base64.b64encode(pronta).decode()
            if dialetto(self.base_url) == "ollama":
                payload = build_ollama_payload(b64, self.prompt, self.modello, max_tokens=self.max_tokens)
            else:
                payload = build_chat_payload(b64, self.prompt, self.modello, max_tokens=self.max_tokens)
            testo = invia_chat(self.base_url, payload, post=self.post, timeout=self.timeout, token=self.token or None)
            return testo, "esterno"
        # bundlato
        preset = self.preset
        prompt_local = preset.prompt.get("system", "Transcribe.") if preset else self.prompt or "Transcribe."
        limite = min(self.max_side, preset.max_side_px) if preset else self.max_side
        try:
            pronta = prepara(png, max_side=limite, contrasto=self.contrasto)
        except Exception as e:
            raise InferenzaError(f"preprocessing fallito: {e}") from e
        modello_id = preset.id if preset else self.modello
        max_tok = preset.max_tokens if preset else self.max_tokens
        payload = build_chat_payload(base64.b64encode(pronta).decode(), prompt_local, modello_id, max_tokens=max_tok)
        base = self.base_url.rstrip("/")
        # Evita doppio /v1/chat/completions se l'utente ha già messo l'endpoint completo
        if base.endswith("/v1/chat/completions"):
            endpoint = base
        else:
            endpoint = base + "/v1/chat/completions"
        return invia_chat(endpoint, payload, post=self.post, timeout=self.timeout), self.motore
