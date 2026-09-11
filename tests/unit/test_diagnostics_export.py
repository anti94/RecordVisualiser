"""Tanılama önizleme ve dışa aktarım — `F6-020`.

Kabul: **Kullanıcı içeriği görür; yalnız seçili öğeler pakete girer.**

İki yarı da ancak arşiv **açılarak** doğrulanabilir: önizlemede ne
yazdığına bakmak yetmez, arşivin içinde ne olduğuna bakmak gerekir. Bu
yüzden testlerin çoğu üretilen `zip`'i açıp içindekileri sayar.

En önemlisi, seçilmeyen bir ham kaydın arşivde **hiç** bulunmamasıdır:
kullanıcının ölçüm verisi, seçmediği hâlde gönderilmiş olmamalı.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from sonar_analyzer.application.diagnostics import (
    DiagnosticItem,
    ItemCategory,
    build_manifest,
)
from sonar_analyzer.application.diagnostics_export import (
    SUMMARY_NAME,
    Selection,
    export,
    preview,
)


def _setup(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Log, ayar ve ham kayıt dosyaları kurar."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    (log_dir / "uygulama.log").write_text("log satiri", encoding="utf-8")

    settings = tmp_path / "settings.json"
    settings.write_text('{"theme": "dark"}', encoding="utf-8")

    recording = tmp_path / "kayit.bin"
    recording.write_bytes(b"OLCUM-VERISI" * 50)
    return (log_dir, settings, recording)


def _manifest(tmp_path: Path):
    log_dir, settings, recording = _setup(tmp_path)
    return build_manifest(
        session_id="s1",
        app_version="3.20.0",
        log_dir=log_dir,
        settings_path=settings,
        recording_paths=[recording],
    )


def _names_in(archive_path: Path) -> set[str]:
    with zipfile.ZipFile(archive_path) as archive:
        return set(archive.namelist())


# --------------------------------------------------------------------------- #
# YALNIZ SECILI OGELER PAKETE GIRER
# --------------------------------------------------------------------------- #


def test_the_default_selection_excludes_raw_data(tmp_path: Path) -> None:
    selection = Selection.from_defaults(_manifest(tmp_path))
    assert selection.includes_raw_data is False


def test_an_unselected_recording_is_not_in_the_archive(tmp_path: Path) -> None:
    """Asıl kabul: seçilmeyen ölçüm verisi arşive hiç girmemeli."""
    selection = Selection.from_defaults(_manifest(tmp_path))
    result = export(selection, tmp_path / "paket.zip")

    names = _names_in(result.path)
    assert not any("kayit.bin" in name for name in names)


def test_the_selected_log_is_in_the_archive(tmp_path: Path) -> None:
    selection = Selection.from_defaults(_manifest(tmp_path))
    result = export(selection, tmp_path / "paket.zip")

    assert any("uygulama.log" in name for name in _names_in(result.path))


def test_an_explicitly_added_recording_is_included(tmp_path: Path) -> None:
    """Kullanıcı açıkça eklerse girer; karar onun."""
    manifest = _manifest(tmp_path)
    selection = Selection.from_defaults(manifest)
    raw = manifest.by_category(ItemCategory.RAW_DATA)[0]
    selection.add(raw)

    result = export(selection, tmp_path / "paket.zip")

    assert selection.includes_raw_data is True
    assert any("kayit.bin" in name for name in _names_in(result.path))


def test_removing_an_item_keeps_it_out_of_the_archive(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    selection = Selection.from_defaults(manifest)
    log_item = manifest.by_category(ItemCategory.ERROR_LOG)[0]
    selection.remove(log_item)

    result = export(selection, tmp_path / "paket.zip")

    assert not any("uygulama.log" in name for name in _names_in(result.path))


def test_the_same_item_is_not_added_twice(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    selection = Selection.from_defaults(manifest)
    raw = manifest.by_category(ItemCategory.RAW_DATA)[0]
    selection.add(raw)
    selection.add(raw)

    assert selection.chosen.count(raw) == 1


def test_an_empty_selection_still_writes_only_the_summary(tmp_path: Path) -> None:
    """Hiçbir şey seçilmezse hiçbir kullanıcı dosyası yazılmaz."""
    result = export(Selection(), tmp_path / "paket.zip")

    assert _names_in(result.path) == {SUMMARY_NAME}


# --------------------------------------------------------------------------- #
# KULLANICI ICERIGI GORUR
# --------------------------------------------------------------------------- #


def test_the_preview_lists_exactly_what_will_be_written(tmp_path: Path) -> None:
    """Önizleme ile arşiv aynı seçimden üretilir; ayrışamazlar."""
    manifest = _manifest(tmp_path)
    selection = Selection.from_defaults(manifest)
    selection.add(manifest.by_category(ItemCategory.RAW_DATA)[0])

    shown = {line.name for line in preview(selection)}
    result = export(selection, tmp_path / "paket.zip")
    written = {Path(name).name for name in _names_in(result.path) if name != SUMMARY_NAME}

    # Dosyasi olan her onizleme satiri arsivde bulunmali.
    with_files = {item.name for item in selection.chosen if item.path is not None}
    assert with_files <= shown
    assert written == with_files


def test_the_preview_warns_about_raw_data(tmp_path: Path) -> None:
    """Kullanıcı ne gönderdiğini okuyabilmeli."""
    manifest = _manifest(tmp_path)
    selection = Selection.from_defaults(manifest)
    selection.add(manifest.by_category(ItemCategory.RAW_DATA)[0])

    warnings = [line.warning for line in preview(selection) if line.warning]
    assert any("HAM SENSOR" in text.upper() for text in warnings)


def test_the_preview_of_a_default_selection_has_no_raw_warning(tmp_path: Path) -> None:
    selection = Selection.from_defaults(_manifest(tmp_path))
    warnings = [line.warning for line in preview(selection) if line.warning]

    assert not any("HAM SENSOR" in text.upper() for text in warnings)


def test_the_preview_shows_sizes(tmp_path: Path) -> None:
    """Kullanıcı ne kadar veri gönderdiğini de görmeli."""
    selection = Selection.from_defaults(_manifest(tmp_path))
    lines = preview(selection)

    assert any(line.size_bytes > 0 for line in lines)
    assert selection.total_bytes > 0


# --------------------------------------------------------------------------- #
# ARSIV ICI
# --------------------------------------------------------------------------- #


def test_the_archive_carries_a_summary_the_opener_can_read(tmp_path: Path) -> None:
    """Paketi açan kişi de ne taşıdığını görebilmeli."""
    selection = Selection.from_defaults(_manifest(tmp_path))
    result = export(selection, tmp_path / "paket.zip", session_id="s1", app_version="3.20.0")

    with zipfile.ZipFile(result.path) as archive:
        summary = json.loads(archive.read(SUMMARY_NAME).decode("utf-8"))

    assert summary["session_id"] == "s1"
    assert summary["app_version"] == "3.20.0"
    assert summary["includes_raw_data"] is False


def test_the_summary_records_when_raw_data_was_included(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    selection = Selection.from_defaults(manifest)
    selection.add(manifest.by_category(ItemCategory.RAW_DATA)[0])
    result = export(selection, tmp_path / "paket.zip")

    with zipfile.ZipFile(result.path) as archive:
        summary = json.loads(archive.read(SUMMARY_NAME).decode("utf-8"))

    assert summary["includes_raw_data"] is True


def test_items_are_grouped_by_category_inside_the_archive(tmp_path: Path) -> None:
    """Açan kişi neyin ne olduğunu klasör adından görsün."""
    selection = Selection.from_defaults(_manifest(tmp_path))
    result = export(selection, tmp_path / "paket.zip")

    names = _names_in(result.path) - {SUMMARY_NAME}
    assert all("/" in name for name in names)


def test_an_item_without_a_file_is_not_written_as_one(tmp_path: Path) -> None:
    """Oturum/sürüm dosyası yoktur; özet dosyasında metin olarak durur."""
    selection = Selection(chosen=[DiagnosticItem(name="oturum-s1", category=ItemCategory.SESSION)])
    result = export(selection, tmp_path / "paket.zip")

    assert _names_in(result.path) == {SUMMARY_NAME}
    with zipfile.ZipFile(result.path) as archive:
        summary = json.loads(archive.read(SUMMARY_NAME).decode("utf-8"))
    assert summary["items"][0]["name"] == "oturum-s1"


def test_the_export_result_reports_what_it_wrote(tmp_path: Path) -> None:
    selection = Selection.from_defaults(_manifest(tmp_path))
    result = export(selection, tmp_path / "paket.zip")

    assert result.ok is True
    assert SUMMARY_NAME in result.written_names
    assert result.total_bytes > 0
