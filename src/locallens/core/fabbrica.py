"""Scelta SorgenteModello dietro la stessa interfaccia client (RF10)."""

from locallens.backend.manager import is_url_privata


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
        ),
        f"{info.candidati[0]} • {handle.base_url}",
        "",
    )
