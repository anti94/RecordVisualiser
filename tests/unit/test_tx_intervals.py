"""TX durumunu başlangıç/bitiş aralıklarına çevirme — `F2-023`.

Kabul: START/STOP ve açık kalan son aralık doğru temsil edilir.
"""

from __future__ import annotations

from tests.golden_bytes import START_TIME_UTC_NS, build_valid_fixture

from sonar_analyzer.domain.transmission import TxState
from sonar_analyzer.io.decoders.profile_a import iter_records
from sonar_analyzer.io.decoders.tx_intervals import tx_intervals_from_records, tx_state_samples
from sonar_analyzer.io.readers.binary_reader import read_file_header_v1

PERIOD_NS = 125_000_000
HEADER_SIZE = 32
RECORD_SIZE = 64
TX_STATUS_OFFSET_IN_RECORD = 60  # name(12)+seq(4)+elapsed(8)+8*float(32)+bit_status(4)


def _timestamp(n: int) -> int:
    return START_TIME_UTC_NS + n * PERIOD_NS


def _set_tx_status(buffer: bytearray, index: int, value: int) -> None:
    offset = HEADER_SIZE + index * RECORD_SIZE + TX_STATUS_OFFSET_IN_RECORD
    buffer[offset : offset + 4] = value.to_bytes(4, "little")


# -- tx_state_samples ---------------------------------------------------


def test_tx_state_samples_decode_known_codes() -> None:
    buffer = build_valid_fixture()
    header = read_file_header_v1(buffer)
    records = list(iter_records(buffer))

    samples = tx_state_samples(records, header)

    assert [state for _, state in samples] == [
        TxState.IDLE,
        TxState.IDLE,
        TxState.ACTIVE,
        TxState.ACTIVE,
        TxState.ACTIVE,
        TxState.ACTIVE,
        TxState.IDLE,
        TxState.IDLE,
    ]
    assert samples[0][0] == _timestamp(0)
    assert samples[7][0] == _timestamp(7)


# -- START/STOP: kapali aralik -------------------------------------------


def test_known_start_stop_pair_produces_single_closed_interval() -> None:
    """Kabul kriteri: START/STOP dogru temsil edilir (golden fixture: seq 2-5 ACTIVE)."""
    buffer = build_valid_fixture()
    header = read_file_header_v1(buffer)
    records = list(iter_records(buffer))

    intervals = tx_intervals_from_records(records, header)

    assert len(intervals) == 1
    interval = intervals[0]
    assert interval.closed is True
    assert interval.start_ns == _timestamp(2)
    assert interval.end_ns == _timestamp(6)  # STOP, ilk ACTIVE-olmayan orneğin zamani
    assert interval.state == TxState.ACTIVE
    assert interval.boundary_uncertainty_ns == PERIOD_NS


# -- acik kalan son aralik ------------------------------------------------


def test_trailing_active_run_produces_open_interval() -> None:
    """Kabul kriteri: acik kalan son aralik dogru temsil edilir (kapanmis gibi gosterilmez)."""
    buffer = bytearray(build_valid_fixture())
    # sequence 6 ve 7'yi de ACTIVE yap -- STOP hicbir zaman gelmesin (dosya
    # ACTIVE iken biter).
    _set_tx_status(buffer, 6, 1)
    _set_tx_status(buffer, 7, 1)
    frozen = bytes(buffer)

    header = read_file_header_v1(frozen)
    records = list(iter_records(frozen))

    intervals = tx_intervals_from_records(records, header)

    assert len(intervals) == 1
    interval = intervals[0]
    assert interval.closed is False
    assert interval.start_ns == _timestamp(2)
    # Son ornegin (seq 7) zamanindan bir periyot sonrasina uzatilir; STOP
    # zamani yok cunku dosya ACTIVE iken bitiyor.
    assert interval.end_ns == _timestamp(7) + PERIOD_NS


def test_no_active_samples_produce_no_intervals() -> None:
    buffer = bytearray(build_valid_fixture())
    for index in range(2, 6):
        _set_tx_status(buffer, index, 0)  # hepsini IDLE yap
    frozen = bytes(buffer)

    header = read_file_header_v1(frozen)
    records = list(iter_records(frozen))

    assert tx_intervals_from_records(records, header) == []


def test_always_active_stream_is_a_single_open_interval_from_first_sample() -> None:
    buffer = bytearray(build_valid_fixture())
    for index in range(8):
        _set_tx_status(buffer, index, 1)
    frozen = bytes(buffer)

    header = read_file_header_v1(frozen)
    records = list(iter_records(frozen))

    intervals = tx_intervals_from_records(records, header)

    assert len(intervals) == 1
    assert intervals[0].closed is False
    assert intervals[0].start_ns == _timestamp(0)
    assert intervals[0].end_ns == _timestamp(7) + PERIOD_NS
