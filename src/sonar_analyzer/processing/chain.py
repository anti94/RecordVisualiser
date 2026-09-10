"""Sıralı işlem zinciri yürütücüsü — `F4-002`.

Bir `ProcessingChain`, `ProcessingStep`'leri **tanımlı sırayla** bir
kanalın örnek dizisine uygular. İki değişmez kural:

1. **Ham dizi değişmez.** Yürütücü hiçbir adımda girdiyi yerinde
   düzenlemez; her adım yeni bir `float64` dizi döndürür.
2. **Deterministik.** Aynı zincir + aynı girdi her zaman bit düzeyinde
   aynı çıktıyı verir; `signature()` bunu önbellek anahtarı olarak dışa
   verir.

Devre dışı (`enabled=False`) adımlar atlanır. Boş zincir girdinin bir
kopyasını döndürür. Saf NumPy — Qt yok, `GUI olmadan` doğrulanır.
Worker'da çalıştırma `F4-003`.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

from sonar_analyzer.domain.data_chunk import Quality
from sonar_analyzer.processing.steps import ProcessingStep, StepKind
from sonar_analyzer.processing.windowing import moving_average

Samples = NDArray[np.float64]
InvalidMask = NDArray[np.bool_]

#: `F4-005` — bir örneğin **değerini** güvenilmez kılan kalite bayrakları.
#: CRC hatası ve fiziksel olarak sıra dışı örnek DSP'ye sokulmaz; zaman
#: bayrakları (`GAP_BEFORE`, `JITTER`, `CLOCK_UNLOCKED`) değeri değil
#: konumu ilgilendirir ve burada geçersiz sayılmaz.
INVALID_QUALITY_MASK = int(Quality.CRC_ERROR | Quality.SUSPECT)


class ChainExecutionError(ValueError):
    """Zincir yürütülemedi (boş girdi bir adım için geçersiz vb.)."""


def invalid_input_mask(
    values: Samples,
    quality: NDArray[np.generic] | None = None,
) -> InvalidMask:
    """DSP için geçersiz örneklerin bool maskesi — `F4-005`.

    Geçersiz sayılanlar: NaN, ±Inf ve `INVALID_QUALITY_MASK` bayraklarından
    en az birini taşıyan örnekler. **Sessizce düzeltilmezler**; çağıran
    zincir bunları NaN'a çevirir ve NaN tüm adımlarda yayılır.
    """
    mask = ~np.isfinite(values)
    if quality is not None:
        flags = np.asarray(quality)
        if flags.shape != values.shape:
            raise ChainExecutionError(
                f"Kalite dizisi örnek dizisiyle aynı uzunlukta olmalı "
                f"({flags.shape} vs {values.shape})"
            )
        mask = mask | ((flags.astype(np.int64) & INVALID_QUALITY_MASK) != 0)
    return mask


def _as_float64(values: NDArray[np.generic]) -> Samples:
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 1:
        raise ChainExecutionError(f"Örnek dizisi tek boyutlu olmalı, boyut {array.ndim}")
    return array


def _detrend(values: Samples, mode: str) -> Samples:
    """Sabit (DC) ya da doğrusal trendi çıkarır — `F4-015`.

    * ``constant`` — sonlu örneklerin ortalamasını çıkarır (DC kaldırma).
    * ``linear`` — sonlu örneklere en küçük kareler doğrusu
      (``slope * i + intercept``, ``i`` = örnek indeksi) uydurur ve
      çıkarır. Katsayılar normal denklemlerin kapalı formuyla hesaplanır;
      bağımsız referans ``numpy.polyfit(i, x, 1)``.

    NaN yayılımı yerine **NaN'a dayanıklıdır**: geçersiz örnekler taban
    çizgisi kestiriminden dışlanır, kendileri NaN kalır. Detrend küresel
    bir işlemdir; tek bir bozuk örnek tüm diziyi bozmamalıdır (yerel olan
    `moving_average`'dan farkı budur). İki sonlu örnekten azsa doğrusal
    uydurma tekildir; sabit çıkarmaya düşülür.
    """
    if values.size == 0:
        return values.copy()
    finite = np.isfinite(values)
    finite_count = int(np.count_nonzero(finite))
    if finite_count == 0:
        return values.copy()

    baseline_mean = float(values[finite].mean())
    if mode == "constant" or finite_count < 2:
        return values - baseline_mean

    if mode == "linear":
        index = np.arange(values.size, dtype=np.float64)
        t = index[finite]
        x = values[finite]
        n = float(finite_count)
        sum_t = float(t.sum())
        sum_x = float(x.sum())
        sum_tt = float((t * t).sum())
        sum_tx = float((t * x).sum())
        denominator = n * sum_tt - sum_t * sum_t
        slope = (n * sum_tx - sum_t * sum_x) / denominator
        intercept = (sum_x - slope * sum_t) / n
        return values - (slope * index + intercept)

    raise ChainExecutionError(f"Bilinmeyen detrend modu: {mode!r}")  # pragma: no cover


def _normalize(values: Samples, mode: str, reference: float) -> Samples:
    """Sinyali `reference` genliğe ölçekler — `F4-019`.

    * ``peak`` — ``|x|`` tepesi ``reference`` olacak şekilde ölçekler.
    * ``rms`` — RMS değeri ``reference`` olacak şekilde ölçekler.

    **Sıfır sinyal bölme hatası üretmez:** norm (tepe ya da RMS) sıfır
    veya sonlu değilse dizi olduğu gibi (kopya) döndürülür — ``inf`` /
    ``nan`` üretilmez, uyarı verilmez. NaN'a dayanıklı: norm yalnız sonlu
    örneklerden hesaplanır, NaN örnekler NaN kalır.
    """
    if values.size == 0:
        return values.copy()
    finite = np.isfinite(values)
    if not finite.any():
        return values.copy()

    good = values[finite]
    if mode == "peak":
        norm = float(np.abs(good).max())
    elif mode == "rms":
        norm = float(np.sqrt(np.mean(np.square(good))))
    else:  # pragma: no cover - `ProcessingStep` doğrulaması bunu engeller
        raise ChainExecutionError(f"Bilinmeyen normalize modu: {mode!r}")

    if norm == 0.0 or not np.isfinite(norm):
        return values.copy()
    return values * (reference / norm)


def apply_step(values: Samples, step: ProcessingStep) -> Samples:
    """Tek bir adımı uygular; **her zaman yeni** bir `float64` dizi döndürür."""
    data = _as_float64(values)
    params = step.parameters
    if step.kind is StepKind.SCALE:
        return data * float(params["factor"])  # type: ignore[arg-type]
    if step.kind is StepKind.OFFSET:
        return data + float(params["delta"])  # type: ignore[arg-type]
    if step.kind is StepKind.ABS:
        return np.abs(data)
    if step.kind is StepKind.CLIP:
        return np.clip(data, float(params["lo"]), float(params["hi"]))  # type: ignore[arg-type]
    if step.kind is StepKind.MOVING_AVERAGE:
        return moving_average(data, int(params["window"]))  # type: ignore[arg-type]
    if step.kind is StepKind.DETREND:
        return _detrend(data, str(params["mode"]))
    if step.kind is StepKind.NORMALIZE:
        return _normalize(
            data,
            str(params["mode"]),
            float(params["reference"]),  # type: ignore[arg-type]
        )
    raise ChainExecutionError(f"Uygulanmayan işlem türü: {step.kind}")  # pragma: no cover


def _empty_mask() -> InvalidMask:
    return np.zeros(0, dtype=np.bool_)


@dataclass(frozen=True)
class ChainResult:
    """Bir zincir yürütmesinin sonucu."""

    values: Samples
    #: Uygulanan (etkin) adımların imzaları, sırayla.
    applied: tuple[str, ...]
    #: `F4-005` — çıktıda **güvenilmez** (NaN / non-finite) örneklerin maskesi.
    #: Geçersiz girdiler burada işaretli kalır; geçerli bir değere dönüşmezler.
    invalid_mask: InvalidMask = field(default_factory=_empty_mask)

    @property
    def step_count(self) -> int:
        return len(self.applied)

    @property
    def invalid_count(self) -> int:
        return int(np.count_nonzero(self.invalid_mask))


def _empty_steps() -> list[ProcessingStep]:
    return []


@dataclass(frozen=True)
class ProcessingChain:
    """Bir kanala uygulanacak sıralı işlem adımları."""

    steps: list[ProcessingStep] = field(default_factory=_empty_steps)

    def __post_init__(self) -> None:
        object.__setattr__(self, "steps", list(self.steps))

    # -- kurma ------------------------------------------------------

    def with_step(self, step: ProcessingStep) -> ProcessingChain:
        return ProcessingChain([*self.steps, step])

    def without_index(self, index: int) -> ProcessingChain:
        if not 0 <= index < len(self.steps):
            raise IndexError(f"Adım indeksi aralık dışı: {index}")
        return ProcessingChain([s for i, s in enumerate(self.steps) if i != index])

    def moved(self, from_index: int, to_index: int) -> ProcessingChain:
        count = len(self.steps)
        if not (0 <= from_index < count and 0 <= to_index < count):
            raise IndexError("Adım indeksi aralık dışı")
        ordered = list(self.steps)
        ordered.insert(to_index, ordered.pop(from_index))
        return ProcessingChain(ordered)

    @property
    def enabled_steps(self) -> list[ProcessingStep]:
        return [s for s in self.steps if s.enabled]

    # -- yürütme --------------------------------------------------

    def run(
        self,
        values: NDArray[np.generic],
        quality: NDArray[np.generic] | None = None,
    ) -> ChainResult:
        """Etkin adımları sırayla uygular; **girdiyi değiştirmez** — `F4-002`, `F4-005`.

        `F4-005` politikası: NaN / ±Inf ve `INVALID_QUALITY_MASK`
        bayraklı örnekler işleme **girmeden** NaN'a çevrilir; NaN tüm
        adımlarda yayılır ve hiçbir adım onu geçerli bir sayıya
        dönüştürmez (`np.clip(inf, …)` gibi sessiz "iyileşme" engellenir).
        Çıktıdaki güvenilmez örnekler `ChainResult.invalid_mask`'te
        işaretli kalır.
        """
        source = _as_float64(values)
        bad_in = invalid_input_mask(source, quality)
        current = source.copy()
        if bad_in.any():
            current[bad_in] = np.nan

        applied: list[str] = []
        for step in self.steps:
            if not step.enabled:
                continue
            current = _as_float64(apply_step(current, step))
            applied.append(step.signature())

        return ChainResult(
            values=current,
            applied=tuple(applied),
            invalid_mask=~np.isfinite(current),
        )

    # -- tekrar üretilebilirlik / serileştirme -----------------

    def signature(self) -> str:
        """Etkin adımların sıralı imzalarından türeyen stabil zincir imzası."""
        return json.dumps([s.signature() for s in self.enabled_steps], separators=(",", ":"))

    def to_list(self) -> list[dict[str, object]]:
        return [s.to_dict() for s in self.steps]

    @classmethod
    def from_list(cls, data: Iterable[object]) -> ProcessingChain:
        return cls([ProcessingStep.from_dict(entry) for entry in data])
