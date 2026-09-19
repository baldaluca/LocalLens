"""Scelta SorgenteModello dietro la stessa interfaccia client (RF10)."""

import base64
import sys

from locallens.app.lingua import t
from locallens.config.settings import Config, as_dict
from locallens.core.orchestrator import solo_cpu as _solo_cpu_default
from locallens.core.rete import is_url_privata, resolve_binary, verifica_health


def _contesto(conf) -> dict:
    """Contesto filtro anti-self-hit: stringa TOML "it,en" → tupla per crea_engine."""
    d = as_dict(conf)
    lingue = tuple(
        lingua.strip()
        for lingua in str(d.get("lingue_filtro", "it")).split(",")
        if lingua.strip()
    ) or ("it",)
    return {
        "lingue_attese": lingue,
        "soglia_righe_loop": int(d.get("soglia_righe_loop", 5)),
        "ignora_eco": bool(d.get("ignora_eco", False)),
    }


def disponibilita_gpu_locale(info, preset, piattaforma=None, bins_root=None, cache_root=None) -> bool:
    """True se la GPU locale è davvero usabile: binario + pesi presenti. Nessun download."""
    from locallens.config.pesi import snapshot_completo

    if not info.candidati:
        return False
    binario = resolve_binary(piattaforma or sys.platform, info.candidati[0], bins_root)
    return binario.is_file() and snapshot_completo(preset, cache_root) is not None


def disponibilita_gpu_locale_da_conf(conf, preset, **rileva_kw) -> bool:
    """True se la GPU locale è usabile per conf/preset. Mai eccezioni: False in caso di errore."""
    try:
        from locallens.hwdetect.detector import detect

        return disponibilita_gpu_locale(detect(), preset, **rileva_kw)
    except Exception:  # noqa: BLE001 — sonda: qualunque errore di rilevamento → non disponibile
        return False


def normalizza_sorgente_da_conf(conf, preset, **rileva_kw) -> tuple[dict, str | None]:
    """normalizza_sorgente con detect() interno (per app: niente hwdetect diretto)."""
    from locallens.hwdetect.detector import detect

    return normalizza_sorgente(conf, detect(), preset, **rileva_kw)


def normalizza_sorgente(conf, info, preset, **rileva_kw) -> tuple[dict, str | None]:
    """Se il config chiede bundlato ma la GPU locale non è rilevata, ripiega su esterno."""
    d = as_dict(conf)
    if d.get("sorgente", "bundlato") == "bundlato" and not disponibilita_gpu_locale(
        info, preset, **rileva_kw
    ):
        nuova = dict(d, sorgente="esterno")
        return nuova, t(d.get("lingua", "it"), "banner_gpu_non_rilevata")
    return d, None


