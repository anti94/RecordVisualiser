"""Uygulama girişi ve temiz kapanış — `F1-007`.

`sonar-analyzer` komutu ve `python -m sonar_analyzer` bu modülün ``main``
fonksiyonunu çağırır.

Qt yalnız gerçekten pencere açılacağı zaman içe aktarılır. Böylece ``--version``
gibi komutlar PySide6 kurulu olmasa da çalışır ve hata iletisi anlaşılır olur.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import traceback
from collections.abc import Sequence
from pathlib import Path

from sonar_analyzer import __version__
from sonar_analyzer.application.bin_check import run_bin_check
from sonar_analyzer.application.error_handling import (
    install_exception_handler,
    qt_notifier,
)
from sonar_analyzer.application.layout_report import build_layout_report
from sonar_analyzer.application.self_check import run_self_check
from sonar_analyzer.logging.setup import setup_logging
from sonar_analyzer.resources import app_icon_path
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
    parser.add_argument(
        "--bin-check",
        type=Path,
        metavar="BIN",
        help="ornek kaydi acar, CSV/PNG uretir ve ikisini geri okur",
    )
    parser.add_argument(
        "--bin-check-out",
        type=Path,
        default=None,
        metavar="DIZIN",
        help="--bin-check ciktilarinin yazilacagi dizin",
    )
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="tema, ikon ve Qt platform plugin'inin yuklendigini dogrular",
    )
    parser.add_argument(
        "--layout-report",
        type=Path,
        default=None,
        metavar="JSON",
        help="ana ekrani olcer ve raporu JSON olarak yazar (F6-031)",
    )
    parser.add_argument(
        "--layout-source",
        type=Path,
        default=None,
        metavar="BIN",
        help="--layout-report icin analiz denetiminde kullanilacak kayit",
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

    # F6-003: ikon paketten (ya da kaynak agacindan) yuklenir. Bulunamazsa
    # uygulama acilmaya devam eder ama bu LOGLANIR; sessizce ikonsuz
    # calismak, paketin eksik ciktigini gizlerdi.
    icon_path = app_icon_path()
    if icon_path is None:
        logger.warning("Uygulama ikonu bulunamadi; varsayilan ikon kullanilacak")
    else:
        from PySide6.QtGui import QIcon

        app.setWindowIcon(QIcon(str(icon_path)))

    logger.info("Arayuz baslatiliyor (oturum %s)", session.session_id)
    window = MainWindow(settings=settings_result.settings)

    if args.bin_check is not None:
        out_dir = args.bin_check_out or (args.bin_check.parent / "bin-check-out")
        bin_report = run_bin_check(args.bin_check, out_dir)
        for line in bin_report.lines:
            print(line)
        window.close()
        window.deleteLater()
        app.processEvents()
        return EXIT_OK if bin_report.ok else EXIT_ERROR

    if args.self_check:
        report = run_self_check(app, window)
        for line in report.lines:
            print(line)
        window.close()
        window.deleteLater()
        app.processEvents()
        return EXIT_OK if report.ok else EXIT_ERROR

    if args.layout_report is not None:
        # F6-031: rapor GOSTERILMIS pencereden olculur. Gosterilmeyen bir
        # pencerede dock alanlari ve boyutlar henuz yerlesmemis olur;
        # olculen sey kullanicinin gordugu ekran olmazdi.
        window.show()
        window.apply_default_layout()
        app.processEvents()
        try:
            layout = build_layout_report(window, args.layout_source)
        except Exception:
            # Tanilama komutunun cokmesi sessiz kalmamali ama modal bir
            # hata penceresi de acmamali: ekransiz/CI calismasinda o
            # pencere kimseye gorunmez ve sureci sonsuza kadar bekletir.
            traceback.print_exc()
            window.close()
            window.deleteLater()
            app.processEvents()
            return EXIT_ERROR
        args.layout_report.parent.mkdir(parents=True, exist_ok=True)
        args.layout_report.write_text(
            json.dumps(layout.data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        for line in layout.lines:
            print(line)
        window.close()
        window.deleteLater()
        app.processEvents()
        return EXIT_OK if layout.ok else EXIT_ERROR

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
