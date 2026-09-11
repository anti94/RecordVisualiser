"""Favori grupların ayar dosyasında kalıcılığı — `F3-017` (şema v2)."""

from __future__ import annotations

import json
from pathlib import Path

from sonar_analyzer.settings.store import (
    SCHEMA_VERSION,
    AppSettings,
    FavoriteGroup,
    load_settings,
    save_settings,
)


def test_round_trip_preserves_favorite_groups(tmp_path: Path) -> None:
    target = tmp_path / "settings.json"
    original = AppSettings(
        favorite_groups=[
            FavoriteGroup(name="Seyir", channel_ids=["ch0", "ch6"]),
            FavoriteGroup(name="Akustik", channel_ids=["ch5"]),
        ]
    )
    save_settings(original, target)

    result = load_settings(target)

    assert result.ok
    assert result.settings == original


def test_saved_json_shape_is_a_list_of_name_and_channel_ids(tmp_path: Path) -> None:
    target = tmp_path / "settings.json"
    save_settings(
        AppSettings(favorite_groups=[FavoriteGroup(name="G", channel_ids=["ch0"])]),
        target,
    )

    raw = json.loads(target.read_text(encoding="utf-8"))

    assert raw["favorite_groups"] == [{"name": "G", "channel_ids": ["ch0"]}]


def test_the_written_file_carries_the_current_schema_version(tmp_path: Path) -> None:
    """`F3-017` bunu 2'ye sabitlemişti; `F5-018` `live_connection` ekleyip 3'e taşıdı.

    Sürüm sabiti ile dosyaya yazılan değerin **birlikte** ilerlediğini
    denetler; ikisinin ayrışması eski dosyaların yanlış sürümle okunması
    demek olurdu.
    """
    target = tmp_path / "settings.json"
    save_settings(AppSettings(), target)

    raw = json.loads(target.read_text(encoding="utf-8"))
    assert raw["schema_version"] == SCHEMA_VERSION == 3


def test_v1_file_without_favorites_loads_with_empty_list(tmp_path: Path) -> None:
    target = tmp_path / "settings.json"
    target.write_text(
        json.dumps({"schema_version": 1, "theme": "light", "recent_files": ["a.bin"]}),
        encoding="utf-8",
    )

    result = load_settings(target)

    assert result.settings.favorite_groups == []
    assert result.settings.theme == "light"
    assert result.settings.recent_files == ["a.bin"]
    assert not any("favorite" in w.lower() for w in result.warnings)


def test_a_broken_group_entry_is_skipped_not_fatal(tmp_path: Path) -> None:
    target = tmp_path / "settings.json"
    target.write_text(
        json.dumps(
            {
                "schema_version": SCHEMA_VERSION,
                "favorite_groups": [
                    {"name": "Iyi", "channel_ids": ["ch0"]},
                    {"channel_ids": ["ch1"]},  # adsiz
                    {"name": "  ", "channel_ids": ["ch2"]},  # bos ad
                    {"name": "BozukIdler", "channel_ids": ["ch3", 7]},  # metin degil
                    "hic sozluk degil",
                ],
            }
        ),
        encoding="utf-8",
    )

    result = load_settings(target)

    assert result.settings.favorite_groups == [
        FavoriteGroup(name="Iyi", channel_ids=["ch0"]),
    ]
    assert len(result.warnings) == 4


def test_non_list_favorite_groups_falls_back_to_empty(tmp_path: Path) -> None:
    target = tmp_path / "settings.json"
    target.write_text(
        json.dumps({"schema_version": SCHEMA_VERSION, "favorite_groups": "nope"}),
        encoding="utf-8",
    )

    result = load_settings(target)

    assert result.settings.favorite_groups == []
    assert any("favorite_groups listesi okunamadi" in w for w in result.warnings)
