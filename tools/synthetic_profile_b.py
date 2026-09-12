"""Parametrik Profil B sentetik üreticisi — plan Bölüm 8.3.13.

`tools/make_acoustic_fixture.py` **tek bir** yapılandırmayı üretir ve
SHA-256'sı sabitlenmiş golden dosyadır; onu parametrik yapmak o
sözleşmeyi bozardı. Bu modül ayrı durur ve şunları dışarıdan alır:

* kanal sayısı,
* örnekleme hızı (kayıt başına örnek buradan türer),
* süre (kayıt sayısı),
* kanal başına ton frekansı ve genliği,
* gürültü genliği,
* TX / BIT / olay bloklarının bulunup bulunmadığı.

Üretim **deterministiktir**: aynı `SyntheticSpec` her zaman aynı baytları
verir. Tekrar üretilemeyen bir fixture ile hata ayıklamak, hatayı iki kez
aramak demektir.

Gürültü `numpy` genel durumuna dokunmaz; kendi `default_rng`'siyle
üretilir. Global durumu kirletmek, aynı süreçte koşan başka bir testin
sonucunu sessizce değiştirirdi.

Kullanım::

    python tools/synthetic_profile_b.py --out ornek.bin --channels 2 \\
        --sample-rate 8000 --duration 1.0 --noise 50 --with-tx --with-bit
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from zlib import crc32

import numpy as np
from numpy.typing import NDArray

ROOT = Path(__file__).resolve().parent.parent
for location in (ROOT, ROOT / "src"):
    if str(location) not in sys.path:
        sys.path.insert(0, str(location))

from sonar_analyzer.io.decoders.naming import record_name  # noqa: E402
from sonar_analyzer.io.profile_b_format import (  # noqa: E402
    ACOUSTIC_DTYPE_CODE,
    ACOUSTIC_DTYPE_SIZE,
    BLOCK_HEADER,
    BLOCK_TYPE_BIT_STATUS,
    BLOCK_TYPE_SENSOR_RAW,
    BLOCK_TYPE_TX_STATUS,
    CHANNEL_ENTRY,
    END_MARKER,
    FILE_HEADER,
    MAGIC,
    RECORD_HEADER,
    RECORD_HEADER_SIZE,
    RECORD_PERIOD_NS,
    RECORD_TRAILER,
    RECORD_TRAILER_SIZE,
)

#: `docs/format/fixture-valid-8records.md` ile ayni ankor.
START_TIME_UTC_NS = 1_788_901_200_000_000_000
DEVICE_ID = b"SONAR-SYNTHETIC"

#: TX / BIT bloklarinin payload boyutu (8'e hizali tutulur).
TX_PAYLOAD_BYTES = 24
BIT_PAYLOAD_BYTES = 24


def _align8(value: int) -> int:
    return (value + 7) & ~7


@dataclass(frozen=True)
class SyntheticSpec:
    """Üretilecek dosyanın parametreleri.

    `tones` verilmezse kanal başına 1 kHz'den başlayan ayrık frekanslar
    kullanılır; aynı frekansı iki kanala vermek, kanalların
    karıştırılmasını **tespit edilemez** kılardı.
    """

    channels: int = 4
    sample_rate_hz: int = 48_000
    duration_s: float = 1.0
    tones: tuple[float, ...] = ()
    amplitude: int = 12_000
    noise: int = 0
    with_tx: bool = False
    with_bit: bool = False
    seed: int = 20260912
    record_period_ns: int = RECORD_PERIOD_NS

    def __post_init__(self) -> None:
        if self.channels < 1:
            raise ValueError(f"kanal sayisi >= 1 olmali: {self.channels}")
        if self.sample_rate_hz <= 0:
            raise ValueError(f"ornekleme hizi pozitif olmali: {self.sample_rate_hz}")
        if self.duration_s <= 0:
            raise ValueError(f"sure pozitif olmali: {self.duration_s}")
        if self.amplitude < 0 or self.noise < 0:
            raise ValueError("genlik ve gurultu negatif olamaz")
        if self.seed < 0:
            raise ValueError(f"seed negatif olamaz: {self.seed}")
        if self.samples_per_record < 1:
            raise ValueError(
                f"ornekleme hizi {self.sample_rate_hz} Hz, "
                f"{self.record_period_ns / 1e6:g} ms pencerede tek ornek bile uretmiyor"
            )
        if self.tones and len(self.tones) != self.channels:
            raise ValueError(
                f"{len(self.tones)} ton verildi ama {self.channels} kanal var; "
                "her kanalin kendi frekansi olmali"
            )

    @property
    def samples_per_record(self) -> int:
        """125 ms penceredeki örnek sayısı — örnekleme hızından türer."""
        return int(self.sample_rate_hz * self.record_period_ns // 1_000_000_000)

    @property
    def record_count(self) -> int:
        return max(1, round(self.duration_s * 1_000_000_000 / self.record_period_ns))

    @property
    def payload_bytes(self) -> int:
        return self.samples_per_record * ACOUSTIC_DTYPE_SIZE

    def tone_for(self, channel: int) -> float:
        """Kanalın ton frekansı; verilmediyse ayrık bir öntanımlı."""
        if self.tones:
            return self.tones[channel]
        return 1_000.0 + channel * 503.0  # asal adim: harmonik cakismasin

    def describe(self) -> str:
        return (
            f"{self.channels} kanal, {self.sample_rate_hz} Hz, "
            f"{self.record_count} kayit ({self.duration_s:g} s), "
            f"gurultu {self.noise}, TX={self.with_tx}, BIT={self.with_bit}"
        )


def channel_samples(spec: SyntheticSpec, channel: int, record_index: int) -> NDArray[np.int16]:
    """Bir kanalın bir kayıttaki örnekleri — deterministik."""
    count = spec.samples_per_record
    start = record_index * count
    n = np.arange(start, start + count, dtype=np.float64)
    wave = spec.amplitude * np.sin(2.0 * math.pi * spec.tone_for(channel) * n / spec.sample_rate_hz)

    if spec.noise:
        # Kendi uretecimiz: global numpy durumu kirletilmez.
        rng = np.random.default_rng(spec.seed + channel * 7919 + record_index)
        wave = wave + rng.integers(-spec.noise, spec.noise + 1, size=count)

    return np.clip(wave, -32768, 32767).astype(np.int16)


def _block(block_type: int, channel_id: int, dtype_code: int, payload: bytes) -> bytes:
    header = BLOCK_HEADER.pack(block_type, 0, len(payload), channel_id, dtype_code, 0, 0)
    body = header + payload
    return body + b"\x00" * (_align8(len(body)) - len(body))


def _file_header(spec: SyntheticSpec) -> bytes:
    body = FILE_HEADER.pack(
        MAGIC,
        1,
        0,
        FILE_HEADER.size,
        spec.channels,
        spec.channels * CHANNEL_ENTRY.size,
        spec.record_period_ns,
        0,
        START_TIME_UTC_NS,
        DEVICE_ID.ljust(16, b"\x00"),
        spec.record_count,
        b"\x00" * 196,
        0,
    )
    return body[:-4] + crc32(body[:-4]).to_bytes(4, "little")


def _channel_table(spec: SyntheticSpec) -> bytes:
    out = bytearray()
    for channel in range(spec.channels):
        out += CHANNEL_ENTRY.pack(
            channel,
            2,  # source = ACOUSTIC
            ACOUSTIC_DTYPE_CODE,
            f"Acoustic/Synthetic {channel + 1}".encode("ascii").ljust(24, b"\x00"),
            b"Pa".ljust(8, b"\x00"),
            float(spec.sample_rate_hz),
            1.0,
            0.0,
            0,
            0,
            f"Synth {channel + 1}".encode("ascii").ljust(12, b"\x00"),
        )
    return bytes(out)


def _record(spec: SyntheticSpec, record_index: int) -> bytes:
    blocks = bytearray()
    block_count = 0

    for channel in range(spec.channels):
        payload = channel_samples(spec, channel, record_index).tobytes()
        blocks += _block(BLOCK_TYPE_SENSOR_RAW, channel, ACOUSTIC_DTYPE_CODE, payload)
        block_count += 1

    if spec.with_tx:
        # TX her dort kayitta bir ACTIVE; START/STOP gecisi olusur.
        state = 1 if record_index % 4 < 2 else 0
        payload = state.to_bytes(4, "little") + b"\x00" * (TX_PAYLOAD_BYTES - 4)
        blocks += _block(BLOCK_TYPE_TX_STATUS, 0, 0x02, payload)
        block_count += 1

    if spec.with_bit and record_index % 8 == 0:
        # BIT yalniz her 8. kayitta; bir bit kasten FAIL.
        mask = 0b0000_0000_0000_0010 if record_index else 0
        payload = mask.to_bytes(4, "little") + b"\x00" * (BIT_PAYLOAD_BYTES - 4)
        blocks += _block(BLOCK_TYPE_BIT_STATUS, 0, 0x02, payload)
        block_count += 1

    payload_crc = crc32(bytes(blocks))
    record_size = RECORD_HEADER_SIZE + len(blocks) + RECORD_TRAILER_SIZE
    assert record_size % 8 == 0, "kayit boyutu 8'in kati olmali"

    header = RECORD_HEADER.pack(
        record_name(record_index).encode("ascii").ljust(12, b"\x00"),
        record_index,
        record_size,
        block_count,
        0,
        record_index * spec.record_period_ns,
        record_index * spec.samples_per_record,  # device_ticks: ornek sayaci
        payload_crc,
        0,
    )
    return header + bytes(blocks) + RECORD_TRAILER.pack(payload_crc, END_MARKER)


def build(spec: SyntheticSpec) -> bytes:
    """Bütün dosyayı bellekte üretir — küçük parametreler için."""
    parts = [_file_header(spec), _channel_table(spec)]
    parts.extend(_record(spec, index) for index in range(spec.record_count))
    return b"".join(parts)


def write(output: Path, spec: SyntheticSpec) -> dict[str, object]:
    """Dosyayı yazar ve özetini döndürür."""
    data = build(spec)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)
    return {
        "path": str(output),
        "bytes": len(data),
        "channels": spec.channels,
        "sample_rate_hz": spec.sample_rate_hz,
        "samples_per_record": spec.samples_per_record,
        "record_count": spec.record_count,
        "with_tx": spec.with_tx,
        "with_bit": spec.with_bit,
        "noise": spec.noise,
        "seed": spec.seed,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Parametrik Profil B sentetik uretici")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--channels", type=int, default=4)
    parser.add_argument("--sample-rate", type=int, default=48_000)
    parser.add_argument("--duration", type=float, default=1.0, help="saniye")
    parser.add_argument("--tone", type=float, action="append", default=None, help="kanal basina Hz")
    parser.add_argument("--amplitude", type=int, default=12_000)
    parser.add_argument("--noise", type=int, default=0)
    parser.add_argument("--with-tx", action="store_true")
    parser.add_argument("--with-bit", action="store_true")
    parser.add_argument("--seed", type=int, default=20260912)
    args = parser.parse_args(argv)

    try:
        spec = SyntheticSpec(
            channels=args.channels,
            sample_rate_hz=args.sample_rate,
            duration_s=args.duration,
            tones=tuple(args.tone) if args.tone else (),
            amplitude=args.amplitude,
            noise=args.noise,
            with_tx=args.with_tx,
            with_bit=args.with_bit,
            seed=args.seed,
        )
    except ValueError as exc:
        print(f"Gecersiz parametre: {exc}", file=sys.stderr)
        return 2

    summary = write(args.out, spec)
    print(spec.describe())
    print(f"yazildi: {summary['path']} ({summary['bytes']} bayt)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
