"""Süreler monoton saatten gelir; hata ölçümü asıl istisnayı değiştirmez."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from sonar_analyzer.logging import performance


@pytest.mark.parametrize("fail", [False, True])
def test_elapsed_time_and_error_status(fail: bool) -> None:
    original = ValueError("expected")
    with (
        patch.object(performance, "perf_counter", side_effect=[10.0, 10.125]),
        patch.object(performance.logger, "info") as log,
    ):
        try:
            with performance.measure("query", channel_id="ch0"):
                if fail:
                    raise original
        except ValueError as exc:
            assert fail and exc is original
        log.assert_called_once()
        assert log.call_args is not None
        payload = json.loads(log.call_args.args[1])
        assert payload == {
            "operation": "query",
            "channel_id": "ch0",
            "duration_ms": 125.0,
            "status": "error" if fail else "ok",
        }
