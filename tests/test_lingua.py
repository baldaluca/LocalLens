"""Catalogo stringhe IT/EN e chiave config `lingua` (fondamenta lingua app)."""

import string

from locallens.app.lingua import LINGUE, STRINGS, t


def _placeholders(s: str) -> set[str]:
    return {nome for _, nome, _, _ in string.Formatter().parse(s) if nome}


def test_parita_chiavi():
    assert set(STRINGS["it"]) == set(STRINGS["en"])


def test_nessun_placeholder_perso():
    for chiave in STRINGS["it"]:
        assert _placeholders(STRINGS["it"][chiave]) == _placeholders(STRINGS["en"][chiave]), chiave


def test_fallback_lingua_ignota():
    assert t("fr", "status_pronto") == STRINGS["en"]["status_pronto"]


def test_chiave_ignota_keyerror():
    import pytest

    with pytest.raises(KeyError):
        t("it", "chiave_che_non_esiste")


def test_nessun_valore_vuoto():
    for lingua in LINGUE:
        for chiave, valore in STRINGS[lingua].items():
            assert valore.strip() != "", (lingua, chiave)


def test_lingua_service_typed():
    from locallens.app.lingua import LinguaService

    s = LinguaService("it")
    assert s.t("btn_apri") == "Apri file/PDF"
    s.set_lingua("en")
    assert s.t("btn_apri") == "Open file/PDF"
    # missing key should raise at type-check, at runtime KeyError
    import pytest

    with pytest.raises(KeyError):
        s.t("chiave_che_non_esiste")
