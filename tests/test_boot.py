"""RED: boot con sorgente=nessuno non avvia processi."""

from locallens.__main__ import costruisci_da_conf
from locallens.config.settings import DEFAULTS


def test_boot_nessuno_solo_cpu():
    conf = dict(DEFAULTS, sorgente="nessuno")
    engine, stato, banner = costruisci_da_conf(conf)
    assert "solo CPU" in stato
    assert banner == ""
    assert hasattr(engine, "submit_document")
