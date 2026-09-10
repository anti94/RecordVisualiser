"""Olayla ilişkili kanal eşlemesi — `F3-044`."""

from __future__ import annotations

from sonar_analyzer.domain.channel import ChannelMetadata, ChannelSource
from sonar_analyzer.domain.event import Event, Severity
from sonar_analyzer.ui.docks.event_table_model import related_channels


def _chan(channel_id: str, name: str, source: ChannelSource) -> ChannelMetadata:
    return ChannelMetadata(
        id=channel_id,
        path=f"{source.value}/{name}",
        name=name,
        dtype="float32",
        source=source,
        unit="u",
        sample_rate_hz=1.0,
    )


CHANNELS = [
    _chan("ch0", "Pressure", ChannelSource.SENSORS),
    _chan("ch1", "Temperature", ChannelSource.SENSORS),
    _chan("ch5", "Hydrophone", ChannelSource.ACOUSTIC),
    _chan("ch6", "Depth", ChannelSource.NAVIGATION),
]


def _event(category: str, message: str, source: str = "System") -> Event:
    return Event(
        timestamp_ns=0,
        source=source,
        category=category,
        severity=Severity.WARNING,
        code="X",
        message=message,
    )


def test_category_matches_channel_source() -> None:
    result = related_channels(_event("navigation", "route recalculated"), CHANNELS)

    assert [c.id for c in result] == ["ch6"]


def test_channel_named_in_the_message_is_related() -> None:
    result = related_channels(_event("system", "Temperature sensor drift detected"), CHANNELS)

    assert [c.id for c in result] == ["ch1"]


def test_channel_id_in_the_message_is_related() -> None:
    result = related_channels(_event("system", "ch5 amplitude clipped"), CHANNELS)

    assert [c.id for c in result] == ["ch5"]


def test_source_text_is_also_searched() -> None:
    result = related_channels(_event("system", "no detail", source="Hydrophone board"), CHANNELS)

    assert [c.id for c in result] == ["ch5"]


def test_both_criteria_yield_each_channel_once() -> None:
    # kategori sensors -> ch0 + ch1; mesajda da "Pressure" geçiyor
    result = related_channels(_event("sensors", "Pressure spike"), CHANNELS)

    assert [c.id for c in result] == ["ch0", "ch1"]


def test_no_relation_returns_empty() -> None:
    assert related_channels(_event("packet", "checksum mismatch"), CHANNELS) == []


def test_channel_order_is_preserved() -> None:
    result = related_channels(_event("sensors", "both Temperature and Pressure"), CHANNELS)

    assert [c.id for c in result] == ["ch0", "ch1"]
