"""RED: sorgente modello (RF10) + avviso privacy URL non locale (RNF1)."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from locallens.app.impostazioni import DialogoImpostazioni


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_default_bundlato_senza_avviso(qapp):
    d = DialogoImpostazioni(preset_ids=["glm-ocr-q8_0"])
    assert d.valori()["sorgente"] == "bundlato"
    assert d.avviso.isHidden()


def test_url_esterna_pubblica_mostra_avviso(qapp):
    d = DialogoImpostazioni(preset_ids=["glm-ocr-q8_0"])
    d.set_sorgente("esterno")
    d.url.setText("http://203.0.113.10:8011")
    d._aggiorna_avviso()
    assert not d.avviso.isHidden()
    assert "locale" in d.avviso.text().lower() or "privacy" in d.avviso.text().lower()
    assert d.valori()["url_esterno"] == "http://203.0.113.10:8011"


def test_url_locale_nessun_avviso(qapp):
    d = DialogoImpostazioni(preset_ids=["glm-ocr-q8_0"])
    d.set_sorgente("esterno")
    d.url.setText("http://127.0.0.1:8011")
    d._aggiorna_avviso()
    assert d.avviso.isHidden()


def test_preset_override(qapp):
    d = DialogoImpostazioni(preset_ids=["glm-ocr-q8_0", "altro"])
    d.set_preset("altro")
    assert d.valori()["preset_id"] == "altro"


def test_contesto_filtro_default_e_valori(qapp):
    d = DialogoImpostazioni(preset_ids=["glm-ocr-q8_0"])
    v = d.valori()
    assert v["lingue_filtro"] == "it"
    assert v["soglia_righe_loop"] == 5
    assert v["ignora_eco"] is False
    d.lingue.setText("it,en")
    d.soglia.setValue(9)
    d.ignora_eco.setChecked(True)
    v = d.valori()
    assert v["lingue_filtro"] == "it,en"
    assert v["soglia_righe_loop"] == 9
    assert v["ignora_eco"] is True
