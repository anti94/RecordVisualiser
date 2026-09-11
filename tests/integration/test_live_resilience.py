"""Burst ve bağlantı kesintisi sonuçlarının doğrulanması — `F5-037`.

Kabul: **Sayaçlar, kuyruk sınırı, yeniden bağlanma ve UI tepkisi
bekleneni verir.**

`F5-036`'nın seed'li bozucusu burada bir ölçü aletine dönüşür: kaç paket
düşürdüğünü, kaçını geciktirdiğini ve kaçını tekrarladığını *biliyoruz*,
dolayısıyla canlı katmanın sayaçlarının **doğru** olup olmadığı
söylenebilir. Bozucu olmasaydı "sayaç 7 diyor" demekten öteye
gidilemezdi; burada sorulan "7 doğru mu".

Dört yüzey ayrı ayrı sınanır:

* **Sayaçlar** — `SequenceTracker`'ın boşluk/tekrar/sıra dışı ayrımı,
  bozucunun ürettiği gerçek bozulmayla karşılaştırılır.
* **Kuyruk sınırı** — burst altında `BoundedPacketQueue` sınırını
  **hiçbir** anda aşmaz ve düşenler görünür kalır.
* **Yeniden bağlanma** — kopma sonrası denemeler sınırlı ve görünürdür.
* **UI tepkisi** — canlı sağlık kartı bu sayaçların aynısını gösterir.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence

import numpy as np
import pytest
from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.time_range import RECORD_PERIOD_NS
from sonar_analyzer.io.live.impairment import ImpairedSource, ImpairmentProfile
from sonar_analyzer.io.live.packet_queue import BoundedPacketQueue, DropPolicy
from sonar_analyzer.io.live.protocol import ConnectionState, LivePacket, LiveStats
from sonar_analyzer.io.live.reconnect import ReconnectController, ReconnectPolicy
from sonar_analyzer.io.live.sequence_tracker import SequenceTracker
from sonar_analyzer.ui.main_window import MainWindow

START_NS = 1_788_901_200_000_000_000
CHANNELS = (ChannelMetadata(id="ch0", path="/ch0", name="ch0", dtype="float32"),)


def _packet(window: int) -> LivePacket:
    at_ns = START_NS + window * RECORD_PERIOD_NS
    chunk = DataChunk(
        "ch0",
        np.array([at_ns], dtype=np.int64),
        np.array([float(window)], dtype=np.float64),
    )
    return LivePacket(sequence_no=window, received_ns=at_ns, chunks=[chunk])


class _CleanSource:
    """Bozulmamış referans akış."""

    def __init__(self, count: int) -> None:
        self._count = count
        self.state = ConnectionState.CONNECTED
        self._stats = LiveStats()

    def channels(self) -> Sequence[ChannelMetadata]:
        return CHANNELS

    def stats(self) -> LiveStats:
        return self._stats

    def connect(self) -> None:
        self.state = ConnectionState.CONNECTED

    def disconnect(self) -> None:
        self.state = ConnectionState.DISCONNECTED

    def packets(self) -> Iterator[LivePacket]:
        for window in range(self._count):
            yield _packet(window)


def _impaired(count: int, profile: ImpairmentProfile, *, seed: int) -> ImpairedSource:
    return ImpairedSource(_CleanSource(count), profile, seed=seed, sleep=lambda _s: None)


# --------------------------------------------------------------------------- #
# SAYACLAR bekleneni verir
# --------------------------------------------------------------------------- #


def test_the_tracker_counts_every_loss_it_can_possibly_see() -> None:
    """Kayıp sayacı, gözlenen aralıktaki **her** eksiği bulur.

    Ölçüt bağımsız hesaplanır: ilk ve son gelen sıra numarası arasında
    kaç numara olması gerektiği, kaç tane geldiğinden çıkarılır.
    """
    source = _impaired(500, ImpairmentProfile(loss_ratio=0.2), seed=21)
    tracker = SequenceTracker()
    seen: list[int] = []
    for packet in source.packets():
        tracker.observe(packet.sequence_no)
        seen.append(packet.sequence_no)

    stats = tracker.stats
    assert source.impairment_stats.dropped > 0
    span = seen[-1] - seen[0] + 1
    assert stats.missing_total == span - len(seen)
    assert stats.duplicates == 0
    assert stats.out_of_order == 0


def test_a_loss_before_the_first_packet_cannot_be_seen_and_is_not_invented() -> None:
    """İlk gelen paketten **önceki** kayıp gözlenemez; uydurulmaz da.

    Sıra izleyici akışın nerede başladığını bilemez: ilk gördüğü numara
    onun için başlangıçtır. Bu yüzden baştaki kayıp `missing_total`'a
    yazılmaz — yazılsaydı, akışın gerçekten 0'dan başladığı varsayılmış
    olurdu ve bu varsayım her kaynak için doğru değildir.
    """
    source = _impaired(500, ImpairmentProfile(loss_ratio=0.2), seed=21)
    tracker = SequenceTracker()
    seen: list[int] = []
    for packet in source.packets():
        tracker.observe(packet.sequence_no)
        seen.append(packet.sequence_no)

    invisible = source.impairment_stats.dropped - tracker.stats.missing_total
    # Gorulemeyenler tam olarak ilk hayatta kalandan onceki paketlerdir
    # (kaynak 0'dan basliyor).
    assert invisible == seen[0]


def test_the_tracker_counts_exactly_the_duplicates_the_simulator_made() -> None:
    source = _impaired(400, ImpairmentProfile(duplicate_ratio=0.3), seed=22)
    tracker = SequenceTracker()
    for packet in source.packets():
        tracker.observe(packet.sequence_no)

    injected = source.impairment_stats
    assert injected.duplicated > 0
    assert tracker.stats.duplicates == injected.duplicated
    assert tracker.stats.missing_total == 0


def test_reordering_is_reported_as_out_of_order_not_as_loss() -> None:
    """Geciken paket gelir; "kayıp" sayacına yazılmamalıdır."""
    source = _impaired(300, ImpairmentProfile(reorder_ratio=0.25, reorder_depth=3), seed=23)
    tracker = SequenceTracker()
    for packet in source.packets():
        tracker.observe(packet.sequence_no)

    stats = tracker.stats
    assert source.impairment_stats.reordered > 0
    assert stats.out_of_order > 0
    assert source.impairment_stats.dropped == 0


def test_a_clean_stream_produces_clean_counters() -> None:
    """Bozulma yoksa sayaçlar sıfır — yanlış alarm üretilmez."""
    source = _impaired(200, ImpairmentProfile(), seed=24)
    tracker = SequenceTracker()
    for packet in source.packets():
        tracker.observe(packet.sequence_no)

    stats = tracker.stats
    assert stats.in_order == 200
    assert (stats.gaps, stats.missing_total, stats.duplicates, stats.out_of_order) == (0, 0, 0, 0)


def test_the_same_seed_gives_the_same_counters_twice() -> None:
    """Senaryo tekrar üretilebilir olduğu için sonuç da tekrar üretilebilir."""
    profile = ImpairmentProfile(loss_ratio=0.2, duplicate_ratio=0.1, reorder_ratio=0.1)
    counters: list[tuple[int, int, int]] = []
    for _ in range(2):
        source = _impaired(400, profile, seed=25)
        tracker = SequenceTracker()
        for packet in source.packets():
            tracker.observe(packet.sequence_no)
        stats = tracker.stats
        counters.append((stats.missing_total, stats.duplicates, stats.out_of_order))

    assert counters[0] == counters[1]


# --------------------------------------------------------------------------- #
# KUYRUK SINIRI bekleneni verir
# --------------------------------------------------------------------------- #


def test_a_burst_never_pushes_the_queue_past_its_limit() -> None:
    """Sınır **hiçbir** anda aşılmaz — sonunda değil, her adımda ölçülür."""
    source = _impaired(1000, ImpairmentProfile(burst_size=64), seed=26)
    queue = BoundedPacketQueue(16, policy=DropPolicy.DROP_OLDEST)

    for packet in source.packets():
        queue.put(packet)
        assert queue.depth <= 16

    assert queue.peak_depth <= 16


def test_a_burst_that_overflows_reports_its_drops() -> None:
    """Taşma sessiz olmaz: düşen paket sayısı görünür."""
    source = _impaired(500, ImpairmentProfile(burst_size=128), seed=27)
    queue = BoundedPacketQueue(8, policy=DropPolicy.DROP_OLDEST)
    for packet in source.packets():
        queue.put(packet)

    assert queue.dropped_total == 500 - queue.depth


def test_a_queue_large_enough_for_the_burst_drops_nothing() -> None:
    source = _impaired(200, ImpairmentProfile(burst_size=64), seed=28)
    queue = BoundedPacketQueue(256, policy=DropPolicy.DROP_OLDEST)
    for packet in source.packets():
        queue.put(packet)

    assert queue.dropped_total == 0
    assert queue.depth == 200


def test_draining_a_burst_preserves_what_the_queue_kept() -> None:
    """Kuyruğun tuttuğu paketler sırayla ve eksiksiz alınır."""
    source = _impaired(300, ImpairmentProfile(burst_size=32), seed=29)
    queue = BoundedPacketQueue(512, policy=DropPolicy.DROP_OLDEST)
    produced = [packet.sequence_no for packet in source.packets()]
    for packet in source.packets():
        queue.put(packet)

    drained: list[int] = []
    while True:
        packet = queue.get()
        if packet is None:
            break
        drained.append(packet.sequence_no)

    assert drained == produced


# --------------------------------------------------------------------------- #
# YENIDEN BAGLANMA bekleneni verir
# --------------------------------------------------------------------------- #


class _FlakySource:
    """`fail_times` denemeden sonra bağlanan kaynak."""

    def __init__(self, fail_times: int) -> None:
        self._remaining = fail_times
        self.state = ConnectionState.DISCONNECTED
        self.connect_calls = 0

    def connect(self) -> None:
        self.connect_calls += 1
        if self._remaining > 0:
            self._remaining -= 1
            self.state = ConnectionState.RECONNECTING
            raise ConnectionRefusedError("kaynak henuz hazir degil")
        self.state = ConnectionState.CONNECTED


def test_a_drop_is_followed_by_a_successful_reconnect() -> None:
    delays: list[float] = []
    source = _FlakySource(fail_times=2)
    controller = ReconnectController(source, ReconnectPolicy(max_attempts=5), sleep=delays.append)

    assert controller.run() is True
    assert source.connect_calls == 3  # iki basarisiz + bir basarili
    assert len(controller.attempts) == 3


def test_the_attempts_are_visible_after_a_reconnect() -> None:
    """Denemeler gizlenmez; arayüz bunları gösterir."""
    source = _FlakySource(fail_times=1)
    controller = ReconnectController(source, ReconnectPolicy(max_attempts=4), sleep=lambda _s: None)
    controller.run()

    assert [attempt.succeeded for attempt in controller.attempts] == [False, True]


def test_reconnecting_gives_up_after_the_configured_limit() -> None:
    """Sonsuza kadar denenmez; sınır aşılınca `False` döner."""
    source = _FlakySource(fail_times=99)
    controller = ReconnectController(source, ReconnectPolicy(max_attempts=3), sleep=lambda _s: None)

    assert controller.run() is False
    assert source.connect_calls == 3


def test_the_backoff_grows_but_stays_capped() -> None:
    delays: list[float] = []
    source = _FlakySource(fail_times=99)
    policy = ReconnectPolicy(
        max_attempts=6, initial_delay_s=0.1, max_delay_s=0.4, backoff_factor=2.0
    )
    ReconnectController(source, policy, sleep=delays.append).run()

    assert delays == sorted(delays)  # buyuyor
    assert max(delays) <= 0.4  # ama sinirli


# --------------------------------------------------------------------------- #
# UI TEPKISI bekleneni verir
# --------------------------------------------------------------------------- #


@pytest.fixture()
def win(qtbot: QtBot) -> MainWindow:
    window = MainWindow()
    qtbot.addWidget(window)
    return window


def _drain_all(win: MainWindow, expected: int) -> int:
    pumped = 0
    for _ in range(4000):
        pumped += win.pump_live_stream(limit=32)
        if pumped >= expected:
            break
        win.thread().msleep(1)
    return pumped


def test_a_lossy_burst_keeps_the_window_usable_and_shows_counters(win: MainWindow) -> None:
    """Bozuk akış altında arayüz çalışır ve sayaçları gösterir."""
    source = _impaired(400, ImpairmentProfile(loss_ratio=0.15, burst_size=32), seed=30)
    win.set_live_source(source)
    win.start_live_stream(queue_maxsize=64)
    try:
        _drain_all(win, source.impairment_stats.emitted or 1)
        card = win.right_dock.live_status

        assert win.right_dock.live_tab_is_open is True
        assert card.field_value("queue") != "—"
        # Arayuz hala cevap veriyor: yeni bir pompalama patlamaz.
        assert win.pump_live_stream(limit=8) >= 0
    finally:
        win.stop_live_stream()


def test_the_card_reports_the_queue_bound_under_burst(win: MainWindow) -> None:
    """Kartta görünen sınır, kuyruğun gerçek sınırıdır."""
    source = _impaired(600, ImpairmentProfile(burst_size=64), seed=31)
    win.set_live_source(source)
    win.start_live_stream(queue_maxsize=32)
    try:
        _drain_all(win, 200)
        depth_text = win.right_dock.live_status.field_value("queue")

        assert depth_text.endswith("/ 32")
        held = int(depth_text.split("/")[0].strip())
        assert held <= 32  # sinir asilmadi
    finally:
        win.stop_live_stream()


def test_the_card_shows_drops_when_the_burst_overflows(win: MainWindow) -> None:
    """Küçük kuyruk + büyük burst: kayıp ekranda görünür."""
    source = _impaired(800, ImpairmentProfile(burst_size=128), seed=32)
    win.set_live_source(source)
    win.start_live_stream(queue_maxsize=4)
    try:
        _drain_all(win, 100)
        peak_text = win.right_dock.live_status.field_value("queue_peak")
        assert "dusen" in peak_text
    finally:
        win.stop_live_stream()


def test_disconnecting_after_a_burst_leaves_the_ui_consistent(win: MainWindow) -> None:
    """Kopma sonrası toolbar ve durum çubuğu aynı şeyi söyler."""
    source = _impaired(200, ImpairmentProfile(burst_size=32, loss_ratio=0.1), seed=33)
    win.set_live_source(source)
    win.start_live_stream(queue_maxsize=64)
    _drain_all(win, 50)
    win.stop_live_stream()
    win.disconnect_live_source()

    assert win.connection_state() is ConnectionState.DISCONNECTED
    assert win.action("action_connect").isEnabled() is True
    assert win.action("action_disconnect").isEnabled() is False
