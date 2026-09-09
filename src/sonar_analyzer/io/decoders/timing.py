"""125 ms kayıt zamanını kanonik ns'ye dönüştürme — `F2-007`.

`docs/adr/ADR-003-time-base.md` §2.1: uygulama içindeki tek zaman temsili
`int64` UTC nanosaniyedir. Profil A kaydı yalnız `elapsed_us` (kayıt başına
göre mikrosaniye) taşır; mutlak zaman header'daki `start_time_utc_ns` ankoruna
göre hesaplanır.

Dönüşüm tamsayı aritmetiğiyle yapılır — `float64` saniyeye çevrilseydi
`docs/adr/ADR-003-time-base.md` §3'te reddedilen ulp kaybı riski doğardı.
"""

from __future__ import annotations

from sonar_analyzer.io.profile_a_format import DataRecordV1, FileHeaderV1

#: 1 mikrosaniye = 1000 nanosaniye.
NS_PER_MICROSECOND = 1_000


def record_timestamp_ns(header: FileHeaderV1, record: DataRecordV1) -> int:
    """Kaydın mutlak UTC ns zamanı: `start_time_utc_ns + elapsed_us * 1000`."""
    return header.start_time_utc_ns + record.elapsed_us * NS_PER_MICROSECOND


def elapsed_us_for_sequence(sequence_no: int, period_us: int) -> int:
    """Nominal ızgaradaki geçen süre: `sequence_no * period_us`.

    Kayıpsız dosyada kaydın `elapsed_us` alanıyla aynı sonucu verir; boşluklu
    dosyada **beklenen** değeri hesaplamak için kullanılır (bkz. `F2-008`).
    """
    return sequence_no * period_us
