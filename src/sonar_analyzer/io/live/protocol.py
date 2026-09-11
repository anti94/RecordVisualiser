"""Canlı veri kaynağı sözleşmesi — `F1-017`.

Bu modül **GUI'yi bilmez**: Qt sinyali, pencere veya zamanlayıcı içermez.
Canlı kaynak yalnız paket üretir; arayüze taşıma işi üst katmanın işidir
(plan Bölüm 13). Aynı sözleşme UDP, TCP, seri port ve "dosyadan replay"
kaynakları için geçerlidir.

Kayıtlı dosya ile canlı akış aynı domain modellerine dönüşür; bu yüzden
paketler ham bayt değil, çözülmüş `DataChunk` ve `Event` taşır.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, runtime_checkable

from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.event import BitResult, Event
from sonar_analyzer.domain.transmission import TransmissionInterval


class ConnectionState(str, Enum):
    """Canlı kaynağın bağlantı durumu."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"

    @property
    def is_active(self) -> bool:
        return self is ConnectionState.CONNECTED


def _empty_chunks() -> list[DataChunk]:
    return []


def _empty_events() -> list[Event]:
    return []


def _empty_bit_results() -> list[BitResult]:
    return []


def _empty_transmissions() -> list[TransmissionInterval]:
    return []


@dataclass(frozen=True)
class LivePacket:
    """Canlı kaynaktan gelen tek bir 125 ms'lik pencere.

    `sequence_no` kaynağın verdiği sıra numarasıdır; atlaması paket kaybı
    demektir ve bu bilgi **saklanır**, sessizce düzeltilmez.
    """

    sequence_no: int
    received_ns: int
    chunks: list[DataChunk] = field(default_factory=_empty_chunks)
    events: list[Event] = field(default_factory=_empty_events)
    #: `F5-034` BIT sonuçları ve transmisyon aralıkları. Dosya tarafındaki
    #: kayıtla **aynı** domain tipleri; kaynak bunları bildirmiyorsa liste
    #: boş kalır — boş olmaları uydurma sonuç üretmemenin karşılığıdır.
    bit_results: list[BitResult] = field(default_factory=_empty_bit_results)
    transmissions: list[TransmissionInterval] = field(default_factory=_empty_transmissions)

    def __post_init__(self) -> None:
        if self.sequence_no < 0:
            raise ValueError(f"Sira numarasi negatif olamaz: {self.sequence_no}")

    @property
    def is_empty(self) -> bool:
        return not (self.chunks or self.events or self.bit_results or self.transmissions)


@dataclass(frozen=True)
class LiveStats:
    """Bağlantı sağlığı — durum çubuğunda ve tanılamada gösterilir."""

    received_packets: int = 0
    dropped_packets: int = 0
    queue_depth: int = 0
    last_sequence_no: int | None = None

    @property
    def loss_ratio(self) -> float:
        total = self.received_packets + self.dropped_packets
        return 0.0 if total == 0 else self.dropped_packets / total


@runtime_checkable
class LiveSource(Protocol):
    """Canlı veri kaynağının sunduğu arayüz."""

    @property
    def state(self) -> ConnectionState:
        """Anlık bağlantı durumu."""
        ...

    def connect(self) -> None:
        """Bağlantıyı kurar. Zaten bağlıysa etkisizdir."""
        ...

    def disconnect(self) -> None:
        """Bağlantıyı kapatır ve kaynakları bırakır. Bağlı değilse etkisizdir."""
        ...

    def channels(self) -> Sequence[ChannelMetadata]:
        """Kaynağın yayınladığı kanallar."""
        ...

    def packets(self) -> Iterator[LivePacket]:
        """Paket akışı.

        Bağlantı kapanana kadar sürer. Tüketici yetişemezse kaynak paket
        düşürür ve bunu `stats()` üzerinden raporlar; sessizce beklemez
        (plan Bölüm 13 backpressure).
        """
        ...

    def stats(self) -> LiveStats:
        """Alınan/düşen paket sayıları ve kuyruk derinliği."""
        ...
