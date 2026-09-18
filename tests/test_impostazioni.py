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
    d = DialogoImpostazioni()
    assert d.valori()["sorgente"] == "bundlato"
    assert d.avviso.isHidden()


def test_url_esterna_pubblica_mostra_avviso(qapp):
    d = DialogoImpostazioni()
    d.set_sorgente("esterno")
    d.url.setText("http://203.0.113.10:8011")
    d._aggiorna_avviso()
    assert not d.avviso.isHidden()
    assert "locale" in d.avviso.text().lower() or "privacy" in d.avviso.text().lower()
    assert d.valori()["url_esterno"] == "http://203.0.113.10:8011"


def test_url_locale_nessun_avviso(qapp):
    d = DialogoImpostazioni()
    d.set_sorgente("esterno")
    d.url.setText("http://127.0.0.1:8011")
    d._aggiorna_avviso()
    assert d.avviso.isHidden()



def test_contesto_filtro_default_e_valori(qapp):
    d = DialogoImpostazioni()
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


def test_dialogo_applica_tema(qapp):
    from locallens.app.tema import TEMI

    d = DialogoImpostazioni(tema="scuro")
    assert TEMI["scuro"]["background"] in d.styleSheet()
    d2 = DialogoImpostazioni()
    assert TEMI["chiaro"]["background"] in d2.styleSheet()


def test_dialogo_tema_ignoto_errore(qapp):
    import pytest

    with pytest.raises(ValueError):
        DialogoImpostazioni(tema="arcobaleno")


def test_aiuto_whats_this_sulle_impostazioni_filtro(qapp):
    from PySide6.QtCore import Qt

    d = DialogoImpostazioni()
    assert d.windowFlags() & Qt.WindowContextHelpButtonHint
    for campo in (d.lingue, d.soglia, d.ignora_eco):
        assert campo.whatsThis().strip() != ""


def test_aiuto_per_riga_con_bottone_punto_domanda(qapp):
    """Ogni voce filtro ha un '?' cliccabile che espande la spiegazione."""
    d = DialogoImpostazioni()
    for campo, attr in ((d.lingue, "aiuto_lingue"), (d.soglia, "aiuto_soglia"), (d.ignora_eco, "aiuto_eco")):
        bottone = getattr(d, attr + "_btn", None)
        spiega = getattr(d, attr, None)
        assert bottone is not None and bottone.text() == "?"
        assert spiega is not None and spiega.text().strip() != ""
        assert spiega.isHidden()
        bottone.click()
        assert not spiega.isHidden()
        bottone.click()
        assert spiega.isHidden()


def test_bottone_aiuto_testo_visibile(qapp):
    """Il '?' non deve restare schiacciato dal padding: regola dedicata nel foglio."""
    d = DialogoImpostazioni()
    assert d.aiuto_lingue_btn.property("aiuto") is True
    assert 'aiuto="true"' in d.styleSheet()


def test_label_gpu_locale_e_flag(qapp):
    d = DialogoImpostazioni()
    assert d.sorgente.itemText(0) == "GPU locale"
    assert d.valori()["sorgente"] == "bundlato"
    d2 = DialogoImpostazioni(gpu_locale_disponibile=False)
    voci = [d2.sorgente.itemText(i) for i in range(d2.sorgente.count())]
    assert voci == ["esterno", "nessuno"]
    d2.set_sorgente("esterno")
    assert d2.valori()["sorgente"] == "esterno"


def test_esterno_mostra_cloud(qapp):
    d = DialogoImpostazioni()
    assert not d.url.isHidden()
    assert d.token.isHidden() and d.modello.isHidden() and d.prompt.isHidden()
    d.set_sorgente("esterno")
    assert not d.url.isHidden()
    assert not d.token.isHidden()
    assert not d.modello.isHidden()
    assert not d.prompt.isHidden()
    d.token.setText("tk")
    d.modello.setText("vision-x")
    d.prompt.setPlainText("Leggi.")
    v = d.valori()
    assert v["token_esterno"] == "tk"
    assert v["modello_esterno"] == "vision-x"
    assert v["prompt_esterno"] == "Leggi."
    assert "preset_id" not in v
    d.set_sorgente("bundlato")
    assert not d.url.isHidden()
    assert d.token.isHidden()


def test_nessuno_nasconde_url_e_cloud(qapp):
    d = DialogoImpostazioni()
    d.set_sorgente("nessuno")
    assert d.url.isHidden()
    assert d.token.isHidden() and d.modello.isHidden() and d.prompt.isHidden()
    d.set_sorgente("esterno")
    assert not d.url.isHidden()
    assert not d.token.isHidden()


