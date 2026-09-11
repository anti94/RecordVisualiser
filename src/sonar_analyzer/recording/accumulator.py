"""125 ms kayıt biriktirme sınırları — `F5-027`.

Kabul: **`Data00000` ve `Data00001` 125 ms aralıklarla oluşur; ham blok
örnekleri korunur.**

Canlı paketler (`LivePacket`, `F1-017`) zaten 125 ms'lik pencerelerdir;
bu modül onları Profil A kayıt ızgarasına oturtur: pencerenin başlangıcı
dosya ankoruna (`start_time_utc_ns`) göre hangi sıraya düşüyorsa o
`DataNNNNN` olur ve `elapsed_us = sequence_no × 125_000` yazılır. Sıra
numarası **zamandan türetilir**, sayaç artırarak değil: bir pencere hiç
gelmezse (paket kaybı) sonraki kayıt kendi doğru sırasına oturur, kayıt
dosyası zamanla kaymaz.

"Ham blok örnekleri korunur" kuralı burada bir **sınır** anlamına gelir:
Profil A kaydı kanal başına **tek** değer taşır (8 × float32). Bir
pencerede bir kanaldan birden çok örnek gelirse o veri Profil A'ya
kayıpsız sığmaz — accumulator bunu sessizce kırpmaz, `LossyRecordError`
ile reddeder. Yüksek örnek hızlı akış Profil B'nin işidir
(`docs/format/profile-b.md`); sessiz kırpma, kullanıcının veri
kaybettiğini hiç bilmemesi demek olurdu.
"""

from __future__ import annotations

from dataclasses import dataclass

from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.time_range import RECORD_PERIOD_NS
from sonar_analyzer.io.live.protocol import LivePacket
from sonar_analyzer.io.profile_a_format import EXPECTED_CHANNEL_COUNT
from sonar_analyzer.recording.record_writer import build_data_record

#: 125 ms kaydın mikrosaniye karşılığı (`docs/format/timing-and-naming.md`).
RECORD_PERIOD_US = RECORD_PERIOD_NS // 1000


class LossyRecordError(ValueError):
    """Veri Profil A kaydına **kayıpsız** sığmıyor; sessiz kırpma yapılmaz."""


@dataclass(frozen=True)
class PendingRecord:
    """Yazılmaya hazır tek bir kayıt."""

    sequence_no: int
    elapsed_us: int
    payload: bytes

    @property
    def name(self) -> str:
        return f"Data{self.sequence_no:05d}"


class RecordAccumulator:
    """Canlı paketleri 125 ms ızgarasındaki `DataNNNNN` kayıtlarına dönüştürür."""

    def __init__(
        self,
        start_time_utc_ns: int,
        channel_ids: list[str],
        *,
        version: int = 2,
    ) -> None:
        if start_time_utc_ns < 0:
            raise ValueError(f"start_time_utc_ns negatif olamaz: {start_time_utc_ns}")
        if len(channel_ids) != EXPECTED_CHANNEL_COUNT:
            raise ValueError(f"Profil A {EXPECTED_CHANNEL_COUNT} kanal bekler: {len(channel_ids)}")
        self._start_ns = start_time_utc_ns
        self._channel_ids = list(channel_ids)
        self._version = version
        self._written = 0

    @property
    def start_time_utc_ns(self) -> int:
        return self._start_ns

    @property
    def channel_ids(self) -> list[str]:
        return list(self._channel_ids)

    @property
    def record_count(self) -> int:
        """Şimdiye kadar üretilen kayıt sayısı."""
        return self._written

    def sequence_for(self, timestamp_ns: int) -> int:
        """Bir anın hangi 125 ms kaydına düştüğü — zamandan türetilir."""
        if timestamp_ns < self._start_ns:
            raise ValueError(f"Zaman kayit baslangicindan once: {timestamp_ns} < {self._start_ns}")
        return (timestamp_ns - self._start_ns) // RECORD_PERIOD_NS

    def accept(self, packet: LivePacket) -> PendingRecord | None:
        """Paketi bir kayda çevirir; pencerede örnek yoksa `None`.

        Bir kanaldan pencerede birden çok örnek gelirse `LossyRecordError`
        yükselir — Profil A o veriyi kayıpsız taşıyamaz.
        """
        by_channel = {chunk.channel_id: chunk for chunk in packet.chunks if len(chunk)}
        if not by_channel:
            return None

        first_ns = min(int(chunk.timestamps_ns[0]) for chunk in by_channel.values())
        sequence_no = self.sequence_for(first_ns)
        values = [
            self._single_value(by_channel.get(channel_id)) for channel_id in self._channel_ids
        ]

        record = PendingRecord(
            sequence_no=sequence_no,
            elapsed_us=sequence_no * RECORD_PERIOD_US,
            payload=build_data_record(
                sequence_no=sequence_no,
                elapsed_us=sequence_no * RECORD_PERIOD_US,
                sensor_values=values,
                version=self._version,
            ),
        )
        self._written += 1
        return record

    def _single_value(self, chunk: DataChunk | None) -> float:
        """Kanalın penceredeki tek değeri; veri yoksa `0.0`, çoksa hata."""
        if chunk is None or not len(chunk):
            return 0.0
        if len(chunk) > 1:
            raise LossyRecordError(
                f"{chunk.channel_id}: 125 ms penceresinde {len(chunk)} ornek var; "
                "Profil A kanal basina tek deger tasir. Yuksek ornek hizli akis "
                "icin Profil B kullanilmali (docs/format/profile-b.md)."
            )
        return float(chunk.values[0])
