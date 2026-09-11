"""Canlı BIT ve TX olaylarının panoya bağlanması — `F5-034`.

Kabul: **Sağ BIT özeti ve grafik marker'ları aynı geçişi gösterir.**

"Aynı geçiş" ölçülebilir hâle getirilir: akışta bir bileşen `pass`'tan
`fail`'e geçer ve

* sağdaki BIT özetinde o bileşenin durumu `fail` olur,
* grafikte **tam o zamana** denk gelen bir marker belirir.

İkisinin ayrışamaması `LiveRepository`'nin geçiş olayını, kartı besleyen
**aynı** BIT akışından üretmesiyle sağlanır; test bunu marker'ın X
konumunu BIT sonucunun zaman damgasından bağımsızca hesaplayıp
karşılaştırarak doğrular.
"""

from __future__ import annotations

from collections.abc import Iterator

import numpy as np
import pytest
from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.event import BitResult, BitState, Severity
from sonar_analyzer.domain.time_range import RECORD_PERIOD_NS, TimeRange
from sonar_analyzer.domain.transmission import TransmissionInterval, TxState
from sonar_analyzer.io.live.protocol import ConnectionState, LivePacket, LiveStats
from sonar_analyzer.io.live.ring_buffer import LiveRingBuffer
from sonar_analyzer.repository.live_repository import BIT_EVENT_CATEGORY, LiveRepository
from sonar_analyzer.ui.main_window import MainWindow
from sonar_analyzer.ui.status_icons import bit_style

FAIL_LABEL = bit_style(BitState.FAIL).label
PASS_LABEL = bit_style(BitState.PASS).label

START_NS = 1_788_901_200_000_000_000
CHANNELS = tuple(
    ChannelMetadata(id=f"ch{index}", path=f"/ch{index}", name=f"Kanal {index}", dtype="float32")
    for index in range(8)
)


def _at(window: int) -> int:
    return START_NS + window * RECORD_PERIOD_NS


def _bit(window: int, state: BitState, component: str = "Sonar Alici") -> BitResult:
    return BitResult(
        timestamp_ns=_at(window),
        test_id=7,
        component=component,
        state=state,
        severity=Severity.ERROR if state.is_failure else Severity.INFO,
        code=42,
    )


def _tx(first: int, last: int) -> TransmissionInterval:
    return TransmissionInterval(
        time_range=TimeRange(_at(first), _at(last)),
        state=TxState.ACTIVE,
    )


def _packet(
    window: int,
    *,
    bit_results: list[BitResult] | None = None,
    transmissions: list[TransmissionInterval] | None = None,
) -> LivePacket:
    chunks = [
        DataChunk(
            channel.id,
            np.array([_at(window)], dtype=np.int64),
            np.array([float(window)], dtype=np.float64),
        )
        for channel in CHANNELS
    ]
    return LivePacket(
        sequence_no=window,
        received_ns=_at(window),
        chunks=chunks,
        bit_results=list(bit_results or []),
        transmissions=list(transmissions or []),
    )


class _ScriptedSource:
    """Hazır paket listesini sırayla veren canlı kaynak."""

    def __init__(self, packets: list[LivePacket]) -> None:
        self._packets = packets
        self.state = ConnectionState.CONNECTED
        self._stats = LiveStats()

    def channels(self) -> tuple[ChannelMetadata, ...]:
        return CHANNELS

    def stats(self) -> LiveStats:
        return self._stats

    def connect(self) -> None:
        self.state = ConnectionState.CONNECTED

    def disconnect(self) -> None:
        self.state = ConnectionState.DISCONNECTED

    def packets(self) -> Iterator[LivePacket]:
        yield from self._packets


@pytest.fixture()
def win(qtbot: QtBot) -> MainWindow:
    window = MainWindow()
    qtbot.addWidget(window)
    return window


def _repository() -> LiveRepository:
    return LiveRepository(LiveRingBuffer(capacity_samples=10_000), channels=CHANNELS)


def _stream(win: MainWindow, packets: list[LivePacket]) -> None:
    """Paketleri gerçek worker üzerinden akıtır."""
    win.set_live_source(_ScriptedSource(packets))
    win.start_live_stream()
    pumped = 0
    for _ in range(3000):
        pumped += win.pump_live_stream(limit=8)
        if pumped >= len(packets):
            return
        win.thread().msleep(1)
    raise AssertionError(f"yalniz {pumped}/{len(packets)} paket pompalandi")


# --------------------------------------------------------------------------- #
# repository: BIT/TX artik tasiniyor, gecis olayi ayni akistan uretiliyor
# --------------------------------------------------------------------------- #


def test_bit_results_reach_the_repository() -> None:
    repository = _repository()
    repository.ingest(_packet(0, bit_results=[_bit(0, BitState.PASS)]))

    results = repository.bit_results(TimeRange(_at(0), _at(1)))
    assert [result.state for result in results] == [BitState.PASS]


def test_a_state_change_produces_exactly_one_transition_event() -> None:
    repository = _repository()
    repository.ingest(_packet(0, bit_results=[_bit(0, BitState.PASS)]))
    repository.ingest(_packet(1, bit_results=[_bit(1, BitState.PASS)]))  # degisiklik yok
    repository.ingest(_packet(2, bit_results=[_bit(2, BitState.FAIL)]))

    events = [
        event
        for event in repository.events(TimeRange(_at(0), _at(3)))
        if event.category == BIT_EVENT_CATEGORY
    ]
    # Ilk gozlem (bilinmiyor -> pass) ve pass -> fail: iki gecis.
    assert [event.message for event in events] == [
        "Sonar Alici: bilinmiyor -> pass",
        "Sonar Alici: pass -> fail",
    ]


