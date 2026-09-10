"""Türetilmiş kanalları repository sözleşmesine ekler — `F4-069`.

`DerivedChannelRepository` var olan bir `RecordingRepository`'yi **sarar**;
`F4-068` tanımlarından üretilen kanalları `Derived/` ağacına ekler ve
onları da `query()` ile sorgulanabilir kılar. GUI için fark yoktur: aynı
sözleşme, bir kanal daha.

**Ham kaynak korunur.** Sarmalayıcı taban repository'ye hiç yazmaz; taban
kanalların metadata'sı ve verisi değişmez, türetilmiş sorgu taban chunk'ın
dizilerine dokunmaz (`ProcessingChain.run` girdiyi değiştirmez, `F4-002`).
Türetilmiş bir kanalı kaldırmak da tabanı etkilemez.

**Nokta bütçesi zincirden sonra uygulanır.** `max_points` verilse bile
zincir **tam çözünürlüklü** veriyle çalışır, indirgeme en sonda yapılır.
Tersi yapılsaydı kayan pencere ortalaması, RMS veya filtre indirgenmiş
veriyi işleyip yanlış sonuç üretirdi.

Türetilmiş bir kanal başka bir türetilmiş kanalı girdi alabilir; `Derived`
gerçekten bir ağaçtır. Döngü kurulamaz: `derived_id` tanımın içeriğinden
türediği için bir tanım kendi kimliğini önceden bilip kendine bakamaz.
"""

from __future__ import annotations

from collections.abc import Sequence

from sonar_analyzer.analysis.downsampling import downsample_chunk
from sonar_analyzer.application.derived_channel import derived_sample_rate
from sonar_analyzer.domain.channel import ChannelMetadata, ChannelSource
from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.derived_channel_definition import DerivedChannelDefinition
from sonar_analyzer.domain.event import BitResult, Event
from sonar_analyzer.domain.recording import RecordingMetadata
from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.domain.transmission import TransmissionInterval
from sonar_analyzer.repository.protocol import EventFilter, RecordingRepository

#: Türetilmiş kanalların Data Explorer'daki kök klasörü.
DERIVED_ROOT = "Derived"


class DerivedChannelError(ValueError):
    """Türetilmiş kanal eklenemiyor veya kaldırılamıyor."""


