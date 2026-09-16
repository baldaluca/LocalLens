"""Icona applicazione: SVG master + PNG per dimensione."""

from locallens.config.percorsi import risorsa


def percorso_icona(dimensione: int = 256) -> str:
    """PNG dell'icona; cade su 256 se la dimensione non esiste."""
    for size in (dimensione, 256, 128, 64, 48, 32, 16):
        candidato = risorsa("assets", "icons", f"locallens-{size}.png")
        if candidato.is_file():
            return str(candidato)
    raise FileNotFoundError("icone non trovate in assets/icons/")
