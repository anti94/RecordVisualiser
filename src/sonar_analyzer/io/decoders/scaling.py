"""Scale ve offset dönüşümü — `F2-020`.

`ChannelMetadata.to_physical()` (`F1-011`) zaten `raw * gain + offset`
hesabını yapar. Bu modül onu kayıt düzeyine taşır: bir `DataRecordV1`/`V2`
kaydının `sensor_values` tuple'ını, kanal kataloğundaki (`F2-019`)
gain/offset'lerle fiziksel (mühendislik) değerler tuple'ına çevirir.

`docs/format/channel-map.md` §6: mevcut fixture profilinde ham `float32`
değeri zaten fiziksel birimdedir (`gain=1.0`, `offset=0.0`) — ama format
gerçek ADC ham değeri taşıyacak şekilde genişlerse (envanter E-04) aynı
kod yolu kullanılır; bu yüzden dönüşüm burada trivial gain/offset ile
değil, gerçek (sıfırdan farklı) bir sayısal dönüşümle de doğrulanır.
"""

from __future__ import annotations

from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.io.decoders.channel_catalog import CHANNELS_8
from sonar_analyzer.io.profile_a_format import DataRecordV1, DataRecordV2


def apply_scale_offset(channel: ChannelMetadata, raw: float) -> float:
    """Tek bir ham değeri kanalın `gain`/`offset`'iyle fiziksel birime çevirir."""
    return channel.to_physical(raw)


def physical_values_for_record(
    record: DataRecordV1 | DataRecordV2,
    channels: tuple[ChannelMetadata, ...] = CHANNELS_8,
) -> tuple[float, ...]:
    """Kaydın `sensor_values`'ını, verilen katalogdaki gain/offset ile fiziksel
    değerlere çevirir. Slot sırası `sensor_values` index'iyle birebirdir
    (`channel-map.md` §6: sıra sözleşmedir).

    Kanal sayısı kayıttaki değer sayısıyla eşleşmezse `ValueError` yükseltir
    — yanlış katalogla sessizce yanlış birime dönüşüm yapılmaz.
    """
    if len(record.sensor_values) != len(channels):
        raise ValueError(
            f"kanal sayisi uyusmuyor: kayitta {len(record.sensor_values)}, "
            f"katalogda {len(channels)}"
        )
    return tuple(channel.to_physical(raw) for channel, raw in zip(channels, record.sensor_values))
