"""Favori kanal grubu liste kuralları — `F3-017`.

Kabul: grup tekrar açılabilir; bulunamayan kanal ayrı raporlanır. Bu
dosya saf liste/çözümleme kurallarını doğrular (dosya G/Ç yok).
"""

from __future__ import annotations

import pytest

from sonar_analyzer.application import favorite_groups
from sonar_analyzer.settings.store import FavoriteGroup


def test_save_appends_a_new_group() -> None:
    result = favorite_groups.save([], "Seyir", ["ch0", "ch1"])

    assert result == [FavoriteGroup(name="Seyir", channel_ids=["ch0", "ch1"])]


def test_save_overwrites_an_existing_group_in_place() -> None:
    existing = [
        FavoriteGroup(name="Seyir", channel_ids=["ch0"]),
        FavoriteGroup(name="Akustik", channel_ids=["ch5"]),
    ]

    result = favorite_groups.save(existing, "Seyir", ["ch0", "ch6"])

    assert result == [
        FavoriteGroup(name="Seyir", channel_ids=["ch0", "ch6"]),
        FavoriteGroup(name="Akustik", channel_ids=["ch5"]),
    ]


def test_save_dedupes_channel_ids_and_keeps_first_seen_order() -> None:
    result = favorite_groups.save([], "G", ["ch2", "ch0", "ch2", "ch0", "ch1"])

    assert result[0].channel_ids == ["ch2", "ch0", "ch1"]


def test_save_strips_the_name() -> None:
    result = favorite_groups.save([], "  Seyir  ", ["ch0"])

    assert result[0].name == "Seyir"


def test_save_rejects_a_blank_name() -> None:
    with pytest.raises(ValueError, match="bos olamaz"):
        favorite_groups.save([], "   ", ["ch0"])


def test_remove_drops_the_named_group() -> None:
    existing = [
        FavoriteGroup(name="Seyir", channel_ids=["ch0"]),
        FavoriteGroup(name="Akustik", channel_ids=["ch5"]),
    ]

    assert favorite_groups.remove(existing, "Seyir") == [
        FavoriteGroup(name="Akustik", channel_ids=["ch5"]),
    ]


def test_remove_unknown_name_is_a_no_op() -> None:
    existing = [FavoriteGroup(name="Seyir", channel_ids=["ch0"])]

    assert favorite_groups.remove(existing, "Yok") == existing


def test_get_returns_the_group_or_none() -> None:
    existing = [FavoriteGroup(name="Seyir", channel_ids=["ch0"])]

    assert favorite_groups.get(existing, "Seyir") == existing[0]
    assert favorite_groups.get(existing, "Yok") is None


def test_names_lists_groups_in_stored_order() -> None:
    existing = [
        FavoriteGroup(name="Seyir", channel_ids=[]),
        FavoriteGroup(name="Akustik", channel_ids=[]),
    ]

    assert favorite_groups.names(existing) == ["Seyir", "Akustik"]


# -- resolve: bulunan / bulunamayan ayrimi --------------------------------


def test_resolve_splits_found_and_missing_keeping_group_order() -> None:
    group = FavoriteGroup(name="G", channel_ids=["ch0", "ch9", "ch1", "ch8"])

    resolution = favorite_groups.resolve(group, ["ch0", "ch1", "ch2"])

    assert resolution.found == ["ch0", "ch1"]
    assert resolution.missing == ["ch9", "ch8"]
    assert resolution.has_missing


def test_resolve_with_everything_present_reports_no_missing() -> None:
    group = FavoriteGroup(name="G", channel_ids=["ch0", "ch1"])

    resolution = favorite_groups.resolve(group, ["ch0", "ch1", "ch2"])

    assert resolution.found == ["ch0", "ch1"]
    assert resolution.missing == []
    assert not resolution.has_missing


def test_resolve_with_nothing_present_reports_all_missing() -> None:
    group = FavoriteGroup(name="G", channel_ids=["ch0", "ch1"])

    resolution = favorite_groups.resolve(group, [])

    assert resolution.found == []
    assert resolution.missing == ["ch0", "ch1"]
