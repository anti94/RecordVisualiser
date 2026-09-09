"""Bilinmeyen paket teşhisi — `F2-015`.

Kabul: güvenilir uzunluk varsa sonraki pakete geçilir; yoksa konum
raporlanır.
"""

from __future__ import annotations

from tests.golden_bytes import build_unknown_packet_fixture, build_valid_fixture

from sonar_analyzer.io.decoders.unknown_packet import (
    UnknownPacket,
    classify_record_bytes,
    iter_records_with_unknown_packets,
    scan_for_resync_point,
)
from sonar_analyzer.io.profile_a_format import DATA_RECORD_V1, DataRecordV1

HEADER_SIZE = 32
RECORD_SIZE = 64


def test_valid_records_are_never_classified_as_unknown() -> None:
    buffer = build_valid_fixture()
    for index in range(8):
        offset = HEADER_SIZE + index * RECORD_SIZE
        raw = buffer[offset : offset + RECORD_SIZE]
        assert classify_record_bytes(raw, offset, RECORD_SIZE) is None


def test_garbage_record_is_classified_as_unknown_with_reliable_length() -> None:
    """Kabul: güvenilir uzunluk (record_size) varsa sonraki pakete geçilir."""
    buffer = build_unknown_packet_fixture()
    offset = HEADER_SIZE + 3 * RECORD_SIZE
    raw = buffer[offset : offset + RECORD_SIZE]

    result = classify_record_bytes(raw, offset, RECORD_SIZE)

    assert isinstance(result, UnknownPacket)
    assert result.byte_offset == offset
    assert result.skipped_bytes == RECORD_SIZE


def test_iterator_skips_unknown_packet_and_keeps_reading_rest_of_file() -> None:
    """Kabul: hatalı kayıt kalan dosyanın okunmasını engellemez."""
    buffer = build_unknown_packet_fixture()

    items = list(iter_records_with_unknown_packets(buffer))

    assert len(items) == 8
    unknown_items = [item for item in items if isinstance(item, UnknownPacket)]
    valid_items = [item for item in items if isinstance(item, DataRecordV1)]
    assert len(unknown_items) == 1
    assert len(valid_items) == 7
    assert unknown_items[0].byte_offset == HEADER_SIZE + 3 * RECORD_SIZE
    # Diger 7 kayit fiziksel sirayla ve dogru sequence_no ile okunabilir.
    assert [r.sequence_no for r in valid_items] == [0, 1, 2, 4, 5, 6, 7]


def test_scan_for_resync_point_finds_next_data_prefix() -> None:
    """Kabul: güvenilir uzunluk yokken sonraki hizalı b"Data" konumu aranır."""
    buffer = build_unknown_packet_fixture()
    corrupt_offset = HEADER_SIZE + 3 * RECORD_SIZE
    next_valid_offset = HEADER_SIZE + 4 * RECORD_SIZE

    found = scan_for_resync_point(buffer, start_offset=corrupt_offset, alignment=8)

    assert found == next_valid_offset


def test_scan_for_resync_point_returns_none_when_pattern_absent() -> None:
    """Kabul: bulunamazsa yalnız konum raporlanır — None döner, tarama ilerletilemez."""
    buffer = bytes(128)  # tamamen sifir, hicbir yerde b"Data" yok
    found = scan_for_resync_point(buffer, start_offset=0, alignment=8)
    assert found is None


def test_scan_for_resync_point_respects_search_limit() -> None:
    buffer = build_unknown_packet_fixture()
    corrupt_offset = HEADER_SIZE + 3 * RECORD_SIZE
    # Sonraki gecerli kayit 64 bayt otede; 16 baytlik arama sinirinda bulunamaz.
    found = scan_for_resync_point(buffer, start_offset=corrupt_offset, search_limit=16)
    assert found is None


def test_unknown_packet_str_with_reliable_length() -> None:
    packet = UnknownPacket(byte_offset=224, reason="beklenmeyen onek b'XXXX'", skipped_bytes=64)
    assert str(packet) == (
        "Bilinmeyen paket: offset 224, beklenmeyen onek b'XXXX', 64 bayt atlanip devam edildi"
    )


def test_unknown_packet_str_without_reliable_length() -> None:
    packet = UnknownPacket(byte_offset=999, reason="resync basarisiz", skipped_bytes=None)
    assert str(packet) == "Bilinmeyen paket: offset 999, resync basarisiz (guvenilir uzunluk yok)"


def test_unknown_packet_is_immutable() -> None:
    import dataclasses

    import pytest

    packet = UnknownPacket(byte_offset=1, reason="x", skipped_bytes=64)
    with pytest.raises(dataclasses.FrozenInstanceError):
        packet.byte_offset = 2  # type: ignore[misc]


def test_name_field_matching_prefix_but_garbage_tail_is_not_unknown() -> None:
    """Yalnız 4 baytlık onek denetlenir — K-06 (sayisal uyumsuzluk) ayri bir
    tesihstir (F2-010), burada tekrar raporlanmaz."""
    record = DATA_RECORD_V1.pack(b"Data99999\x00\x00\x00", 2, 2 * 125_000, *([0.0] * 8), 0, 0)
    assert classify_record_bytes(record, byte_offset=0, record_size=64) is None
