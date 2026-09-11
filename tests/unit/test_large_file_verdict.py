"""Büyük dosya koşusunun §11.1 kararı — `F4-065`.

Kabul: Bölüm 11.1 hedeflerinin geçtiği veya saptığı kanıtlanır.

İki katman denetlenir: karar kuralları (elle kurulmuş koşularla, sınırlar
dahil) ve **gerçekten işlenmiş** koşu — depoya girmiş
`docs/perf/results/large-file.json` üzerinde üretilen kararın depoya
girmiş `large-file-verdict.json` ile birebir aynı olması.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from tools.evaluate_large_file_run import (
    DEVIATED,
    INSUFFICIENT,
    PASSED,
    evaluate,
    evaluate_frame_rate,
    evaluate_memory,
    evaluate_metadata,
    evaluate_queries,
    to_markdown,
)

RESULTS = Path(__file__).resolve().parents[2] / "docs" / "perf" / "results"
RUN_PATH = RESULTS / "large-file.json"
VERDICT_PATH = RESULTS / "large-file-verdict.json"


def _file(
    name: str,
    *,
    file_bytes: int = 1_000_000,
    metadata_seconds: float = 0.001,
    query_ms: tuple[float, ...] = (10.0,),
    fps: float = 60.0,
    peak_per_file_byte: float = 0.1,
    frames: int = 10,
    truncated: bool = False,
) -> dict[str, Any]:
    return {
        "path": f"/tmp/{name}.bin",
        "file_bytes": file_bytes,
        "metadata": {"seconds": metadata_seconds},
        "queries": [
            {"label": f"q{index}", "duration_ms": value} for index, value in enumerate(query_ms)
        ],
        "frame_rate": {
            "pipeline_fps": fps,
            "frames_completed": frames,
            "frames_requested": frames,
            "frame_ms_p50": 1000.0 / fps if fps else 0.0,
            "truncated": truncated,
        },
        "memory": {"peak_per_file_byte": peak_per_file_byte},
    }


def _report(*files: dict[str, Any]) -> dict[str, Any]:
    return {
        "benchmark": "large-file",
        "machine": {"platform": "test"},
        "targets": {"metadata_seconds": 5.0, "query_ms": 150.0, "pipeline_fps": 30.0},
        "files": list(files),
    }


# --------------------------------------------------------------------------- #
# metadata
# --------------------------------------------------------------------------- #


def test_metadata_inside_the_budget_passes() -> None:
    verdict = evaluate_metadata([_file("a", metadata_seconds=4.999)], 5.0)
    assert verdict.status == PASSED
    assert verdict.passed
    assert "4999" in verdict.measured.replace(".", "")


def test_metadata_exactly_at_the_budget_passes() -> None:
    assert evaluate_metadata([_file("a", metadata_seconds=5.0)], 5.0).status == PASSED


def test_metadata_over_the_budget_deviates() -> None:
    verdict = evaluate_metadata([_file("a", metadata_seconds=5.001)], 5.0)
    assert verdict.status == DEVIATED
    assert not verdict.passed


def test_the_worst_file_decides_the_metadata_verdict() -> None:
    verdict = evaluate_metadata(
        [_file("fast", metadata_seconds=0.1), _file("slow", metadata_seconds=9.0)], 5.0
    )
    assert verdict.status == DEVIATED
    assert "slow" in verdict.measured


# --------------------------------------------------------------------------- #
# sorgu
# --------------------------------------------------------------------------- #


def test_most_queries_inside_the_budget_pass() -> None:
    verdict = evaluate_queries([_file("a", query_ms=(10.0, 20.0, 900.0))], 150.0)
    assert verdict.status == PASSED
    assert "2/3" in verdict.measured


def test_exactly_half_is_not_most_and_deviates() -> None:
    """'Çoğu durumda' > %50 demektir; tam yarı yeterli değildir."""
    verdict = evaluate_queries([_file("a", query_ms=(10.0, 900.0))], 150.0)
    assert verdict.status == DEVIATED
    assert "1/2" in verdict.measured


def test_no_query_inside_the_budget_deviates_and_names_the_worst() -> None:
    verdict = evaluate_queries([_file("a", query_ms=(300.0, 15_000.0))], 150.0)
    assert verdict.status == DEVIATED
    assert "0/2" in verdict.measured
    assert "a/q1" in verdict.detail
    assert "100x" in verdict.detail  # 15000 / 150


def test_queries_from_every_file_are_counted() -> None:
    verdict = evaluate_queries(
        [_file("a", query_ms=(10.0, 10.0)), _file("b", query_ms=(900.0, 900.0))], 150.0
    )
    assert "2/4" in verdict.measured
    assert verdict.status == DEVIATED


def test_a_run_without_queries_is_refused() -> None:
    with pytest.raises(ValueError, match="sorgu"):
        evaluate_queries([_file("a", query_ms=())], 150.0)


# --------------------------------------------------------------------------- #
# FPS
# --------------------------------------------------------------------------- #


def test_frame_rate_above_the_floor_passes() -> None:
    assert evaluate_frame_rate([_file("a", fps=30.0)], 30.0).status == PASSED


def test_the_slowest_file_decides_the_frame_rate_verdict() -> None:
    verdict = evaluate_frame_rate([_file("fast", fps=90.0), _file("slow", fps=0.5)], 30.0)
    assert verdict.status == DEVIATED
    assert "slow" in verdict.measured
    assert "0.50 FPS" in verdict.measured


def test_a_truncated_run_says_so() -> None:
    verdict = evaluate_frame_rate([_file("a", fps=0.2, truncated=True)], 30.0)
    assert "kesildi" in verdict.measured


def test_the_frame_rate_verdict_states_the_paint_exclusion() -> None:
    assert "Qt paint hariç" in evaluate_frame_rate([_file("a")], 30.0).detail


# --------------------------------------------------------------------------- #
# bellek olceklenmesi
# --------------------------------------------------------------------------- #


def test_a_single_file_cannot_answer_the_linearity_question() -> None:
    verdict = evaluate_memory([_file("a")])
    assert verdict.status == INSUFFICIENT
    assert "--input" in verdict.detail


def test_two_files_too_close_in_size_are_insufficient() -> None:
    verdict = evaluate_memory([_file("a", file_bytes=1_000_000), _file("b", file_bytes=1_500_000)])
    assert verdict.status == INSUFFICIENT


def test_a_constant_footprint_passes() -> None:
    """Bellek sabitse bayt başına oran boyut kadar düşer."""
    verdict = evaluate_memory(
        [
            _file("small", file_bytes=64_000_000, peak_per_file_byte=5.0),
            _file("large", file_bytes=1_024_000_000, peak_per_file_byte=5.0 / 16),
        ]
    )
    assert verdict.status == PASSED
    assert "0.06x" in verdict.measured


def test_a_footprint_that_scales_with_the_file_deviates() -> None:
    verdict = evaluate_memory(
        [
            _file("small", file_bytes=64_000_000, peak_per_file_byte=5.11),
            _file("large", file_bytes=1_000_000_000, peak_per_file_byte=5.11),
        ]
    )
    assert verdict.status == DEVIATED
    assert "1.00x" in verdict.measured
    assert "15.6x büyüdü" in verdict.detail


def test_halving_the_per_byte_cost_is_the_boundary() -> None:
    """Sınır: oran yarıya inmezse doğrusal sayılır."""
    scaled = evaluate_memory(
        [
            _file("small", file_bytes=1_000_000, peak_per_file_byte=1.0),
            _file("large", file_bytes=4_000_000, peak_per_file_byte=0.5),
        ]
    )
    assert scaled.status == DEVIATED  # tam 0.50x, "< 0.50" degil
    better = evaluate_memory(
        [
            _file("small", file_bytes=1_000_000, peak_per_file_byte=1.0),
            _file("large", file_bytes=4_000_000, peak_per_file_byte=0.49),
        ]
    )
    assert better.status == PASSED


# --------------------------------------------------------------------------- #
# butun karar
# --------------------------------------------------------------------------- #


def test_a_run_that_meets_every_target_passes_overall() -> None:
    result = evaluate(
        _report(
            _file(
                "small", file_bytes=64_000_000, query_ms=(10.0,), fps=60.0, peak_per_file_byte=5.0
            ),
            _file(
                "large",
                file_bytes=1_024_000_000,
                query_ms=(20.0,),
                fps=45.0,
                peak_per_file_byte=5.0 / 16,
            ),
        )
    )
    assert result["status"] == PASSED
    assert result["deviated"] == []
    assert result["insufficient"] == []
    assert len(result["passed"]) == 4


def test_every_target_is_decided_once() -> None:
    result = evaluate(_report(_file("a")))
    assert [item["target"] for item in result["verdicts"]] == [
        "metadata_seconds",
        "query_ms",
        "pipeline_fps",
        "memory_scaling",
    ]
    assert result["task"] == "F4-065"
    assert result["files_measured"] == ["a"]
    assert result["machine"] == {"platform": "test"}


def test_an_insufficient_target_keeps_the_run_from_passing() -> None:
    result = evaluate(_report(_file("a")))  # tek dosya -> bellek yetersiz
    assert result["insufficient"] == ["memory_scaling"]
    assert result["status"] == DEVIATED


def test_an_empty_run_is_refused() -> None:
    with pytest.raises(ValueError, match="files"):
        evaluate({"files": []})


def test_the_markdown_has_one_row_per_target() -> None:
    text = to_markdown(evaluate(_report(_file("a"))))
    lines = text.splitlines()
    assert lines[0].startswith("| Hedef |")
    assert len(lines) == 6  # baslik + ayrac + dort hedef
    assert "`metadata_seconds`" in text


# --------------------------------------------------------------------------- #
# depodaki gercek kosu
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("stem", ["large-file", "large-file-indexed", "large-file-streaming"])
def test_the_recorded_verdict_matches_the_recorded_run(stem: str) -> None:
    """Depodaki karar, depodaki ölçümden **yeniden üretilebilir**."""
    run = json.loads((RESULTS / f"{stem}.json").read_text(encoding="utf-8"))
    recorded = json.loads((RESULTS / f"{stem}-verdict.json").read_text(encoding="utf-8"))
    assert evaluate(run) == recorded


def test_the_recorded_run_proves_which_targets_deviate() -> None:
    recorded = json.loads(VERDICT_PATH.read_text(encoding="utf-8"))
    assert recorded["passed"] == ["metadata_seconds"]
    assert recorded["deviated"] == ["query_ms", "pipeline_fps", "memory_scaling"]
    assert recorded["insufficient"] == []
    assert recorded["status"] == DEVIATED
    assert recorded["files_measured"] == [
        "profile-b-64mb",
        "profile-b-256mb",
        "profile-b-1gb",
    ]


def test_the_recorded_run_spans_enough_sizes_to_judge_memory() -> None:
    run = json.loads(RUN_PATH.read_text(encoding="utf-8"))
    sizes = sorted(int(entry["file_bytes"]) for entry in run["files"])
    assert sizes[-1] / sizes[0] > 15.0  # 64 MB -> 1 GB
    assert sizes[-1] >= 1_000_000_000


def test_the_streaming_run_proves_every_target_now_passes() -> None:
    """`F4-094`/`F4-095` sonrası: dört §11.1 hedefinin hepsi geçer."""
    recorded = json.loads((RESULTS / "large-file-streaming-verdict.json").read_text("utf-8"))
    assert recorded["passed"] == [
        "metadata_seconds",
        "query_ms",
        "pipeline_fps",
        "memory_scaling",
    ]
    assert recorded["deviated"] == []
    assert recorded["insufficient"] == []
    assert recorded["status"] == PASSED
    assert recorded["files_measured"] == [
        "profile-b-64mb",
        "profile-b-256mb",
        "profile-b-1gb",
    ]
