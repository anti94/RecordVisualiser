"""`LiveWireHeader` çözümü — `F5-006`.

`docs/live/protocol-contract.md` §2'nin 28 baytlık zarfını uygular. Bu
modül yalnız **başlığı** çözer/üretir; kanal/olay payload kodlaması
`payload_codec.py`'nin, parça birleştirme `fragment_reassembly.py`'nin işi.

Kısa veya bozuk bir çerçeve **sessizce atlanmaz**: `LiveWireDecodeError`
alt sınıflarından biri fırlatılır, çağıran bunu tanılama olayı olarak
sayar (protokol sözleşmesi §2.1, §3.1–3.3'ün kayıp politikaları).
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

MAGIC = b"SNLV"
SUPPORTED_VERSION = 1

#: `docs/live/protocol-contract.md` §2 — magic(4s) version(B) protocol_id(B)
#: flags(H) sequence_no(I) fragment_index(H) fragment_count(H) device_ticks(q)
#: payload_length(I).
HEADER_STRUCT = struct.Struct("<4sBBHIHHqI")
HEADER_SIZE = HEADER_STRUCT.size
assert HEADER_SIZE == 28

PROTOCOL_UDP = 1
PROTOCOL_TCP = 2
PROTOCOL_SERIAL = 3

FLAG_HAS_EVENTS = 1 << 0


class LiveWireDecodeError(ValueError):
    """Taban sınıf: bir çerçeve tel sözleşmesine göre çözülemedi."""


class TruncatedDatagramError(LiveWireDecodeError):
    """Çerçeve, başlık veya beyan edilen `payload_length` için çok kısa."""


class UnrecognizedFrameError(LiveWireDecodeError):
    """`magic` veya `version` tanınmıyor (§2.1: sessizce atlanmaz)."""


@dataclass(frozen=True)
class LiveWireHeader:
    """28 baytlık zarfın çözülmüş alanları."""

    protocol_id: int
    flags: int
    sequence_no: int
    fragment_index: int
    fragment_count: int
    device_ticks: int
    payload_length: int

    def __post_init__(self) -> None:
        if self.fragment_count < 1:
            raise TruncatedDatagramError(f"fragment_count en az 1 olmali: {self.fragment_count}")
        if not 0 <= self.fragment_index < self.fragment_count:
            raise TruncatedDatagramError(
                f"fragment_index ({self.fragment_index}) fragment_count "
                f"({self.fragment_count}) disinda"
            )

    @property
    def has_events(self) -> bool:
        return bool(self.flags & FLAG_HAS_EVENTS)

    @property
    def is_single_fragment(self) -> bool:
        return self.fragment_count == 1


def pack_frame(
    header: LiveWireHeader,
    payload: bytes,
    *,
    version: int = SUPPORTED_VERSION,
) -> bytes:
    """Başlık + payload'ı tek bir çerçeveye paketler (testler ve simülatör için)."""
    return (
        HEADER_STRUCT.pack(
            MAGIC,
            version,
            header.protocol_id,
            header.flags,
            header.sequence_no,
            header.fragment_index,
            header.fragment_count,
            header.device_ticks,
            len(payload),
        )
        + payload
    )


def unpack_frame(data: bytes) -> tuple[LiveWireHeader, bytes]:
    """Baştaki 28 baytı çözüp `payload_length` kadar payload'ı ayırır.

    `data` başlıktan kısaysa veya beyan edilen `payload_length`e ulaşmıyorsa
    `TruncatedDatagramError`; `magic`/`version` tanınmıyorsa
    `UnrecognizedFrameError` fırlatılır — ikisi de `LiveWireDecodeError`.
    """
    if len(data) < HEADER_SIZE:
        raise TruncatedDatagramError(
            f"cerceve {len(data)} bayt, en az {HEADER_SIZE} bayt (baslik) gerekli"
        )
    (
        magic,
        version,
        protocol_id,
        flags,
        sequence_no,
        fragment_index,
        fragment_count,
        device_ticks,
        payload_length,
    ) = HEADER_STRUCT.unpack_from(data, 0)
    if magic != MAGIC:
        raise UnrecognizedFrameError(f"gecersiz magic: {magic!r}, beklenen {MAGIC!r}")
    if version != SUPPORTED_VERSION:
        raise UnrecognizedFrameError(
            f"desteklenmeyen surum: {version}, beklenen {SUPPORTED_VERSION}"
        )

    payload = data[HEADER_SIZE:]
    if len(payload) < payload_length:
        raise TruncatedDatagramError(
            f"payload {len(payload)} bayt, beyan edilen payload_length "
            f"{payload_length} bayta ulasmiyor"
        )

    header = LiveWireHeader(
        protocol_id=protocol_id,
        flags=flags,
        sequence_no=sequence_no,
        fragment_index=fragment_index,
        fragment_count=fragment_count,
        device_ticks=device_ticks,
        payload_length=payload_length,
    )
    return header, payload[:payload_length]
