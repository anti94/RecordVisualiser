"""Dönen log ve oturum kimliği testleri — `F1-010`."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from sonar_analyzer import __version__
from sonar_analyzer.logging.setup import (
    LOGGER_NAME,
    PayloadRedactingFilter,
    new_session_id,
    setup_logging,
)


def _read_log(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_session_id_is_short_and_unique() -> None:
    first, second = new_session_id(), new_session_id()
    assert first != second
    assert len(first) == 8


def test_log_line_contains_version_and_session(tmp_path: Path) -> None:
    setup = setup_logging(tmp_path, session_id="abc12345", console=False)
    logging.getLogger(LOGGER_NAME).info("dosya acildi")

    text = _read_log(setup.log_file)
    assert __version__ in text
    assert "abc12345" in text
    assert "dosya acildi" in text


def test_log_file_rotates(tmp_path: Path) -> None:
    setup = setup_logging(tmp_path, session_id="rot00001", console=False, max_bytes=2048)
    logger = logging.getLogger(LOGGER_NAME)

    for index in range(400):
        logger.info("satir %d - %s", index, "x" * 60)

    rotated = sorted(p.name for p in tmp_path.glob("sonar_analyzer.log*"))
    assert len(rotated) > 1, f"log donmedi: {rotated}"
    assert setup.log_file.stat().st_size <= 4096


def test_raw_bytes_payload_is_not_written(tmp_path: Path) -> None:
    setup = setup_logging(tmp_path, session_id="sec00001", console=False)
    payload = bytes(range(256)) * 4  # 1024 bayt ham veri

    logging.getLogger(LOGGER_NAME).info("kayit alindi: %s", payload)

    text = _read_log(setup.log_file)
    assert "icerik yazilmadi" in text
    assert "len=1024" in text
    # Ham baytlarin metin gosterimi log'a girmemeli.
    assert "\\x00\\x01\\x02" not in text
    assert repr(payload) not in text


def test_numpy_array_payload_is_not_written(tmp_path: Path) -> None:
    setup = setup_logging(tmp_path, session_id="sec00002", console=False)
    samples = np.arange(12000, dtype=np.int16)

    logging.getLogger(LOGGER_NAME).info("kanal verisi: %s", samples)

    text = _read_log(setup.log_file)
    assert "icerik yazilmadi" in text
    assert "shape=(12000,)" in text
    assert "dtype=int16" in text


def test_short_values_are_kept() -> None:
    redactor = PayloadRedactingFilter(limit=32)
    record = logging.LogRecord(
        name=LOGGER_NAME,
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="kisa deger: %s",
        args=(b"ENDR",),
        exc_info=None,
    )
    assert redactor.filter(record)
    assert record.args == (b"ENDR",), "kisa degerler okunabilir kalmali"


def test_setup_replaces_previous_handlers(tmp_path: Path) -> None:
    setup_logging(tmp_path / "birinci", session_id="aaa00001", console=False)
    setup_logging(tmp_path / "ikinci", session_id="bbb00002", console=False)

    logger = logging.getLogger(LOGGER_NAME)
    assert len(logger.handlers) == 1, "eski handler'lar birikmemeli"

    logger.info("ikinci oturum")
    ikinci = _read_log(tmp_path / "ikinci" / "sonar_analyzer.log")
    assert "bbb00002" in ikinci
    assert "ikinci oturum" in ikinci
