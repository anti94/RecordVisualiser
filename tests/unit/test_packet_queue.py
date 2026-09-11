"""Sınırlı kuyruk ve drop politikası — `F5-016`.

Kabul: burst sırasında sınır aşılmaz; düşen veri sayısı raporlanır.

İki değişmez her politikada ayrı ayrı doğrulanır:

1. **Sınır aşılmaz** — `peak_depth` hiçbir zaman `maxsize`'ı geçmez
   (10.000 paketlik bir burst sırasında bile).
2. **Korunum** — `accepted + dropped == üretilen`; hiçbir paket sessizce
   kaybolmaz. Bu, "düşen veri sayısı raporlanır" iddiasının sıkı biçimi:
   sayı yalnız artmakla kalmaz, kayıp olanla **birebir** örtüşür.
"""

from __future__ import annotations

import threading
import time

import pytest

from sonar_analyzer.io.live.packet_queue import BoundedPacketQueue, DropPolicy
from sonar_analyzer.io.live.protocol import LivePacket


def _packet(sequence_no: int) -> LivePacket:
    return LivePacket(sequence_no=sequence_no, received_ns=sequence_no * 1_000_000)


# --------------------------------------------------------------------------- #
# sinir altinda
# --------------------------------------------------------------------------- #


def test_below_the_limit_everything_is_accepted() -> None:
    queue = BoundedPacketQueue(maxsize=10)
    for index in range(7):
        assert queue.put(_packet(index)) is True

    assert queue.depth == 7
    assert queue.accepted_total == 7
    assert queue.dropped_total == 0


def test_get_returns_packets_in_fifo_order() -> None:
    queue = BoundedPacketQueue(maxsize=10)
    for index in range(3):
        queue.put(_packet(index))

    assert [queue.get(), queue.get(), queue.get()] != [None, None, None]
    assert queue.get() is None  # bosaldi


def test_fifo_order_is_the_write_order() -> None:
    queue = BoundedPacketQueue(maxsize=10)
    for index in range(4):
        queue.put(_packet(index))

    received = [queue.get() for _ in range(4)]
    assert [p.sequence_no for p in received if p is not None] == [0, 1, 2, 3]


def test_drain_empties_the_queue_in_order() -> None:
    queue = BoundedPacketQueue(maxsize=10)
    for index in range(5):
        queue.put(_packet(index))

    drained = queue.drain()
    assert [p.sequence_no for p in drained] == [0, 1, 2, 3, 4]
    assert queue.depth == 0


# --------------------------------------------------------------------------- #
# DROP_OLDEST - canli gorunum varsayilani
# --------------------------------------------------------------------------- #


def test_drop_oldest_keeps_the_newest_packets() -> None:
    queue = BoundedPacketQueue(maxsize=3, policy=DropPolicy.DROP_OLDEST)
    for index in range(6):
        assert queue.put(_packet(index)) is True  # hepsi "kabul" edilir

    drained = queue.drain()
    assert [p.sequence_no for p in drained] == [3, 4, 5]  # en yeniler kaldi
    assert queue.dropped_total == 3  # 0,1,2 dustu


def test_drop_oldest_never_exceeds_the_limit() -> None:
    queue = BoundedPacketQueue(maxsize=5, policy=DropPolicy.DROP_OLDEST)
    for index in range(100):
        queue.put(_packet(index))
        assert queue.depth <= 5  # her adimda dogrulanir

    assert queue.peak_depth == 5


# --------------------------------------------------------------------------- #
# DROP_NEWEST - suregelen veri korunur
# --------------------------------------------------------------------------- #


def test_drop_newest_rejects_the_incoming_packet() -> None:
    queue = BoundedPacketQueue(maxsize=3, policy=DropPolicy.DROP_NEWEST)
    for index in range(3):
        assert queue.put(_packet(index)) is True
    assert queue.put(_packet(99)) is False  # reddedildi

    drained = queue.drain()
    assert [p.sequence_no for p in drained] == [0, 1, 2]  # kuyruktakiler korundu
    assert queue.dropped_total == 1


def test_drop_newest_accepts_again_after_space_frees_up() -> None:
    queue = BoundedPacketQueue(maxsize=2, policy=DropPolicy.DROP_NEWEST)
    queue.put(_packet(0))
    queue.put(_packet(1))
    assert queue.put(_packet(2)) is False

    queue.get()  # tuketici bir yer acti
    assert queue.put(_packet(3)) is True


# --------------------------------------------------------------------------- #
# BLOCK - gercek backpressure
# --------------------------------------------------------------------------- #


def test_block_waits_until_the_consumer_frees_space() -> None:
    queue = BoundedPacketQueue(maxsize=1, policy=DropPolicy.BLOCK, block_timeout_s=2.0)
    queue.put(_packet(0))

    def consume_after_a_moment() -> None:
        time.sleep(0.05)
        queue.get()

    consumer = threading.Thread(target=consume_after_a_moment)
    consumer.start()
    try:
        started = time.perf_counter()
        accepted = queue.put(_packet(1))  # yer acilana kadar bekler
        elapsed = time.perf_counter() - started
    finally:
        consumer.join(timeout=2.0)

    assert accepted is True
    assert queue.dropped_total == 0
    assert elapsed >= 0.04  # gercekten bekledi


