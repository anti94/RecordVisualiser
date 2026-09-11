"""Canlı akışı ortak `RecordingRepository` sözleşmesine bağlar — `F5-021`.

Plan Bölüm 7.1/7.4: *"Kayıtlı dosya ve canlı akış aynı sözleşmeyi
karşılar; böylece ekranlar veri kaynağına göre değişmez."* Bu sınıf o
cümlenin gerçeklemesi: `LiveRingBuffer`'a (`F5-014`/`F5-015`) yazılan
canlı paketler, dosya tarafındakiyle **aynı** `query()`/`events()`
imzalarıyla okunur.

`F5-034` ile `LivePacket` artık BIT sonucu ve transmisyon aralığı da
taşıyor; ikisi de dosya tarafıyla **aynı** domain tipleridir ve burada
aynı `bit_results()`/`transmissions()` imzalarıyla verilir. Kaynak
bunları bildirmiyorsa listeler boş kalır — uydurma sonuç üretilmez.

BIT **geçişleri** ayrıca bir `Event` olarak yayımlanır. Sebebi kabul
kriteridir: *"Sağ BIT özeti ve grafik marker'ları aynı geçişi
gösterir."* Kart BIT sonuçlarından, marker'lar olaylardan beslendiği
için ikisinin ayrışmaması ancak **tek bir kaynaktan** türemeleriyle
garanti edilebilir; bu yüzden geçiş olayı, kartı besleyen aynı BIT
akışından üretilir. Ayrı ayrı üretilselerdi er geç ayrışırlardı.

Bellek sınırı korunur: örnekler halka tamponda (sabit kapasite), olaylar
sabit uzunluklu bir kuyrukta tutulur — canlı oturum saatlerce sürse de
ikisi de büyümez.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence

from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.event import BitResult, BitState, Event
from sonar_analyzer.domain.recording import RecordingMetadata
from sonar_analyzer.domain.time_range import RECORD_PERIOD_NS, TimeRange
from sonar_analyzer.domain.transmission import TransmissionInterval
from sonar_analyzer.io.live.protocol import LivePacket
from sonar_analyzer.io.live.ring_buffer import LiveRingBuffer
from sonar_analyzer.repository.protocol import EventFilter

#: Canlı kaynağın arayüzde görünen etiketi — simülasyonla karıştırılmaz.
LIVE_LABEL = "Canli"

#: Saklanan olay sayısı üst sınırı (bellek sınırlı kalsın diye).
DEFAULT_EVENT_CAPACITY = 10_000

#: `F5-034` BIT geçiş olaylarının kategorisi — dosya tarafıyla aynı etiket.
BIT_EVENT_CATEGORY = "BIT"

#: Bir bileşenin ilk gözleminde "önceki durum" olarak yazılan etiket.
BIT_UNKNOWN_LABEL = "bilinmiyor"


class LiveRepository:
    """Canlı akışı `RecordingRepository` gibi sorgulanabilir kılar."""

    def __init__(
        self,
        buffer: LiveRingBuffer,
        *,
        channels: Sequence[ChannelMetadata] = (),
        recording_id: str = "live",
        device_id: str = "",
        event_capacity: int = DEFAULT_EVENT_CAPACITY,
    ) -> None:
        if event_capacity < 1:
            raise ValueError(f"event_capacity pozitif olmali: {event_capacity}")
        self._buffer = buffer
        self._channels = tuple(channels)
        self._recording_id = recording_id
        self._device_id = device_id
        self._events: deque[Event] = deque(maxlen=event_capacity)
        # F5-034: BIT ve TX de sinirli kuyruklarda tutulur; canli oturum
        # saatlerce surse de bellek buyumez (olay kuyruguyla ayni ilke).
        self._bit_results: deque[BitResult] = deque(maxlen=event_capacity)
        self._transmissions: deque[TransmissionInterval] = deque(maxlen=event_capacity)
        self._last_bit_state: dict[str, BitState] = {}
        self._packet_count = 0
        self._closed = False

    # -- besleme ---------------------------------------------------------

    @property
    def buffer(self) -> LiveRingBuffer:
        return self._buffer

    @property
    def packet_count(self) -> int:
        return self._packet_count

    def ingest(self, packet: LivePacket) -> int:
        """Paketi tampona ve olay kuyruğuna yazar; **çıkarılan örnek** sayısını döner."""
        if self._closed:
            raise RuntimeError("Repository kapatildi")
        evicted = self._buffer.append_packet(packet)
        self._events.extend(packet.events)
        # F5-034: BIT gecisleri kartla AYNI akistan uretilir; marker ile
        # ozetin ayrisamamasi bundan gelir.
        for result in packet.bit_results:
            transition = self._bit_transition_event(result)
            if transition is not None:
                self._events.append(transition)
        self._bit_results.extend(packet.bit_results)
        self._transmissions.extend(packet.transmissions)
        self._packet_count += 1
        return evicted

    def _bit_transition_event(self, result: BitResult) -> Event | None:
        """Durum değiştiyse geçişi anlatan olayı üretir; değişmediyse `None`.

        İlk gözlem de bir geçiştir: bileşenin durumu o ana kadar
        **bilinmiyordu**. Bunu atlamak, oturumun başında zaten arızalı olan
        bir bileşenin grafikte hiç işaretlenmemesi demek olurdu.
        """
        previous = self._last_bit_state.get(result.component)
        if previous is result.state:
            return None
        self._last_bit_state[result.component] = result.state
        before = BIT_UNKNOWN_LABEL if previous is None else previous.value
        return Event(
            timestamp_ns=result.timestamp_ns,
            source=result.component,
            category=BIT_EVENT_CATEGORY,
            severity=result.severity,
            code=str(result.code),
            message=f"{result.component}: {before} -> {result.state.value}",
            state=result.state.value,
        )

    def set_channels(self, channels: Sequence[ChannelMetadata]) -> None:
        """Kaynağın bildirdiği kanal listesini günceller."""
        self._channels = tuple(channels)

    # -- RecordingRepository sozlesmesi -----------------------------------

    def metadata(self) -> RecordingMetadata:
        """Canlı kaydın anlık üst bilgisi.

        Zaman aralığı **tampondan** türetilir ve akış sürdükçe büyür; bu
        kayıtlı dosyadan tek farktır (orada aralık sabittir).
        """
        span = self._current_span()
        return RecordingMetadata(
            recording_id=self._recording_id,
            source_path=LIVE_LABEL,
            time_range=span,
            channel_count=len(self._channels),
            record_count=self._packet_count,
            record_period_ns=RECORD_PERIOD_NS,
            device_id=self._device_id or LIVE_LABEL,
        )

    def channels(self) -> Sequence[ChannelMetadata]:
        return self._channels

    def query(
        self,
        channel_id: str,
        time_range: TimeRange,
        max_points: int | None = None,
    ) -> DataChunk:
        """Dosya tarafıyla **aynı** imza; veriyi halka tampondan verir."""
        if self._closed:
            raise RuntimeError("Repository kapatildi")
        return self._buffer.query(channel_id, time_range, max_points)

    def events(
        self,
        time_range: TimeRange,
        filters: EventFilter | None = None,
    ) -> Sequence[Event]:
        """Aralıktaki olaylar, zamana göre artan sırada — dosya tarafıyla aynı kural."""
        selected = [event for event in self._events if time_range.contains(event.timestamp_ns)]
        if filters is not None:
            selected = [event for event in selected if filters.matches(event)]
        return sorted(selected, key=lambda event: (event.timestamp_ns, event.source))

    def bit_results(self, time_range: TimeRange) -> Sequence[BitResult]:
        """Aralıktaki BIT sonuçları, zamana göre artan sırada — `F5-034`.

        Kaynak BIT bildirmiyorsa boş döner; uydurma sonuç üretilmez.
        """
        selected = [
            result for result in self._bit_results if time_range.contains(result.timestamp_ns)
        ]
        return sorted(selected, key=lambda result: (result.timestamp_ns, result.test_id))

    def transmissions(self, time_range: TimeRange) -> Sequence[TransmissionInterval]:
        """Aralıkla **kesişen** transmisyon aralıkları — `F5-034`.

        Ölçüt kesişimdir, içerilme değil: görünen pencerenin ortasında
        başlayıp dışında biten bir transmisyon da çizilmelidir.
        """
        selected = [
            interval for interval in self._transmissions if interval.time_range.overlaps(time_range)
        ]
        return sorted(selected, key=lambda interval: interval.time_range.start_ns)

    def close(self) -> None:
        """Tamponu ve olay kuyruğunu bırakır; sonrasında sorgu yapılmaz."""
        self._buffer.clear()
        self._events.clear()
        self._bit_results.clear()
        self._transmissions.clear()
        self._last_bit_state.clear()
        self._closed = True

    # -- yardimcilar -----------------------------------------------------

    def _current_span(self) -> TimeRange:
        """Bütün kanalların kapsadığı birleşik aralık; veri yoksa boş aralık."""
        spans = [
            span
            for span in (self._buffer.time_span(channel) for channel in self._buffer.channels())
            if span is not None
        ]
        if not spans:
            return TimeRange(0, 0)
        return TimeRange(min(span.start_ns for span in spans), max(span.end_ns for span in spans))
