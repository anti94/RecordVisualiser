"""Profil B kayıt dizisi teşhisleri — plan Bölüm 8.3.12.

Bu modül `iter_records`'un **çözebildiği** ama tek başına doğrulayamadığı
üç kuralı denetler. Üçü de tek bir kayda bakarak görülemez; ancak
ardışık kayıtlar karşılaştırılınca ortaya çıkar:

1. **`record_index` monotonluğu** — atlama bir boşluktur (`GAP_BEFORE`),
   geri gidiş bozulma ya da cihazın yeniden başlamasıdır
   (`INDEX_BACKWARD`). İkisi aynı şey değildir: boşlukta veri
   *kaybolmuştur*, geri gidişte dosyanın **sırası** bozulmuştur ve
   zaman ekseni artık güvenilmez.
2. **`device_ticks` düzenliliği** — ardışık kayıtlar arasındaki cihaz
   sayacı farkı, kayıt başına beklenen tick sayısından toleransın
   dışına çıkıyorsa cihazın saati kaymıştır (`TICK_JITTER`). Denetim
   sayacın **kendi biriminde** yapılır: tick frekansı bilinmediği için
   (`E-07`) ns'ye çevirmek, bilinmeyen bir sayıyla çarpmak olurdu.
3. **`t_start_offset_ns` tutarlılığı** — kaydın bildirdiği başlangıç
   offseti `record_index × 125 ms`'ten toleransın dışındaysa, dosyanın
   iki zaman kaynağı birbirini tutmuyordur (`TIME_INCONSISTENT`).

Hiçbiri **okumayı durdurmaz**. Bunlar teşhistir: kayıt işaretlenir,
kullanıcıya bildirilir ve veri yine de sunulur. Bozuk zamanlı bir kaydı
atmak, onu göstermekten daha çok bilgi kaybettirirdi — ama sessizce
doğru sanmak en kötüsüdür.

Toleranslar **yapılandırılabilir**: farklı cihazların saat kalitesi
farklıdır ve sabit bir eşik ya sürekli çalar ya hiç çalmaz.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from sonar_analyzer.io.decoders.profile_b import DecodedRecord, iter_records
from sonar_analyzer.io.profile_b_format import RECORD_PERIOD_NS
from sonar_analyzer.io.readers.binary_reader import ReadableBuffer

#: Cihaz sayacinin nominal adimdan sapabilecegi oran (varsayilan %1).
DEFAULT_TICK_TOLERANCE = 0.01

#: `t_start_offset_ns`'in nominal izgaradan sapabilecegi sure (1 ms).
DEFAULT_TIME_TOLERANCE_NS = 1_000_000


@dataclass(frozen=True)
class SequenceLimits:
    """Dizi denetiminin toleransları.

    Sabit bir eşik ya her cihazda çalar ya hiçbirinde; bu yüzden
    değerler dışarıdan verilebilir.

    `ticks_per_record` **bilerek zorunlu değildir ve varsayılanı yoktur**:
    cihazın tick frekansı bilinmiyor (`E-07`, `K-05`). Verilmediğinde
    jitter denetimi yapılmaz — bir varsayımla "sorun yok" demek, hiç
    bakmamaktan daha yanıltıcı olurdu. Değer verildiğinde denetim
    sayacın **kendi biriminde** yapılır; ns'ye çevirmek, bilinmeyen bir
    frekansla çarpmak demek olurdu.
    """

    tick_tolerance: float = DEFAULT_TICK_TOLERANCE
    time_tolerance_ns: int = DEFAULT_TIME_TOLERANCE_NS
    ticks_per_record: int | None = None
    record_period_ns: int = RECORD_PERIOD_NS

    def __post_init__(self) -> None:
        if self.tick_tolerance < 0:
            raise ValueError(f"tick toleransi negatif olamaz: {self.tick_tolerance}")
        if self.time_tolerance_ns < 0:
            raise ValueError(f"zaman toleransi negatif olamaz: {self.time_tolerance_ns}")
        if self.ticks_per_record is not None and self.ticks_per_record <= 0:
            raise ValueError(f"kayit basina tick pozitif olmali: {self.ticks_per_record}")
        if self.record_period_ns <= 0:
            raise ValueError(f"kayit periyodu pozitif olmali: {self.record_period_ns}")

    @property
    def checks_ticks(self) -> bool:
        """Jitter denetimi yapılabilir mi — `ticks_per_record` verildi mi."""
        return self.ticks_per_record is not None


DEFAULT_LIMITS = SequenceLimits()


@dataclass(frozen=True)
class SequenceIssue:
    """Tek bir teşhis: hangi kayıt, nerede, ne oldu."""

    code: str
    record_index: int
    byte_offset: int
    message: str

    def __str__(self) -> str:
        return (
            f"{self.code}: kayit {self.record_index} (offset {self.byte_offset}) — {self.message}"
        )


def check_record_sequence(
    records: Iterable[DecodedRecord],
    limits: SequenceLimits = DEFAULT_LIMITS,
) -> list[SequenceIssue]:
    """Ardışık kayıtları karşılaştırır ve teşhisleri döndürür.

    Boş dizi ve tek kayıt sorunsuzdur: karşılaştıracak bir önceki kayıt
    yoktur. Bunu "sorun yok" diye raporlamak, denetimin yapıldığı
    izlenimini verirdi.
    """
    issues: list[SequenceIssue] = []
    ordered: Sequence[DecodedRecord] = list(records)

    for position, record in enumerate(ordered):
        _check_time_grid(record, limits, issues)
        if position == 0:
            continue
        previous = ordered[position - 1]
        _check_index(previous, record, issues)
        _check_ticks(previous, record, limits, issues)

    return issues


def _check_index(
    previous: DecodedRecord,
    record: DecodedRecord,
    issues: list[SequenceIssue],
) -> None:
    step = record.record_index - previous.record_index
    if step == 1:
        return
    if step <= 0:
        issues.append(
            SequenceIssue(
                code="INDEX_BACKWARD",
                record_index=record.record_index,
                byte_offset=record.byte_offset,
                message=(
                    f"kayit indeksi geriye gitti ({previous.record_index} -> "
                    f"{record.record_index}); bozulma ya da cihaz yeniden basladi"
                ),
            )
        )
        return
    missing = step - 1
    issues.append(
        SequenceIssue(
            code="GAP_BEFORE",
            record_index=record.record_index,
            byte_offset=record.byte_offset,
            message=(
                f"{previous.record_index} ile {record.record_index} arasinda {missing} kayit eksik"
            ),
        )
    )


def _check_ticks(
    previous: DecodedRecord,
    record: DecodedRecord,
    limits: SequenceLimits,
    issues: list[SequenceIssue],
) -> None:
    nominal_step = limits.ticks_per_record
    if nominal_step is None:
        return  # tick frekansi bilinmiyor; varsayimla hukum vermeyiz
    step = record.record_index - previous.record_index
    if step <= 0:
        return  # geri gidiste tick farki anlamsiz; zaten raporlandi
    if not previous.device_ticks and not record.device_ticks:
        return  # sayac yok: bilmedigimiz seyi jitter diye raporlamayiz

    nominal = step * nominal_step
    actual = record.device_ticks - previous.device_ticks
    allowed = nominal * limits.tick_tolerance
    drift = actual - nominal
    if abs(drift) <= allowed:
        return
    issues.append(
        SequenceIssue(
            code="TICK_JITTER",
            record_index=record.record_index,
            byte_offset=record.byte_offset,
            message=(
                f"cihaz sayaci {actual} tick ilerledi, beklenen {nominal} "
                f"(+-%{limits.tick_tolerance * 100:g}); sapma {drift} tick"
            ),
        )
    )


def _check_time_grid(
    record: DecodedRecord,
    limits: SequenceLimits,
    issues: list[SequenceIssue],
) -> None:
    expected_ns = record.record_index * limits.record_period_ns
    drift_ns = record.t_start_offset_ns - expected_ns
    if abs(drift_ns) <= limits.time_tolerance_ns:
        return
    issues.append(
        SequenceIssue(
            code="TIME_INCONSISTENT",
            record_index=record.record_index,
            byte_offset=record.byte_offset,
            message=(
                f"t_start_offset_ns {record.t_start_offset_ns}, izgara {expected_ns} "
                f"(sapma {drift_ns} ns, tolerans {limits.time_tolerance_ns} ns)"
            ),
        )
    )


def check_buffer_sequence(
    buffer: ReadableBuffer,
    limits: SequenceLimits = DEFAULT_LIMITS,
) -> list[SequenceIssue]:
    """Profil B tamponunu çözüp kayıt dizisini denetler.

    Çağıran taraf kayıtları ayrıca çözmek zorunda kalmasın diye vardır;
    denetim mantığı `check_record_sequence`'tedir.
    """
    return check_record_sequence(iter_records(buffer), limits)


def issue_codes(issues: Iterable[SequenceIssue]) -> list[str]:
    """Teşhis kodları — testler ve özet satırları için."""
    return [issue.code for issue in issues]


def summarize(
    issues: Sequence[SequenceIssue],
    limits: SequenceLimits = DEFAULT_LIMITS,
) -> str:
    """Tek satırlık özet.

    Sorun yoksa bunu **açıkça** söyler: sessizlik, denetimin hiç
    çalışmadığı anlamına da gelebilirdi. Jitter denetimi yapılamadıysa
    bu da yazılır — yapılmamış bir denetimi geçmiş saymak en sessiz
    yanlıştır.
    """
    suffix = "" if limits.checks_ticks else " (tick frekansi bilinmiyor, jitter denetlenmedi)"
    if not issues:
        return f"kayit dizisi: sorun yok{suffix}"
    counts: dict[str, int] = {}
    for issue in issues:
        counts[issue.code] = counts.get(issue.code, 0) + 1
    detail = ", ".join(f"{code}={count}" for code, count in sorted(counts.items()))
    return f"kayit dizisi: {len(issues)} tesbit ({detail}){suffix}"
