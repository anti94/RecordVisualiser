"""Serial çerçeve sınırı ve zaman aşımı — `F5-010`.

Kabul: sanal portta eksik paket beklenir veya sözleşmeye göre raporlanır.

Gerçek seri donanım yok; enjekte edilen sahte bir aktarım (F5-009'daki
`transport_factory` enjeksiyonu) ve sahte bir saat (`FileReplaySource`/
`UdpLiveSource` ile aynı ilke) gerçek 1000 ms beklemeden zaman aşımı
senaryolarını test eder.
"""

from __future__ import annotations

import numpy as np
import pytest

from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.time_base import TimeBase
from sonar_analyzer.io.decoders.crc import crc32
from sonar_analyzer.io.live.payload_codec import encode_payload
from sonar_analyzer.io.live.protocol import ConnectionState, LiveSource
from sonar_analyzer.io.live.serial_connection import SerialConnection, SerialPortConfig
from sonar_analyzer.io.live.serial_live_source import SILENCE_TIMEOUT_NS, SYNC, SerialLiveSource
from sonar_analyzer.io.live.wire_header import PROTOCOL_SERIAL, LiveWireHeader, pack_frame

_CONFIG = SerialPortConfig(port="COM7", baud_rate=115200)


class _FakeClock:
    def __init__(self, start_ns: int = 0) -> None:
        self.now_ns = start_ns

    def __call__(self) -> int:
        return self.now_ns


class _ScriptedTransport:
    """Programlanmış bir bayt kuyruğu döndürür.

    Kuyruk tükenince (ya da hiç girilmemişse) `read()` boş bayt döner ve
    **sahte saati `timeout_s` kadar ilerletir** — gerçek `pyserial`'in
    zaman aşımında bir okumanın o kadar sürmesinin taklidi (`F5-010`'un
    zaman aşımı testlerini gerçek 1000 ms beklemeden çalıştırır).
    """

    def __init__(self, clock: _FakeClock, timeout_s: float, script: list[bytes] | None = None):
        self._clock = clock
        self._advance_ns = int(timeout_s * 1_000_000_000)
        self._script = list(script or [])
        self.closed = False

    def push(self, data: bytes) -> None:
        """Testin akış ortasında yeni bayt eklemesini sağlar."""
        self._script.append(data)

    def read(self, size: int = 1) -> bytes:
        if self._script:
            return self._script.pop(0)
        self._clock.now_ns += self._advance_ns
        return b""

    def write(self, data: bytes) -> int | None:
        return len(data)

    def close(self) -> None:
        self.closed = True


def _chunk(channel_id: str, n: int) -> DataChunk:
    timestamps = np.arange(n, dtype=np.int64) * 1_000_000
    values = np.linspace(0.0, 1.0, n, dtype=np.float64)
    return DataChunk(channel_id, timestamps, values)


def _frame(sequence_no: int, payload: bytes) -> bytes:
    """SYNC + LiveWireHeader + payload + crc32 — §3.3'ün tam çerçevesi."""
    header = LiveWireHeader(
        PROTOCOL_SERIAL,
        flags=0,
        sequence_no=sequence_no,
        fragment_index=0,
        fragment_count=1,
        device_ticks=0,
        payload_length=0,
    )
    body = pack_frame(header, payload)  # LiveWireHeader + payload (SYNC/CRC haric)
    return SYNC + body + crc32(body).to_bytes(4, "little")


def _source(
    script: list[bytes] | None = None, *, timeout_s: float = 0.05
) -> tuple[SerialLiveSource, _FakeClock, _ScriptedTransport]:
    clock = _FakeClock()
    transport = _ScriptedTransport(clock, timeout_s, script)
    connection = SerialConnection(
        _CONFIG, timeout_s=timeout_s, transport_factory=lambda _cfg, _t: transport
    )
    connection.connect()
    live = SerialLiveSource(connection, clock_ns=clock)
    return live, clock, transport


