"""Profil B 48 kHz akustik blok fixture yazıcısı — `F4-010`.

`docs/format/profile-b.md` sözleşmesine göre deterministik bir Profil B
`.bin` dosyası üretir: `FileHeader(256)` + `ChannelTable(4×64)` + N kayıt.
Her kayıt 4 akustik kanal için birer `SENSOR_RAW` bloğu (kanal başına
125 ms = **6000 örnek** `int16`) ve bir `RecordTrailer` taşır; kayıtlar
`Data00000`, `Data00001`, … sırasıyla yazılır.

Kullanım:
    python tools/make_acoustic_fixture.py
    python tools/make_acoustic_fixture.py --out path/acoustic_8records.bin --records 8
"""

from __future__ import annotations

import argparse
import hashlib
import math
import sys
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sonar_analyzer.io.decoders.crc import crc32  # noqa: E402
from sonar_analyzer.io.profile_b_format import (  # noqa: E402
    ACOUSTIC_CHANNELS,
    ACOUSTIC_DTYPE_CODE,
    ACOUSTIC_PAYLOAD_BYTES,
    ACOUSTIC_SAMPLE_RATE_HZ,
    BLOCK_HEADER,
    BLOCK_HEADER_SIZE,
    BLOCK_TYPE_SENSOR_RAW,
    CHANNEL_ENTRY,
    END_MARKER,
    FILE_HEADER,
    MAGIC,
    RECORD_HEADER,
    RECORD_HEADER_SIZE,
    RECORD_PERIOD_NS,
    RECORD_TRAILER,
    RECORD_TRAILER_SIZE,
    SAMPLES_PER_BLOCK,
    SUPPORTED_VERSION,
    record_name,
)

DEFAULT_OUT = ROOT / "tests" / "fixtures" / "acoustic_8records.bin"

#: docs/format/fixture-valid-8records.md ile aynı ankor.
START_TIME_UTC_NS = 1_788_901_200_000_000_000
DEVICE_ID = b"SONAR-ACOUSTIC-1"

#: Kanal başına ton frekansı (Hz) ve genlik (int16). Deterministik.
_TONES: tuple[tuple[float, int], ...] = (
    (997.0, 12000),
    (1499.0, 9000),
    (2003.0, 6000),
    (3001.0, 3000),
)

#: 8 kayıtlık öntanımlı dosyanın SHA-256'sı (yalnız `--records 8` için).
ACOUSTIC_8RECORDS_SHA256 = "6c501175e295d10b57c4a3c86783e7710b933f2e501cc3061650fc13c9c7b4f5"


def _channel_samples(channel_id: int, record_index: int) -> NDArray[np.int16]:
    """`record_index` kaydının `channel_id` kanalı için 6000 `int16` örnek."""
    tone_hz, amplitude = _TONES[channel_id]
    start = record_index * SAMPLES_PER_BLOCK
    n = np.arange(start, start + SAMPLES_PER_BLOCK, dtype=np.float64)
    wave = amplitude * np.sin(2.0 * math.pi * tone_hz * n / ACOUSTIC_SAMPLE_RATE_HZ)
    return np.round(wave).astype(np.int16)


def _file_header(record_count: int) -> bytes:
    body = FILE_HEADER.pack(
        MAGIC,
        SUPPORTED_VERSION,  # version_major
        0,  # version_minor
        FILE_HEADER.size,  # header_size
        len(ACOUSTIC_CHANNELS),  # channel_count
        len(ACOUSTIC_CHANNELS) * CHANNEL_ENTRY.size,  # channel_table_size
        RECORD_PERIOD_NS,
        0,  # flags
        START_TIME_UTC_NS,
        DEVICE_ID.ljust(16, b"\x00"),
        record_count,
        b"\x00" * 196,
        0,  # header_crc32 placeholder
    )
    return body[:-4] + crc32(body[:-4]).to_bytes(4, "little")


def _channel_table() -> bytes:
    out = bytearray()
    for channel_id, path, name, unit in ACOUSTIC_CHANNELS:
        out += CHANNEL_ENTRY.pack(
            channel_id,
            2,  # source = ACOUSTIC
            ACOUSTIC_DTYPE_CODE,
            path.encode("ascii").ljust(24, b"\x00"),
            unit.encode("ascii").ljust(8, b"\x00"),
            float(ACOUSTIC_SAMPLE_RATE_HZ),
            1.0,  # gain
            0.0,  # offset
            0,  # calibration_id
            0,  # reserved
            name.encode("ascii").ljust(12, b"\x00"),
        )
    return bytes(out)


def _record(record_index: int) -> bytes:
    blocks = bytearray()
    for channel_id, _p, _n, _u in ACOUSTIC_CHANNELS:
        payload = _channel_samples(channel_id, record_index).tobytes()
        assert len(payload) == ACOUSTIC_PAYLOAD_BYTES
        blocks += BLOCK_HEADER.pack(
            BLOCK_TYPE_SENSOR_RAW,
            0,  # flags
            ACOUSTIC_PAYLOAD_BYTES,  # block_size
            channel_id,
            ACOUSTIC_DTYPE_CODE,
            0,  # rsv
            0,  # t_offset_ns
        )
        blocks += payload
        # align8(16 + 12000) = 12016, zaten hizalı -> pad yok.
        assert (BLOCK_HEADER_SIZE + len(payload)) % 8 == 0

    payload_crc = crc32(bytes(blocks))
    record_size = RECORD_HEADER_SIZE + len(blocks) + RECORD_TRAILER_SIZE
    assert record_size % 8 == 0

    header = RECORD_HEADER.pack(
        record_name(record_index).encode("ascii").ljust(12, b"\x00"),
        record_index,
        record_size,
        len(ACOUSTIC_CHANNELS),  # block_count
        0,  # flags
        record_index * RECORD_PERIOD_NS,  # t_start_offset_ns
        record_index * SAMPLES_PER_BLOCK,  # device_ticks (örnek sayacı)
        payload_crc,
        0,  # reserved
    )
    trailer = RECORD_TRAILER.pack(payload_crc, END_MARKER)
    return header + bytes(blocks) + trailer


def build_acoustic_fixture(record_count: int = 8) -> bytes:
    """Deterministik Profil B akustik `.bin` içeriği."""
    if record_count < 1:
        raise ValueError("record_count >= 1 olmalı")
    out = bytearray(_file_header(record_count))
    out += _channel_table()
    for index in range(record_count):
        out += _record(index)
    return bytes(out)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--records", type=int, default=8)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    data = build_acoustic_fixture(args.records)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    print(f"{args.out} yazildi: {len(data)} byte, {args.records} kayit")
    print(f"sha256: {digest}")
    if args.records == 8 and ACOUSTIC_8RECORDS_SHA256 and digest != ACOUSTIC_8RECORDS_SHA256:
        print("HATA: 8 kayitlik dosya beklenen SHA-256 ile uyusmuyor", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
