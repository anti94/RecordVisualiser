"""Profil B akustik blok boyut ve sample rate doğrulaması — `F4-014`.

`profile_b.py` decoder'ı **yapısal** olarak ölümcül hataları çözüm
sırasında reddeder (dtype boyutuna bölünmeyen `block_size`, dosya sonunu
aşan payload). Bu modül bir adım öteye geçer ve **anlamsal** sınırları
denetler:

* Bir `SENSOR_RAW` bloğu 125 ms pencerede tam `SAMPLES_PER_BLOCK`
  (= 6000) örnek taşımalıdır. Farklıysa örnek sayısı bozuktur
  (`SAMPLE_COUNT_MISMATCH`).
* Örnek sayısından türeyen **örtük örnekleme hızı**, beklenen 48 kHz'e
  uymuyorsa blok akustik veri değildir (`SAMPLE_RATE_MISMATCH`). Böylece
  kayıt başına 1 örnek taşıyan 8 Hz telemetri, 48 kHz (veya 10 kHz)
  akustik veri gibi sunulamaz.
* Beklenmeyen dtype ve tanımsız kanal ayrı kodlarla raporlanır.

`validate_*` sorunları **liste** olarak döndürür (okuma durmaz);
`ensure_acoustic_record` ilk sorunda `ProfileBValidationError` yükseltir
(sert ret yolu). Saf Python — Qt yok, `GUI olmadan` doğrulanır.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from sonar_analyzer.io.decoders.profile_b import (
    DecodedBlock,
    DecodedRecord,
    ProfileBFormatError,
    iter_records,
)
from sonar_analyzer.io.profile_b_format import (
    ACOUSTIC_CHANNEL_IDS,
    ACOUSTIC_DTYPE_CODE,
    ACOUSTIC_SAMPLE_RATE_HZ,
    RECORD_PERIOD_NS,
    SAMPLES_PER_BLOCK,
)
from sonar_analyzer.io.readers.binary_reader import ReadableBuffer

NS_PER_SECOND = 1_000_000_000

#: Örtük hız ile beklenen hız arasında kabul edilen bağıl fark (%1).
#: 6000 örnek/125 ms tam 48 kHz verdiği için sağlam bloklarda pay sıfırdır;
#: tolerans yalnız kayan-nokta gürültüsüne karşıdır, bozuk sayıyı geçirmez.
RATE_RELATIVE_TOLERANCE = 0.01


class ProfileBValidationError(ProfileBFormatError):
    """Bir Profil B kaydı akustik anlamsal sözleşmeyi ihlal ediyor."""


@dataclass(frozen=True)
class AcousticIssue:
    """Bir `SENSOR_RAW` bloğundaki anlamsal sorun."""

    code: str
    message: str
    channel_id: int
    byte_offset: int
    sample_count: int


@dataclass(frozen=True)
class AcousticLimits:
    """Bir bloğun uyması gereken akustik sınırlar (test için ayarlanabilir)."""

    record_period_ns: int = RECORD_PERIOD_NS
    expected_samples: int = SAMPLES_PER_BLOCK
    expected_sample_rate_hz: int = ACOUSTIC_SAMPLE_RATE_HZ
    expected_dtype_code: int = ACOUSTIC_DTYPE_CODE
    known_channel_ids: tuple[int, ...] = ACOUSTIC_CHANNEL_IDS
    rate_relative_tolerance: float = RATE_RELATIVE_TOLERANCE


DEFAULT_LIMITS = AcousticLimits()


def implied_sample_rate_hz(sample_count: int, record_period_ns: int = RECORD_PERIOD_NS) -> float:
    """`sample_count` örnek `record_period_ns` sürede taşınıyorsa örtük örnekleme hızı (Hz).

    6000 örnek / 125 ms → 48000.0; 1 örnek / 125 ms → 8.0.
    """
    if record_period_ns <= 0:
        raise ValueError(f"record_period_ns pozitif olmalı: {record_period_ns}")
    return sample_count * NS_PER_SECOND / record_period_ns


def rates_match(actual_hz: float, expected_hz: float, *, relative_tolerance: float) -> bool:
    """`actual_hz`, `expected_hz`'e bağıl toleransta eşit mi?"""
    return abs(actual_hz - expected_hz) <= relative_tolerance * expected_hz