# --------------------------------------------------------------------------- #
# gecerli cerceve cozulur
# --------------------------------------------------------------------------- #


def test_a_single_frame_in_one_read_decodes() -> None:
    frame = _frame(1, encode_payload([_chunk("ch0", 10)], []))
    live, _clock, _transport = _source([frame])

    packet = next(iter(live.packets()))
    assert packet.sequence_no == 1
    assert len(packet.chunks[0]) == 10


def test_a_frame_split_into_many_small_reads_decodes() -> None:
    frame = _frame(2, encode_payload([_chunk("ch0", 30)], []))
    script = [frame[i : i + 3] for i in range(0, len(frame), 3)]  # 3'er baytlik parcalar
    live, _clock, _transport = _source(script)

    packet = next(iter(live.packets()))
    assert packet.sequence_no == 2
    assert len(packet.chunks[0]) == 30


def test_two_frames_in_one_read_both_decode_in_order() -> None:
    first = _frame(10, encode_payload([_chunk("ch0", 3)], []))
    second = _frame(11, encode_payload([_chunk("ch1", 4)], []))
    live, _clock, _transport = _source([first + second])

    iterator = live.packets()
    packet_a, packet_b = next(iterator), next(iterator)
    assert (packet_a.sequence_no, packet_b.sequence_no) == (10, 11)
    assert live.stats().received_packets == 2


# --------------------------------------------------------------------------- #
# yeniden esitleme (resync)
# --------------------------------------------------------------------------- #


def test_garbage_before_a_valid_frame_is_skipped() -> None:
    frame = _frame(5, encode_payload([_chunk("ch0", 2)], []))
    live, _clock, _transport = _source([b"\x00\x01\x02cop-veri-SYNC-degil" + frame])

    packet = next(iter(live.packets()))
    assert packet.sequence_no == 5


def test_a_crc_corrupted_frame_is_dropped_and_the_next_frame_still_decodes() -> None:
    good = _frame(1, encode_payload([_chunk("ch0", 5)], []))
    corrupted = bytearray(_frame(2, encode_payload([_chunk("ch1", 5)], [])))
    corrupted[-1] ^= 0xFF  # crc'nin son baytini boz
    third = _frame(3, encode_payload([_chunk("ch2", 5)], []))
    live, _clock, _transport = _source([bytes(corrupted) + third, good])

    iterator = live.packets()
    first_received = next(iterator)
    assert first_received.sequence_no == 3  # bozuk (seq=2) atlandi
    second_received = next(iterator)
    assert second_received.sequence_no == 1
    assert live.diagnostics == (1, 0, 0)  # (crc_hatasi, taninmayan, zaman_asimi)
    assert live.stats().dropped_packets == 1


def test_a_coincidental_sync_pattern_inside_garbage_does_not_prevent_recovery() -> None:
    """Çöp içinde tesadüfi bir `SYNC` baytı olsa da sonraki gerçek çerçeve çözülür."""
    frame = _frame(7, encode_payload([_chunk("ch0", 2)], []))
    garbage_with_fake_sync = b"once" + SYNC + b"gecersiz-baslik-burada-devam-ediyor"
    live, _clock, _transport = _source([garbage_with_fake_sync + frame])

    packet = next(iter(live.packets()))
    assert packet.sequence_no == 7


# --------------------------------------------------------------------------- #
# eksik paket: beklenir ya da zaman asimiyla raporlanir
# --------------------------------------------------------------------------- #


def test_a_valid_frame_arriving_after_a_near_threshold_gap_resets_the_silence_clock() -> None:
    """1000 ms eşiğinin **hemen altındaki** bir boşluk zaman aşımı saymaz — "beklenir"."""
    first = _frame(0, encode_payload([_chunk("ch0", 2)], []))
    second = _frame(1, encode_payload([_chunk("ch1", 2)], []))
    live, clock, transport = _source([first], timeout_s=0.1)

    iterator = live.packets()
    assert next(iterator).sequence_no == 0

    clock.now_ns += 900_000_000  # esigin (1000 ms) hemen altinda gercek bir bosluk
    transport.push(second)

    assert next(iterator).sequence_no == 1
    assert live.diagnostics == (0, 0, 0)  # zaman asimi olmadi
    assert clock.now_ns < SILENCE_TIMEOUT_NS


