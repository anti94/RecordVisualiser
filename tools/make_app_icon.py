"""Uygulama ikonunu üretir — `F6-003`.

İkon bir **kaynak dosyası** olarak depoda durur (`packaging/sonar-analyzer.ico`),
ama elle çizilmiş bir ikili olarak değil: bu betik onu üretir, böylece
nasıl oluştuğu okunabilir ve değiştirilebilir kalır.

Çizim Qt ile yapılır (`QPainter`), projede zaten kullanılan yol
(`ui/status_icons.py`). Dış bir görüntü kütüphanesi eklenmez.

ICO kabı **elle** yazılır. Qt'nin ICO yazıcısı tek boyut üretir; Windows
ise küçük simge, görev çubuğu ve büyük simge için farklı boyutlar ister ve
yoksa tek boyutu ölçekleyip bulanıklaştırır. ICO biçimi Vista'dan beri
her boyut için PNG gömmeye izin verir, bu yüzden her boyut PNG olarak
kodlanıp tek kaba dizilir.

Kullanım::

    .venv\\Scripts\\python.exe tools\\make_app_icon.py
"""

from __future__ import annotations

import argparse
import struct
import sys
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from PySide6.QtCore import QBuffer

ROOT = Path(__file__).resolve().parent.parent
for location in (ROOT, ROOT / "src"):
    if str(location) not in sys.path:
        sys.path.insert(0, str(location))

#: Windows'un istediği boyutlar: küçük simge, orta, görev çubuğu, büyük.
ICON_SIZES: tuple[int, ...] = (16, 24, 32, 48, 64, 128, 256)

DEFAULT_OUTPUT = ROOT / "packaging" / "sonar-analyzer.ico"


def render_png(size: int) -> bytes:
    """Tek boyutu çizip PNG baytlarına kodlar.

    Çizim: koyu daire zemin üzerinde açık renkli bir sonar tarama yayı ve
    merkez nokta. Tema paletiyle aynı renkler kullanılır ki paketlenmiş
    uygulamanın ikonu ile arayüzü aynı görünsün.
    """
    from PySide6.QtCore import QBuffer, QByteArray, QRectF, Qt
    from PySide6.QtGui import QColor, QImage, QPainter, QPen

    from sonar_analyzer.ui.theme import DARK

    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    inset = max(1.0, size * 0.04)
    face = QRectF(inset, inset, size - 2 * inset, size - 2 * inset)

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(DARK.surface))
    painter.drawEllipse(face)

    accent = QColor(DARK.accent)
    # Ic ice iki yay: sonar taramasi. Kalinlik boyutla olcekelenir ki
    # 16 pikselde kaybolmasin, 256 pikselde ciliz kalmasin.
    pen = QPen(accent)
    pen.setWidthF(max(1.0, size * 0.07))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    for scale in (0.62, 0.38):
        span = face.width() * scale
        arc = QRectF(
            face.center().x() - span / 2,
            face.center().y() - span / 2,
            span,
            span,
        )
        # Qt acilari 1/16 derece; -45 dereceden 150 derecelik yay.
        painter.drawArc(arc, -45 * 16, 150 * 16)

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(accent)
    dot = max(1.5, size * 0.09)
    painter.drawEllipse(face.center(), dot, dot)
    painter.end()

    # QByteArray'e AYRI bir referans tutulur: QBuffer onu sahiplenmez ve
    # gecici nesne toplanirsa Qt serbest bellege yazar (cokme).
    store = QByteArray()
    buffer = QBuffer(store)
    buffer.open(QBuffer.OpenModeFlag.WriteOnly)
    # PySide6 TASLAGI bicim adini `bytes` sanıyor, calisma zamani ise `str`
    # istiyor (bytes verilince ValueError). Taslak yanlis oldugu icin cagri
    # tiplenmis bir sarmalayici uzerinden yapilir.
    saver = cast("Callable[[QBuffer, str], bool]", image.save)
    saved = saver(buffer, "PNG")
    buffer.close()
    if not saved:
        raise RuntimeError(f"{size}px PNG kodlanamadi")
    return bytes(store.data())


def build_ico(sizes: tuple[int, ...] = ICON_SIZES) -> bytes:
    """PNG'leri tek bir ICO kabına dizer.

    Kap düzeni: 6 baytlık başlık, boyut başına 16 baytlık dizin girdisi,
    ardından PNG verileri. Dizin girdisindeki genişlik/yükseklik alanı tek
    bayttır ve 256 için **0** yazılır (biçimin kuralı).
    """
    if not sizes:
        raise ValueError("En az bir boyut gerekli")

    images = [(size, render_png(size)) for size in sizes]
    header = struct.pack("<HHH", 0, 1, len(images))  # rezerve, tip=ICO, adet
    offset = len(header) + 16 * len(images)

    entries = bytearray()
    payload = bytearray()
    for size, data in images:
        dimension = 0 if size >= 256 else size
        entries += struct.pack(
            "<BBBBHHII",
            dimension,  # genislik
            dimension,  # yukseklik
            0,  # palet rengi yok
            0,  # rezerve
            1,  # renk duzlemi
            32,  # bit/piksel
            len(data),
            offset,
        )
        payload += data
        offset += len(data)

    return header + bytes(entries) + bytes(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Uygulama ikonunu uretir (F6-003)")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    # QPainter bir QGuiApplication ister; ekransiz ortamda da calissin.
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QGuiApplication

    # Uygulama nesnesi bilerek SERBEST BIRAKILMAZ: Qt'nin kendi yikim sirasi
    # yorumlayici kapanisiyla yaris haline girip cokebiliyor.
    _app = QGuiApplication.instance() or QGuiApplication([])
    assert _app is not None

    data = build_ico()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(data)
    print(f"{args.output} yazildi: {len(data)} bayt, {len(ICON_SIZES)} boyut")
    return 0


if __name__ == "__main__":  # pragma: no cover - komut satiri girisi
    raise SystemExit(main())
