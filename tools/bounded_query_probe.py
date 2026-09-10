"""ADR-010 kanıtı: blok sınırlı Profil B sorgusunun maliyeti — `F4-067`.

`F4-065` darboğazın **algoritmik** olduğunu ölçtü: `query_acoustic_channel`
her sorguda kanalın tamamını çözüyor. Bu sonda o iddianın karşı tarafını
ölçülebilir kılar — kayıt ızgarası aritmetikle adreslenip yalnız pencereye
düşen bloklar okunursa maliyet ne olur.

**Bu üretim kodu değildir.** Gerçek düzeltme Profil B okuma yoluna kayıt
indeksi eklemektir ve ayrı bir iş olarak planlanır. Sonda yalnız ADR-010'un
"saf Python/NumPy bütçeyi zaten karşılıyor mu" sorusunu yanıtlar; bu yüzden
kalite bayrağı, CRC, düzensiz kayıt sırası gibi üretim sorumluluklarını
üstlenmez ve yalnız düzgün ızgaralı dosyalarda geçerlidir.

Doğruluk `tests/unit/test_bounded_query_probe.py`'de referans decoder'a
(`query_acoustic_channel`) karşı bit düzeyinde denetlenir; sınırlılık ise
dokunulan kayıt aralığının dosya boyutundan bağımsız olmasıyla gösterilir.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

ROOT = Path(__file__).resolve().parent.parent
for location in (ROOT, ROOT / "src"):
    if str(location) not in sys.path:
        sys.path.insert(0, str(location))

from sonar_analyzer.domain.time_range import TimeRange  # noqa: E402
from sonar_analyzer.io.decoders.profile_b import ProfileBHeader  # noqa: E402
from sonar_analyzer.io.profile_b_format import (  # noqa: E402
    ACOUSTIC_NUMPY_DTYPE,
    ACOUSTIC_PAYLOAD_BYTES,
    ACOUSTIC_SAMPLE_RATE_HZ,
    BLOCK_HEADER_SIZE,
    CHANNEL_ENTRY_SIZE,
    FILE_HEADER_SIZE,
    RECORD_HEADER_SIZE,
    SAMPLES_PER_BLOCK,
    align8,
)
from sonar_analyzer.io.readers.binary_reader import ReadableBuffer  # noqa: E402

NS_PER_SECOND = 1_000_000_000


@dataclass(frozen=True)
class BoundedResult:
    """Sorgunun sonucu ve **kaç kayda dokunduğu**.

    `first_record`/`record_count` sınırlılığın kanıtıdır: dosya büyürken
    bu sayılar değişmezse okuma gerçekten pencereyle sınırlıdır.
    """

    timestamps_ns: NDArray[np.int64]
    values: NDArray[np.float64]
    first_record: int
    record_count: int


def record_span(header: ProfileBHeader, window: TimeRange) -> tuple[int, int]:
    """Pencereye dokunan `[ilk, son)` kayıt indeksleri — `O(1)` aritmetik.

    Kayıtlar `record_period_ns` ızgarasına oturduğu için hangi kayıtların
    okunacağı taranmadan hesaplanır; maliyeti dosya boyutundan bağımsızdır.
    """
    period = header.record_period_ns
    if period <= 0:
        raise ValueError(f"record_period_ns pozitif olmalı: {period}")
    first = (window.start_ns - header.t0_utc_ns) // period
    last = (window.end_ns - header.t0_utc_ns + period - 1) // period
    first = max(0, min(int(first), header.record_count))
    last = max(first, min(int(last), header.record_count))
    return first, last


def bounded_query(
    buffer: ReadableBuffer,
    header: ProfileBHeader,
    channel_id: int,
    window: TimeRange,
    sample_rate_hz: int = ACOUSTIC_SAMPLE_RATE_HZ,
) -> BoundedResult:
    """`window`'a düşen blokları okur; dosyanın kalanına hiç dokunmaz."""
    if not 0 <= channel_id < header.channel_count:
        raise ValueError(f"Kanal aralık dışı: {channel_id}")
    first, last = record_span(header, window)
    area = FILE_HEADER_SIZE + header.channel_count * CHANNEL_ENTRY_SIZE
    block_stride = align8(BLOCK_HEADER_SIZE + ACOUSTIC_PAYLOAD_BYTES)
    record_stride = align8(RECORD_HEADER_SIZE + header.channel_count * block_stride + align8(8))
    offsets = np.arange(SAMPLES_PER_BLOCK, dtype=np.int64) * NS_PER_SECOND // sample_rate_hz

    samples: list[NDArray[np.int16]] = []
    times: list[NDArray[np.int64]] = []
    for record in range(first, last):
        start = (
            area
            + record * record_stride
            + RECORD_HEADER_SIZE
            + channel_id * block_stride
            + BLOCK_HEADER_SIZE
        )
        samples.append(
            np.frombuffer(buffer, dtype=ACOUSTIC_NUMPY_DTYPE, count=SAMPLES_PER_BLOCK, offset=start)
        )
        times.append(header.t0_utc_ns + record * header.record_period_ns + offsets)

    if not samples:
        return BoundedResult(np.empty(0, dtype=np.int64), np.empty(0, dtype=np.float64), first, 0)

    stamps = np.concatenate(times)
    values = np.concatenate(samples).astype(np.float64)
    low = int(np.searchsorted(stamps, window.start_ns, side="left"))
    high = int(np.searchsorted(stamps, window.end_ns, side="left"))
    return BoundedResult(
        np.ascontiguousarray(stamps[low:high]),
        np.ascontiguousarray(values[low:high]),
        first,
        last - first,
    )
