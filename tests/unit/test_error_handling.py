"""Merkezi exception yakalama testleri — `F1-008`."""

from __future__ import annotations

import logging
import sys
import threading

import pytest

from sonar_analyzer.application.error_handling import (
    ErrorReport,
    ExceptionHandler,
    build_report,
    install_exception_handler,
    stderr_notifier,
)


def _raise(message: str = "sentetik hata") -> ErrorReport:
    try:
        raise ValueError(message)
    except ValueError as exc:
        return build_report(type(exc), exc, exc.__traceback__)


def test_report_carries_type_message_and_traceback() -> None:
    report = _raise()
    assert report.exc_type == "ValueError"
    assert report.message == "sentetik hata"
    assert "ValueError: sentetik hata" in report.traceback_text
    assert "test_error_handling.py" in report.traceback_text


def test_user_message_is_readable_and_hides_traceback() -> None:
    report = _raise()
    text = report.user_message
    assert "ValueError" in text
    assert "sentetik hata" in text
    assert "Traceback" not in text, "kullaniciya ham traceback gosterilmemeli"
    assert "loguna yazildi" in text


def test_user_message_handles_empty_exception_message() -> None:
    try:
        raise RuntimeError
    except RuntimeError as exc:
        report = build_report(type(exc), exc, exc.__traceback__)
    assert "(ayrinti yok)" in report.user_message


def test_handler_logs_and_notifies(caplog: pytest.LogCaptureFixture) -> None:
    seen: list[ErrorReport] = []
    handler = ExceptionHandler(notifier=seen.append)

    with caplog.at_level(logging.ERROR, logger="sonar_analyzer"):
        try:
            raise ValueError("kayit bozuk")
        except ValueError as exc:
            handler.handle(type(exc), exc, exc.__traceback__)

    assert len(seen) == 1
    assert seen[0].exc_type == "ValueError"
    assert "Islenmemis hata" in caplog.text
    assert "kayit bozuk" in caplog.text, "traceback log'a yazilmali"


def test_keyboard_interrupt_is_not_treated_as_error(caplog: pytest.LogCaptureFixture) -> None:
    """Kullanıcının durdurması hata kutusu üretmez, bilgi olarak loglanır."""
    seen: list[ErrorReport] = []
    handler = ExceptionHandler(notifier=seen.append)

    with caplog.at_level(logging.INFO, logger="sonar_analyzer"):
        try:
            raise KeyboardInterrupt
        except KeyboardInterrupt as exc:
            handler.handle(type(exc), exc, exc.__traceback__)

    assert seen == []
    assert handler.reports == []
    assert "Kullanici islemi durdurdu" in caplog.text


def test_failing_notifier_does_not_propagate(caplog: pytest.LogCaptureFixture) -> None:
    def broken(_: ErrorReport) -> None:
        raise OSError("bildirim penceresi acilamadi")

    handler = ExceptionHandler(notifier=broken)
    with caplog.at_level(logging.ERROR, logger="sonar_analyzer"):
        try:
            raise ValueError("asil hata")
        except ValueError as exc:
            handler.handle(type(exc), exc, exc.__traceback__)

    assert "Hata bildirimi gosterilemedi" in caplog.text


def test_install_and_uninstall_restore_hooks() -> None:
    original = sys.excepthook
    handler = install_exception_handler(notifier=lambda _: None)
    assert sys.excepthook is not original
    handler.uninstall()
    assert sys.excepthook is original


def test_background_thread_exception_is_captured() -> None:
    seen: list[ErrorReport] = []
    handler = ExceptionHandler(notifier=seen.append)
    handler.install()
    try:

        def boom() -> None:
            raise RuntimeError("arka plan hatasi")

        thread = threading.Thread(target=boom, name="worker-1")
        thread.start()
        thread.join(timeout=5)
    finally:
        handler.uninstall()

    assert len(seen) == 1
    assert seen[0].exc_type == "RuntimeError"
    assert seen[0].thread_name == "worker-1"


def test_stderr_notifier_writes_message(capsys: pytest.CaptureFixture[str]) -> None:
    stderr_notifier(_raise("diske yazilamadi"))
    captured = capsys.readouterr()
    assert "diske yazilamadi" in captured.err
    assert "Traceback" not in captured.err
