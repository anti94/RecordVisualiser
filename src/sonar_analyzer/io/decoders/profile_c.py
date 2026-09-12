"""Profil C çözücüsü — `F7-019`…`F7-028`.

Bir saniyelik `TxData00000.bin` dosyasını şemaya göre çözer. Şema C++
tarafının struct tanımlarının tarifidir (`D-29`); bu modül o tarifi
uygular ve **tarif ile dosya ayrışırsa durur**.

Ayrışmayı yakalamak bu çözücünün asıl işidir. Yanlış bir şema dosyayı
hatasız okur: bayt sayısı tutar, CRC tutar, hiçbir istisna oluşmaz ve
her alan kaymış hâlde çıkar. Üç bağımsız kapı bunu engeller
(`docs/format/profile-c.md` §7).

Bozuk bir frame kaydın tamamını düşürmez. Kesik son frame atılır ve kaç
baytın atıldığı söylenir; CRC'si tutmayan frame işaretlenir ama komşuları
etkilenmez. Tek bir bozuk frame yüzünden 10 dakikalık bir kaydı
okunamaz saymak, veriyi korumak değil yok etmektir.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as dataclass_field
from typing import Any
from zlib import crc32

import numpy as np
from numpy.typing import NDArray

from sonar_analyzer.io.schema.errors import SchemaMismatchError
from sonar_analyzer.io.schema.model import Schema
from sonar_analyzer.io.schema.runtime import build_reader, read_payload

#: Dosya ve frame basliklarinin sema icindeki adlari.
FILE_HEADER = "FileHeader"
FRAME_HEADER = "FrameHeader"

#: CRC alanlarinin adlari. Bulunmuyorlarsa dogrulama atlanir ve bu
#: durum raporlanir — sessizce "gecti" sayilmaz.
PAYLOAD_CRC = "payload_crc32"
HEADER_CRC = "header_crc32"


class ProfileCError(Exception):
    """Profil C çözümleme hatası."""


def _empty_flags() -> dict[str, int]:
    """Boş bayrak sözlüğü — tipli fabrika."""
    return {}


@dataclass(frozen=True)
class FrameIssue:
    """Bir frame'de bulunan sorun."""

    frame_index: int
    code: str
    detail: str


@dataclass(frozen=True)
class DecodedFrame:
    """Çözülmüş bir frame: başlık alanları ve yük."""

    index: int
    header: dict[str, Any]
    samples: NDArray[np.complex64]
    #: Bit alanlarinin cozulmus hali (`status` gibi alanlardan).
    flags: dict[str, int] = dataclass_field(default_factory=_empty_flags)
    crc_ok: bool = True

    @property
    def timestamp_ns(self) -> int:
        """Kanonik zaman — frame sayacından değil, başlıktan (`D-33`)."""
        value = self.header.get("timestamp_utc_ns")
        if value is None:
            raise ProfileCError(
                "frame basliginda timestamp_utc_ns yok; kanonik zaman kaynagi eksik "
                "(docs/format/profile-c.md Bolum 6)"
            )
        return int(value)


@dataclass(frozen=True)
class DecodedFile:
    """Çözülmüş bir saniyelik dosya."""

    header: dict[str, Any]
    frames: tuple[DecodedFrame, ...]
    issues: tuple[FrameIssue, ...] = ()
    #: Kesik son frame yuzunden atilan bayt sayisi.
    dropped_bytes: int = 0
    #: CRC alani semada yoksa dogrulama yapilamaz; bu durum tasinir.
    crc_checked: bool = True

    @property
    def frame_count(self) -> int:
        return len(self.frames)


def _crc_excluding_own_field(data: bytes, offset: int, size: int, crc_offset: int) -> int:
    """CRC'yi kendi alanı hariç hesaplar — `ADR-011`.

    Kendi alanını da kapsasaydı, doğru CRC'yi hesaplamak imkânsız olurdu:
    değeri yazmak girdiyi değiştirirdi.
    """
    block = bytearray(data[offset : offset + size])
    block[crc_offset : crc_offset + 4] = b"\x00\x00\x00\x00"
    return crc32(bytes(block)) & 0xFFFFFFFF


