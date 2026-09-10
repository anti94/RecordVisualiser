"""Kaynak fingerprint ve parser sürümünü kaydetme — `F2-030`.

Bir indeksin geçerliliği iki şeye bağlıdır: kaynak `.bin` dosyası
değişmemiş olmalı ve indeksi üreten decoder mantığı değişmemiş olmalı.
İkisinden biri değişirse indeks **eskimiş** sayılır ve yeniden üretilir
(plan Bölüm 8.5: "İndeks, kaynak `.bin` değişmediyse tekrar kullanılmalı").
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from sonar_analyzer.io.readers.binary_reader import ReadableBuffer

#: Decoder/parser mantığı (struct sabitleri, teşhis kuralları) değiştiğinde
#: bilinçli olarak artırılır — `VERSION` dosyasındaki proje sürümünden
#: **bağımsızdır**; yalnız üretilen indeksin şekli değişince bumplenir.
PARSER_VERSION = 1


@dataclass(frozen=True)
class SourceFingerprint:
    """Kaynak `.bin` dosyasının kimliği — boyut ve içerik hash'i."""

    file_size: int
    content_sha256: str

    @staticmethod
    def from_bytes(data: ReadableBuffer) -> SourceFingerprint:
        return SourceFingerprint(
            file_size=len(data), content_sha256=hashlib.sha256(data).hexdigest()
        )

    @staticmethod
    def from_path(path: Path) -> SourceFingerprint:
        return SourceFingerprint.from_bytes(path.read_bytes())


@dataclass(frozen=True)
class IndexProvenance:
    """Bir indeksin hangi kaynaktan ve hangi parser sürümünden üretildiği."""

    fingerprint: SourceFingerprint
    parser_version: int

    @staticmethod
    def current(data: bytes) -> IndexProvenance:
        """Verilen kaynak baytlar ve şu anki `PARSER_VERSION` için provenance üretir."""
        return IndexProvenance(
            fingerprint=SourceFingerprint.from_bytes(data),
            parser_version=PARSER_VERSION,
        )

    def is_valid_for(self, data: bytes, parser_version: int = PARSER_VERSION) -> bool:
        """Kaynak değişmemişse **ve** decoder sürümü aynıysa `True` döner.

        Kabul kriteri: kaynak değişikliği veya decoder değişikliği
        indeksi geçersiz kılar — ikisi de bağımsız olarak kontrol edilir.
        """
        if self.parser_version != parser_version:
            return False
        return self.fingerprint == SourceFingerprint.from_bytes(data)
