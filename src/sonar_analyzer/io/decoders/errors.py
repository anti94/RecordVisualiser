"""Parser hata türleri — konum bilgili teşhis.

Plan Bölüm 8.2 decoder tasarımı: "Bilinmeyen paketleri atmak yerine konum ve
tür bilgisiyle raporla." Bu yüzden her format hatası `byte_offset` taşır;
kullanıcıya veya log'a yalnız "dosya bozuk" değil, **nerede** bozuk olduğu
gösterilebilir.
"""

from __future__ import annotations


class FormatError(ValueError):
    """Bir `.bin` dosyasının Profil A sözleşmesini ihlal ettiğini gösterir.

    Tüm alt sınıflar `byte_offset` taşır (bkz. `docs/format/profile-a.md` §3).
    """

    def __init__(self, message: str, byte_offset: int) -> None:
        super().__init__(f"{message} (offset {byte_offset})")
        self.byte_offset = byte_offset


class InvalidMagicError(FormatError):
    """`magic` alanı `SONARBIN` değil — bu dosya Profil A değil."""

    def __init__(self, found: bytes, byte_offset: int = 0) -> None:
        super().__init__(f"gecersiz magic: {found!r}, beklenen b'SONARBIN'", byte_offset)
        self.found = found


class UnsupportedVersionError(FormatError):
    """`version` desteklenen kümede değil (`docs/format/profile-a.md` §3 adım 3)."""

    def __init__(self, found: int, supported: frozenset[int], byte_offset: int = 8) -> None:
        supported_text = ", ".join(str(v) for v in sorted(supported))
        super().__init__(
            f"desteklenmeyen surum: {found} (desteklenen: {supported_text})", byte_offset
        )
        self.found = found
        self.supported = supported


class TruncatedHeaderError(FormatError):
    """Dosya, header'in tamamini tasimayacak kadar kisa (docs/format/profile-a.md §3 adim 1)."""

    def __init__(self, available_bytes: int, required_bytes: int) -> None:
        super().__init__(
            f"kesik header: {required_bytes} bayt gerekli, {available_bytes} bayt bulundu",
            byte_offset=0,
        )
        self.available_bytes = available_bytes
        self.required_bytes = required_bytes


class HeaderContractError(FormatError):
    """header_size/record_size/channel_count beklenenle uyusmuyor (adim 4, 6)."""
