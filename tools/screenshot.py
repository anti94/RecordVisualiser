"""Uygulamanın ekran görüntüsünü üretir — görsel kabul için.

`docs/ui/acceptance-checklist.md` §8: karşılaştırma, referans PNG ile **aynı
mantıksal pencere boyutunda** alınmış uygulama görüntüsüyle yapılır. Bu betik o
görüntüyü üretir ve görünür pencere açmaz.

Yazı tipi uyarısı: Qt'nin `offscreen` platformu sistem yazı tiplerini kendiliğinden
bulmaz; `QT_QPA_FONTDIR` verilmezse **tüm metinler kutu (tofu) olarak çizilir** ve
görüntü kabul için işe yaramaz. Betik bunu kendisi ayarlar.

Kullanım:
    python tools/screenshot.py out.png
    python tools/screenshot.py out.png --channel ch5 --duration 30
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

WINDOWS_FONT_DIR = "C:/Windows/Fonts"


def prepare_environment() -> None:
    """Görünür pencere açmadan ve yazı tipsiz kalmadan çizim için ortamı hazırlar."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    if "QT_QPA_FONTDIR" not in os.environ and Path(WINDOWS_FONT_DIR).is_dir():
        os.environ["QT_QPA_FONTDIR"] = WINDOWS_FONT_DIR


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", help="yazilacak PNG yolu")
    parser.add_argument("--channel", default="ch2", help="cizilecek kanal kimligi")
    parser.add_argument("--duration", type=float, default=60.0, help="simulasyon suresi (s)")
    parser.add_argument("--width", type=int, default=0, help="pencere genisligi")
    parser.add_argument("--height", type=int, default=0, help="pencere yuksekligi")
    args = parser.parse_args(argv)

    prepare_environment()

    from PySide6.QtGui import QFontDatabase
    from PySide6.QtWidgets import QApplication

    from sonar_analyzer.repository.mock_repository import MockRecordingRepository
    from sonar_analyzer.ui.main_window import DEFAULT_WINDOW_SIZE, MainWindow

    app = QApplication.instance() or QApplication([])

    families = QFontDatabase.families()
    if not families:
        print(
            "UYARI: hic yazi tipi bulunamadi; metinler kutu olarak cizilecek. "
            "QT_QPA_FONTDIR ayarlayin.",
            file=sys.stderr,
        )

    width = args.width or DEFAULT_WINDOW_SIZE[0]
    height = args.height or DEFAULT_WINDOW_SIZE[1]

    window = MainWindow()
    window.resize(width, height)
    window.show()
    app.processEvents()
    window.apply_default_layout()
    app.processEvents()

    window.set_repository(MockRecordingRepository(duration_s=args.duration))
    window.open_channel(args.channel)
    for _ in range(5):
        app.processEvents()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    pixmap = window.grab()
    if not pixmap.save(str(output), "PNG"):
        print(f"HATA: goruntu yazilamadi: {output}", file=sys.stderr)
        return 1

    print(f"{output} yazildi ({pixmap.width()}x{pixmap.height()}), {len(families)} yazi tipi")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
