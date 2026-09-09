"""Format ve dosya erişim hatalarını gösterme — `F3-006`.

Kabul: kullanıcı mesajı anlaşılır; teknik ayrıntı logda bulunur.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.application.load_errors import LoadErrorMessage, describe_load_error
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


# -- ceviri: teknik tur -> anlasilir metin ---------------------------------


@pytest.mark.parametrize(
    ("error_type", "expected_fragment"),
    [
        ("TruncatedHeaderError", "baslik eksik"),
        ("InvalidMagicError", "imzasi uyusmuyor"),
        ("UnsupportedVersionError", "surumu bu uygulama tarafindan desteklenmiyor"),
        ("HeaderContractError", "beklenen duzene uymuyor"),
        ("HeaderCrcMismatchError", "butunlugu bozuk"),
        ("FileNotFoundError", "Dosya bulunamadi"),
        ("PermissionError", "erisim izni yok"),
        ("IsADirectoryError", "klasor"),
        ("OSError", "Dosya okunamadi"),
    ],
)
def test_known_error_types_get_a_plain_language_message(
    error_type: str, expected_fragment: str
) -> None:
    """Kabul kriteri (ilk yarı): kullanıcı mesajı anlaşılır."""
    message = describe_load_error(Path("C:/kayitlar/ornek.bin"), error_type, "ham teknik ileti")

    assert expected_fragment in message.user_text
    # Kullanici metni teknik terim ve traceback tasimaz.
    assert "Error" not in message.user_text
    assert "ham teknik ileti" not in message.user_text


def test_unknown_error_type_still_names_the_type() -> None:
    """Tanınmayan tür genel metinle gösterilir ama adı gizlenmez."""
    message = describe_load_error(Path("x.bin"), "GaripBirHata", "detay")

    assert "Dosya acilamadi" in message.user_text
    assert "GaripBirHata" in message.user_text


def test_technical_text_keeps_path_type_and_raw_message() -> None:
    """Kabul kriteri (ikinci yarı): teknik ayrıntı kaybolmaz."""
    message = describe_load_error(
        Path("C:/kayitlar/ornek.bin"), "TruncatedHeaderError", "kesik header: 32/20"
    )

    assert "ornek.bin" in message.technical_text
    assert "TruncatedHeaderError" in message.technical_text
    assert "kesik header: 32/20" in message.technical_text


def test_empty_raw_message_does_not_produce_a_dangling_detail() -> None:
    message = describe_load_error(Path("x.bin"), "OSError", "   ")
    assert message.technical_text.endswith("(ayrinti yok)")


def test_title_names_the_file() -> None:
    message = describe_load_error(Path("C:/a/b/kayit.bin"), "OSError", "x")
    assert message.title == "Dosya acilamadi: kayit.bin"


# -- pencere: kullaniciya gosterim + log ------------------------------------


def _open(qtbot: QtBot, window: MainWindow, paths: list[Path]) -> None:
    window.file_open._dialog = lambda _p, _s: [str(path) for path in paths]  # type: ignore[assignment]
    with qtbot.waitSignal(window.file_loader.request_finished, timeout=10_000):
        window.action("action_open").trigger()


def test_user_sees_a_plain_message_for_a_corrupt_file(qtbot: QtBot, tmp_path: Path) -> None:
    shown: list[LoadErrorMessage] = []

    def recorder(_parent: object, message: LoadErrorMessage) -> None:
        shown.append(message)

    window = MainWindow(error_notifier=recorder)
    qtbot.addWidget(window)
    target = tmp_path / "kesik.bin"
    shutil.copyfile(FIXTURES_DIR / "truncated_header.bin", target)

    _open(qtbot, window, [target])

    assert len(shown) == 1
    assert "baslik eksik" in shown[0].user_text
    assert shown[0].title == "Dosya acilamadi: kesik.bin"
    window.close()


def test_technical_detail_reaches_the_application_log(
    qtbot: QtBot, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Kabul kriteri: teknik ayrıntı **logda** bulunur."""
    window = MainWindow(error_notifier=lambda _p, _m: None)
    qtbot.addWidget(window)
    target = tmp_path / "surum.bin"
    shutil.copyfile(FIXTURES_DIR / "unsupported_version.bin", target)

    with caplog.at_level(logging.ERROR, logger="sonar_analyzer"):
        _open(qtbot, window, [target])

    logged = "\n".join(record.getMessage() for record in caplog.records)
    assert "UnsupportedVersionError" in logged
    assert "surum.bin" in logged
    window.close()


def test_operator_log_line_is_user_language_not_a_traceback(qtbot: QtBot, tmp_path: Path) -> None:
    window = MainWindow(error_notifier=lambda _p, _m: None)
    qtbot.addWidget(window)
    target = tmp_path / "bozuk.bin"
    target.write_bytes(b"gecersiz")

    _open(qtbot, window, [target])

    log_text = "\n".join(window.bottom_dock.log_lines())
    assert "Yuklenemedi: bozuk.bin" in log_text
    assert "Traceback" not in log_text
    window.close()


def test_missing_file_reports_a_file_access_message(qtbot: QtBot, tmp_path: Path) -> None:
    shown: list[LoadErrorMessage] = []
    window = MainWindow(error_notifier=lambda _p, m: shown.append(m))
    qtbot.addWidget(window)

    _open(qtbot, window, [tmp_path / "olmayan.bin"])

    assert len(shown) == 1
    assert "bulunamadi" in shown[0].user_text.lower()
    window.close()


def test_successful_load_shows_no_error(qtbot: QtBot, tmp_path: Path) -> None:
    shown: list[LoadErrorMessage] = []
    window = MainWindow(error_notifier=lambda _p, m: shown.append(m))
    qtbot.addWidget(window)
    target = tmp_path / "iyi.bin"
    shutil.copyfile(FIXTURES_DIR / "valid_8records.bin", target)

    _open(qtbot, window, [target])

    assert shown == []
    window.close()


def test_partly_failing_batch_reports_only_the_failing_file(qtbot: QtBot, tmp_path: Path) -> None:
    """Bir dosya bozuksa yalnız o bildirilir; sağlam dosya yine açılır."""
    shown: list[LoadErrorMessage] = []
    window = MainWindow(error_notifier=lambda _p, m: shown.append(m))
    qtbot.addWidget(window)

    good = tmp_path / "iyi.bin"
    shutil.copyfile(FIXTURES_DIR / "valid_8records.bin", good)
    bad = tmp_path / "bozuk.bin"
    bad.write_bytes(b"gecersiz")

    _open(qtbot, window, [good, bad])

    assert [message.path for message in shown] == [bad]
    assert [result.path for result in window.loaded_results] == [good]
    assert "iyi.bin" in window.left_dock.summary_value("File")
    window.close()
