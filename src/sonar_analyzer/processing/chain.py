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

from sonar_analyzer.processing.steps import ProcessingStep, StepKind

Samples = NDArray[np.float64]


class ChainExecutionError(ValueError):
    """Zincir yürütülemedi (boş girdi bir adım için geçersiz vb.)."""


def _as_float64(values: NDArray[np.generic]) -> Samples:
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 1:
        raise ChainExecutionError(f"Örnek dizisi tek boyutlu olmalı, boyut {array.ndim}")
    return array


def _moving_average(values: Samples, window: int) -> Samples:
    """Merkezli kayan pencere ortalaması; çıktı uzunluğu girdiyle aynı.

    Uçlarda pencere kısalır (kısmi ortalama) — böylece dizi uzunluğu ve
    zaman hizası korunur.
    """
    if window <= 1 or values.size == 0:
        return values.copy()
    kernel = np.ones(window, dtype=np.float64)
    padded = np.convolve(values, kernel, mode="same")
    counts = np.convolve(np.ones_like(values), kernel, mode="same")
    return padded / counts


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
        return _moving_average(data, int(params["window"]))  # type: ignore[arg-type]
    raise ChainExecutionError(f"Uygulanmayan işlem türü: {step.kind}")  # pragma: no cover


@dataclass(frozen=True)
class ChainResult:
    """Bir zincir yürütmesinin sonucu."""

    values: Samples
    #: Uygulanan (etkin) adımların imzaları, sırayla.
    applied: tuple[str, ...]

    @property
    def step_count(self) -> int:
        return len(self.applied)


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

    def run(self, values: NDArray[np.generic]) -> ChainResult:
        """Etkin adımları sırayla uygular; **girdiyi değiştirmez**."""
        source = _as_float64(values)
        current = source.copy()
        applied: list[str] = []
        for step in self.steps:
            if not step.enabled:
                continue
            current = _as_float64(apply_step(current, step))
            applied.append(step.signature())
        return ChainResult(values=current, applied=tuple(applied))

    # -- tekrar üretilebilirlik / serileştirme -----------------

    def signature(self) -> str:
        """Etkin adımların sıralı imzalarından türeyen stabil zincir imzası."""
        return json.dumps([s.signature() for s in self.enabled_steps], separators=(",", ":"))

    def to_list(self) -> list[dict[str, object]]:
        return [s.to_dict() for s in self.steps]

    @classmethod
    def from_list(cls, data: Iterable[object]) -> ProcessingChain:
        return cls([ProcessingStep.from_dict(entry) for entry in data])