def costruisci(conf, info, preset, gestore=None, crea=None, solo_cpu=None, pesi=None, verifica=None, crea_cloud=None):
    """(engine, stato, banner). Dipendenze iniettabili; default = reali."""
    from locallens.core.orchestrator import crea_engine as _crea

    d = as_dict(conf)
    crea = crea or _crea
    verifica = verifica or verifica_health
    sorgente = d.get("sorgente", "bundlato")
    lingua = d.get("lingua", "it")

    if sorgente == "esterno":
        url = d.get("url_esterno", "http://127.0.0.1:8011")
        modello = (d.get("modello_esterno") or "").strip()
        token = (d.get("token_esterno") or "").strip()
        manca_modello = not modello
        manca_token = not token
        if manca_modello or manca_token:
            if solo_cpu is None:
                solo_cpu = _solo_cpu_default
            if manca_modello and manca_token:
                motivo = t(lingua, "motivo_esterno_manca_modello_token")
            elif manca_modello:
                motivo = t(lingua, "motivo_esterno_manca_modello")
            else:
                motivo = t(lingua, "motivo_esterno_manca_token")
            return (
                solo_cpu(motivo),
                t(lingua, "stato_esterno_non_configurato"),
                t(lingua, "banner_esterno_non_configurato"),
            )
        banner = "" if is_url_privata(url) else t(lingua, "banner_privacy_url")
        # Cloud tutto a mano: token+modello+prompt, nessun preset.
        if crea_cloud is None:
            from locallens.core.orchestrator import crea_engine_cloud as _crea_cloud

            crea_cloud = _crea_cloud
        engine = crea_cloud(
            url,
            modello=modello,
            prompt=d.get("prompt_esterno", ""),
            token=token,
            max_side=d.get("max_side_px", 2048),
            contrasto=d.get("contrasto", False),
            **_contesto(d),
        )
        return engine, f"esterno • {url}", banner

    if sorgente == "nessuno":
        if solo_cpu is None:
            solo_cpu = _solo_cpu_default
        return (
            solo_cpu(t(lingua, "motivo_solo_tesseract")),
            t(lingua, "stato_nessuno"),
            "",
        )

    # bundlato = GPU locale: usa il server all'URL configurato, senza avviare binari.
    url = d.get("url_gpu_locale") or d.get("url_esterno", "http://127.0.0.1:8011")
    if verifica(url):
        return (
            crea(
                url,
                preset,
                motore="bundlato",
                max_side=d.get("max_side_px", 2048),
                contrasto=d.get("contrasto", False),
                **_contesto(d),
            ),
            t(lingua, "stato_gpu_locale", url=url),
            "",
        )
    if solo_cpu is None:
        solo_cpu = _solo_cpu_default
    motivo = t(lingua, "motivo_gpu_non_raggiungibile", url=url)
    return solo_cpu(motivo), t(lingua, "stato_gpu_solo_cpu"), t(lingua, "banner_solo_cpu_assente", url=url)


