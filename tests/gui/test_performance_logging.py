"""Gerçek aç/sorgula/çiz akışı aynı oturumda ayrı maliyetler kaydeder."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest
from tests.golden_bytes import build_valid_fixture

pytest.importorskip("PySide6")
pytest.importorskip("pyqtgraph")

from pytestqt.qtbot import QtBot

from sonar_analyzer.logging.setup import LOGGER_NAME, setup_logging
from sonar_analyzer.repository.file_repository import FileRecordingRepository
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui


def test_index_query_and_render_share_one_session(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    logger = logging.getLogger(LOGGER_NAME)
    monkeypatch.setattr(logger, "handlers", [])
    monkeypatch.setattr(logger, "level", logger.level)
    monkeypatch.setattr(logger, "propagate", logger.propagate)
    setup = setup_logging(tmp_path / "logs", session_id="perf-test", console=False)
    source = tmp_path / "fixture.bin"
    source.write_bytes(build_valid_fixture(record_count=100))
    try:
        with FileRecordingRepository() as repo:
            repo.open(source)
            win = MainWindow()
            qtbot.addWidget(win)
            win.set_repository(repo)
            win.open_channel("ch0")
            win.close()
        lines = [
            line
            for line in setup.log_file.read_text(encoding="utf-8").splitlines()
            if "performance {" in line
        ]
        records = [json.loads(line.split("performance ", 1)[1]) for line in lines]
        operations = {record["operation"] for record in records}
        assert {"index", "query", "render.plot", "render.analysis"} <= operations
        assert all("perf-test" in line for line in lines)
        assert all(record["duration_ms"] >= 0 and record["status"] == "ok" for record in records)
        assert {record["kind"] for record in records if record["operation"] == "query"} == {
            "analysis",
            "display",
        }
        assert not any("values" in record or "timestamps" in record for record in records)
        analysis = [record for record in records if record["operation"] == "render.analysis"]
        assert len(analysis) == 1  # gizli sekmelere sahte render maliyeti yazılmaz
    finally:
        for handler in logger.handlers:
            handler.close()
