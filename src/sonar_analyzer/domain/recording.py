"""Kayıt üst bilgisi — `F1-013`.

`RecordingMetadata`, açılan `.bin` dosyasının kimliğini ve kapsadığı zamanı
taşır. Data Explorer'daki dosya özeti (plan Bölüm 5.1, bölge 1) bu modelden
beslenir; değerler kayıttan gelir, sabit değildir.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sonar_analyzer.domain.time_range import RECORD_PERIOD_NS, TimeRange


def _empty_str_list() -> list[str]:
    return []


@dataclass(frozen=True)
class RecordingMetadata:
    """Bir kaydın değişmeyen üst bilgisi."""

    recording_id: str
    source_path: str
    time_range: TimeRange
    format_profile: str = "A"
    format_version: int = 1
    channel_count: int = 0
    record_count: int = 0
    record_period_ns: int = RECORD_PERIOD_NS
    device_id: str = ""
    firmware_version: str = ""
    file_size_bytes: int = 0
    diagnostics: list[str] = field(default_factory=_empty_str_list)

    def __post_init__(self) -> None:
        if not self.recording_id.strip():
            raise ValueError("Kayit kimligi bos olamaz")
        if not self.source_path.strip():
            raise ValueError(f"{self.recording_id}: kaynak dosya yolu bos olamaz")
        if self.channel_count < 0:
            raise ValueError(f"{self.recording_id}: kanal sayisi negatif olamaz")
        if self.record_count < 0:
            raise ValueError(f"{self.recording_id}: kayit sayisi negatif olamaz")
        if self.record_period_ns <= 0:
            raise ValueError(
                f"{self.recording_id}: kayit periyodu pozitif olmali, "
                f"verilen {self.record_period_ns}"
            )
        if self.file_size_bytes < 0:
            raise ValueError(f"{self.recording_id}: dosya boyutu negatif olamaz")

    @property
    def start_ns(self) -> int:
        return self.time_range.start_ns

    @property
    def end_ns(self) -> int:
        return self.time_range.end_ns

    @property
    def duration_seconds(self) -> float:
        return self.time_range.duration_seconds

    @property
    def expected_record_count(self) -> int:
        """Aralığın tamamı kayıtlıysa beklenen kayıt sayısı."""
        return self.time_range.duration_ns // self.record_period_ns

    @property
    def missing_record_count(self) -> int:
        """Beklenen ile gerçek kayıt sayısı farkı; negatifse 0."""
        return max(0, self.expected_record_count - self.record_count)

    @property
    def has_gaps(self) -> bool:
        return self.missing_record_count > 0

    @property
    def sample_rate_hz(self) -> float:
        """Kayıt (record) hızı — örnek hızı değil."""
        return 1_000_000_000 / self.record_period_ns
