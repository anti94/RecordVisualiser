"""Sürümlü dosya header yazıcısı — `F5-025`.

Kabul kriterinin özü: **dosya format sürümü uygulama sürümünden bağımsız
yazılır.** `VERSION` dosyasındaki `2.25.0` ile başlığa yazılan format
sürümü (`1` ya da `2`) aynı şey değildir; ikisinin karışması, uygulama
sürümü her arttığında okunamayan kayıtlar üretirdi. Bu modül format
sürümünü **yalnız** `docs/format/profile-a.md` ve `ADR-011`'den alır;
uygulama sürümüne hiçbir yerde bakmaz.

Yazılan bayt düzeni okuma tarafıyla (`F2-001`'in `profile_a_format`
sabitleri) aynı `struct.Struct` sözleşmesini kullanır — iki taraf tek bir
tanımı paylaştığı için ayrışamazlar.

Sürüm 2 başlığı `header_crc32` taşır; CRC **kendi alanı hariç**, başlığın
ilk baytından CRC alanının hemen öncesine kadar hesaplanır (ADR-011 §2.2).
"""

from __future__ import annotations

from sonar_analyzer.io.decoders.crc import header_crc32
from sonar_analyzer.io.profile_a_format import (
    EXPECTED_CHANNEL_COUNT,
    EXPECTED_HEADER_SIZE_V1,
    EXPECTED_HEADER_SIZE_V2,
    EXPECTED_PERIOD_US,
    EXPECTED_RECORD_SIZE_V1,
    EXPECTED_RECORD_SIZE_V2,
    FILE_HEADER_V1,
    FILE_HEADER_V2,
    MAGIC,
    SUPPORTED_VERSIONS,
)

#: Yeni kayıtların öntanımlı format sürümü. Uygulama sürümünden **bağımsız**;
#: yalnız format değiştiğinde ve bilinçli bir kararla artar (ADR-011).
DEFAULT_FORMAT_VERSION = 2

#: `(sürüm) -> (header_size, record_size)` — okuma tarafındaki sabitlerle aynı.
_LAYOUT: dict[int, tuple[int, int]] = {
    1: (EXPECTED_HEADER_SIZE_V1, EXPECTED_RECORD_SIZE_V1),
    2: (EXPECTED_HEADER_SIZE_V2, EXPECTED_RECORD_SIZE_V2),
}


def header_size_for(version: int) -> int:
    """Sürümün başlık boyutu."""
    return _layout(version)[0]


def record_size_for(version: int) -> int:
    """Sürümün kayıt boyutu."""
    return _layout(version)[1]


def build_file_header(
    *,
    start_time_utc_ns: int,
    version: int = DEFAULT_FORMAT_VERSION,
    period_us: int = EXPECTED_PERIOD_US,
    channel_count: int = EXPECTED_CHANNEL_COUNT,
) -> bytes:
    """Dosya başlığını baytlara yazar.

    `version` **format** sürümüdür; uygulama sürümüyle ilgisi yoktur.
    Sürüm 2'de `header_crc32` hesaplanıp sona eklenir.
    """
    header_size, record_size = _layout(version)
    if start_time_utc_ns < 0:
        raise ValueError(f"start_time_utc_ns negatif olamaz: {start_time_utc_ns}")
    if period_us <= 0:
        raise ValueError(f"period_us pozitif olmali: {period_us}")
    if channel_count != EXPECTED_CHANNEL_COUNT:
        # Profil A kayit duzeni 8 kanali SABITLER (`docs/format/profile-a.md`
        # §5.1: 64 baytin 32'si 8 x float32). Baska bir sayi yazilsa dosya
        # uretim okuyucusu tarafindan reddedilirdi — yaziciyi okunamayan
        # dosya uretemez kilmak icin burada durdurulur.
        raise ValueError(
            f"channel_count Profil A'da {EXPECTED_CHANNEL_COUNT} olmali: {channel_count}"
        )

    body = (
        MAGIC,
        version,
        header_size,
        record_size,
        period_us,
        channel_count,
        start_time_utc_ns,
    )
    if version == 1:
        return FILE_HEADER_V1.pack(*body)

    # ADR-011 §2.2: CRC kendi alani HARIC, basligin basindan CRC'nin
    # hemen oncesine kadar hesaplanir.
    without_crc = FILE_HEADER_V1.pack(*body)
    return FILE_HEADER_V2.pack(*body, header_crc32(without_crc))


def _layout(version: int) -> tuple[int, int]:
    if version not in SUPPORTED_VERSIONS:
        raise ValueError(
            f"Desteklenmeyen format surumu: {version} (desteklenen: {sorted(SUPPORTED_VERSIONS)})"
        )
    return _LAYOUT[version]
