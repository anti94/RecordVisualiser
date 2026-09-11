"""Paket kaybı, kuyruk ve tampon göstergesi — `F5-020`.

Kabul: **sentetik kayıp ve burst** ekranda **doğru sayaçlarla** görünür.

"Doğru" burada bağımsız bir referansla değil, sayacın kendisiyle
karşılaştırılır: ekrandaki metin, akışın gerçek sayacından (kuyruk,
tampon, sıra izleyici, `LiveStats`) türetilmiş olmalı. Kart hiçbir sayıyı
kendi hesaplamaz; hesaplasaydı ekran ile gerçek ayrışabilirdi ve
kullanıcı "kayıp yok" yazısına bakıp veri kaybederdi.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")
pytest.importorskip("pyqtgraph", reason="pyqtgraph kurulu degil")

import numpy as np
from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.io.live.packet_queue import BoundedPacketQueue, DropPolicy
from sonar_analyzer.io.live.protocol import LivePacket, LiveStats
from sonar_analyzer.io.live.ring_buffer import LiveRingBuffer
from sonar_analyzer.io.live.sequence_tracker import SequenceTracker
from sonar_analyzer.ui.cards.live_status import EMPTY_VALUE, LiveHealth, LiveStatusCard
from sonar_analyzer.ui.main_window import MainWindow

pytestmark = pytest.mark.gui


@pytest.fixture()
def card(qtbot: QtBot) -> LiveStatusCard:
    widget = LiveStatusCard()
    qtbot.addWidget(widget)
    return widget


def _packet(sequence_no: int) -> LivePacket:
    return LivePacket(sequence_no=sequence_no, received_ns=sequence_no)


def _chunk(channel_id: str, first: int, n: int) -> DataChunk:
    timestamps = np.arange(first, first + n, dtype=np.int64)
    return DataChunk(channel_id, timestamps, timestamps.astype(np.float64))


# --------------------------------------------------------------------------- #
# bos durum: yok ile sifir ayrisir
# --------------------------------------------------------------------------- #


def test_every_field_starts_empty(card: LiveStatusCard) -> None:
    for name in card.field_names():
        assert card.field_value(name) == EMPTY_VALUE


def test_a_missing_part_shows_em_dash_not_zero(card: LiveStatusCard) -> None:
    """ "Sayaç yok" ile "sayaç sıfır" farklıdır; kart ikisini karıştırmaz."""
    card.update_health(LiveHealth(stats=LiveStats(received_packets=5)))
    assert card.field_value("received") == "5"
    assert card.field_value("queue") == EMPTY_VALUE  # kuyruk kurulu degil
    assert card.field_value("buffer") == EMPTY_VALUE


def test_clear_returns_every_field_to_empty(card: LiveStatusCard) -> None:
    card.update_health(LiveHealth(stats=LiveStats(received_packets=5, dropped_packets=1)))
    card.clear()
    for name in card.field_names():
        assert card.field_value(name) == EMPTY_VALUE


def test_an_unknown_field_is_refused(card: LiveStatusCard) -> None:
    with pytest.raises(KeyError, match="Tanimsiz canli durum alani"):
        card.field_value("yok")


# --------------------------------------------------------------------------- #
# SENTETIK KAYIP dogru sayaclarla gorunur
# --------------------------------------------------------------------------- #


def test_synthetic_packet_loss_appears_with_the_exact_counters(card: LiveStatusCard) -> None:
    """0,1,2 → 7 (4 paket atlandı) → 7 tekrar → 5 geç gelen."""
    tracker = SequenceTracker()
    for sequence_no in (0, 1, 2, 7, 7, 5):
        tracker.observe(sequence_no)

    card.update_health(LiveHealth(sequence=tracker.stats))

    # Elle hesap: 1 bosluk, icinde 4 paket (3,4,5,6); 1 tekrar; 1 sira disi.
    assert tracker.stats.gaps == 1
    assert tracker.stats.missing_total == 4
    assert card.field_value("gaps") == "1 (4 paket)"
    assert card.field_value("duplicates") == "1"
    assert card.field_value("out_of_order") == "1"


def test_the_loss_ratio_matches_live_stats(card: LiveStatusCard) -> None:
    stats = LiveStats(received_packets=90, dropped_packets=10)
    card.update_health(LiveHealth(stats=stats))

    assert card.field_value("received") == "90"
    assert card.field_value("dropped") == "10"
    assert card.field_value("loss_ratio") == "%10.0"  # 10 / (90 + 10)


def test_a_clean_stream_shows_zero_loss_not_an_empty_field(card: LiveStatusCard) -> None:
    tracker = SequenceTracker()
    for sequence_no in range(20):
        tracker.observe(sequence_no)

    card.update_health(LiveHealth(stats=LiveStats(received_packets=20), sequence=tracker.stats))
    assert card.field_value("gaps") == "0 (0 paket)"
    assert card.field_value("loss_ratio") == "%0.0"


# --------------------------------------------------------------------------- #
# BURST dogru sayaclarla gorunur
# --------------------------------------------------------------------------- #


def test_a_queue_burst_shows_the_depth_limit_peak_and_drops(card: LiveStatusCard) -> None:
    """Kapasitesi 10 olan kuyruğa 1000 paketlik burst."""
    queue = BoundedPacketQueue(maxsize=10, policy=DropPolicy.DROP_OLDEST)
    for index in range(1000):
        queue.put(_packet(index))

    card.update_health(LiveHealth(queue=queue))

    assert card.field_value("queue") == "10 / 10"  # sinir asilmadi
    assert card.field_value("queue_peak") == f"10 (dusen {queue.dropped_total})"
    assert queue.dropped_total == 990  # 1000 uretildi, 10 kuyrukta


def test_the_queue_field_tracks_consumption(card: LiveStatusCard) -> None:
    queue = BoundedPacketQueue(maxsize=8)
    for index in range(5):
        queue.put(_packet(index))
    queue.get()
    queue.get()

    card.update_health(LiveHealth(queue=queue))
    assert card.field_value("queue") == "3 / 8"


def test_a_buffer_burst_shows_held_samples_capacity_and_eviction(card: LiveStatusCard) -> None:
    buffer = LiveRingBuffer(capacity_samples=100)
    buffer.append_chunk(_chunk("ch0", 0, 250))  # kapasitenin 2.5 kati

    card.update_health(LiveHealth(buffer=buffer, buffer_channel="ch0"))

    assert card.field_value("buffer") == "100 / 100 ornek"
    assert card.field_value("buffer_evicted") == "150"
    assert buffer.evicted_total == 150


def test_the_buffer_field_reports_the_named_channel_only(card: LiveStatusCard) -> None:
    buffer = LiveRingBuffer(capacity_samples=50)
    buffer.append_chunk(_chunk("ch0", 0, 30))
    buffer.append_chunk(_chunk("ch1", 0, 10))

    card.update_health(LiveHealth(buffer=buffer, buffer_channel="ch1"))
    assert card.field_value("buffer") == "10 / 50 ornek"


def test_an_unnamed_buffer_channel_shows_zero_held(card: LiveStatusCard) -> None:
    buffer = LiveRingBuffer(capacity_samples=50)
    buffer.append_chunk(_chunk("ch0", 0, 30))

    card.update_health(LiveHealth(buffer=buffer))  # kanal adi verilmedi
    assert card.field_value("buffer") == "0 / 50 ornek"


# --------------------------------------------------------------------------- #
# kart sayilari TURETMEZ: gercek sayacla ayrisamaz
# --------------------------------------------------------------------------- #


def test_the_card_never_computes_a_number_of_its_own(card: LiveStatusCard) -> None:
    """Aynı görüntü iki kez yazılırsa sonuç değişmez; kartın kendi durumu yoktur."""
    queue = BoundedPacketQueue(maxsize=4)
    for index in range(10):
        queue.put(_packet(index))
    health = LiveHealth(stats=LiveStats(received_packets=10, dropped_packets=6), queue=queue)

    card.update_health(health)
    first = {name: card.field_value(name) for name in card.field_names()}
    card.update_health(health)
    assert {name: card.field_value(name) for name in card.field_names()} == first


def test_counters_follow_the_source_as_it_keeps_running(card: LiveStatusCard) -> None:
    queue = BoundedPacketQueue(maxsize=5, policy=DropPolicy.DROP_OLDEST)
    for index in range(5):
        queue.put(_packet(index))
    card.update_health(LiveHealth(queue=queue))
    assert card.field_value("queue_peak") == "5 (dusen 0)"

    for index in range(5, 12):  # burst devam etti
        queue.put(_packet(index))
    card.update_health(LiveHealth(queue=queue))
    assert card.field_value("queue_peak") == "5 (dusen 7)"


# --------------------------------------------------------------------------- #
# ana pencereye bagli
# --------------------------------------------------------------------------- #


@pytest.fixture()
def win(qtbot: QtBot) -> MainWindow:
    window = MainWindow()
    qtbot.addWidget(window)
    return window


def test_the_live_tab_is_absent_until_a_source_is_attached(win: MainWindow) -> None:
    """Inspector'la aynı desen: sekme varsayılan düzende yoktur."""
    assert win.right_dock.live_tab_is_open is False
    assert "Live" not in win.right_dock.tab_titles()