def test_campi_cloud_sopravvivono_ai_cambi_opzione(qapp):
    d = DialogoImpostazioni()
    d.set_sorgente("esterno")
    d.token.setText("tk")
    d.modello.setText("vision-x")
    d.prompt.setPlainText("Leggi.")
    d.set_sorgente("nessuno")
    d.set_sorgente("bundlato")
    d.set_sorgente("esterno")
    assert d.token.text() == "tk"
    assert d.modello.text() == "vision-x"
    assert d.prompt.toPlainText() == "Leggi."


def test_url_distinti_per_opzione(qapp):
    d = DialogoImpostazioni()
    d.set_sorgente("esterno")
    d.url.setText("http://cloud:8000")
    d.set_sorgente("bundlato")
    assert d.url.text() != "http://cloud:8000"
    d.url.setText("http://127.0.0.1:10000")
    d.set_sorgente("esterno")
    assert d.url.text() == "http://cloud:8000"
    d.set_sorgente("bundlato")
    assert d.url.text() == "http://127.0.0.1:10000"
    v = d.valori()
    assert v["url_esterno"] == "http://cloud:8000"
    assert v["url_gpu_locale"] == "http://127.0.0.1:10000"


def test_dialogo_inglese_mostra_testi_inglesi(qapp):
    from locallens.app.lingua import STRINGS

    d = DialogoImpostazioni(lingua="en")
    assert d.windowTitle() == STRINGS["en"]["dlg_impostazioni_titolo"]
    assert d.etichetta_url.text() == STRINGS["en"]["etichetta_url"]
    assert d.etichetta_token.text() == STRINGS["en"]["etichetta_token"]
    assert d.aiuto_lingue.text() == STRINGS["en"]["aiuto_lingue"]
    assert d.avviso.text() == STRINGS["en"]["avviso_privacy_esterno"]


def test_selettore_lingua_roundtrip(qapp):
    from locallens.app.lingua import STRINGS

    d = DialogoImpostazioni()
    assert d.valori()["lingua"] == "it"
    voci = [d.selettore_lingua.itemText(i) for i in range(d.selettore_lingua.count())]
    assert voci == [STRINGS["it"]["lingua_nome_it"], STRINGS["it"]["lingua_nome_en"]]
    d.set_lingua("en")
    assert d.valori()["lingua"] == "en"
    d.set_lingua("it")
    assert d.valori()["lingua"] == "it"


def test_set_lingua_invalida_non_cambia(qapp):
    d = DialogoImpostazioni()
    d.set_lingua("en")
    d.set_lingua("fr")
    assert d.valori()["lingua"] == "en"


def test_riga_lingua_sempre_visibile(qapp):
    d = DialogoImpostazioni()
    for sorg in ("bundlato", "esterno", "nessuno"):
        d.set_sorgente(sorg)
        assert not d.selettore_lingua.isHidden()


def test_token_placeholder_tooltip_tradotti(qapp):
    """Frizione B: il campo token spiega che vive solo in memoria (it/en)."""
    from locallens.app.lingua import STRINGS

    d_en = DialogoImpostazioni(lingua="en")
    assert d_en.token.placeholderText() == STRINGS["en"]["token_placeholder"]
    assert d_en.token.toolTip() == STRINGS["en"]["token_tooltip"]
    d_en.set_cloud(token="", modello="m", prompt="p")
    assert d_en.token.placeholderText() == STRINGS["en"]["token_placeholder"]
    assert d_en.token.toolTip() == STRINGS["en"]["token_tooltip"]
    d_it = DialogoImpostazioni(lingua="it")
    assert d_it.token.placeholderText() == STRINGS["it"]["token_placeholder"]
    assert d_it.token.toolTip() == STRINGS["it"]["token_tooltip"]


def test_lingua_e_prima_riga_del_dialogo(qapp):
    from PySide6.QtWidgets import QFormLayout

    from locallens.app.impostazioni import DialogoImpostazioni

    dlg = DialogoImpostazioni()
    layout = dlg.layout()
    assert isinstance(layout, QFormLayout)
    assert layout.itemAt(0, QFormLayout.ItemRole.LabelRole).widget() is dlg.etichetta_lingua
    assert layout.itemAt(0, QFormLayout.ItemRole.FieldRole).widget() is dlg.selettore_lingua
