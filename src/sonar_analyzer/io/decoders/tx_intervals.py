"""TX durumunu başlangıç/bitiş aralıklarına çevirme — `F2-023`.

Kayıttaki `tx_status` alanı ham bir durum **örneğidir** (kod: `0=IDLE`,
`1=ACTIVE`, `2=FAULT`). Örnekleri aralığa çevirme mantığının kendisi
`domain.transmission.TransmissionInterval.from_state_samples()`'ta zaten
tanımlıdır (`F1-015`): `ACTIVE`'e geçiş `START`, `ACTIVE`'ten çıkış `STOP`
sayılır; kayıt `ACTIVE` iken biterse aralık **açık** işaretlenir
(`closed=False`) ve son örneğin penceresi kadar uzatılır — kapanmış gibi
gösterilmez.

Bu modül yalnız parser tarafını (`io`) o fonksiyona bağlar: kaydın
`tx_status`'unu `TxState`'e, `elapsed_us`'unu (`F2-007` ile) mutlak
`timestamp_ns`'e çevirip domain fonksiyonuna verir.
"""

from __future__ import annotations

from collections.abc import Iterable

from sonar_analyzer.domain.transmission import TransmissionInterval, TxState
from sonar_analyzer.io.decoders.timing import record_timestamp_ns
from sonar_analyzer.io.profile_a_format import DataRecordV1, FileHeaderV1


def tx_state_samples(
    records: Iterable[DataRecordV1], header: FileHeaderV1
) -> list[tuple[int, TxState]]:
    """Her kaydın `tx_status`'unu `(timestamp_ns, TxState)` örneğine çevirir."""
    return [
        (record_timestamp_ns(header, record), TxState.from_code(record.tx_status))
        for record in records
    ]


def tx_intervals_from_records(
    records: Iterable[DataRecordV1], header: FileHeaderV1
) -> list[TransmissionInterval]:
    """Kayıt akışını transmisyon aralıklarına çevirir (`F1-015`'in sarmalayıcısı).

    Sınır belirsizliği `header.period_us`'tan hesaplanır — sabit
    `125_000` varsayılmaz, header'dan okunur.
    """
    samples = tx_state_samples(records, header)
    period_ns = header.period_us * 1_000
    return TransmissionInterval.from_state_samples(samples, period_ns=period_ns)