def _verify_header_crc(
    schema: Schema, struct_name: str, header: dict[str, Any], data: bytes, offset: int
) -> None:
    """Başlık CRC'sini doğrular — `ADR-011`: başlık CRC'si ölümcüldür.

    Kayıt CRC'si bir frame'i işaretler ve okumaya devam edilir. Başlık
    CRC'si öyle değildir: başlık bozuksa sensör sayısı, frame sayısı ve
    örnekleme hızı güvenilmezdir ve onlara dayanan her şey yanlış olur.

    Şemada `header_crc32` alanı yoksa doğrulama yapılamaz ve **yapılmış
    sayılmaz**; çağıran taraf bunu `crc_checked` üzerinden görür.
    """
    definition = schema.struct(struct_name)
    field = next((f for f in definition.fields if f.name == HEADER_CRC), None)
    if field is None:
        return
    expected = int(header[HEADER_CRC])
    if expected == 0:
        # Sifir "hesaplanmadi" demektir; sifiri dogru CRC sayip reddetmek
        # CRC yazmayan bir ureticinin dosyalarini okunamaz kilardi.
        return
    actual = _crc_excluding_own_field(data, offset, definition.size, field.offset)
    if actual != expected:
        raise SchemaMismatchError(
            f"{struct_name} CRC'si tutmuyor; baslik bozuksa ona dayanan "
            f"her alan guvenilmezdir (ADR-011)",
            expected=f"{expected:#010x}",
            found=f"{actual:#010x}",
        )


def check_identity(schema: Schema, header: dict[str, Any]) -> None:
    """Şema kimliği ile dosya başlığını karşılaştırır — ikinci kapı.

    Sürüm tutmuyorsa okuma **başlamaz**. Devam edilseydi her alan kaymış
    hâlde çözülür ve sonuçlar hatasız görünürdü.
    """
    found = header.get("schema_version")
    if found is None:
        return
    if int(found) != schema.version:
        raise SchemaMismatchError(
            "dosya baska bir sema surumuyle yazilmis",
            expected=schema.version,
            found=int(found),
        )


def check_sanity(schema: Schema, header: dict[str, Any], total_bytes: int) -> None:
    """Boyut denklemi — üçüncü kapı.

    ``dosya = dosya_header + frame_sayisi x (frame_header + S x N x B)``

    Bu kapı şema kimliği unutulsa bile çalışır: frame başlığının boyutu
    bir bayt bile değişse denklem tutmaz.
    """
    file_size = schema.struct(FILE_HEADER).size
    frame_size = schema.struct(FRAME_HEADER).size + schema.payload.frame_bytes

    declared = header.get("frame_count")
    if declared is not None:
        expected = file_size + int(declared) * frame_size
        # Kesik bir son frame ile yanlis bir sema ayri seylerdir ve ayri
        # islenmeli. Kesik dosya EKSIK bayt tasir ve eksik bir frame'den
        # azdir; kayit yine okunur (F7-024). Fazla bayt ya da bir frame'den
        # buyuk eksik, semanin dosyayla ayristigini gosterir.
        shortfall = expected - total_bytes
        if shortfall < 0 or shortfall >= frame_size:
            raise SchemaMismatchError(
                f"boyut denklemi tutmuyor: {file_size} + {declared} x {frame_size}",
                expected=expected,
                found=total_bytes,
            )

    for key, schema_value in (
        ("sensor_count", schema.payload.sensor_count),
        ("frame_samples", schema.payload.frame_samples),
    ):
        found = header.get(key)
        if found is not None and int(found) != schema_value:
            raise SchemaMismatchError(
                f"dosya basligindaki {key} semayla uyusmuyor",
                expected=schema_value,
                found=int(found),
            )


