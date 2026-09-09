"""Son açılan dosyalar listesi kuralı — `F3-008`.

Kabul: yeniden açılışta liste korunur; eksik dosya anlaşılır hata verir
(ikinci yarı `tests/gui/test_recent_files_persistence.py`'de).
"""

from __future__ import annotations

from pathlib import Path

from sonar_analyzer.application.recent_files import (
    MAX_RECENT_FILES,
    add,
    add_all,
    default_directory,
    drop,
)


def test_add_puts_the_new_path_first() -> None:
    result = add([], Path("C:/kayit/a.bin"))
    assert result == ["C:\\kayit\\a.bin"]


def test_add_moves_a_reopened_file_to_the_front() -> None:
    existing = ["C:\\a.bin", "C:\\b.bin", "C:\\c.bin"]
    result = add(existing, Path("C:/b.bin"))
    assert result == ["C:\\b.bin", "C:\\a.bin", "C:\\c.bin"]


def test_add_deduplicates_case_and_separator_differences() -> None:
    existing = ["C:\\Kayit\\A.BIN"]
    result = add(existing, Path("c:/kayit/a.bin"))
    assert len(result) == 1
    assert result[0] == "c:\\kayit\\a.bin"


def test_add_respects_the_limit() -> None:
    existing = [f"C:\\f{i}.bin" for i in range(MAX_RECENT_FILES)]
    result = add(existing, Path("C:/new.bin"), limit=MAX_RECENT_FILES)
    assert len(result) == MAX_RECENT_FILES
    assert result[0] == "C:\\new.bin"
    assert result[-1] != f"C:\\f{MAX_RECENT_FILES - 1}.bin"  # en eski dustu


def test_add_all_preserves_selection_order_with_newest_first() -> None:
    """Çoklu seçimde [a, b, c] seçildiyse listede a, b, c sırasıyla görünür."""
    paths = [Path("C:/a.bin"), Path("C:/b.bin"), Path("C:/c.bin")]
    result = add_all([], paths)
    assert result == ["C:\\a.bin", "C:\\b.bin", "C:\\c.bin"]


def test_add_all_on_top_of_existing_history() -> None:
    existing = ["C:\\old.bin"]
    paths = [Path("C:/a.bin"), Path("C:/b.bin")]
    result = add_all(existing, paths)
    assert result == ["C:\\a.bin", "C:\\b.bin", "C:\\old.bin"]


def test_drop_removes_a_missing_file() -> None:
    existing = ["C:\\a.bin", "C:\\b.bin"]
    result = drop(existing, Path("C:/a.bin"))
    assert result == ["C:\\b.bin"]


def test_drop_is_a_no_op_for_an_absent_entry() -> None:
    existing = ["C:\\a.bin"]
    assert drop(existing, Path("C:/other.bin")) == existing


def test_default_directory_uses_the_most_recent_file() -> None:
    existing = ["C:\\kayit\\a.bin", "C:\\eski\\b.bin"]
    assert default_directory(existing) == "C:\\kayit"


def test_default_directory_falls_back_when_empty() -> None:
    assert default_directory([], fallback="C:\\varsayilan") == "C:\\varsayilan"
