"""Grafik görüntüsü dışa aktarma — `F3-062` (PNG).

`QWidget.grab()` grafiğin o anki görünümünü **piksel piksel** yakalar:
başlık, seriler, legend ve eksen birimleri neyse çıktıya o girer. Bu
yüzden "başlık ve birimler görünür" kabulü grafiğin kendi çiziminden
gelir; dışa aktarma yalnız onu bir PNG dosyasına yazar.

Vektörel SVG çıktısı (`F3-063`) pyqtgraph'ın sahne grafiğini dolaşan
kendi dışa aktarıcısını gerektirir; o yüzden `PlotPanel.export_svg`
içinde, grafik adaptör katmanında durur (ADR-002).
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

#: Geçerli bir PNG dosyasının ilk sekiz baytı.
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def export_widget_png(widget: QWidget, path: str | Path, *, scale: float = 1.0) -> Path:
    """`widget`'ın görünümünü `path`'e PNG olarak yazar; yazılan yolu döndürür.

    `scale` > 1 daha yüksek çözünürlüklü (rapor/baskı için) çıktı verir.

    Hatalar sessizce yutulmaz:

    * `ValueError` — `scale` pozitif değil ya da widget'ın boyutu sıfır
      (henüz gösterilmemiş / düzenlenmemiş).
    * `OSError` — Qt görüntüyü diske yazamadı (izin, dolu disk, geçersiz
      uzantı).
    """
    if scale <= 0.0:
        raise ValueError(f"scale pozitif olmalı: {scale}")
    width, height = widget.width(), widget.height()
    if width <= 0 or height <= 0:
        raise ValueError(
            "Grafik boyutu sıfır; dışa aktarmadan önce pencere gösterilmeli veya "
            "widget yeniden boyutlandırılmalı"
        )

    pixmap = widget.grab()
    if scale != 1.0:
        pixmap = pixmap.scaled(
            round(pixmap.width() * scale),
            round(pixmap.height() * scale),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not pixmap.save(str(dest), "PNG"):
        raise OSError(f"PNG yazilamadi: {dest}")
    return dest