def _frame_magic(schema: Schema, data: bytes, offset: int) -> bytes | None:
    """İlk frame'in sihirli sayısı; şemada `magic` alanı yoksa `None`.

    Beklenen değer sabit yazılmaz, **ilk frame'den okunur**. Sabit yazmak
    bu çözücüyü tek bir sihirli sayıya bağlardı; oysa sihirli sayı da
    C++ tarafının seçimidir ve şemayla gelir. Aranan şey sabit bir dizge
    değil, **her frame'de aynı olması**dır.
    """
    definition = schema.struct(FRAME_HEADER)
    magic_field = next((f for f in definition.fields if f.name == "magic"), None)
    if magic_field is None or len(data) < offset + definition.size:
        return None
    reader = build_reader(definition, schema.endianness)
    value = reader.unpack(data, offset).get("magic")
    return value if isinstance(value, bytes) else None


def decode_file(schema: Schema, data: bytes, *, verify_crc: bool = True) -> DecodedFile:
    """Bir saniyelik dosyayı çözer."""
    file_reader = build_reader(schema.struct(FILE_HEADER), schema.endianness)
    frame_definition = schema.struct(FRAME_HEADER)
    frame_reader = build_reader(frame_definition, schema.endianness)

    if len(data) < file_reader.size:
        raise SchemaMismatchError(
            "dosya basligi icin yeterli bayt yok", expected=file_reader.size, found=len(data)
        )

    header = file_reader.unpack(data)
    _verify_header_crc(schema, FILE_HEADER, header, data, 0)
    check_identity(schema, header)
    check_sanity(schema, header, len(data))

    frame_size = frame_definition.size + schema.payload.frame_bytes
    body = len(data) - file_reader.size
    whole, remainder = divmod(body, frame_size)

    has_payload_crc = any(f.name == PAYLOAD_CRC for f in frame_definition.fields)
    bit_fields = [f.name for f in frame_definition.fields if f.bits]

    frames: list[DecodedFrame] = []
    issues: list[FrameIssue] = []
    cursor = file_reader.size

    expected_magic = _frame_magic(schema, data, file_reader.size)

    for position in range(whole):
        frame_header = frame_reader.unpack(data, cursor)
        # Frame sihirli sayisi, boyut denklemi gecse bile yanlis semayi
        # yakalar. C++ tarafi frame basligina bir alan ekleyip surumu
        # artirmadiysa ikinci kapi gecer; bu gecmez, cunku sihirli sayi
        # ikinci frame'den itibaren beklenen offsette bulunmaz.
        if expected_magic is not None and frame_header.get("magic") != expected_magic:
            raise SchemaMismatchError(
                f"{position}. frame'in sihirli sayisi beklenen offsette degil; "
                f"sema frame basligini {frame_definition.size} bayt sayiyor",
                expected=expected_magic,
                found=frame_header.get("magic"),
            )
        payload_offset = cursor + frame_definition.size
        samples = read_payload(schema, data, payload_offset)

        index = int(frame_header.get("frame_index", position))
        crc_ok = True
        if verify_crc and has_payload_crc:
            expected = int(frame_header[PAYLOAD_CRC])
            actual = crc32(data[payload_offset : payload_offset + schema.payload.frame_bytes])
            crc_ok = (actual & 0xFFFFFFFF) == expected
            if not crc_ok:
                issues.append(
                    FrameIssue(
                        frame_index=index,
                        code="CRC_ERROR",
                        detail=f"yuk CRC'si tutmuyor: beklenen {expected:#010x}, "
                        f"hesaplanan {actual & 0xFFFFFFFF:#010x}",
                    )
                )

        flags: dict[str, int] = {}
        for name in bit_fields:
            raw = frame_header.get(name)
            if raw is not None:
                flags.update(frame_reader.decode_bits(name, int(raw)))

        frames.append(
            DecodedFrame(
                index=index, header=frame_header, samples=samples, flags=flags, crc_ok=crc_ok
            )
        )
        cursor += frame_size

    if remainder:
        issues.append(
            FrameIssue(
                frame_index=whole,
                code="TRUNCATED",
                detail=f"son frame kesik: {remainder} bayt atildi (tam frame {frame_size} bayt)",
            )
        )

    return DecodedFile(
        header=header,
        frames=tuple(frames),
        issues=tuple(issues),
        dropped_bytes=remainder,
        crc_checked=verify_crc and has_payload_crc,
    )


