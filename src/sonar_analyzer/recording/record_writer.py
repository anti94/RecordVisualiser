"""`DataNNNNN` kayıt serileştirmesi — `F5-026`.

Kabul kriteri: **ad, sıra, elapsed_us, payload ve varsa CRC decoder ile
eşleşir.** Bu yüzden yazıcı hiçbir alanı kendi yorumuyla üretmez:

* Ad `profile_a_format.record_name()` ile kurulur — okuma tarafındaki
  beklenen adla **aynı fonksiyondan**.
* Bayt düzeni `DATA_RECORD_V1`/`DATA_RECORD_V2` sözleşmesidir; decoder de
  aynı sabitleri kullanır.
* Sürüm 2'nin `crc32` alanı ADR-011 §2.2'ye göre **kendi alanı hariç**,
  kaydın ilk baytından CRC'nin hemen öncesine kadar hesaplanır.

Zaman alanı `elapsed_us`'tur: kayıt başlangıcına göre geçen süre
(mikrosaniye). Mutlak zaman yalnız dosya başlığında durur
(`start_time_utc_ns`, `F5-025`) — ADR-003'ün "üç zaman, üç ayrı alan"
kuralıyla tutarlı; kayıt başına mutlak zaman yazmak ikisinin
ayrışabileceği bir ikinci doğruluk kaynağı yaratırdı.
"""

from __future__ import annotations

from collections.abc import Sequence

from sonar_analyzer.io.decoders.crc import record_crc32
from sonar_analyzer.io.profile_a_format import (
    DATA_RECORD_V1,
    DATA_RECORD_V2,
    EXPECTED_CHANNEL_COUNT,
    SUPPORTED_VERSIONS,
    record_name,
)

#: Ad alanı 12 bayttır (`docs/format/profile-a.md` §5.1); `DataNNNNN` 9 bayt
#: tutar, kalanı `0x00` dolgudur.
NAME_FIELD_BYTES = 12


def build_data_record(
    *,
    sequence_no: int,
    elapsed_us: int,
    sensor_values: Sequence[float],
    bit_status: int = 0,
    tx_status: int = 0,
    version: int = 2,
) -> bytes:
    """Tek bir `DataNNNNN` kaydını baytlara yazar.

    `sensor_values` tam olarak `EXPECTED_CHANNEL_COUNT` (8) değer taşımalıdır;
    Profil A kayıt düzeni bunu sabitler.
    """
    if version not in SUPPORTED_VERSIONS:
        raise ValueError(
            f"Desteklenmeyen format surumu: {version} (desteklenen: {sorted(SUPPORTED_VERSIONS)})"
        )
    if sequence_no < 0:
        raise ValueError(f"sequence_no negatif olamaz: {sequence_no}")
    if elapsed_us < 0:
        raise ValueError(f"elapsed_us negatif olamaz: {elapsed_us}")
    values = tuple(float(value) for value in sensor_values)
    if len(values) != EXPECTED_CHANNEL_COUNT:
        raise ValueError(f"sensor_values {EXPECTED_CHANNEL_COUNT} deger tasimali: {len(values)}")

    body = (
        encoded_record_name(sequence_no),
        sequence_no,
        elapsed_us,
        *values,
        bit_status,
        tx_status,
    )
    if version == 1:
        return DATA_RECORD_V1.pack(*body)

    without_crc = DATA_RECORD_V1.pack(*body)
    return DATA_RECORD_V2.pack(*body, record_crc32(without_crc))


def encoded_record_name(sequence_no: int) -> bytes:
    """Kayıt adının 12 baytlık, `0x00` dolgulu hâli — okuma tarafıyla aynı ad."""
    name = record_name(sequence_no).encode("ascii")
    if len(name) > NAME_FIELD_BYTES:
        raise ValueError(
            f"Kayit adi {NAME_FIELD_BYTES} bayta sigmiyor: {name!r} ({len(name)} bayt)"
        )
    return name.ljust(NAME_FIELD_BYTES, b"\x00")