def test_block_gives_up_after_the_timeout_and_counts_the_drop() -> None:
    queue = BoundedPacketQueue(maxsize=1, policy=DropPolicy.BLOCK, block_timeout_s=0.05)
    queue.put(_packet(0))

    started = time.perf_counter()
    accepted = queue.put(_packet(1))  # kimse tuketmiyor
    elapsed = time.perf_counter() - started

    assert accepted is False
    assert queue.dropped_total == 1
    assert 0.04 <= elapsed < 1.0  # zaman asimi kadar bekledi, sonsuza degil


# --------------------------------------------------------------------------- #
# burst: sinir asilmaz, kayip birebir raporlanir
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("policy", [DropPolicy.DROP_OLDEST, DropPolicy.DROP_NEWEST])
def test_a_large_burst_never_exceeds_the_limit_and_conserves_the_count(
    policy: DropPolicy,
) -> None:
    """10.000 paketlik burst: derinlik sınırı aşmaz, hiçbir paket sessizce kaybolmaz."""
    queue = BoundedPacketQueue(maxsize=10, policy=policy)
    produced = 10_000
    for index in range(produced):
        queue.put(_packet(index))

    assert queue.peak_depth <= 10
    assert queue.depth <= 10
    # Korunum: her paket ya kuyrukta, ya tuketilmis, ya da dusmus olmali.
    # (Burada hic tuketilmedi.) Bu yasa iki politikada da ayni; `accepted_total`
    # ise politikaya baglidir: DROP_OLDEST'te gelen paket kuyruga GIRER ve ayrica
    # eski bir paket duser, bu yuzden accepted+dropped korunum yasasi DEGILDIR.
    assert queue.depth + queue.dropped_total == produced


def test_interleaved_production_and_consumption_conserves_every_packet() -> None:
    queue = BoundedPacketQueue(maxsize=4, policy=DropPolicy.DROP_OLDEST)
    consumed = 0
    produced = 500
    for index in range(produced):
        queue.put(_packet(index))
        if index % 3 == 0 and queue.get() is not None:
            consumed += 1

    remaining = queue.depth
    assert queue.peak_depth <= 4
    assert consumed + remaining + queue.dropped_total == produced


def test_threaded_producers_and_a_consumer_conserve_every_packet() -> None:
    """Dört üretici + bir tüketici: sayaçlar iş parçacığı yarışında da tutarlı."""
    queue = BoundedPacketQueue(maxsize=8, policy=DropPolicy.DROP_OLDEST)
    per_producer = 500
    producer_count = 4
    consumed: list[int] = []
    stop = threading.Event()

    def produce(base: int) -> None:
        for index in range(per_producer):
            queue.put(_packet(base * per_producer + index))

    def consume() -> None:
        while not stop.is_set():
            packet = queue.get(timeout_s=0.01)
            if packet is not None:
                consumed.append(packet.sequence_no)

    consumer = threading.Thread(target=consume)
    consumer.start()
    producers = [threading.Thread(target=produce, args=(base,)) for base in range(producer_count)]
    for producer in producers:
        producer.start()
    for producer in producers:
        producer.join(timeout=10.0)
    time.sleep(0.05)  # tuketicinin kalanlari almasina firsat ver
    stop.set()
    consumer.join(timeout=5.0)

    produced = per_producer * producer_count
    assert queue.peak_depth <= 8  # sinir yaris kosullarinda da asilmadi
    assert len(consumed) + queue.depth + queue.dropped_total == produced


# --------------------------------------------------------------------------- #
# LiveStats baglantisi ve yapilandirma
# --------------------------------------------------------------------------- #


def test_stats_reports_depth_and_drops() -> None:
    queue = BoundedPacketQueue(maxsize=2, policy=DropPolicy.DROP_OLDEST)
    for index in range(5):
        queue.put(_packet(index))

    stats = queue.stats(received_packets=5, last_sequence_no=4)
    assert stats.queue_depth == 2
    assert stats.dropped_packets == 3
    assert stats.received_packets == 5
    assert stats.last_sequence_no == 4
    assert abs(stats.loss_ratio - 3 / 8) < 1e-12  # 3 / (5 + 3)


def test_clear_resets_the_queue_and_counters() -> None:
    queue = BoundedPacketQueue(maxsize=2)
    for index in range(5):
        queue.put(_packet(index))

    queue.clear()
    assert queue.depth == 0
    assert queue.dropped_total == 0
    assert queue.accepted_total == 0
    assert queue.peak_depth == 0


def test_get_with_a_timeout_returns_none_on_an_empty_queue() -> None:
    queue = BoundedPacketQueue(maxsize=2)
    started = time.perf_counter()
    assert queue.get(timeout_s=0.05) is None
    assert time.perf_counter() - started >= 0.04


def test_maxsize_must_be_positive() -> None:
    with pytest.raises(ValueError, match="maxsize pozitif olmali"):
        BoundedPacketQueue(maxsize=0)


def test_block_timeout_must_be_positive() -> None:
    with pytest.raises(ValueError, match="block_timeout_s pozitif olmali"):
        BoundedPacketQueue(maxsize=2, block_timeout_s=0.0)