def check_frame_sequence(
    decoded: DecodedFile, *, file_index: int | None = None
) -> list[FrameIssue]:
    """Frame indekslerinin sırasını denetler — `F7-025`.

    Dosya adındaki sayaç verilirse, ilk frame'in indeksinin ona uyup
    uymadığı da denetlenir. `RxData00007.bin` içinde 70'ten farklı
    başlayan bir indeks, dosyaların karıştığını gösterir.
    """
    issues: list[FrameIssue] = []
    if not decoded.frames:
        return issues

    if file_index is not None:
        frames_per_file = decoded.frame_count
        expected_first = file_index * frames_per_file
        actual_first = decoded.frames[0].index
        if actual_first != expected_first:
            issues.append(
                FrameIssue(
                    frame_index=actual_first,
                    code="INDEX_MISMATCH",
                    detail=f"dosya sayaci {file_index} ise ilk frame indeksi "
                    f"{expected_first} olmaliydi, {actual_first} bulundu",
                )
            )

    for previous, current in zip(decoded.frames, decoded.frames[1:]):
        step = current.index - previous.index
        if step == 1:
            continue
        code = "INDEX_BACKWARD" if step <= 0 else "GAP_BEFORE"
        issues.append(
            FrameIssue(
                frame_index=current.index,
                code=code,
                detail=f"onceki frame {previous.index}, simdiki {current.index}",
            )
        )
    return issues


@dataclass(frozen=True)
class DriftMeasurement:
    """Timestamp ile frame sayacı arasındaki kayma — `F7-026`."""

    #: Olculen ortalama frame periyodu (ns).
    measured_period_ns: float
    #: Semadan turetilen nominal periyot (ns): frame_samples / fs.
    nominal_period_ns: float
    #: Sapma, milyonda bir. Isaret onemli: hangi tarafin hizli oldugunu soyler.
    ppm: float
    #: Kac frame uzerinden olculdu.
    frames: int

    @property
    def measurable(self) -> bool:
        """Ölçüm için en az iki frame gerekir."""
        return self.frames >= 2

    def accumulated_ns(self, duration_s: float) -> float:
        """Verilen sürede birikecek kayma."""
        return self.ppm * 1e-6 * duration_s * 1e9


def measure_drift(
    decoded: DecodedFile, sample_rate_hz: float, frame_samples: int
) -> DriftMeasurement:
    """Zaman damgası adımını nominal frame periyoduyla karşılaştırır.

    Nominal periyot **şemadan türer**: ``frame_samples / fs``. 820 örnek
    ve 8192 Hz için 100,0977 ms eder, 100 ms değil.

    Sapma bir hata değil bir **ölçümdür** (`ADR-003` §2.6: drift ölçülür,
    sessizce düzeltilmez). Cihaz saati nominal 100 ms ızgarasına yazıyorsa
    sapma −975,6 ppm çıkar; işaret hangi tarafın hızlı olduğunu söyler.

    İki frame'den azsa ölçüm yapılamaz ve bu `measurable` ile bildirilir;
    sıfır döndürüp "sapma yok" demek, ölçülmemişi ölçülmüş göstermek olurdu.
    """
    nominal_ns = frame_samples / sample_rate_hz * 1e9
    stamps = [frame.timestamp_ns for frame in decoded.frames if "timestamp_utc_ns" in frame.header]
    if len(stamps) < 2:
        return DriftMeasurement(
            measured_period_ns=float("nan"),
            nominal_period_ns=nominal_ns,
            ppm=float("nan"),
            frames=len(stamps),
        )

    measured = (stamps[-1] - stamps[0]) / (len(stamps) - 1)
    return DriftMeasurement(
        measured_period_ns=measured,
        nominal_period_ns=nominal_ns,
        ppm=(measured - nominal_ns) / nominal_ns * 1e6,
        frames=len(stamps),
    )
