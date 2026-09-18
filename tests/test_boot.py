"""RED: boot con sorgente=nessuno non avvia processi."""

from locallens.__main__ import costruisci_da_conf
from locallens.config.settings import DEFAULTS


def test_boot_nessuno_solo_cpu():
    conf = dict(DEFAULTS, sorgente="nessuno")
    engine, stato, banner = costruisci_da_conf(conf)
    assert "solo CPU" in stato
    assert banner == ""
    assert hasattr(engine, "submit_document")


def test_boot_bundlato_senza_pesi_va_su_esterno(monkeypatch):
    import locallens.core.fabbrica as fab
    from locallens.__main__ import costruisci_da_conf

    monkeypatch.setattr(fab, "disponibilita_gpu_locale", lambda *a, **k: False)
    conf = dict(DEFAULTS, sorgente="bundlato")
    _engine, stato, banner = costruisci_da_conf(conf)
    assert stato.startswith("esterno")
    assert "GPU locale non rilevata" in banner