def validate_acoustic_block(
    block: DecodedBlock,
    limits: AcousticLimits = DEFAULT_LIMITS,
) -> list[AcousticIssue]:
    """Tek bir `SENSOR_RAW` bloğunu akustik sınırlara karşı denetler.

    `SENSOR_RAW` olmayan bloklar sessizce atlanır (bu modülün konusu değil).
    """
    if not block.is_sensor_raw:
        return []

    count = 0 if block.samples is None else int(block.samples.shape[0])
    issues: list[AcousticIssue] = []

    def add(code: str, message: str) -> None:
        issues.append(AcousticIssue(code, message, block.channel_id, block.byte_offset, count))

    if block.channel_id not in limits.known_channel_ids:
        add("UNKNOWN_CHANNEL", f"kanal {block.channel_id} akustik kanal kümesinde değil")

    if block.dtype_code != limits.expected_dtype_code:
        add(
            "UNEXPECTED_DTYPE",
            f"akustik dtype {block.dtype_code:#x}, beklenen {limits.expected_dtype_code:#x}",
        )

    if count == 0:
        add("EMPTY_BLOCK", "SENSOR_RAW bloğu boş — akustik pencere örnek taşımıyor")
        return issues

    if count != limits.expected_samples:
        add(
            "SAMPLE_COUNT_MISMATCH",
            (
                f"{count} örnek, beklenen {limits.expected_samples} "
                f"({limits.record_period_ns} ns / {limits.expected_sample_rate_hz} Hz). "
                f"Bozuk örnek sayısı reddedilir."
            ),
        )

    rate = implied_sample_rate_hz(count, limits.record_period_ns)
    if not rates_match(
        rate,
        limits.expected_sample_rate_hz,
        relative_tolerance=limits.rate_relative_tolerance,
    ):
        add(
            "SAMPLE_RATE_MISMATCH",
            (
                f"{count} örnek / {limits.record_period_ns} ns → örtük {rate:.4g} Hz; "
                f"beklenen {limits.expected_sample_rate_hz} Hz. "
                f"Düşük hızlı telemetri yüksek hızlı akustik veri gibi sunulamaz."
            ),
        )

    return issues


def validate_acoustic_record(
    record: DecodedRecord,
    limits: AcousticLimits = DEFAULT_LIMITS,
) -> list[AcousticIssue]:
    """Bir kaydın tüm `SENSOR_RAW` bloklarını denetler; sorunları birleştirir."""
    issues: list[AcousticIssue] = []
    for block in record.blocks:
        issues.extend(validate_acoustic_block(block, limits))
    return issues


def validate_acoustic_buffer(
    buffer: ReadableBuffer,
    limits: AcousticLimits = DEFAULT_LIMITS,
) -> list[AcousticIssue]:
    """Tampondaki her kaydı denetler; ilk hatalı kayıtta durmaz, hepsini toplar."""
    issues: list[AcousticIssue] = []
    for record in iter_records(buffer):
        issues.extend(validate_acoustic_record(record, limits))
    return issues


def ensure_acoustic_record(record: DecodedRecord, limits: AcousticLimits = DEFAULT_LIMITS) -> None:
    """İlk anlamsal sorunda `ProfileBValidationError` yükseltir (sert ret)."""
    issues = validate_acoustic_record(record, limits)
    if issues:
        first = issues[0]
        raise ProfileBValidationError(
            f"[{first.code}] kayıt {record.record_index} kanal {first.channel_id}: {first.message}",
            byte_offset=first.byte_offset,
        )


def is_acoustic_record(record: DecodedRecord, limits: AcousticLimits = DEFAULT_LIMITS) -> bool:
    """Kayıt tüm anlamsal denetimleri geçiyorsa `True`."""
    return not validate_acoustic_record(record, limits)


def issue_codes(issues: Iterable[AcousticIssue]) -> list[str]:
    """Sorun listesindeki kodlar (test/log kısaltması)."""
    return [issue.code for issue in issues]
