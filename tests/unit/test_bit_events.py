"""BIT maskesini durum ve değişim olaylarına çevirme — `F2-022`.

Kabul: bilinen bit değişimi doğru bileşen için tek geçiş üretir.
"""

from __future__ import annotations

from tests.golden_bytes import build_valid_fixture

from sonar_analyzer.io.decoders.bit_events import (
    BitState,
    BitTransitionEvent,
    component_name_for_bit,
    component_states,
    detect_bit_transitions,
    unknown_active_bits,
)
from sonar_analyzer.io.decoders.profile_a import decode_record_at_index, record_count_in_buffer

HEADER_SIZE = 32
RECORD_SIZE = 64


def _indexed_records(buffer: bytes) -> list[tuple[int, object]]:
    count = record_count_in_buffer(len(buffer))
    return [
        (HEADER_SIZE + i * RECORD_SIZE, decode_record_at_index(buffer, i)) for i in range(count)
    ]


# -- component_states: tek bit -> tek bilesen FAIL --------------------------


def test_zero_bit_status_is_all_pass() -> None:
    states = component_states(0)
    assert all(state == BitState.PASS for state in states.values())
    assert set(states) == {"Power Supply", "Communication", "Thermal Management"}


def test_bit_8_sets_only_thermal_management_to_fail() -> None:
    """docs/format/fixture-valid-8records.md: n=4'te bit_status = 0x100 (bit 8)."""
    states = component_states(0x00000100)
    assert states["Thermal Management"] == BitState.FAIL
    assert states["Power Supply"] == BitState.PASS
    assert states["Communication"] == BitState.PASS


def test_any_bit_in_a_group_marks_the_whole_component_fail() -> None:
    for bit in range(4):  # Power Supply: 0-3
        states = component_states(1 << bit)
        assert states["Power Supply"] == BitState.FAIL
        assert states["Communication"] == BitState.PASS
        assert states["Thermal Management"] == BitState.PASS


def test_multiple_bits_in_same_component_still_single_fail_state() -> None:
    """Ayni bilesendeki birden fazla bit ayri ayri degil tek FAIL'e daralir."""
    states = component_states(0b1111)  # bit 0,1,2,3 -- hepsi Power Supply
    assert states["Power Supply"] == BitState.FAIL
    assert len(states) == 3


# -- atanmamis bitler ---------------------------------------------------


def test_unknown_bit_uses_raw_bit_number_label() -> None:
    assert component_name_for_bit(17) == "Bilinmeyen test (bit 17)"


def test_known_bit_uses_component_name() -> None:
    assert component_name_for_bit(0) == "Power Supply"
    assert component_name_for_bit(4) == "Communication"
    assert component_name_for_bit(8) == "Thermal Management"


def test_unknown_active_bits_detects_bits_above_11() -> None:
    bit_status = (1 << 17) | (1 << 20)
    assert unknown_active_bits(bit_status) == (17, 20)


def test_unknown_active_bits_ignores_known_bits() -> None:
    assert unknown_active_bits(0x00000100) == ()  # yalniz bit 8 (bilinen)


# -- detect_bit_transitions: kabul kriteri ----------------------------------


def test_known_bit_change_produces_exactly_one_transition_for_correct_component() -> None:
    """Kabul kriteri: bilinen bit degisimi dogru bilesen icin tek gecis uretir."""
    buffer = build_valid_fixture()
    records = _indexed_records(buffer)

    transitions = list(detect_bit_transitions(records))  # type: ignore[arg-type]

    # n=3->4: Thermal Management PASS->FAIL; n=4->5: FAIL->PASS. Baska hicbir
    # bilesen (Power Supply, Communication) hicbir zaman degismez.
    assert len(transitions) == 2
    assert all(t.component == "Thermal Management" for t in transitions)

    first, second = transitions
    assert first.sequence_no == 4
    assert first.from_state == BitState.PASS
    assert first.to_state == BitState.FAIL
    assert first.byte_offset == HEADER_SIZE + 4 * RECORD_SIZE

    assert second.sequence_no == 5
    assert second.from_state == BitState.FAIL
    assert second.to_state == BitState.PASS
    assert second.byte_offset == HEADER_SIZE + 5 * RECORD_SIZE


def test_no_transitions_when_bit_status_never_changes() -> None:
    buffer = bytearray(build_valid_fixture())
    # bit_status alanlarini hepsi 0 kalsin (zaten oyle, n=4 haric); n=4'u de sifirla.
    offset = HEADER_SIZE + 4 * RECORD_SIZE + 12 + 4 + 8 + 8 * 4  # bit_status alani
    buffer[offset : offset + 4] = bytes(4)
    records = _indexed_records(bytes(buffer))

    transitions = list(detect_bit_transitions(records))  # type: ignore[arg-type]

    assert transitions == []


def test_single_record_stream_produces_no_transitions() -> None:
    buffer = build_valid_fixture(record_count=1)
    records = _indexed_records(buffer)
    assert list(detect_bit_transitions(records)) == []  # type: ignore[arg-type]


def test_transition_event_str_shape() -> None:
    event = BitTransitionEvent(
        sequence_no=4,
        byte_offset=288,
        component="Thermal Management",
        from_state=BitState.PASS,
        to_state=BitState.FAIL,
    )
    assert str(event) == "BIT gecisi: Thermal Management pass -> fail, seq 4, offset 288"


def test_transition_event_is_immutable() -> None:
    import dataclasses

    import pytest

    event = BitTransitionEvent(
        sequence_no=1,
        byte_offset=1,
        component="x",
        from_state=BitState.PASS,
        to_state=BitState.FAIL,
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        event.sequence_no = 2  # type: ignore[misc]
