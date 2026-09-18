"""Scelta SorgenteModello dietro la stessa interfaccia client (RF10)."""

import sys

from locallens.backend.manager import is_url_privata


def _contesto(conf) -> dict:
    """Contesto filtro anti-self-hit: stringa TOML "it,en" → tupla per crea_engine."""
    lingue = tuple(
        l.strip()
        for l in str(conf.get("lingue_filtro", "it")).split(",")
        if l.strip()
    ) or ("it",)
    return {
        "lingue_attese": lingue,
        "soglia_righe_loop": int(conf.get("soglia_righe_loop", 5)),
        "ignora_eco": bool(conf.get("ignora_eco", False)),
    }


def disponibilita_gpu_locale(info, preset, piattaforma=None, bins_root=None, cache_root=None) -> bool:
    """True se la GPU locale è davvero usabile: binario + pesi presenti. Nessun download."""
    from locallens.backend.manager import resolve_binary
    from locallens.config.pesi import snapshot_completo

    if not info.candidati:
        return False
    binario = resolve_binary(piattaforma or sys.platform, info.candidati[0], bins_root)
    return binario.is_file() and snapshot_completo(preset, cache_root) is not None


def normalizza_sorgente(conf, info, preset, **rileva_kw) -> tuple[dict, str | None]:
    """Se il config chiede bundlato ma la GPU locale non è rilevata, ripiega su esterno."""
    if conf.get("sorgente", "bundlato") == "bundlato" and not disponibilita_gpu_locale(
        info, preset, **rileva_kw
    ):
        nuova = dict(conf, sorgente="esterno")
        return nuova, "GPU locale non rilevata (binari o pesi assenti): uso il server esterno."
    return conf, None


def costruisci(conf, info, preset, gestore=None, crea=None, solo_cpu=None, pesi=None, verifica=None, crea_cloud=None):
    """(engine, stato, banner). Dipendenze iniettabili; default = reali."""
    from locallens.backend.manager import verifica_health
    from locallens.core.orchestrator import crea_engine as _crea

    crea = crea or _crea
    verifica = verifica or verifica_health
    sorgente = conf.get("sorgente", "bundlato")

    if sorgente == "esterno":
        url = conf.get("url_esterno", "http://127.0.0.1:8011")
        banner = (
            ""
            if is_url_privata(url)
            else "Attenzione privacy: l'URL non punta alla rete locale."
        )
        modello = (conf.get("modello_esterno") or "").strip()
        if modello:
            # Cloud tutto a mano: token+modello+prompt, nessun preset.
            if crea_cloud is None:
                from locallens.core.orchestrator import crea_engine_cloud as _crea_cloud

                crea_cloud = _crea_cloud
            engine = crea_cloud(
                url,
                modello=modello,
                prompt=conf.get("prompt_esterno", ""),
                token=(conf.get("token_esterno") or "").strip(),
                max_side=conf.get("max_side_px", 2048),
                contrasto=conf.get("contrasto", False),
                **_contesto(conf),
            )
            return engine, f"esterno • {url}", banner
        engine = crea(
            url,
            preset,
            motore="esterno",
            max_side=conf.get("max_side_px", 2048),
            contrasto=conf.get("contrasto", False),
            **_contesto(conf),
        )
        return engine, f"esterno • {url}", banner

    if sorgente == "nessuno":
        if solo_cpu is None:
            from locallens.__main__ import _solo_cpu as _reale

            solo_cpu = _reale
        return (
            solo_cpu("scelta utente: solo Tesseract"),
            "nessuno (solo CPU)",
            "",
        )

    # bundlato = GPU locale: usa il server all'URL configurato, senza avviare binari.
    url = conf.get("url_gpu_locale") or conf.get("url_esterno", "http://127.0.0.1:8011")
    if verifica(url):
        return (
            crea(
                url,
                preset,
                motore="esterno",
                max_side=conf.get("max_side_px", 2048),
                contrasto=conf.get("contrasto", False),
                **_contesto(conf),
            ),
            f"GPU locale • {url}",
            "",
        )
    if solo_cpu is None:
        from locallens.__main__ import _solo_cpu as _reale

        solo_cpu = _reale
    motivo = f"GPU locale non raggiungibile: {url}"
    return solo_cpu(motivo), "GPU locale (solo CPU)", f"Solo CPU: server assente su {url}"
