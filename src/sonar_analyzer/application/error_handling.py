"""Merkezi exception yakalama — `F1-008`.

Amaç: hiçbir işlenmemiş istisnanın sessizce kaybolmaması ve kullanıcıya ham
traceback yerine okunabilir bir ileti gösterilmesi (plan Bölüm 12).

Katman kuralı: bu modül **Qt'yi içe aktarmaz**. Kullanıcıya bildirme işi
dışarıdan verilen bir `notifier` ile yapılır; GUI kurulu değilse veya
kurulmamışsa ileti stderr'e yazılır.
"""

from __future__ import annotations

import logging
import sys
import threading
import traceback
from dataclasses import dataclass
from types import TracebackType
from typing import Callable, Optional

logger = logging.getLogger("sonar_analyzer")

#: Kullanıcıya gösterilecek iletiyi alan geri çağrı.
Notifier = Callable[["ErrorReport"], None]

ExceptionHook = Callable[
    [type[BaseException], BaseException, Optional[TracebackType]],
    None,
]


@dataclass(frozen=True)
class ErrorReport:
    """Tek bir işlenmemiş hatanın kullanıcıya ve log'a giden gösterimi."""

    exc_type: str
    message: str
    traceback_text: str
    thread_name: str

    @property
    def user_message(self) -> str:
        """Kullanıcıya gösterilecek kısa metin — traceback içermez."""
        detail = self.message.strip() or "(ayrinti yok)"
        return (
            "Beklenmeyen bir hata olustu ve islem tamamlanamadi.\n\n"
            f"Hata turu: {self.exc_type}\n"
            f"Ayrinti: {detail}\n\n"
            "Teknik ayrinti uygulama loguna yazildi."
        )


def build_report(
    exc_type: type[BaseException],
    exc: BaseException,
    tb: TracebackType | None,
    thread_name: str | None = None,
) -> ErrorReport:
    return ErrorReport(
        exc_type=exc_type.__name__,
        message=str(exc),
        traceback_text="".join(traceback.format_exception(exc_type, exc, tb)),
        thread_name=thread_name or threading.current_thread().name,
    )


def stderr_notifier(report: ErrorReport) -> None:
    """GUI yokken kullanılan öntanımlı bildirim."""
    print(report.user_message, file=sys.stderr)


def qt_notifier(report: ErrorReport) -> None:
    """Qt çalışıyorsa hata kutusu gösterir, yoksa stderr'e düşer."""
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
    except ImportError:
        stderr_notifier(report)
        return

    if QApplication.instance() is None:
        stderr_notifier(report)
        return

    box = QMessageBox()
    box.setIcon(QMessageBox.Icon.Critical)
    box.setWindowTitle("Hata")
    box.setText(report.user_message)
    box.setDetailedText(report.traceback_text)
    box.exec()


class ExceptionHandler:
    """Ana iş parçacığı ve arka plan iş parçacıkları için tek giriş noktası."""

    def __init__(self, notifier: Notifier | None = None) -> None:
        self._notifier: Notifier = notifier or stderr_notifier
        self._previous_hook: ExceptionHook | None = None
        self._previous_thread_hook: object | None = None
        self.reports: list[ErrorReport] = []

    def handle(
        self,
        exc_type: type[BaseException],
        exc: BaseException,
        tb: TracebackType | None,
        thread_name: str | None = None,
    ) -> None:
        """Hatayı loglar ve kullanıcıya bildirir. Kendisi asla istisna atmaz."""
        if issubclass(exc_type, KeyboardInterrupt):
            # Kullanicinin bilerek durdurmasi hata degildir: hata kutusu
            # gosterilmez ve rapor uretilmez. Onceki hook'a devredilmez;
            # devredilseydi ayni olay bir de yorumlayicinin varsayilan
            # ciktisi olarak yazilirdi.
            logger.info("Kullanici islemi durdurdu (KeyboardInterrupt)")
            return

        report = build_report(exc_type, exc, tb, thread_name)
        self.reports.append(report)

        logger.error(
            "Islenmemis hata (%s): %s",
            report.thread_name,
            report.exc_type,
            exc_info=(exc_type, exc, tb),
        )

        try:
            self._notifier(report)
        except Exception:  # pragma: no cover - bildirim kendisi patlarsa
            logger.exception("Hata bildirimi gosterilemedi")

    def install(self) -> None:
        """`sys.excepthook` ve iş parçacığı hook'unu devralır."""
        self._previous_hook = sys.excepthook
        sys.excepthook = self.handle

        thread_excepthook = getattr(threading, "excepthook", None)
        if thread_excepthook is not None:
            self._previous_thread_hook = thread_excepthook
            threading.excepthook = self._handle_thread

    def uninstall(self) -> None:
        """Önceki hook'ları geri koyar."""
        if self._previous_hook is not None:
            sys.excepthook = self._previous_hook
            self._previous_hook = None
        if self._previous_thread_hook is not None:
            threading.excepthook = self._previous_thread_hook  # type: ignore[assignment]
            self._previous_thread_hook = None

    def _handle_thread(self, args: threading.ExceptHookArgs) -> None:
        if args.exc_type is SystemExit:
            return
        exc = args.exc_value if args.exc_value is not None else args.exc_type()
        thread_name = args.thread.name if args.thread is not None else None
        self.handle(args.exc_type, exc, args.exc_traceback, thread_name)


def install_exception_handler(notifier: Notifier | None = None) -> ExceptionHandler:
    """Uygulama açılışında çağrılır; kurulan handler'ı döndürür."""
    handler = ExceptionHandler(notifier)
    handler.install()
    return handler
