"""CRC-32/ISO-HDLC hesaplama — `F2-013`.

`docs/adr/ADR-011-crc.md` §2.1: Profil A sürüm 2 ve Profil B, standart
CRC-32/ISO-HDLC (zlib/PNG/Ethernet ile aynı; polinom `0x04C11DB7`,
init `0xFFFFFFFF`, giriş/çıkış yansıtma açık, XOR out `0xFFFFFFFF`) kullanır.
`zlib.crc32` bu algoritmayla birebir eşleşir — ek bağımlılık gerekmez.

§2.2 kapsam kuralı: CRC her zaman **kendi alanı hariç**, o yapının (kayıt
veya header) ilk baytından CRC alanının hemen öncesine kadar hesaplanır.
`record_crc32`/`header_crc32` bu kuralı isimle netleştirir; ikisi de aynı
`crc32()`'yi çağırır.
"""

from __future__ import annotations

import zlib

from sonar_analyzer.io.readers.binary_reader import ReadableBuffer


def crc32(data: ReadableBuffer) -> int:
    """ADR-011 §2.1'deki CRC-32/ISO-HDLC değerini döner (`0..0xFFFFFFFF`)."""
    return zlib.crc32(data) & 0xFFFFFFFF


def record_crc32(record_body_without_crc: ReadableBuffer) -> int:
    """ADR-011 §2.2: kaydın ilk baytından `crc32` alanının öncesine kadar."""
    return crc32(record_body_without_crc)


def header_crc32(header_body_without_crc: ReadableBuffer) -> int:
    """ADR-011 §2.2: header'ın ilk baytından `header_crc32` alanının öncesine kadar."""
    return crc32(header_body_without_crc)