def test_the_transition_event_carries_the_bit_timestamp() -> None:
    """Marker ile özetin aynı anı göstermesi buna dayanır."""
    repository = _repository()
    repository.ingest(_packet(0, bit_results=[_bit(0, BitState.PASS)]))
    repository.ingest(_packet(4, bit_results=[_bit(4, BitState.FAIL)]))

    events = [
        event
        for event in repository.events(TimeRange(_at(0), _at(5)))
        if event.category == BIT_EVENT_CATEGORY
    ]
    assert events[-1].timestamp_ns == _at(4)


def test_an_unchanged_state_produces_no_event() -> None:
    repository = _repository()
    for window in range(5):
        repository.ingest(_packet(window, bit_results=[_bit(window, BitState.PASS)]))

    events = [
        event
        for event in repository.events(TimeRange(_at(0), _at(6)))
        if event.category == BIT_EVENT_CATEGORY
    ]
    assert len(events) == 1  # yalniz ilk gozlem


def test_each_component_is_tracked_on_its_own() -> None:
    repository = _repository()
    repository.ingest(
        _packet(
            0,
            bit_results=[_bit(0, BitState.PASS, "Alici"), _bit(0, BitState.PASS, "Verici")],
        )
    )
    repository.ingest(_packet(1, bit_results=[_bit(1, BitState.FAIL, "Verici")]))

    events = [
        event
        for event in repository.events(TimeRange(_at(0), _at(2)))
        if event.category == BIT_EVENT_CATEGORY
    ]
    assert events[-1].source == "Verici"
    assert events[-1].message == "Verici: pass -> fail"


def test_transmissions_that_overlap_the_window_are_returned() -> None:
    """Ölçüt kesişimdir: pencerenin dışında biten aralık da çizilmelidir."""
    repository = _repository()
    repository.ingest(_packet(0, transmissions=[_tx(2, 9)]))

    assert len(repository.transmissions(TimeRange(_at(0), _at(4)))) == 1
    assert len(repository.transmissions(TimeRange(_at(20), _at(30)))) == 0


def test_a_source_without_bit_data_stays_empty() -> None:
    """Uydurma sonuç üretilmez."""
    repository = _repository()
    repository.ingest(_packet(0))

    assert repository.bit_results(TimeRange(_at(0), _at(2))) == []
    assert repository.transmissions(TimeRange(_at(0), _at(2))) == []


# --------------------------------------------------------------------------- #
# SAG BIT OZETI VE GRAFIK MARKER'LARI AYNI GECISI GOSTERIR
# --------------------------------------------------------------------------- #


def test_the_bit_summary_shows_the_live_failure(win: MainWindow) -> None:
    packets = [_packet(0, bit_results=[_bit(0, BitState.PASS)])]
    packets += [_packet(window) for window in range(1, 4)]
    packets.append(_packet(4, bit_results=[_bit(4, BitState.FAIL)]))
    packets += [_packet(window) for window in range(5, 8)]
    _stream(win, packets)
    try:
        assert win.right_dock.bit_status.status_text("Sonar Alici") == FAIL_LABEL
    finally:
        win.stop_live_stream()


def test_the_plot_marks_the_same_moment_the_summary_reports(win: MainWindow) -> None:
    """Asıl kabul: özetteki geçiş, grafikte tam o zamanda işaretlenir."""
    packets = [_packet(0, bit_results=[_bit(0, BitState.PASS)])]
    packets += [_packet(window) for window in range(1, 4)]
    packets.append(_packet(4, bit_results=[_bit(4, BitState.FAIL)]))
    packets += [_packet(window) for window in range(5, 8)]
    win.set_live_plot_channel("ch0")
    _stream(win, packets)
    try:
        assert win.right_dock.bit_status.status_text("Sonar Alici") == FAIL_LABEL

        panel = win.plot_panel
        assert panel.event_marker_count() == 2  # ilk gozlem + pass->fail
        # Marker'in X konumu, BIT sonucunun zamanindan BAGIMSIZ hesaplanir:
        # beklenen deger testin kendi zaman ankorundan gelir.
        expected_x = panel.x_for_timestamp_ns(_at(4))
        positions = [panel.event_marker_x(index) for index in range(2)]
        assert min(abs(position - expected_x) for position in positions) < 1e-6
    finally:
        win.stop_live_stream()


def test_the_transition_marker_is_absent_before_the_transition(win: MainWindow) -> None:
    """Geçişten önce yalnız ilk gözlemin işareti vardır."""
    packets = [_packet(0, bit_results=[_bit(0, BitState.PASS)])]
    packets += [_packet(window) for window in range(1, 4)]
    win.set_live_plot_channel("ch0")
    _stream(win, packets)
    try:
        assert win.plot_panel.event_marker_count() == 1
        assert win.right_dock.bit_status.status_text("Sonar Alici") == PASS_LABEL
    finally:
        win.stop_live_stream()


def test_live_transmissions_reach_the_plot_and_the_panel(win: MainWindow) -> None:
    packets = [_packet(0, transmissions=[_tx(1, 3)])]
    packets += [_packet(window) for window in range(1, 6)]
    win.set_live_plot_channel("ch0")
    _stream(win, packets)
    try:
        assert win.plot_panel.tx_region_count() == 1
        assert win.transmission_panel.interval_count() == 1
    finally:
        win.stop_live_stream()


def test_a_live_stream_without_bit_leaves_the_summary_empty(win: MainWindow) -> None:
    _stream(win, [_packet(window) for window in range(6)])
    try:
        assert win.right_dock.bit_status.row_count() == 0
    finally:
        win.stop_live_stream()
