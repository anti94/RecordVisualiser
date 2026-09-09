"""Profil A magic/sürüm doğrulaması — `F2-003`.

Sıra `docs/format/profile-a.md` §3'teki adımlarla aynıdır: magic önce, sonra
sürüm. Boyut/sınır denetimleri (`F2-004`) ayrı fonksiyondadır.
"""

from __future__ import annotations

from sonar_analyzer.io.decoders.errors import InvalidMagicError, UnsupportedVersionError
from sonar_analyzer.io.profile_a_format import MAGIC, SUPPORTED_VERSIONS, FileHeaderV1


def validate_magic(header: FileHeaderV1) -> None:
    """`magic == b"SONARBIN"` değilse `InvalidMagicError` yükseltir."""
    if header.magic != MAGIC:
        raise InvalidMagicError(header.magic, byte_offset=0)


def validate_version(header: FileHeaderV1) -> None:
    """`version` desteklenen kümede değilse `UnsupportedVersionError` yükseltir."""
    if header.version not in SUPPORTED_VERSIONS:
        raise UnsupportedVersionError(header.version, SUPPORTED_VERSIONS, byte_offset=8)
