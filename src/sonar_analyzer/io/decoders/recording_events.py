"""Profil A kayıtlarını domain olaylarına ve durumlarına birleştir — F2-035."""

from __future__ import annotations

from dataclasses import dataclass, replace

from sonar_analyzer.domain.event import BitResult, BitState, Event, Severity
from sonar_analyzer.domain.transmission import TransmissionInterval, TxState
from sonar_analyzer.io.decoders.anomalies import DuplicateSequence, detect_anomalies
from sonar_analyzer.io.decoders.bit_events import (
    component_name_for_bit,
    component_states,
    unknown_active_bits,
)
from sonar_analyzer.io.decoders.crc_validation import check_record_crc
from sonar_analyzer.io.decoders.diagnostics_to_events import (
    crc_mismatch_to_event,
    duplicate_sequence_to_event,
    gap_to_event,
    name_mismatch_to_event,
    out_of_order_to_event,
    truncated_tail_to_event,
    unknown_packet_to_event,
)
from sonar_analyzer.io.decoders.gaps import detect_gaps
from sonar_analyzer.io.decoders.naming import check_name_consistency
from sonar_analyzer.io.decoders.truncation import find_truncated_tail
from sonar_analyzer.io.decoders.unknown_packet import classify_record_bytes
from sonar_analyzer.io.profile_a_format import BIT_COMPONENT_BY_BIT, DataRecordV1, FileHeaderV1
from sonar_analyzer.io.readers.binary_reader import (
    ReadableBuffer,
    read_data_record_v1,
    read_data_record_v2,
)
from sonar_analyzer.io.readers.recording_reader import MAX_TIMESTAMP_NS


@dataclass(frozen=True)
class RecordingEvents:
    events: tuple[Event, ...]
    bit_results: tuple[BitResult, ...]
    transmissions: tuple[TransmissionInterval, ...]


def _bit_samples(mask: int | None, timestamp: int) -> list[BitResult]:
    states = component_states(mask or 0)
    results = [
        BitResult(
            timestamp_ns=timestamp,
            test_id=min(bit for bit, name in BIT_COMPONENT_BY_BIT.items() if name == component),
            component=component,
            state=BitState(state.value) if mask is not None else BitState.UNKNOWN,
            severity=(
                Severity.WARNING
                if mask is None
                else Severity.ERROR
                if state.value == "fail"
                else Severity.INFO
            ),
        )
        for component, state in states.items()
    ]
    if mask is not None:
        results.extend(
            BitResult(
                timestamp,
                bit,
                component_name_for_bit(bit),
                BitState.UNKNOWN,
                severity=Severity.WARNING,
                code=1 << bit,
            )
            for bit in unknown_active_bits(mask)
        )
    return results