class EngineFactory:
    """Deep module owning SorgenteModello. Hides verifica_health, resolve_binary, snapshot_completo."""

    def __init__(self, config: Config, verify=None):
        # hide verifica_health inside factory; allow injection for tests
        if verify is not None:
            self._verify = verify
        else:
            from locallens.core.rete import verifica_health as _vh

            self._verify = _vh
        self._config = config

    def _make_infer(self, sorgente: str, base_url: str, preset, d: dict):
        """Unified prepara→build_payload→invia_chat closure. One path for both sorgenti."""
        # hide prepara, client payload builders inside closure
        import base64 as _b64

        from locallens.core.client import build_chat_payload, build_ollama_payload, dialetto, invia_chat
        from locallens.preprocessing.immagini import prepara

        max_side = d.get("max_side_px", 2048)
        contrasto = d.get("contrasto", False)

        if sorgente == "esterno":
            modello = (d.get("modello_esterno") or "").strip()
            prompt = d.get("prompt_esterno", "")
            token = (d.get("token_esterno") or "").strip()

            def infer(pagina_id: int, png: bytes) -> tuple[str, str]:
                try:
                    pronta = prepara(png, max_side=max_side, contrasto=contrasto)
                except Exception as e:
                    from locallens.core.errori import InferenzaError

                    raise InferenzaError(f"preprocessing fallito: {e}") from e
                b64 = _b64.b64encode(pronta).decode()
                if dialetto(base_url) == "ollama":
                    payload = build_ollama_payload(b64, prompt, modello, max_tokens=2048)
                else:
                    payload = build_chat_payload(b64, prompt, modello, max_tokens=2048)
                testo = invia_chat(base_url, payload, post=None, timeout=600, token=token or None)
                return testo, "esterno"

            return infer
        # bundlato
        prompt_local = preset.prompt.get("system", "Transcribe.") if preset else "Transcribe."
        limite = min(max_side, preset.max_side_px) if preset else max_side

        def infer(pagina_id: int, png: bytes) -> tuple[str, str]:
            try:
                pronta = prepara(png, max_side=limite, contrasto=contrasto)
            except Exception as e:
                from locallens.core.errori import InferenzaError

                raise InferenzaError(f"preprocessing fallito: {e}") from e
            payload = build_chat_payload(
                _b64.b64encode(pronta).decode(), prompt_local, preset.id, max_tokens=preset.max_tokens
            )
            endpoint = base_url.rstrip("/") + "/v1/chat/completions"
            return invia_chat(endpoint, payload, post=None, timeout=600), "bundlato"

        return infer

    def rebuild(self, config: Config) -> tuple:
        """(engine, stato, banner) from Config. Owns SorgenteModello + hardware check."""
        # hide verifica_health, resolve_binary and snapshot_completo inside implementation (via disponibilita helper)
        from locallens.config.presets import preset_da_conf
        from locallens.core.orchestrator import OcrEngine
        from locallens.hwdetect.detector import detect

        d = as_dict(config)
        lingua = d.get("lingua", "it")
        preset = preset_da_conf(d)
        # ensure preset_id in dict
        d = dict(d, preset_id=preset.id)

        # hidden hardware availability check (resolve_binary + snapshot_completo via helper)
        info = detect()
        avviso = None
        if d.get("sorgente", "bundlato") == "bundlato":
            # use helper that internally hides resolve_binary/snapshot_completo; respects monkeypatch in tests
            if not disponibilita_gpu_locale(info, preset):
                d = dict(d, sorgente="esterno")
                avviso = t(lingua, "banner_gpu_non_rilevata")

        sorgente = d.get("sorgente", "bundlato")

        # branch esterno
        if sorgente == "esterno":
            url = d.get("url_esterno", "http://127.0.0.1:8011")
            modello = (d.get("modello_esterno") or "").strip()
            token = (d.get("token_esterno") or "").strip()
            manca_modello = not modello
            manca_token = not token
            if manca_modello or manca_token:
                if manca_modello and manca_token:
                    motivo = t(lingua, "motivo_esterno_manca_modello_token")
                elif manca_modello:
                    motivo = t(lingua, "motivo_esterno_manca_modello")
                else:
                    motivo = t(lingua, "motivo_esterno_manca_token")
                banner_base = t(lingua, "banner_esterno_non_configurato")
                banner = "; ".join(b for b in (avviso, banner_base) if b)
                return (
                    _solo_cpu_default(motivo),
                    t(lingua, "stato_esterno_non_configurato"),
                    banner,
                )
            banner_priv = "" if is_url_privata(url) else t(lingua, "banner_privacy_url")
            banner = "; ".join(b for b in (avviso, banner_priv) if b)
            infer = self._make_infer("esterno", url, preset, d)
            from locallens.fallback.tesseract import estrai as tesseract_estrai

            fallback_fn = lambda pid, png: tesseract_estrai(png)
            engine = OcrEngine(
                infer=infer, fallback=fallback_fn, sorgente="esterno", **_contesto(d)
            )
            return engine, f"esterno • {url}", banner

        if sorgente == "nessuno":
            banner = avviso or ""
            return (
                _solo_cpu_default(t(lingua, "motivo_solo_tesseract")),
                t(lingua, "stato_nessuno"),
                banner,
            )

        # bundlato
        url = d.get("url_gpu_locale") or d.get("url_esterno", "http://127.0.0.1:8011")
        if self._verify(url):
            infer = self._make_infer("bundlato", url, preset, d)
            from locallens.fallback.tesseract import estrai as tesseract_estrai

            fallback_fn = lambda pid, png: tesseract_estrai(png)
            engine = OcrEngine(
                infer=infer, fallback=fallback_fn, sorgente="bundlato", **_contesto(d)
            )
            stato = t(lingua, "stato_gpu_locale", url=url)
            banner = avviso or ""
            return engine, stato, banner
        motivo = t(lingua, "motivo_gpu_non_raggiungibile", url=url)
        banner_base = t(lingua, "banner_solo_cpu_assente", url=url)
        banner = "; ".join(b for b in (avviso, banner_base) if b)
        return _solo_cpu_default(motivo), t(lingua, "stato_gpu_solo_cpu"), banner