def test_attaching_a_source_opens_the_live_tab_without_touching_the_cards(
    win: MainWindow,
) -> None:
    from sonar_analyzer.io.live.file_replay_source import FileReplaySource
    from sonar_analyzer.repository.mock_repository import MockRecordingRepository

    win.set_live_source(
        FileReplaySource(MockRecordingRepository(duration_s=0.5), sleep=lambda _s: None)
    )

    assert win.right_dock.live_tab_is_open is True
    assert "Live" in win.right_dock.tab_titles()
    # Mockup'in dokuz bolgesi ve Overview kart sirasi degismedi.
    assert win.right_dock.card_titles() == [
        "BIT / System Status",
        "Analysis Tools",
        "Data Export",
    ]


def test_detaching_the_source_closes_the_live_tab_and_clears_it(win: MainWindow) -> None:
    from sonar_analyzer.io.live.file_replay_source import FileReplaySource
    from sonar_analyzer.repository.mock_repository import MockRecordingRepository

    win.set_live_source(
        FileReplaySource(MockRecordingRepository(duration_s=0.5), sleep=lambda _s: None)
    )
    win.update_live_health(LiveHealth(stats=LiveStats(received_packets=7)))
    assert win.right_dock.live_status.field_value("received") == "7"

    win.set_live_source(None)
    assert win.right_dock.live_tab_is_open is False
    assert win.right_dock.live_status.field_value("received") == EMPTY_VALUE


def test_update_live_health_writes_to_the_card(win: MainWindow) -> None:
    queue = BoundedPacketQueue(maxsize=3)
    for index in range(9):
        queue.put(_packet(index))

    win.update_live_health(LiveHealth(stats=LiveStats(received_packets=9), queue=queue))
    assert win.right_dock.live_status.field_value("queue") == "3 / 3"
    assert win.right_dock.live_status.field_value("received") == "9"


def test_refresh_live_health_reads_the_connected_source(win: MainWindow) -> None:
    from sonar_analyzer.io.live.file_replay_source import FileReplaySource
    from sonar_analyzer.repository.mock_repository import MockRecordingRepository

    source = FileReplaySource(MockRecordingRepository(duration_s=0.5), sleep=lambda _s: None)
    win.set_live_source(source)
    source.connect()
    consumed = list(source.packets())

    win.refresh_live_health()
    assert win.right_dock.live_status.field_value("received") == str(len(consumed))


def test_refresh_without_a_source_shows_empty_fields(win: MainWindow) -> None:
    win.refresh_live_health()
    assert win.right_dock.live_status.field_value("received") == EMPTY_VALUE
