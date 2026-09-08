"""Uygulama girişi ve temiz kapanış — `F1-007`.

`sonar-analyzer` komutu ve `python -m sonar_analyzer` bu modülün ``main``
fonksiyonunu çağırır.

Qt yalnız gerçekten pencere açılacağı zaman içe aktarılır. Böylece ``--version``
gibi komutlar PySide6 kurulu olmasa da çalışır ve hata iletisi anlaşılır olur.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from sonar_analyzer import __version__

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_MISSING_GUI = 3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sonar-analyzer",
        description="SONAR telemetri ve veri analiz arayuzu",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"sonar-analyzer {__version__}",
    )
    parser.add_argument(
        "--no-window",
        action="store_true",
        help="pencere acmadan baslatmayi dogrular (duman testi)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Uygulamayı başlatır ve çıkış kodunu döndürür."""
    args = build_parser().parse_args(argv)

    try:
        from PySide6.QtWidgets import QApplication

        from sonar_analyzer.ui.main_window import MainWindow
    except ImportError as exc:
        print(
            f'Arayuz katmani kurulu degil. Kurulum:\n    pip install -e ".[gui]"\nAyrinti: {exc}',
            file=sys.stderr,
        )
        return EXIT_MISSING_GUI

    app = QApplication.instance() or QApplication(list(sys.argv[:1]))
    if not isinstance(app, QApplication):  # pragma: no cover - savunma amacli
        print("QApplication olusturulamadi", file=sys.stderr)
        return EXIT_ERROR

    window = MainWindow()

    if args.no_window:
        # Pencere hic gosterilmeden yasam dongusu tamamlanir: giris yolunun
        # calistigini ekransiz ortamda da kanitlar.
        window.close()
        window.deleteLater()
        app.processEvents()
        return EXIT_OK

    window.show()
    return int(app.exec())


if __name__ == "__main__":  # pragma: no cover - modul dogrudan calistirildiginda
    raise SystemExit(main())