class DerivedChannelRepository:
    """Taban repository'yi sarar; türetilmiş kanalları ekler, hamı korur."""

    def __init__(self, base: RecordingRepository) -> None:
        self._base = base
        self._definitions: dict[str, DerivedChannelDefinition] = {}
        self._metadata: dict[str, ChannelMetadata] = {}

    # -- turetilmis kanal yonetimi ---------------------------------------

    @property
    def base(self) -> RecordingRepository:
        """Sarılan kaynak; **salt okunur** olarak kullanılır."""
        return self._base

    def definitions(self) -> tuple[DerivedChannelDefinition, ...]:
        """Eklenme sırasıyla tanımlar."""
        return tuple(self._definitions.values())

    def definition(self, channel_id: str) -> DerivedChannelDefinition | None:
        return self._definitions.get(channel_id)

    def is_derived(self, channel_id: str) -> bool:
        return channel_id in self._definitions

    def add(self, definition: DerivedChannelDefinition) -> ChannelMetadata:
        """Tanımı ekler ve ürettiği kanalın metadata'sını döndürür.

        Aynı `derived_id` zaten varsa aynı veriyi üreten bir tanım demektir
        (kimlik içerikten türer); yalnız görünen bilgiler tazelenir.
        """
        if len(definition.inputs) > 1:
            # Sessizce ilk girişi kullanmak yanlış veri üretirdi; açıkça reddedilir.
            raise DerivedChannelError(
                f"'{definition.name}' {len(definition.inputs)} giriş bildiriyor; işlem zinciri "
                f"tek akış işler. Çok girişli kanallar formül desteğiyle gelir (`F4-070`+)."
            )
        for channel_id in definition.inputs:
            if self._lookup(channel_id) is None:
                raise DerivedChannelError(
                    f"Bilinmeyen giriş kanalı: {channel_id!r}; "
                    f"türetilmiş kanal '{definition.name}' eklenemedi"
                )
        derived_id = definition.derived_id
        self._definitions[derived_id] = definition
        self._metadata[derived_id] = self._build_metadata(definition)
        return self._metadata[derived_id]

    def remove(self, channel_id: str) -> bool:
        """Türetilmiş kanalı kaldırır; başkası ona bağlıysa reddeder."""
        if channel_id not in self._definitions:
            return False
        dependents = sorted(
            other.name
            for other_id, other in self._definitions.items()
            if other_id != channel_id and channel_id in other.inputs
        )
        if dependents:
            raise DerivedChannelError(
                f"{channel_id!r} kaldırılamaz; şu türetilmiş kanallar ona bağlı: {dependents}"
            )
        del self._definitions[channel_id]
        del self._metadata[channel_id]
        return True

    def clear_derived(self) -> None:
        """Tüm türetilmiş kanalları kaldırır; taban etkilenmez."""
        self._definitions.clear()
        self._metadata.clear()

    # -- sozlesme --------------------------------------------------------

    def metadata(self) -> RecordingMetadata:
        """Taban kaydın üst bilgisi — türetilmiş kanal kaydı değiştirmez."""
        return self._base.metadata()

    def channels(self) -> tuple[ChannelMetadata, ...]:
        """Önce ham kanallar, sonra `Derived/` ağacı."""
        return (*self._base.channels(), *self._metadata.values())

    def query(
        self,
        channel_id: str,
        time_range: TimeRange,
        max_points: int | None = None,
    ) -> DataChunk:
        """Ham kanalı tabana iletir; türetilmiş kanalı zinciri koşarak üretir."""
        definition = self._definitions.get(channel_id)
        if definition is None:
            return self._base.query(channel_id, time_range, max_points)

        # Zincir tam çözünürlüklü veriyle çalışır; bütçe en sonda uygulanır.
        source = self._query_source(definition.inputs[0], time_range)
        result = definition.chain.run(source.values, source.quality)
        derived = DataChunk(
            channel_id=channel_id,
            timestamps_ns=source.timestamps_ns,
            values=result.values,
            quality=source.quality,
        )
        return downsample_chunk(derived, max_points)

    def events(
        self,
        time_range: TimeRange,
        filters: EventFilter | None = None,
    ) -> Sequence[Event]:
        return self._base.events(time_range, filters)

    def bit_results(self, time_range: TimeRange) -> Sequence[BitResult]:
        return self._base.bit_results(time_range)

    def transmissions(self, time_range: TimeRange) -> Sequence[TransmissionInterval]:
        return self._base.transmissions(time_range)

    def close(self) -> None:
        """Tabanı kapatır; tanımlar bellekte kalır (kaynak yeniden açılabilir)."""
        self._base.close()

    # -- ic --------------------------------------------------------------

    def _lookup(self, channel_id: str) -> ChannelMetadata | None:
        if channel_id in self._metadata:
            return self._metadata[channel_id]
        return next(
            (channel for channel in self._base.channels() if channel.id == channel_id), None
        )

    def _query_source(self, channel_id: str, time_range: TimeRange) -> DataChunk:
        """Girdiyi tam çözünürlükte okur; türetilmiş girdide özyinelenir."""
        return self.query(channel_id, time_range, None)

    def _build_metadata(self, definition: DerivedChannelDefinition) -> ChannelMetadata:
        base = self._lookup(definition.inputs[0])
        assert base is not None  # `add` önce doğruladı
        rate = base.sample_rate_hz
        if rate is not None:
            new_rate = derived_sample_rate(rate, definition.chain)
            rate = new_rate if new_rate > 0 else None
        return ChannelMetadata(
            id=definition.derived_id,
            path=f"{DERIVED_ROOT}/{definition.name}",
            name=definition.name,
            dtype="float64",  # zincir her zaman float64 üretir (`F4-002`)
            source=ChannelSource.DERIVED,
            unit=definition.unit if definition.unit is not None else base.unit,
            sample_rate_hz=rate,
            time_base_id=base.time_base_id,
        )
