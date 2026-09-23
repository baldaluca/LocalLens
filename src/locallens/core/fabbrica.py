"""Scelta SorgenteModello dietro la stessa interfaccia client (RF10)."""

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
    """Se il config chiede bundlato ma la GPU locale non è rilevata, segnala ma non ripiega (server generico)."""
    d = as_dict(conf)
    if d.get("sorgente", "bundlato") == "bundlato" and not disponibilita_gpu_locale(
        info, preset, **rileva_kw
    ):
        return d, t(d.get("lingua", "it"), "banner_gpu_non_rilevata")
    return d, None


def costruisci(conf, info, preset, gestore=None, crea=None, solo_cpu=None, pesi=None, verifica=None, crea_cloud=None):
    """(engine, stato, banner). Dipendenze iniettabili; default = reali. Server generico verbatim."""
    from locallens.core.orchestrator import crea_engine as _crea

    d = as_dict(conf)
    crea = crea or _crea
    verifica = verifica or verifica_health
    sorgente = d.get("sorgente", "bundlato")
    lingua = d.get("lingua", "it")

    if sorgente == "nessuno":
        if solo_cpu is None:
            solo_cpu = _solo_cpu_default
        return (
            solo_cpu(t(lingua, "motivo_solo_tesseract")),
            t(lingua, "stato_nessuno"),
            "",
        )

    if sorgente in ("bundlato", "esterno"):
        url = (d.get("url_gpu_locale") or d.get("url_esterno") or "http://127.0.0.1:8011")
        url = str(url).strip() or "http://127.0.0.1:8011"
        # modello fallback su preset.id per llama-server
        modello = (d.get("modello_esterno") or "").strip()
        if not modello and preset and getattr(preset, "id", ""):
            modello = str(preset.id).strip()
        token = (d.get("token_esterno") or "").strip()
        manca_modello = not modello
        manca_token_pubblico = not token and not is_url_privata(url)
        if manca_modello and manca_token_pubblico:
            if solo_cpu is None:
                solo_cpu = _solo_cpu_default
            motivo = t(lingua, "motivo_esterno_manca_modello_token")
            return (
                solo_cpu(motivo),
                t(lingua, "stato_esterno_non_configurato"),
                t(lingua, "banner_esterno_non_configurato"),
            )
        if manca_modello:
            if solo_cpu is None:
                solo_cpu = _solo_cpu_default
            motivo = t(lingua, "motivo_esterno_manca_modello")
            return (
                solo_cpu(motivo),
                t(lingua, "stato_esterno_non_configurato"),
                t(lingua, "banner_esterno_non_configurato"),
            )
        # token opzionale per URL private, obbligatorio per pubbliche
        if manca_token_pubblico:
            if solo_cpu is None:
                solo_cpu = _solo_cpu_default
            motivo = t(lingua, "motivo_esterno_manca_token")
            return (
                solo_cpu(motivo),
                t(lingua, "stato_esterno_non_configurato"),
                t(lingua, "banner_esterno_non_configurato"),
            )
        banner_priv = "" if is_url_privata(url) else t(lingua, "banner_privacy_url")
        if verifica(url):
            # se modello_esterno esplicito → crea_cloud verbatim, altrimenti preset (bundlato)
            if (d.get("modello_esterno") or "").strip():
                if crea_cloud is None:
                    from locallens.core.orchestrator import (
                        crea_engine_cloud as _crea_cloud,
                    )

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
                return engine, t(lingua, "stato_esterno", url=url), banner_priv
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
                banner_priv,
            )
        if solo_cpu is None:
            solo_cpu = _solo_cpu_default
        motivo = t(lingua, "motivo_gpu_non_raggiungibile", url=url)
        return solo_cpu(motivo), t(lingua, "stato_gpu_solo_cpu"), t(lingua, "banner_solo_cpu_assente", url=url)

    # fallback sconosciuto → solo CPU
    if solo_cpu is None:
        solo_cpu = _solo_cpu_default
    return solo_cpu(t(lingua, "motivo_solo_tesseract")), t(lingua, "stato_nessuno"), ""


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
        """Delega a HttpInferAdapter — unico seam HTTP prepara/payload/invia."""
        from locallens.core.client import HttpInferAdapter

        max_side = d.get("max_side_px", 2048)
        contrasto = d.get("contrasto", False)

        if sorgente == "esterno":
            return HttpInferAdapter(
                base_url=base_url,
                preset=preset,
                modello=(d.get("modello_esterno") or "").strip(),
                prompt=d.get("prompt_esterno", ""),
                token=(d.get("token_esterno") or "").strip(),
                max_side=max_side,
                contrasto=contrasto,
                sorgente="esterno",
            )
        return HttpInferAdapter(
            base_url=base_url,
            preset=preset,
            max_side=max_side,
            contrasto=contrasto,
            sorgente="bundlato",
            motore="bundlato",
        )

    def rebuild(self, config: Config) -> tuple:
        """(engine, stato, banner) from Config. Owns SorgenteModello + hardware check. Server generico verbatim."""
        from locallens.config.presets import preset_da_conf
        from locallens.core.orchestrator import OcrEngine
        from locallens.hwdetect.detector import detect

        d = as_dict(config)
        lingua = d.get("lingua", "it")
        preset = preset_da_conf(d)
        d = dict(d, preset_id=preset.id)

        info = detect()
        avviso = None
        if d.get("sorgente", "bundlato") == "bundlato":
            if not disponibilita_gpu_locale(info, preset):
                avviso = t(lingua, "banner_gpu_non_rilevata")

        sorgente = d.get("sorgente", "bundlato")

        if sorgente == "nessuno":
            banner = avviso or ""
            return (
                _solo_cpu_default(t(lingua, "motivo_solo_tesseract")),
                t(lingua, "stato_nessuno"),
                banner,
            )

        if sorgente in ("bundlato", "esterno"):
            url = (d.get("url_gpu_locale") or d.get("url_esterno") or "http://127.0.0.1:8011")
            url = str(url).strip() or "http://127.0.0.1:8011"
            modello = (d.get("modello_esterno") or "").strip()
            if not modello and preset and getattr(preset, "id", ""):
                modello = str(preset.id).strip()
            token = (d.get("token_esterno") or "").strip()
            manca_modello = not modello
            manca_token_pubblico = not token and not is_url_privata(url)
            if manca_modello and manca_token_pubblico:
                motivo = t(lingua, "motivo_esterno_manca_modello_token")
                banner_base = t(lingua, "banner_esterno_non_configurato")
                banner = "; ".join(b for b in (avviso, banner_base) if b)
                return (
                    _solo_cpu_default(motivo),
                    t(lingua, "stato_esterno_non_configurato"),
                    banner,
                )
            if manca_modello:
                motivo = t(lingua, "motivo_esterno_manca_modello")
                banner_base = t(lingua, "banner_esterno_non_configurato")
                banner = "; ".join(b for b in (avviso, banner_base) if b)
                return (
                    _solo_cpu_default(motivo),
                    t(lingua, "stato_esterno_non_configurato"),
                    banner,
                )
            if manca_token_pubblico:
                motivo = t(lingua, "motivo_esterno_manca_token")
                banner_base = t(lingua, "banner_esterno_non_configurato")
                banner = "; ".join(b for b in (avviso, banner_base) if b)
                return (
                    _solo_cpu_default(motivo),
                    t(lingua, "stato_esterno_non_configurato"),
                    banner,
                )
            banner_priv = "" if is_url_privata(url) else t(lingua, "banner_privacy_url")
            banner_ok = "; ".join(b for b in (avviso, banner_priv) if b)
            if self._verify(url):
                # infer verbatim: se modello_esterno esplicito usa esterno, altrimenti preset (bundlato)
                if (d.get("modello_esterno") or "").strip():
                    infer = self._make_infer("esterno", url, preset, d)
                    sorg_infer = "esterno"
                    stato = t(lingua, "stato_esterno", url=url)
                else:
                    infer = self._make_infer("bundlato", url, preset, d)
                    sorg_infer = "bundlato"
                    stato = t(lingua, "stato_gpu_locale", url=url)
                from locallens.fallback.tesseract import estrai as tesseract_estrai

                fallback_fn = lambda pid, png: tesseract_estrai(png)
                engine = OcrEngine(
                    infer=infer, fallback=fallback_fn, sorgente=sorg_infer, **_contesto(d)
                )
                return engine, stato, banner_ok
            motivo = t(lingua, "motivo_gpu_non_raggiungibile", url=url)
            banner_base = t(lingua, "banner_solo_cpu_assente", url=url)
            banner = "; ".join(b for b in (avviso, banner_base) if b)
            return _solo_cpu_default(motivo), t(lingua, "stato_gpu_solo_cpu"), banner

        # fallback sconosciuto
        banner = avviso or ""
        return _solo_cpu_default(t(lingua, "motivo_solo_tesseract")), t(lingua, "stato_nessuno"), banner
