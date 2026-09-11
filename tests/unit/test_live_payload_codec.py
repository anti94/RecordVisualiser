"""Kanal/olay payload kodlaması — `F5-006`.

Kabul (üst iş F5-006): geçerli veri domain nesnelerine dönüşür, kesik veri
teşhis edilir.
"""

from __future__ import annotations

import numpy as np
import pytest

from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.event import Event, Severity
from sonar_analyzer.io.live.payload_codec import decode_payload, encode_payload
from sonar_analyzer.io.live.wire_header import TruncatedDatagramError


def _chunk(channel_id: str, n: int, *, with_quality: bool = False, seed: int = 0) -> DataChunk:
    rng = np.random.default_rng(seed)
    timestamps = (np.arange(n, dtype=np.int64) * 1_000_000) + 1_788_901_200_000_000_000
    values = rng.normal(size=n).astype(np.float64)
    quality = rng.integers(0, 3, size=n).astype(np.uint8) if with_quality else None
    return DataChunk(channel_id, timestamps, values, quality)


_EVENT_FULL = Event(
    timestamp_ns=1_788_901_200_500_000_000,
    source="BIT/Power Supply",
    category="bit",
    severity=Severity.ERROR,
    code="0x0412",
    message="Guc kaynagi testi basarisiz",
    state="FAIL",
    value=3.7,
    unit="V",
)

_EVENT_MINIMAL = Event(
    timestamp_ns=0,
    source="live",
    category="sistem",
    severity=Severity.INFO,
    code="",
    message="baglanti kuruldu",
)

_EVENT_STRING_VALUE = Event(
    timestamp_ns=1,
    source="s",
    category="c",
    severity=Severity.WARNING,
    code="w1",
    message="serbest metin degerli olay",
    value="beklenmeyen durum",
)


# --------------------------------------------------------------------------- #
# tur-gidis (round trip)
# --------------------------------------------------------------------------- #


def test_empty_payload_round_trips() -> None:
    chunks, events = decode_payload(encode_payload([], []))
    assert chunks == []
    assert events == []


def test_a_single_channel_round_trips_exactly() -> None:
    original = _chunk("ch0", 500)
    chunks, _events = decode_payload(encode_payload([original], []))
    assert len(chunks) == 1
    restored = chunks[0]
    assert restored.channel_id == "ch0"
    assert restored.timestamps_ns.tolist() == original.timestamps_ns.tolist()
    assert restored.values.tolist() == original.values.tolist()
    assert restored.quality is None


def test_quality_flags_round_trip() -> None:
    original = _chunk("ch1", 250, with_quality=True, seed=3)
    chunks, _events = decode_payload(encode_payload([original], []))
    restored = chunks[0]
    assert restored.quality is not None
    assert restored.quality.tolist() == original.quality.tolist()  # type: ignore[union-attr]


def test_multiple_channels_preserve_order_and_content() -> None:
    originals = [
        _chunk("ch0", 10, seed=1),
        _chunk("ch1", 20, with_quality=True, seed=2),
        _chunk("ch2", 5, seed=5),
    ]
    chunks, _events = decode_payload(encode_payload(originals, []))
    assert [chunk.channel_id for chunk in chunks] == ["ch0", "ch1", "ch2"]
    for original, restored in zip(originals, chunks):
        assert restored.timestamps_ns.tolist() == original.timestamps_ns.tolist()
        assert restored.values.tolist() == original.values.tolist()


@pytest.mark.parametrize("event", [_EVENT_FULL, _EVENT_MINIMAL, _EVENT_STRING_VALUE])
def test_events_round_trip_every_optional_field_combination(event: Event) -> None:
    _chunks, events = decode_payload(encode_payload([], [event]))
    assert len(events) == 1
    restored = events[0]
    assert restored.timestamp_ns == event.timestamp_ns
    assert restored.source == event.source
    assert restored.category == event.category
    assert restored.severity == event.severity
    assert restored.code == event.code
    assert restored.message == event.message
    assert restored.state == event.state
    assert restored.value == event.value
    assert restored.unit == event.unit
    assert restored.source_offset is None  # canli veri dosya offseti tasimaz


def test_events_and_channels_together_round_trip() -> None:
    chunks, events = decode_payload(
        encode_payload([_chunk("ch0", 3)], [_EVENT_FULL, _EVENT_MINIMAL])
    )
    assert len(chunks) == 1
    assert len(events) == 2
    assert events[0].code == _EVENT_FULL.code
    assert events[1].code == _EVENT_MINIMAL.code


def test_large_sample_count_round_trips_without_precision_loss() -> None:
    original = _chunk("acoustic0", 6000, seed=11)  # profil B blok buyuklugu
    chunks, _events = decode_payload(encode_payload([original], []))
    np.testing.assert_array_equal(chunks[0].timestamps_ns, original.timestamps_ns)
    np.testing.assert_array_equal(chunks[0].values, original.values)


def test_unicode_text_fields_round_trip() -> None:
    event = Event(
        timestamp_ns=0,
        source="Hidrofon 1",
        category="ısı",
        severity=Severity.CRITICAL,
        code="ÇĞİÖŞÜ",
        message="Sıcaklık eşiği aşıldı — acil müdahale gerekiyor",
    )
    _chunks, events = decode_payload(encode_payload([], [event]))
    assert events[0].source == "Hidrofon 1"
    assert events[0].category == "ısı"
    assert events[0].message == "Sıcaklık eşiği aşıldı — acil müdahale gerekiyor"


# --------------------------------------------------------------------------- #
# kesik / bozuk veri teshis edilir
# --------------------------------------------------------------------------- #


def test_a_payload_cut_mid_channel_header_is_truncated() -> None:
    full = encode_payload([_chunk("ch0", 100)], [])
    with pytest.raises(TruncatedDatagramError):
        decode_payload(full[:5])


def test_a_payload_cut_mid_sample_array_is_truncated() -> None:
    full = encode_payload([_chunk("ch0", 100)], [])
    with pytest.raises(TruncatedDatagramError):
        decode_payload(full[:-50])  # basligi koru, ornek dizisini yarida kes


def test_a_payload_cut_mid_event_text_is_truncated() -> None:
    full = encode_payload([], [_EVENT_FULL])
    with pytest.raises(TruncatedDatagramError):
        decode_payload(full[:-5])


def test_an_unknown_severity_value_is_diagnosed_not_a_bare_value_error() -> None:
    """Uzunluklar doğru ama içerik bozuksa da `TruncatedDatagramError` — tek yakalanacak tür."""
    good = encode_payload([], [_EVENT_MINIMAL])
    # severity metnini "info" -> "ge" gibi ayni uzunlukta gecersiz bir degerle degistir.
    corrupted = good.replace(b"info", b"cccc")
    with pytest.raises(TruncatedDatagramError, match="payload bozuk"):
        decode_payload(corrupted)


def test_an_empty_bytes_object_is_truncated_not_an_index_error() -> None:
    with pytest.raises(TruncatedDatagramError):
        decode_payload(b"")
