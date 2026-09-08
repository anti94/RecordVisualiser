"""Veri erişim sözleşmesi — `F1-016`.

GUI, `.bin` byte düzenini veya paket yapısını **bilmez**; yalnız bu arayüzle ve
domain modelleriyle konuşur (plan Bölüm 7.1, 7.4). Kayıtlı dosya ve canlı akış
aynı sözleşmeyi karşılar; böylece ekranlar veri kaynağına göre değişmez.

`max_points` görünür piksel genişliğiyle ilişkilendirilir: repository uygun
downsample seviyesini seçer. Milyonlarca nokta doğrudan grafik nesnesine
gönderilmez (plan Bölüm 7.4, `docs/perf/budget.md` §4.1).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.event import BitResult, Event, Severity
from sonar_analyzer.domain.recording import RecordingMetadata
from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.domain.transmission import TransmissionInterval


def _empty_str_list() -> list[str]:
    return []


@dataclass(frozen=True)
class EventFilter:
    """Olay sorgusunu daraltan ölçütler. Boş filtre her şeyi kabul eder."""

    sources: list[str] = field(default_factory=_empty_str_list)
    categories: list[str] = field(default_factory=_empty_str_list)
    min_severity: Severity | None = None
    text: str = ""

    def matches(self, event: Event) -> bool:
        if self.sources and event.source not in self.sources:
            return False
        if self.categories and event.category not in self.categories:
            return False
        if self.min_severity is not None and event.severity.rank < self.min_severity.rank:
            return False
        return not (self.text and self.text.casefold() not in event.message.casefold())


@runtime_checkable
class RecordingRepository(Protocol):
    """Kayıtlı bir veri kaynağının GUI'ye sunduğu arayüz."""

    def metadata(self) -> RecordingMetadata:
        """Kaydın üst bilgisi."""
        ...

    def channels(self) -> Sequence[ChannelMetadata]:
        """Kaynakta gerçekten bulunan kanallar."""
        ...

    def query(
        self,
        channel_id: str,
        time_range: TimeRange,
        max_points: int | None = None,
    ) -> DataChunk:
        """Bir kanalın verilen aralıktaki verisi.

        `max_points` verilirse sonuç en fazla o kadar nokta içerir; indirgeme
        yöntemi repository'nin seçimidir ama dar impulslar kaybolmamalıdır.
        Aralıkta veri yoksa **boş ama geçerli** bir `DataChunk` döner; hata
        fırlatılmaz.
        """
        ...

    def events(
        self,
        time_range: TimeRange,
        filters: EventFilter | None = None,
    ) -> Sequence[Event]:
        """Aralıktaki olaylar, zamana göre artan sırada."""
        ...

    def bit_results(self, time_range: TimeRange) -> Sequence[BitResult]:
        """Aralıktaki BIT sonuçları."""
        ...

    def transmissions(self, time_range: TimeRange) -> Sequence[TransmissionInterval]:
        """Aralıkla kesişen transmisyon aralıkları."""
        ...

    def close(self) -> None:
        """Açık dosya tanıtıcılarını ve eşlemeleri bırakır."""
        ...
