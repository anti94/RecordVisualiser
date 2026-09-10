"""Dışa aktarma hedefi ve üzerine yazma kararı — `F3-065`.

Kabul: var olan dosya onaysız değişmez; raw/processed seçimi açıktır.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sonar_analyzer.application.export_controller import (
    DataVariant,
    ExportKind,
    ExportPlan,
    ensure_extension,
    kind_for_format,
    resolve_target,
)


def test_known_formats_map_to_a_kind() -> None:
    assert kind_for_format("CSV") is ExportKind.CSV
    assert kind_for_format("png") is ExportKind.PNG
    assert kind_for_format("Svg") is ExportKind.SVG


def test_not_yet_supported_formats_raise() -> None:
    with pytest.raises(KeyError, match="Desteklenmeyen"):
        kind_for_format("TSV")
    with pytest.raises(KeyError):
        kind_for_format("JSON")


def test_ensure_extension_appends_when_missing() -> None:
    assert ensure_extension(Path("out"), ExportKind.CSV) == Path("out.csv")
    assert ensure_extension(Path("plot.dat"), ExportKind.PNG) == Path("plot.dat.png")


def test_ensure_extension_keeps_a_correct_suffix() -> None:
    assert ensure_extension(Path("a/b/plot.png"), ExportKind.PNG) == Path("a/b/plot.png")
    assert ensure_extension(Path("PLOT.PNG"), ExportKind.PNG) == Path("PLOT.PNG")


def test_resolve_target_returns_the_path_when_the_file_is_new() -> None:
    dest = resolve_target(
        "report",
        ExportKind.CSV,
        exists=lambda _p: False,
        confirm_overwrite=lambda _p: pytest.fail("onay istenmemeli"),
    )
    assert dest == Path("report.csv")


def test_resolve_target_asks_before_overwriting_and_proceeds_on_yes() -> None:
    asked: list[Path] = []
    dest = resolve_target(
        "report.csv",
        ExportKind.CSV,
        exists=lambda _p: True,
        confirm_overwrite=lambda p: asked.append(p) or True,
    )
    assert dest == Path("report.csv")
    assert asked == [Path("report.csv")]


def test_resolve_target_aborts_when_overwrite_is_declined() -> None:
    dest = resolve_target(
        "report.csv",
        ExportKind.CSV,
        exists=lambda _p: True,
        confirm_overwrite=lambda _p: False,
    )
    assert dest is None  # çağıran hiçbir şey yazmamalı


def test_resolve_target_checks_existence_of_the_extended_path() -> None:
    seen: list[Path] = []

    def _exists(p: Path) -> bool:
        seen.append(p)
        return False

    resolve_target("out", ExportKind.SVG, exists=_exists, confirm_overwrite=lambda _p: True)
    assert seen == [Path("out.svg")]  # uzantı eklendikten SONRA kontrol edilir


def test_export_plan_flags() -> None:
    png = ExportPlan(kind=ExportKind.PNG, path=Path("a.png"))
    assert png.is_image and not png.wants_raw

    csv_raw = ExportPlan(kind=ExportKind.CSV, path=Path("a.csv"), variant=DataVariant.RAW)
    assert not csv_raw.is_image
    assert csv_raw.wants_raw
