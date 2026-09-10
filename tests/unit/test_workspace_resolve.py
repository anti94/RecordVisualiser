"""Workspace kaynak dosyalarını çözümleme — `F3-070`.

Kabul: eksik dosya bildirilir; sessizce atlanmaz.
"""

from __future__ import annotations

from collections.abc import Callable

from sonar_analyzer.workspace.resolve import SourceResolution, resolve_sources


def _present(*names: str) -> Callable[[str], bool]:
    known = set(names)

    def _exists(path: str) -> bool:
        return path in known

    return _exists


def test_all_present_when_every_path_exists() -> None:
    result = resolve_sources(["a.bin", "b.bin"], exists=_present("a.bin", "b.bin"))
    assert result == SourceResolution(found=["a.bin", "b.bin"], missing=[])
    assert result.all_present and not result.has_missing


def test_missing_paths_are_separated_not_dropped() -> None:
    result = resolve_sources(["a.bin", "gone.bin", "c.bin"], exists=_present("a.bin", "c.bin"))
    assert result.found == ["a.bin", "c.bin"]
    assert result.missing == ["gone.bin"]
    assert result.has_missing
    assert "gone.bin" in result.summary()


def test_input_order_is_preserved_within_each_bucket() -> None:
    result = resolve_sources(["1", "2", "3", "4"], exists=_present("2", "4"))
    assert result.found == ["2", "4"]
    assert result.missing == ["1", "3"]


def test_empty_input_is_all_present() -> None:
    result = resolve_sources([], exists=_present())
    assert result.all_present
    assert result.summary().startswith("0 ")
