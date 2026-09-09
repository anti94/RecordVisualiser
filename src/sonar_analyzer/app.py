"""Uygulama girişi ve temiz kapanış — `F1-007`.

`sonar-analyzer` komutu ve `python -m sonar_analyzer` bu modülün ``main``
fonksiyonunu çağırır.

Qt yalnız gerçekten pencere açılacağı zaman içe aktarılır. Böylece ``--version``
gibi komutlar PySide6 kurulu olmasa da çalışır ve hata iletisi anlaşılır olur.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence

from sonar_analyzer import __version__
from sonar_analyzer.application.error_handling import (
    install_exception_handler,
    qt_notifier,
)
from sonar_analyzer.logging.setup import setup_logging
from sonar_analyzer.settings.store import load_settings

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

    # Log ve ayarlar Qt'den once kurulur: GUI hic acilamasa bile ne oldugu
    # log'a yazilmis olur (F1-009, F1-010).
    session = setup_logging()
    logger = logging.getLogger("sonar_analyzer")
    settings_result = load_settings()
    for warning in settings_result.warnings:
        logger.warning("Ayar uyarisi: %s", warning)

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

    # Islenmemis hatalar sessizce kaybolmasin (F1-008).
    install_exception_handler(qt_notifier)

    logger.info("Arayuz baslatiliyor (oturum %s)", session.session_id)
    window = MainWindow(settings=settings_result.settings)

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
