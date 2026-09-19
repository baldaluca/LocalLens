"""Scelta SorgenteModello dietro la stessa interfaccia client (RF10)."""

import sys

from locallens.app.lingua import t
from locallens.config.settings import as_dict
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
