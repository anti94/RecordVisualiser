"""Tanılama paketi içerik listesi — `F6-019`.

Kabul: **Session, sürüm ve hata logları listelenir; ham sensör veri
varsayılan değildir.**

Kabulün ikinci yarısı asıl olandır. Tanılama paketi kullanıcıdan
istenen bir şeydir; içine farkında olmadan ölçüm verisi girerse, kullanıcı
kendi verisini dışarı göndermiş olur. Bu yüzden testlerin çoğu ham
verinin **varsayılan seçili olmadığını** farklı yollardan doğrular.

Liste üretimi dosya **okumaz**; yalnız varlığı ve boyutu bildirir. Okuma
`F6-020`'nin işidir ve orada da yalnız seçili öğeler okunur.
"""

from __future__ import annotations

from pathlib import Path

from sonar_analyzer.application.diagnostics import (
    DEFAULT_SELECTED,
    MAX_LOG_FILES,
    DiagnosticItem,
    ItemCategory,
    build_manifest,
)


def _manifest(tmp_path: Path, **kwargs: object):
    return build_manifest(
        session_id="abc123",
        app_version="3.19.0",
        **kwargs,  # type: ignore[arg-type]
    )


# --------------------------------------------------------------------------- #
# SESSION, SURUM VE HATA LOGLARI LISTELENIR
# --------------------------------------------------------------------------- #


def test_the_session_is_listed(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    session = manifest.by_category(ItemCategory.SESSION)

    assert len(session) == 1
    assert "abc123" in session[0].name


def test_the_version_is_listed(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    version = manifest.by_category(ItemCategory.VERSION)

    assert len(version) == 1
    assert "3.19.0" in version[0].name


def test_log_files_are_listed(tmp_path: Path) -> None:
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    (log_dir / "a.log").write_text("satir", encoding="utf-8")
    (log_dir / "b.log").write_text("satir satir", encoding="utf-8")

    manifest = _manifest(tmp_path, log_dir=log_dir)
    logs = manifest.by_category(ItemCategory.ERROR_LOG)

    assert {item.name for item in logs} == {"a.log", "b.log"}
    assert all(item.size_bytes > 0 for item in logs)


def test_only_the_newest_logs_are_listed(tmp_path: Path) -> None:
    """Yıllarca birikmiş log, tanılama paketini şişirmemeli."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    for index in range(MAX_LOG_FILES + 5):
        (log_dir / f"{index:03d}.log").write_text("x", encoding="utf-8")

    logs = _manifest(tmp_path, log_dir=log_dir).by_category(ItemCategory.ERROR_LOG)
    assert len(logs) == MAX_LOG_FILES


def test_a_missing_log_directory_is_not_an_error(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path, log_dir=tmp_path / "yok")
    assert manifest.by_category(ItemCategory.ERROR_LOG) == []


def test_the_settings_file_is_listed_when_present(tmp_path: Path) -> None:
    settings = tmp_path / "settings.json"
    settings.write_text("{}", encoding="utf-8")

    manifest = _manifest(tmp_path, settings_path=settings)
    assert [item.name for item in manifest.by_category(ItemCategory.SETTINGS)] == ["settings.json"]


# --------------------------------------------------------------------------- #
# HAM SENSOR VERISI VARSAYILAN DEGILDIR
# --------------------------------------------------------------------------- #


def test_raw_data_is_never_selected_by_default(tmp_path: Path) -> None:
    """Kabulün asıl yarısı: ölçüm verisi istemeden gönderilmemeli."""
    recording = tmp_path / "kayit.bin"
    recording.write_bytes(b"0" * 500)

    manifest = _manifest(tmp_path, recording_paths=[recording])
    raw = manifest.by_category(ItemCategory.RAW_DATA)

    assert len(raw) == 1
    assert raw[0].default_selected is False


def test_raw_data_is_not_in_the_default_category_set() -> None:
    """Kural veri yapısında da geçerli olmalı, yalnız bir dalda değil."""
    assert ItemCategory.RAW_DATA not in DEFAULT_SELECTED


def test_raw_data_never_appears_among_the_default_items(tmp_path: Path) -> None:
    recording = tmp_path / "kayit.bin"
    recording.write_bytes(b"0" * 500)

    manifest = _manifest(tmp_path, recording_paths=[recording])

    assert all(item.category is not ItemCategory.RAW_DATA for item in manifest.default_items)
    assert any(item.category is ItemCategory.RAW_DATA for item in manifest.optional_items)


def test_raw_data_does_not_count_toward_the_default_size(tmp_path: Path) -> None:
    """Varsayılan paket boyutu, gönderilmeyecek veriyi saymamalı."""
    recording = tmp_path / "kayit.bin"
    recording.write_bytes(b"0" * 10_000)
    settings = tmp_path / "settings.json"
    settings.write_text("{}", encoding="utf-8")

    manifest = _manifest(tmp_path, settings_path=settings, recording_paths=[recording])

    assert manifest.default_bytes < 10_000


def test_the_workspace_is_offered_but_not_default(tmp_path: Path) -> None:
    """Çalışma alanı da kullanıcının içeriğidir; sunulur ama seçilmez."""
    workspace = tmp_path / "calisma.json"
    workspace.write_text("{}", encoding="utf-8")

    manifest = _manifest(tmp_path, workspace_path=workspace)
    items = manifest.by_category(ItemCategory.WORKSPACE)

    assert len(items) == 1
    assert items[0].default_selected is False


def test_the_raw_data_entry_says_it_is_raw_data(tmp_path: Path) -> None:
    """Kullanıcı ne eklediğini okuyabilmeli."""
    recording = tmp_path / "kayit.bin"
    recording.write_bytes(b"0")

    item = _manifest(tmp_path, recording_paths=[recording]).by_category(ItemCategory.RAW_DATA)[0]
    assert "HAM SENSOR" in item.detail.upper()


# --------------------------------------------------------------------------- #
# LISTE URETIMI DOSYA OKUMAZ
# --------------------------------------------------------------------------- #


def test_building_the_manifest_does_not_read_file_contents(tmp_path: Path) -> None:
    """Boyut bildirilir, içerik okunmaz; okuma `F6-020`'nin işidir."""
    recording = tmp_path / "kayit.bin"
    recording.write_bytes(b"gizli" * 100)

    item = _manifest(tmp_path, recording_paths=[recording]).by_category(ItemCategory.RAW_DATA)[0]

    assert item.size_bytes == 500
    assert "gizli" not in item.detail


def test_a_missing_recording_is_skipped(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path, recording_paths=[tmp_path / "yok.bin"])
    assert manifest.by_category(ItemCategory.RAW_DATA) == []


def test_default_and_optional_items_together_are_everything(tmp_path: Path) -> None:
    """Hiçbir öğe iki listeden de düşmemeli."""
    recording = tmp_path / "kayit.bin"
    recording.write_bytes(b"0")
    manifest = _manifest(tmp_path, recording_paths=[recording])

    assert len(manifest.default_items) + len(manifest.optional_items) == len(manifest.items)


def test_an_item_in_a_default_category_is_selected() -> None:
    item = DiagnosticItem(name="x", category=ItemCategory.ERROR_LOG)
    assert item.default_selected is True
