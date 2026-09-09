"""Profil A sensör alanlarını kanal metadata'sına eşleme — `F2-019`.

`docs/format/channel-map.md` §2: `channel_count = 8` (fixture profili) için
minimal sözlük. `CH0`–`CH7` sırası, `dtype` (`sensor_values` her zaman
`float32` — `DATA_RECORD_V1`/`V2`'deki `"8f"` struct format harfi) ve
birimler bu sözlükle sabitlenir. Slot sırası **sözleşmedir**
(`channel-map.md` §6): sıra değişirse `version` artmalıdır.

Plan Bölüm 7.1 katman ayrımına uyar: parser (`io`) ham `CH0..CH7`
`float32` dizisini domain `ChannelMetadata` listesine çevirir; GUI kanal
adını asla kod içinde sabitlemez, katalogdan okur.

**Bu bir öneridir, gerçek kanal kataloğu değildir** (envanter E-04/E-05,
`channel-map.md` başlığı) — gerçek katalog geldiğinde bu modül güncellenir.
"""

from __future__ import annotations

from sonar_analyzer.domain.channel import ChannelMetadata, ChannelSource

#: Profil A'da tüm kanallar aynı kayıt periyodunu paylaşır (`125_000 µs` = 8 Hz).
_SAMPLE_RATE_HZ = 8.0

#: docs/format/channel-map.md §2 — minimal sözlük, CH0-CH7 sırasıyla.
CHANNELS_8: tuple[ChannelMetadata, ...] = (
    ChannelMetadata(
        id="ch0",
        path="Sensors/Pressure",
        name="Pressure",
        dtype="float32",
        source=ChannelSource.SENSORS,
        unit="bar",
        sample_rate_hz=_SAMPLE_RATE_HZ,
    ),
    ChannelMetadata(
        id="ch1",
        path="Sensors/Temperature",
        name="Temperature",
        dtype="float32",
        source=ChannelSource.SENSORS,
        unit="°C",
        sample_rate_hz=_SAMPLE_RATE_HZ,
    ),
    ChannelMetadata(
        id="ch2",
        path="Sensors/Accelerometer/X",
        name="Accelerometer X",
        dtype="float32",
        source=ChannelSource.SENSORS,
        unit="g",
        sample_rate_hz=_SAMPLE_RATE_HZ,
    ),
    ChannelMetadata(
        id="ch3",
        path="Sensors/Accelerometer/Y",
        name="Accelerometer Y",
        dtype="float32",
        source=ChannelSource.SENSORS,
        unit="g",
        sample_rate_hz=_SAMPLE_RATE_HZ,
    ),
    ChannelMetadata(
        id="ch4",
        path="Sensors/Accelerometer/Z",
        name="Accelerometer Z",
        dtype="float32",
        source=ChannelSource.SENSORS,
        unit="g",
        sample_rate_hz=_SAMPLE_RATE_HZ,
    ),
    ChannelMetadata(
        id="ch5",
        path="Acoustic/Hydrophone 1",
        name="Hydrophone 1",
        dtype="float32",
        source=ChannelSource.ACOUSTIC,
        unit="Pa",
        sample_rate_hz=_SAMPLE_RATE_HZ,
    ),
    ChannelMetadata(
        id="ch6",
        path="Navigation/Depth",
        name="Depth",
        dtype="float32",
        source=ChannelSource.NAVIGATION,
        unit="m",
        sample_rate_hz=_SAMPLE_RATE_HZ,
    ),
    ChannelMetadata(
        id="ch7",
        path="Vehicle/Voltage",
        name="Voltage",
        dtype="float32",
        source=ChannelSource.TRANSMISSION,
        unit="V",
        sample_rate_hz=_SAMPLE_RATE_HZ,
    ),
)


def channel_metadata_for_slot(slot: int) -> ChannelMetadata:
    """`CHn` (`slot = n`) için sözlük kaydını döner.

    `slot`, `sensor_values` tuple'ındaki index ile birebir aynıdır
    (`0..channel_count - 1`); geçersizse `ValueError` yükseltir.
    """
    if not 0 <= slot < len(CHANNELS_8):
        raise ValueError(f"gecersiz kanal slotu: {slot} (0..{len(CHANNELS_8) - 1} beklenir)")
    return CHANNELS_8[slot]