def test_prolonged_silence_reports_a_timeout_and_reconnects() -> None:
    """`SYNC` bile hiç görülmezse 1000 ms sonra bağlantı `RECONNECTING`'e düşer."""
    live, clock, transport = _source([], timeout_s=0.1)  # bos betik -> surekli bos okuma

    with pytest.raises(StopIteration):
        next(iter(live.packets()))

    assert live.state is ConnectionState.RECONNECTING
    assert live.diagnostics[2] == 1  # zaman_asimi
    assert transport.closed
    assert clock.now_ns >= SILENCE_TIMEOUT_NS


def test_continuous_garbage_without_a_valid_frame_still_times_out() -> None:
    """Sözleşme harfiyen: yalnız *geçerli* çerçeve saati sıfırlar, çöp değil."""
    garbage = [b"cop" * 3 for _ in range(50)]  # SYNC'e hic denk gelmeyen surekli veri
    live, clock, _transport = _source(garbage, timeout_s=0.05)

    with pytest.raises(StopIteration):
        next(iter(live.packets()))
    assert live.state is ConnectionState.RECONNECTING
    assert clock.now_ns >= SILENCE_TIMEOUT_NS


# --------------------------------------------------------------------------- #
# sozlesme
# --------------------------------------------------------------------------- #


def test_satisfies_the_live_source_protocol() -> None:
    live, _clock, _transport = _source([])
    assert isinstance(live, LiveSource)


def test_disconnect_ends_the_packets_generator() -> None:
    live, _clock, _transport = _source([_frame(0, encode_payload([_chunk("ch0", 1)], []))])
    iterator = live.packets()
    live.disconnect()
    with pytest.raises(StopIteration):
        next(iterator)


# --------------------------------------------------------------------------- #
# kanonik zaman baglantisi (F5-013)
# --------------------------------------------------------------------------- #


def test_without_a_time_base_no_window_is_computed() -> None:
    live, _clock, _transport = _source([_frame(0, encode_payload([_chunk("ch0", 2)], []))])
    next(iter(live.packets()))
    assert live.last_timed_window is None


def test_device_ticks_become_the_canonical_window_start() -> None:
    """`F5-013`: Serial tarafında da ham sayaç `TimeBase` ile kanonik zamana çevrilir."""
    time_base = TimeBase(id="device0", epoch_utc_ns=1_788_901_200_000_000_000, tick_hz=48_000)
    canonical = time_base.epoch_utc_ns + 1_000_000_000  # tam 1 saniye
    timestamps = canonical + np.arange(3, dtype=np.int64) * 1_000_000
    chunk = DataChunk("ch0", timestamps, np.zeros(3, dtype=np.float64))

    header = LiveWireHeader(
        PROTOCOL_SERIAL,
        flags=0,
        sequence_no=0,
        fragment_index=0,
        fragment_count=1,
        device_ticks=48_000,
        payload_length=0,
    )
    body = pack_frame(header, encode_payload([chunk], []))
    frame = SYNC + body + crc32(body).to_bytes(4, "little")

    clock = _FakeClock()
    transport = _ScriptedTransport(clock, 0.05, [frame])
    connection = SerialConnection(
        _CONFIG, timeout_s=0.05, transport_factory=lambda _cfg, _t: transport
    )
    connection.connect()
    live = SerialLiveSource(connection, clock_ns=clock, time_base=time_base)

    next(iter(live.packets()))
    window = live.last_timed_window
    assert window is not None
    assert window.canonical_window_start_ns == canonical
    assert window.agrees_with_payload is True