def scan_recording_events(data: ReadableBuffer, header: FileHeaderV1) -> RecordingEvents:
    """CRC'si bozuk veriden PASS/FAIL veya TX geçişi uydurmadan tüm dosyayı tarar."""
    events: list[Event] = []
    bits: list[BitResult] = []
    tx_samples: list[tuple[int, TxState]] = []
    offsets_by_time: dict[int, int] = {}
    states_by_time: dict[int, TxState] = {}
    uncertain_ends: set[int] = set()
    previous: tuple[int, DataRecordV1] | None = None
    previous_states: dict[str, BitState] = {}
    period = header.period_us * 1000
    count = (len(data) - header.header_size) // header.record_size

    for index in range(count):
        offset = header.header_size + index * header.record_size
        raw = data[offset : offset + header.record_size]
        nominal = min(header.start_time_utc_ns + index * period, MAX_TIMESTAMP_NS - period)
        invalid: Event | None = None
        if header.version == 2:
            mismatch = check_record_crc(read_data_record_v2(data, offset), raw[:64], offset)
            if mismatch is not None:
                invalid = replace(crc_mismatch_to_event(mismatch, header), timestamp_ns=nominal)
        unknown = classify_record_bytes(raw, offset, header.record_size)
        if invalid is None and unknown is not None:
            invalid = replace(unknown_packet_to_event(unknown, header), timestamp_ns=nominal)
        record = read_data_record_v1(data, offset)
        timestamp = header.start_time_utc_ns + record.elapsed_us * 1000
        if invalid is None and timestamp > MAX_TIMESTAMP_NS - period:
            invalid = Event(
                nominal,
                "parser",
                "time",
                Severity.ERROR,
                "INVALID_TIMESTAMP",
                "Kayit zamani int64 ns sinirini asiyor",
                source_offset=offset,
            )
        if invalid is not None:
            events.append(invalid)
            bits.extend(_bit_samples(None, nominal))
            tx_samples.append((nominal, TxState.UNKNOWN))
            uncertain_ends.add(nominal)
            previous, previous_states = None, {}
            continue

        if previous is not None:
            previous_record = previous[1]
            for gap in detect_gaps((previous_record, record), header.period_us):
                events.append(gap_to_event(gap, header, offset))
            for anomaly in detect_anomalies((previous, (offset, record)), header):
                events.append(
                    duplicate_sequence_to_event(anomaly)
                    if isinstance(anomaly, DuplicateSequence)
                    else out_of_order_to_event(anomaly)
                )
            previous_time = header.start_time_utc_ns + previous_record.elapsed_us * 1000
            if timestamp > previous_time + period:
                missing_time = previous_time + period
                tx_samples.append((missing_time, TxState.UNKNOWN))
                uncertain_ends.add(missing_time)
                previous_states = {}
        mismatch_name = check_name_consistency(record, offset)
        if mismatch_name is not None:
            events.append(
                replace(name_mismatch_to_event(mismatch_name, header), timestamp_ns=timestamp)
            )
        if record.elapsed_us != record.sequence_no * header.period_us:
            events.append(
                Event(
                    timestamp,
                    "parser",
                    "time",
                    Severity.WARNING,
                    "JITTER",
                    "Zaman nominal kayit izgarasindan sapti",
                    source_offset=offset,
                )
            )

        current_bits = _bit_samples(record.bit_status, timestamp)
        bits.extend(current_bits)
        for result in current_bits:
            before = previous_states.get(result.component)
            if (before is not None and before is not result.state) or (
                before is None and result.state is not BitState.PASS
            ):
                events.append(
                    Event(
                        timestamp,
                        "BIT",
                        "BIT",
                        result.severity,
                        f"BIT_{result.state.name}",
                        f"{result.component}: {result.state.value}",
                        state=result.state.value,
                        source_offset=offset,
                    )
                )
        previous_states = {result.component: result.state for result in current_bits}
        state = (
            TxState.from_code(record.tx_status)
            if record.tx_status in (0, 1, 2)
            else TxState.UNKNOWN
        )
        if state is TxState.UNKNOWN:
            events.append(
                Event(
                    timestamp,
                    "TX",
                    "TX",
                    Severity.WARNING,
                    "TX_UNKNOWN",
                    f"Bilinmeyen TX durum kodu: {record.tx_status}",
                    value=record.tx_status,
                    source_offset=offset,
                )
            )
            uncertain_ends.add(timestamp)
        tx_samples.append((timestamp, state))
        offsets_by_time.setdefault(timestamp, offset)
        states_by_time[timestamp] = state
        previous = offset, record

    tail = find_truncated_tail(len(data), header.header_size, header.record_size)
    if tail is not None:
        events.append(truncated_tail_to_event(tail, header))
    intervals = tuple(
        replace(interval, closed=False) if interval.end_ns in uncertain_ends else interval
        for interval in TransmissionInterval.from_state_samples(tx_samples, period_ns=period)
    )
    for interval in intervals:
        events.append(
            Event(
                interval.start_ns,
                "TX",
                "TX",
                Severity.INFO,
                "TX_START",
                "Transmisyon basladi",
                state=TxState.ACTIVE.value,
                source_offset=offsets_by_time.get(interval.start_ns),
            )
        )
        if interval.closed:
            events.append(
                Event(
                    interval.end_ns,
                    "TX",
                    "TX",
                    Severity.INFO,
                    "TX_STOP",
                    "Transmisyon durdu",
                    state=states_by_time.get(interval.end_ns, TxState.UNKNOWN).value,
                    source_offset=offsets_by_time.get(interval.end_ns),
                )
            )
    return RecordingEvents(
        tuple(sorted(events, key=lambda item: item.timestamp_ns)),
        tuple(sorted(bits, key=lambda item: item.timestamp_ns)),
        intervals,
    )
