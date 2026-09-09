"""Calibration seçimi ve kalite eşlemesi — `F2-021`.

`docs/format/channel-map.md` §6:

* **`NaN`** — "ölçüm yok" demektir; grafikte kesinti olarak gösterilir,
  `0.0`'a çevrilmez.
* **Birim ve gain/offset kayıtta taşınmaz** — kalibrasyon kanal
  kataloğundan gelmelidir (envanter E-04); katalogda `calibration_id`
  atanmamış bir kanal sessizce "kalibre edilmiş" sayılamaz.

Bu modül iki durumu açıkça işaretler: **eksik kalibrasyon**
(`ChannelMetadata.calibration_id is None`) ve **geçersiz örnek**
(`NaN` ham değer) — ikisi de sessizce bir varsayılan değere
(`0.0`, sahte bir kalibrasyon kimliği) düşürülmez.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from sonar_analyzer.domain.channel import ChannelMetadata


class SampleQuality(str, Enum):
    """Bir örneğin güvenilirlik durumu."""

    VALID = "valid"
    #: `NaN` ham değer — "ölçüm yok" (channel-map.md §6), `0.0` değildir.
    INVALID = "invalid"


def sample_quality(raw: float) -> SampleQuality:
    """`NaN` "ölçüm yok" anlamına gelir; `0.0`'a çevrilmeden `INVALID` işaretlenir."""
    if math.isnan(raw):
        return SampleQuality.INVALID
    return SampleQuality.VALID


def is_calibrated(channel: ChannelMetadata) -> bool:
    """`calibration_id` atanmamışsa kanal kalibre edilmiş sayılmaz."""
    return channel.calibration_id is not None


@dataclass(frozen=True)
class QualifiedSample:
    """Fiziksel değer, kalite ve kalibrasyon durumu bir arada."""

    physical_value: float
    quality: SampleQuality
    calibration_id: str | None

    @property
    def is_calibrated(self) -> bool:
        return self.calibration_id is not None


def qualify_sample(channel: ChannelMetadata, raw: float) -> QualifiedSample:
    """Ham değeri kalite ve kalibrasyon bilgisiyle birlikte paketler.

    `NaN` ham değer hiçbir zaman `0.0`'a çevrilmez: `channel.to_physical`
    doğal olarak `NaN`'i korur (`NaN * gain + offset == NaN`); yalnız
    `quality` `INVALID` işaretlenir. Eksik kalibrasyon da aynı şekilde
    gizlenmez — `calibration_id` `None` ise `QualifiedSample.calibration_id`
    de `None` kalır, sahte bir kimlik üretilmez.
    """
    return QualifiedSample(
        physical_value=channel.to_physical(raw),
        quality=sample_quality(raw),
        calibration_id=channel.calibration_id,
    )
