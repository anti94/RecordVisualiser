"""Profil C kayıt klasörü yazıcısı — **yalnız test ve ölçüm için**.

Gerçek kayıtları C++ tarafı üretir (`D-29`). Bu modül bir ürün özelliği
değildir; okuma yolunu, indeksi ve analizleri sınayacak veriyi üretir.

Üretim **deterministiktir**: aynı parametreler aynı baytları verir.
Tekrar üretilemeyen bir fixture ile hata ayıklamak, hatayı iki kez
aramak demektir.

Yazılan baytlar `schemas/profile-c.example.toml` şemasına uyar; şema
değişirse bu yazıcı da değişmelidir. İkisinin ayrışmadığını testler
doğrular: üretilen dosya **üretim çözücüsüyle** okunur.
"""

from __future__ import annotations

import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from zlib import crc32

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
for location in (ROOT, ROOT / "src"):
    if str(location) not in sys.path:
        sys.path.insert(0, str(location))

from sonar_analyzer.io.schema.model import Schema  # noqa: E402

#: Ornek semadaki sabit offsetler. Sema degisirse burasi da degismeli;
#: bir test ikisinin ayrismadigini dogrular.
FILE_MAGIC = b"SNRPROFC"
FRAME_MAGIC = b"FRMC"

#: 8192 Hz'de 820 ornek = 100,0977 ms. Nominal 100 ms DEGIL (D-27).
FRAME_PERIOD_NS = 100_097_656

DEFAULT_START_NS = 1_700_000_000_000_000_000


@dataclass(frozen=True)
class WriteSpec:
    """Üretilecek kaydın parametreleri."""

    seconds: int = 10
    sensors: int = 32
    samples: int = 820
    frames_per_file: int = 10
    sample_rate_hz: int = 8192
    start_ns: int = DEFAULT_START_NS
    #: Yayin yapilan saniyeler; bos ise her saniyede Tx uretilir.
    tx_seconds: tuple[int, ...] | None = None
    #: Uretimi tekrarlanabilir kilan tohum.
    seed: int = 20260913

    def __post_init__(self) -> None:
        if self.seconds < 1:
            raise ValueError(f"sure >= 1 saniye olmali: {self.seconds}")
        if self.sensors < 1 or self.samples < 1:
            raise ValueError("sensor ve ornek sayisi pozitif olmali")

    @property
    def payload_bytes(self) -> int:
        return self.sensors * self.samples * 8

    @property
    def frame_bytes(self) -> int:
        return 128 + self.payload_bytes

    @property
    def file_bytes(self) -> int:
        return 64 + self.frames_per_file * self.frame_bytes

    def transmits(self, second: int) -> bool:
        return self.tx_seconds is None or second in self.tx_seconds


#: Tx ornekleri Rx'ten bu kadar kaydirilir. Ikisi ayni veriyi tasisaydi,
#: iki akimi karistiran bir hata hicbir testte gorunmezdi.
STREAM_OFFSET = 500_000.0


def _payload(spec: WriteSpec, frame_index: int, *, stream: str) -> bytes:
    """Bir frame'in yükü — deterministik, frame'e **ve akıma** göre farklı.

    Bütün frame'ler aynı olsaydı bir offset hatası okunan veride fark
    edilmezdi. Tx ile Rx aynı olsaydı, iki akımı karıştıran bir hata da
    fark edilmezdi.
    """
    count = spec.sensors * spec.samples
    shift = STREAM_OFFSET if stream == "Tx" else 0.0
    base = np.arange(count, dtype=np.float32) + frame_index * 1000.0 + shift
    buffer = np.empty(count, dtype=np.complex64)
    buffer.real = base
    buffer.imag = -base
    return buffer.tobytes()


def _frame(spec: WriteSpec, frame_index: int, *, stream: str) -> bytes:
    body = _payload(spec, frame_index, stream=stream)
    blob = bytearray(128)
    blob[0:4] = FRAME_MAGIC
    struct.pack_into("<I", blob, 4, frame_index)
    struct.pack_into("<q", blob, 8, spec.start_ns + frame_index * FRAME_PERIOD_NS)
    struct.pack_into("<H", blob, 16, 0x0003 if stream == "Tx" else 0x0002)
    struct.pack_into("<H", blob, 18, spec.sensors)
    struct.pack_into("<I", blob, 20, spec.samples)
    struct.pack_into("<I", blob, 120, crc32(body) & 0xFFFFFFFF)
    return bytes(blob) + body


