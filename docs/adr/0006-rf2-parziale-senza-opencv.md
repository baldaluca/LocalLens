# RF2 parziale in v1: resize + contrasto, niente deskew/crop né OpenCV

Deskew e crop richiederebbero OpenCV (~90 MB in più nel bundle) per un beneficio
marginale sull'immagine gold. v1 implementa `prepara()` con Pillow (già dipendenza):
resize Lanczos anti-OOM + contrasto opzionale. I flag `deskew`/`crop` sono stati
rimossi dai settings invece di restare come no-op silenziosi.
