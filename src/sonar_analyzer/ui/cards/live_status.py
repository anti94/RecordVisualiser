"""Canlı akış sağlık kartı — `F5-020`.

Paket kaybı, kuyruk doluluğu ve halka tamponun durumu tek yerde görünür.
Kabul kriteri "sentetik kayıp ve burst ekranda **doğru sayaçlarla**
görünür" olduğu için kart hiçbir sayıyı kendi hesaplamaz: değerler
üretildikleri yerden gelir —

* paket sayıları `LiveStats` (`F1-017`),
* sıra sınıflandırması `SequenceStats` (`F5-012`),
* kuyruk derinliği/tepe/düşen `BoundedPacketQueue` (`F5-016`),
* tampon doluluğu `LiveRingBuffer` (`F5-014`).

Kart yalnız biçimlendirir. Böylece ekranda görünen sayı ile akışın
gerçek sayacı **ayrışamaz**; ayrışabilseydi kullanıcı "kayıp yok"
yazısına bakıp veri kaybederdi.

Değeri olmayan alan gizlenmez, `—` gösterir (durum çubuğuyla aynı kural).
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QLabel,
    QWidget,
)

from sonar_analyzer.io.live.packet_queue import BoundedPacketQueue
from sonar_analyzer.io.live.protocol import LiveStats
from sonar_analyzer.io.live.ring_buffer import LiveRingBuffer
from sonar_analyzer.io.live.sequence_tracker import SequenceStats

CARD_OBJECT_NAME = "card_live_status"
CARD_TITLE = "Canli Akis Durumu"
EMPTY_VALUE = "—"

#: (alan adi, etiket) — yukaridan asagiya sabit sira.
FIELD_SPECS: tuple[tuple[str, str], ...] = (
    ("received", "Alinan paket"),
    ("dropped", "Dusen paket"),
    ("loss_ratio", "Kayip orani"),
    ("gaps", "Atlanan (sira bosluğu)"),
    ("duplicates", "Tekrarli"),
    ("out_of_order", "Sira disi"),
    ("queue", "Kuyruk"),
    ("queue_peak", "Kuyruk tepe"),
    ("buffer", "Tampon"),
    ("buffer_evicted", "Tampondan dusen"),
)


@dataclass(frozen=True)
class LiveHealth:
    """Karta verilecek anlık sağlık görüntüsü.

    Hepsi opsiyoneldir: canlı oturumun her parçası (kuyruk, tampon, sıra
    izleyici) her zaman kurulu olmayabilir; olmayan parça `—` gösterir,
    sıfır **gösterilmez** — "sayaç yok" ile "sayaç sıfır" farklıdır.
    """

    stats: LiveStats | None = None
    sequence: SequenceStats | None = None
    queue: BoundedPacketQueue | None = None
    buffer: LiveRingBuffer | None = None
    buffer_channel: str = ""


class LiveStatusCard(QGroupBox):
    """Canlı akışın paket/kuyruk/tampon sayaçlarını gösteren kart."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(CARD_TITLE, parent)
        self.setObjectName(CARD_OBJECT_NAME)

        layout = QFormLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        self._values: dict[str, QLabel] = {}
        for name, label_text in FIELD_SPECS:
            value = QLabel(EMPTY_VALUE, self)
            value.setObjectName(f"live_status_{name}")
            self._values[name] = value
            layout.addRow(QLabel(label_text, self), value)

    def field_names(self) -> list[str]:
        return [name for name, _ in FIELD_SPECS]

    def field_value(self, name: str) -> str:
        """Alanın gösterilen metni — testler ve kabul için."""
        try:
            return self._values[name].text()
        except KeyError as exc:
            raise KeyError(f"Tanimsiz canli durum alani: {name}") from exc

    def clear(self) -> None:
        for label in self._values.values():
            label.setText(EMPTY_VALUE)

    def update_health(self, health: LiveHealth) -> None:
        """Kartı verilen görüntüden tazeler; hiçbir sayıyı kendi türetmez."""
        self._set_packet_fields(health.stats)
        self._set_sequence_fields(health.sequence)
        self._set_queue_fields(health.queue)
        self._set_buffer_fields(health.buffer, health.buffer_channel)

    # -- alan gruplari ---------------------------------------------------

    def _set(self, name: str, text: str) -> None:
        self._values[name].setText(text or EMPTY_VALUE)

    def _set_packet_fields(self, stats: LiveStats | None) -> None:
        if stats is None:
            for name in ("received", "dropped", "loss_ratio"):
                self._set(name, EMPTY_VALUE)
            return
        self._set("received", str(stats.received_packets))
        self._set("dropped", str(stats.dropped_packets))
        self._set("loss_ratio", f"%{stats.loss_ratio * 100:.1f}")

    def _set_sequence_fields(self, sequence: SequenceStats | None) -> None:
        if sequence is None:
            for name in ("gaps", "duplicates", "out_of_order"):
                self._set(name, EMPTY_VALUE)
            return
        # Atlanan pencere sayisi ve kacinin kayboldugu birlikte gosterilir:
        # "3 bosluk / 12 paket" tek bir sayidan daha fazlasini soyler.
        self._set("gaps", f"{sequence.gaps} ({sequence.missing_total} paket)")
        self._set("duplicates", str(sequence.duplicates))
        self._set("out_of_order", str(sequence.out_of_order))

    def _set_queue_fields(self, queue: BoundedPacketQueue | None) -> None:
        if queue is None:
            self._set("queue", EMPTY_VALUE)
            self._set("queue_peak", EMPTY_VALUE)
            return
        self._set("queue", f"{queue.depth} / {queue.maxsize}")
        self._set("queue_peak", f"{queue.peak_depth} (dusen {queue.dropped_total})")

    def _set_buffer_fields(self, buffer: LiveRingBuffer | None, channel_id: str) -> None:
        if buffer is None:
            self._set("buffer", EMPTY_VALUE)
            self._set("buffer_evicted", EMPTY_VALUE)
            return
        held = buffer.count(channel_id) if channel_id else 0
        self._set("buffer", f"{held} / {buffer.capacity_samples} ornek")
        self._set("buffer_evicted", str(buffer.evicted_total))
