"""Deterministik sentetik sinyal üreteçleri — `F1-018`.

Gerçek kayıt gelene kadar arayüz ve analiz hattı bu sinyallerle beslenir
(`docs/format/inventory.md` §3). İki kural:

* **Deterministik:** aynı parametreler her çağrıda **bit düzeyinde aynı** zaman
  ve değer dizisini üretir. Aksi hâlde beklenen sonuçlar sabitlenemez ve
  testler kırılgan olur.
* **Sahte veri sahte olduğunu söyler:** üretilen kanal kimlikleri çağıran
  tarafından verilir; bu modül hiçbir yerde "gerçek kayıt" iddiasında bulunmaz
  (plan Bölüm 3.1).

Zaman ekseni kanoniktir: `int64` UTC nanosaniye (`docs/adr/ADR-003-time-base.md`).
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from numpy.typing import NDArray

from sonar_analyzer.domain.data_chunk import DataChunk

NS_PER_SECOND = 1_000_000_000


def sample_count(sample_rate_hz: float, duration_s: float) -> int:
    """Süre ve örnekleme hızından örnek sayısı."""
    if sample_rate_hz <= 0:
        raise ValueError(f"Ornekleme hizi pozitif olmali, verilen: {sample_rate_hz}")
    if duration_s < 0:
        raise ValueError(f"Sure negatif olamaz: {duration_s}")
    return round(sample_rate_hz * duration_s)


def time_axis(
    sample_rate_hz: float,
    duration_s: float,
    start_ns: int = 0,
) -> NDArray[np.int64]:
    """Nanosaniye zaman ekseni.

    Örnek konumları tamsayı aritmetiğiyle hesaplanır; `start + i/fs` biçiminde
    kayan noktalı toplama kullanılsaydı uzun dizilerde hata birikirdi.
    """
    count = sample_count(sample_rate_hz, duration_s)
    indices = np.arange(count, dtype=np.int64)
    offsets = (indices * NS_PER_SECOND) // round(sample_rate_hz)
    return (start_ns + offsets).astype(np.int64)


def sine(
    channel_id: str,
    sample_rate_hz: float,
    duration_s: float,
    frequency_hz: float,
    amplitude: float = 1.0,
    phase_rad: float = 0.0,
    offset: float = 0.0,
    start_ns: int = 0,
) -> DataChunk:
    """Sabit frekanslı sinüs.

    Aynı parametrelerle çağrıldığında birebir aynı diziyi üretir.
    """
    if frequency_hz <= 0:
        raise ValueError(f"Frekans pozitif olmali, verilen: {frequency_hz}")
    if frequency_hz > sample_rate_hz / 2:
        raise ValueError(
            f"Frekans Nyquist sinirini asiyor: {frequency_hz} Hz > "
            f"{sample_rate_hz / 2} Hz. Ortaya cikan sinyal katlanma (aliasing) icerir."
        )

    stamps = time_axis(sample_rate_hz, duration_s, start_ns)
    # Ornek indisi uzerinden hesap: zaman ekseni tamsayi oldugu icin
    # dogrudan ns kullanmak yuvarlama farki yaratirdi.
    indices = np.arange(stamps.size, dtype=np.float64)
    angle = 2.0 * np.pi * frequency_hz * indices / sample_rate_hz + phase_rad
    values = (amplitude * np.sin(angle) + offset).astype(np.float32)

    return DataChunk(channel_id=channel_id, timestamps_ns=stamps, values=values)


def noise(
    channel_id: str,
    sample_rate_hz: float,
    duration_s: float,
    amplitude: float = 1.0,
    seed: int = 0,
    start_ns: int = 0,
) -> DataChunk:
    """Gauss gürültüsü.

    `seed` **zorunlu olarak sabittir** (öntanımlı 0): aynı seed aynı diziyi
    üretir. Sistem entropisiyle beslenen bir üreteç kullanılsaydı beklenen
    sonuçlar sabitlenemez ve testler her koşuda başka değer görürdü.
    """
    if amplitude < 0:
        raise ValueError(f"Genlik negatif olamaz: {amplitude}")

    stamps = time_axis(sample_rate_hz, duration_s, start_ns)
    generator = np.random.default_rng(seed)
    values = (generator.standard_normal(stamps.size) * amplitude).astype(np.float32)
    return DataChunk(channel_id=channel_id, timestamps_ns=stamps, values=values)


def chirp(
    channel_id: str,
    sample_rate_hz: float,
    duration_s: float,
    start_hz: float,
    end_hz: float,
    amplitude: float = 1.0,
    start_ns: int = 0,
) -> DataChunk:
    """Doğrusal frekans süpürmesi (LFM).

    Anlık frekans `start_hz` değerinden `end_hz` değerine doğrusal gider.
    Faz, frekansın integrali alınarak hesaplanır; doğrudan
    `sin(2*pi*f(t)*t)` yazmak yanlış anlık frekans üretirdi.
    """
    if start_hz <= 0 or end_hz <= 0:
        raise ValueError(f"Frekanslar pozitif olmali: {start_hz} -> {end_hz}")
    nyquist = sample_rate_hz / 2
    if max(start_hz, end_hz) > nyquist:
        raise ValueError(
            f"Frekans Nyquist sinirini asiyor: {max(start_hz, end_hz)} Hz > {nyquist} Hz"
        )
    if duration_s <= 0:
        raise ValueError(f"Chirp suresi pozitif olmali: {duration_s}")

    stamps = time_axis(sample_rate_hz, duration_s, start_ns)
    seconds = np.arange(stamps.size, dtype=np.float64) / sample_rate_hz
    sweep_rate = (end_hz - start_hz) / duration_s
    phase = 2.0 * np.pi * (start_hz * seconds + 0.5 * sweep_rate * seconds**2)
    values = (amplitude * np.sin(phase)).astype(np.float32)
    return DataChunk(channel_id=channel_id, timestamps_ns=stamps, values=values)


def impulse(
    channel_id: str,
    sample_rate_hz: float,
    duration_s: float,
    positions_s: Sequence[float],
    amplitude: float = 1.0,
    start_ns: int = 0,
) -> DataChunk:
    """Belirtilen anlarda tek örneklik darbeler; aralar sıfırdır.

    Downsample testleri için kullanılır: dar darbeler indirgeme sonrasında
    kaybolmamalıdır (`docs/perf/budget.md` §4.1).
    """
    stamps = time_axis(sample_rate_hz, duration_s, start_ns)
    values = np.zeros(stamps.size, dtype=np.float32)

    for position in positions_s:
        if position < 0:
            raise ValueError(f"Darbe konumu negatif olamaz: {position}")
        index = round(position * sample_rate_hz)
        if index >= values.size:
            raise ValueError(f"Darbe konumu sinyal disinda: {position} s, sinyal {duration_s} s")
        values[index] = amplitude

    return DataChunk(channel_id=channel_id, timestamps_ns=stamps, values=values)