def _file_bytes(spec: WriteSpec, second: int, stream: str) -> bytes:
    """Bir saniyelik dosyanın tamamı, başlık CRC'si dâhil."""
    first = second * spec.frames_per_file
    frames = b"".join(
        _frame(spec, first + offset, stream=stream) for offset in range(spec.frames_per_file)
    )

    blob = bytearray(64)
    blob[0:8] = FILE_MAGIC
    struct.pack_into("<H", blob, 8, 1)  # schema_version
    struct.pack_into("<H", blob, 10, 64)  # header_size
    struct.pack_into("<B", blob, 12, 1 if stream == "Tx" else 2)  # stream_kind
    struct.pack_into("<H", blob, 16, spec.sensors)
    struct.pack_into("<H", blob, 18, spec.samples)
    struct.pack_into("<I", blob, 20, spec.frames_per_file)
    struct.pack_into("<I", blob, 24, spec.sample_rate_hz)
    struct.pack_into("<I", blob, 28, second)  # file_index
    struct.pack_into("<q", blob, 32, spec.start_ns + first * FRAME_PERIOD_NS)

    # Baslik CRC'si KENDI ALANI HARIC hesaplanir (ADR-011). Kendi alanini
    # kapsasaydi dogru degeri yazmak girdiyi degistirirdi.
    block = bytearray(blob)
    block[60:64] = b"\x00\x00\x00\x00"
    struct.pack_into("<I", blob, 60, crc32(bytes(block)) & 0xFFFFFFFF)
    return bytes(blob) + frames


def folder_name(spec: WriteSpec) -> str:
    """Kayıt klasörünün adı — UTC damgası, `:` yerine `-`."""
    seconds = spec.start_ns // 1_000_000_000
    from datetime import datetime, timezone

    stamp = datetime.fromtimestamp(seconds, tz=timezone.utc)
    return stamp.strftime("%Y-%m-%dT%H-%M-%SZ")


def write_recording(root: Path, spec: WriteSpec) -> Path:
    """Bir kayıt klasörü yazar ve yolunu döndürür."""
    folder = Path(root) / folder_name(spec)
    for stream in ("Tx", "Rx"):
        (folder / stream).mkdir(parents=True, exist_ok=True)

    for second in range(spec.seconds):
        payload = _file_bytes(spec, second, "Rx")
        (folder / "Rx" / f"RxData{second:05d}.bin").write_bytes(payload)
        if spec.transmits(second):
            (folder / "Tx" / f"TxData{second:05d}.bin").write_bytes(_file_bytes(spec, second, "Tx"))

    manifest = folder / "manifest.toml"
    manifest.write_text(
        "\n".join(
            [
                'schema_id = "sonar-profile-c"',
                "schema_version = 1",
                f"start_time_utc_ns = {spec.start_ns}",
                f"sample_rate_hz = {spec.sample_rate_hz}",
                f"frame_samples = {spec.samples}",
                f"sensor_count = {spec.sensors}",
                'sample_dtype = "complex64"',
                f"duration_s = {spec.seconds}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return folder


def schema_matches(schema: Schema) -> bool:
    """Bu yazıcının ürettiği düzen verilen şemayla uyuşuyor mu.

    Yazıcı offsetleri **sabit** yazar; şema onları veri olarak taşır. İkisi
    ayrışırsa üretilen fixture'lar üretim çözücüsüyle okunamaz ve bu,
    fark edilmesi güç bir kırılma olur.
    """
    try:
        file_header = schema.struct("FileHeader")
        frame_header = schema.struct("FrameHeader")
    except KeyError:
        return False
    return (
        file_header.size == 64
        and frame_header.size == 128
        and schema.payload.sample_type.size == 8
        and schema.endianness == "little"
    )
