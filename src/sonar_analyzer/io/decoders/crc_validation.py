"""CRC alanlı format doğrulaması — `F2-014`.

`F2-013`'teki `crc32()` hesaplamasını `.bin` dosyasının gerçek CRC
alanlarına bağlar. `docs/adr/ADR-011-crc.md` §2.4 hata davranışı:

* **Header CRC hatası fatal'dır** — header güvenilmezse boyut alanları da
  güvenilmez; dosya açılmaz (`HeaderCrcMismatchError` yükseltilir, diğer
  header-düzeyi hatalarla aynı `FormatError` ailesindendir).
* **Kayıt CRC hatası fatal değildir** — kayıt `CRC_ERROR` işaretlenir,
  verisi çizilmez ama diğer kayıtlar normal okunur (`RecordCrcMismatch`,
  `NameMismatch`/anomali dataclass'ları gibi döner, yükseltilmez).

Sürüm 1 dosyada CRC alanı yoktur; `is_crc_validated()` bu farkı açıkça
işaretler — CRC'siz bir dosya sessizce "doğrulanmış" sayılmaz.
"""

from __future__ import annotations

from dataclasses import dataclass

from sonar_analyzer.io.decoders.crc import header_crc32, record_crc32
from sonar_analyzer.io.decoders.errors import FormatError
from sonar_analyzer.io.profile_a_format import DataRecordV2, FileHeaderV2


class HeaderCrcMismatchError(FormatError):
    """Header CRC'si tutmuyor — boyut alanları da güvenilmez, dosya açılmaz."""

    def __init__(self, expected: int, found: int, byte_offset: int = 0) -> None:
        super().__init__(
            f"header butunlugu bozuk: beklenen crc32 0x{expected:08X}, bulunan 0x{found:08X}",
            byte_offset,
        )
        self.expected = expected
        self.found = found


@dataclass(frozen=True)
class RecordCrcMismatch:
    """Bir kaydın CRC'si tutmuyor — kayıt atılmaz, `CRC_ERROR` işaretlenir."""

    byte_offset: int
    sequence_no: int
    expected_crc32: int
    found_crc32: int

    def __str__(self) -> str:
        return (
            f"CRC_ERROR: seq {self.sequence_no}, offset {self.byte_offset}, "
            f"beklenen 0x{self.expected_crc32:08X}, bulunan 0x{self.found_crc32:08X}"
        )


def validate_header_crc(
    header: FileHeaderV2, header_body_without_crc: bytes, byte_offset: int = 0
) -> None:
    """`header.header_crc32` ile hesaplanan CRC eşleşmezse `HeaderCrcMismatchError` yükseltir.

    `header_body_without_crc`, header'ın ilk baytından `header_crc32`
    alanının hemen öncesine kadar olan ham baytlardır (ADR-011 §2.2).
    """
    computed = header_crc32(header_body_without_crc)
    if computed != header.header_crc32:
        raise HeaderCrcMismatchError(
            expected=header.header_crc32, found=computed, byte_offset=byte_offset
        )


def check_record_crc(
    record: DataRecordV2, record_body_without_crc: bytes, byte_offset: int
) -> RecordCrcMismatch | None:
    """`record.record_crc32` ile hesaplanan CRC eşleşmezse `RecordCrcMismatch` döner.

    Kayıt asla atılmaz (ADR-011 §2.4) — dönen değer yalnız bir teşhistir;
    çağıran taraf kaydı `CRC_ERROR` olarak işaretleyip veriyi çizmemeyi
    seçer, okumayı durdurmaz.
    """
    computed = record_crc32(record_body_without_crc)
    if computed == record.record_crc32:
        return None
    return RecordCrcMismatch(
        byte_offset=byte_offset,
        sequence_no=record.sequence_no,
        expected_crc32=record.record_crc32,
        found_crc32=computed,
    )


def is_crc_validated(version: int) -> bool:
    """`version == 2` değilse dosyanın bütünlüğü CRC ile doğrulanmamıştır.

    Sürüm 1'de CRC alanı yoktur; bu fonksiyon "CRC yok = doğrulanmamış"
    ayrımını açıkça temsil eder — CRC'siz bir örnek dosya hiçbir zaman
    sessizce doğrulanmış sayılmaz (kabul kriteri).
    """
    return version == 2
