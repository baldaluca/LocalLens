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


def costruisci(conf, info, preset, gestore=None, crea=None, solo_cpu=None, pesi=None):
    """(engine, stato, banner). Dipendenze iniettabili; default = reali."""
    from locallens.core.orchestrator import crea_engine as _crea

    crea = crea or _crea
    sorgente = conf.get("sorgente", "bundlato")

    if sorgente == "esterno":
        url = conf.get("url_esterno", "http://127.0.0.1:8011")
        banner = (
            ""
            if is_url_privata(url)
            else "Attenzione privacy: l'URL non punta alla rete locale."
        )
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

    # bundlato
    if gestore is None:
        from locallens.backend.manager import BackendManager

        gestore = BackendManager()
    if pesi is None:
        from locallens.config.pesi import risolvi_pesi

        try:
            pesi = risolvi_pesi(preset)
        except FileNotFoundError as e:
            if solo_cpu is None:
                from locallens.__main__ import _solo_cpu as _reale

                solo_cpu = _reale
            return solo_cpu(str(e)), "bundlato (solo CPU)", f"Solo CPU: {e}"
    try:
        handle = gestore.start(info.candidati[0], preset=preset, modello=pesi[0], mmproj=pesi[1])
    except (FileNotFoundError, RuntimeError, OSError) as e:
        if solo_cpu is None:
            from locallens.__main__ import _solo_cpu as _reale

            solo_cpu = _reale
        return solo_cpu(str(e)), "bundlato (solo CPU)", f"Solo CPU: {e}"
    return (
        crea(
            handle.base_url,
            preset,
            motore=info.candidati[0],
            max_side=conf.get("max_side_px", 2048),
            contrasto=conf.get("contrasto", False),
            **_contesto(conf),
        ),
        f"{info.candidati[0]} • {handle.base_url}",
        "",
    )
