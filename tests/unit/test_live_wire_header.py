"""`LiveWireHeader` çözümü — `F5-006`.

`docs/live/protocol-contract.md` §2'nin 28 baytlık zarfı.
"""

from __future__ import annotations

import pytest

from sonar_analyzer.io.live.wire_header import (
    HEADER_SIZE,
    MAGIC,
    PROTOCOL_UDP,
    LiveWireHeader,
    TruncatedDatagramError,
    UnrecognizedFrameError,
    pack_frame,
    unpack_frame,
)

_HEADER = LiveWireHeader(
    protocol_id=PROTOCOL_UDP,
    flags=0,
    sequence_no=42,
    fragment_index=0,
    fragment_count=1,
    device_ticks=1_788_901_200_000,
    payload_length=0,  # pack_frame kendisi hesaplar
)


def test_header_size_is_28_bytes() -> None:
    """`docs/live/protocol-contract.md` §2: 4+1+1+2+4+2+2+8+4 = 28."""
    assert HEADER_SIZE == 28


def test_round_trips_header_fields() -> None:
    frame = pack_frame(_HEADER, b"merhaba")
    header, payload = unpack_frame(frame)
    assert header.protocol_id == PROTOCOL_UDP
    assert header.sequence_no == 42
    assert header.fragment_index == 0
    assert header.fragment_count == 1
    assert header.device_ticks == 1_788_901_200_000
    assert header.payload_length == len(b"merhaba")
    assert payload == b"merhaba"


def test_empty_payload_round_trips() -> None:
    frame = pack_frame(_HEADER, b"")
    _header, payload = unpack_frame(frame)
    assert payload == b""


def test_has_events_flag() -> None:
    with_events = pack_frame(
        LiveWireHeader(
            PROTOCOL_UDP,
            flags=1,
            sequence_no=0,
            fragment_index=0,
            fragment_count=1,
            device_ticks=0,
            payload_length=0,
        ),
        b"",
    )
    header, _ = unpack_frame(with_events)
    assert header.has_events is True

    without_events = pack_frame(_HEADER, b"")
    header2, _ = unpack_frame(without_events)
    assert header2.has_events is False


def test_extra_trailing_bytes_beyond_payload_length_are_ignored() -> None:
    """`payload_length` gerçek kesim noktasıdır; fazladan bayt (dolgu) yok sayılır."""
    frame = pack_frame(_HEADER, b"gercek") + b"cop-veri"
    _header, payload = unpack_frame(frame)
    assert payload == b"gercek"


# --------------------------------------------------------------------------- #
# taninmayan cerceve
# --------------------------------------------------------------------------- #


def test_wrong_magic_is_unrecognized() -> None:
    frame = pack_frame(_HEADER, b"x")
    corrupted = b"XXXX" + frame[4:]
    with pytest.raises(UnrecognizedFrameError, match="gecersiz magic"):
        unpack_frame(corrupted)


def test_wrong_version_is_unrecognized() -> None:
    frame = pack_frame(_HEADER, b"x", version=99)
    with pytest.raises(UnrecognizedFrameError, match="desteklenmeyen surum"):
        unpack_frame(frame)


def test_magic_constant_is_four_ascii_bytes() -> None:
    assert MAGIC == b"SNLV"
    assert len(MAGIC) == 4


# --------------------------------------------------------------------------- #
# kesik veri
# --------------------------------------------------------------------------- #


def test_a_frame_shorter_than_the_header_is_truncated() -> None:
    with pytest.raises(TruncatedDatagramError, match="en az 28 bayt"):
        unpack_frame(b"\x00" * 10)


def test_an_empty_datagram_is_truncated() -> None:
    with pytest.raises(TruncatedDatagramError):
        unpack_frame(b"")


def test_a_payload_shorter_than_declared_length_is_truncated() -> None:
    frame = pack_frame(_HEADER, b"12345678")
    cut = frame[:-3]  # basligi koru, payload'i erken kes
    with pytest.raises(TruncatedDatagramError, match="payload_length"):
        unpack_frame(cut)


@pytest.mark.parametrize("fragment_count", [0, -1])
def test_fragment_count_below_one_is_rejected(fragment_count: int) -> None:
    with pytest.raises(TruncatedDatagramError, match="fragment_count"):
        LiveWireHeader(
            PROTOCOL_UDP,
            0,
            sequence_no=0,
            fragment_index=0,
            fragment_count=fragment_count,
            device_ticks=0,
            payload_length=0,
        )


@pytest.mark.parametrize(("index", "count"), [(1, 1), (5, 3), (-1, 2)])
def test_fragment_index_outside_fragment_count_is_rejected(index: int, count: int) -> None:
    with pytest.raises(TruncatedDatagramError, match="fragment_index"):
        LiveWireHeader(
            PROTOCOL_UDP,
            0,
            sequence_no=0,
            fragment_index=index,
            fragment_count=count,
            device_ticks=0,
            payload_length=0,
        )


def test_single_fragment_windows_are_flagged() -> None:
    single = LiveWireHeader(
        PROTOCOL_UDP, 0, 0, fragment_index=0, fragment_count=1, device_ticks=0, payload_length=0
    )
    multi = LiveWireHeader(
        PROTOCOL_UDP, 0, 0, fragment_index=0, fragment_count=3, device_ticks=0, payload_length=0
    )
    assert single.is_single_fragment is True
    assert multi.is_single_fragment is False
