"""Icona applicazione: SVG master + PNG per dimensione."""

from locallens.config.percorsi import risorsa


def percorso_icona(dimensione: int = 256) -> str:
    """PNG dell'icona; cade su 256 se la dimensione non esiste."""
    for size in (dimensione, 256, 128, 64, 48, 32, 16):
        candidato = risorsa("assets", "icons", f"locallens-{size}.png")
        if candidato.is_file():
            return str(candidato)
    raise FileNotFoundError("icone non trovate in assets/icons/")


def percorso_freccia(tema: str, direzione: str) -> str:
    """Freccia UI (combo/spin) nel colore del tema: 'giu' | 'su'."""
    if direzione not in ("giu", "su"):
        raise ValueError(f"direzione ignota: {direzione} (giu|su)")
    candidato = risorsa("assets", "icons", f"freccia-{direzione}-{tema}.png")
    if candidato.is_file():
        return str(candidato)
    raise FileNotFoundError(f"freccia non trovata: {candidato}")


def percorso_spunta() -> str:
    """Icona check bianca per QCheckBox::indicator:checked (su sfondo primary)."""
    for ext in ("png", "svg"):
        candidato = risorsa("assets", "icons", f"spunta.{ext}")
        if candidato.is_file():
            return str(candidato)
    raise FileNotFoundError("spunta non trovata in assets/icons/")
