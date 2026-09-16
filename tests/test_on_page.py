"""RED: callback per-pagina (base del progress in GUI)."""

from locallens.core.pipeline import elabora_pagine


def test_on_page_chiamata_per_ogni_pagina():
    viste = []

    def infer(pid, img):
        return (f"t{pid}", "cuda")

    def fb(pid, img):
        return "fb"

    out = elabora_pagine(
        [b"a", b"b"],
        infer=infer,
        fallback=fb,
        on_page=lambda e, i, n: viste.append((e.pagina_id, i, n)),
    )
    assert [(1, 1, 2), (2, 2, 2)] == viste
    assert len(out) == 2


def test_on_page_opzionale():
    out = elabora_pagine([b"a"], infer=lambda p, i: ("t", "cpu"), fallback=lambda p, i: "f")
    assert out[0].testo == "t"
