"""İşlem adımı ve parametre modeli — `F4-001`.

Bir *işlem adımı*, bir kanalın örnek dizisine uygulanacak tek bir DSP
işlemidir: hangi işlem (`kind`), hangi kanaldan okuyacağı
(`input_channel_id`) ve **tekrar üretilebilir** parametreleri
(`parameters`). Saf veri modeli — Qt yok, NumPy yalnız tip için;
`GUI olmadan` doğrulanır. Yürütme `F4-002`.

Tekrar üretilebilirlik iki kuralla sağlanır:

1. Parametreler yalnız JSON'a serileşen ilkellerdir (`int`, `float`,
   `str`, `bool`) — dizi, callable, rastgele durum yok.
2. Her adımın `signature()`'ı yalnız `kind` + `input_channel_id` +
   sıralı parametrelerden türer; aynı girdi her zaman aynı imzayı verir
   ve önbellek anahtarı olarak kullanılabilir.

Her `kind`'in zorunlu parametreleri `PARAMETER_SPECS` ile tanımlıdır;
eksik / fazla / yanlış tipli parametre `StepValidationError` verir —
sessizce varsayılana düşülmez.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import cast

from sonar_analyzer.processing.windowing import MAX_WINDOW as MAX_MOVING_AVERAGE_WINDOW


class StepValidationError(ValueError):
    """İşlem adımı bozuk: eksik/fazla/yanlış tipli parametre ya da boş kanal."""


class StepKind(str, Enum):
    """Uygulanan tek-örnek DSP işlemleri (zincir `F4-002`+ ile büyür)."""

    SCALE = "scale"  # y = x * factor
    OFFSET = "offset"  # y = x + delta
    ABS = "abs"  # y = |x|
    CLIP = "clip"  # y = min(max(x, lo), hi)
    MOVING_AVERAGE = "moving_average"  # kayan pencere ortalaması (tek boyutlu)
    DETREND = "detrend"  # sabit (DC) ya da doğrusal trend çıkarma — `F4-015`
    NORMALIZE = "normalize"  # sinyali referans genliğe ölçekle — `F4-019`
    WINDOWED_RMS = "windowed_rms"  # kayan pencere RMS'i — `F4-021`
    ENVELOPE = "envelope"  # kayan pencere tepe-tutma zarfı — `F4-021`
    PHASE_UNWRAP = "phase_unwrap"  # faz sıçramalarını sürekliliğe çevir — `F4-023`


#: `window` parametresi taşıyan ve `1 <= window <= MAX_MOVING_AVERAGE_WINDOW`
#: sınırına tabi işlem türleri.
WINDOWED_KINDS: frozenset[StepKind] = frozenset(
    {StepKind.MOVING_AVERAGE, StepKind.WINDOWED_RMS, StepKind.ENVELOPE}
)


#: `DETREND` adımının `mode` parametresi için geçerli değerler.
#: `constant` = örnek ortalamasını çıkar (DC kaldırma);
#: `linear` = en küçük kareler doğrusunu çıkar.
DETREND_MODES: tuple[str, ...] = ("constant", "linear")

#: `NORMALIZE` adımının `mode` parametresi için geçerli değerler.
#: `peak` = |x| tepesini `reference`'a getir; `rms` = RMS'i `reference`'a getir.
NORMALIZE_MODES: tuple[str, ...] = ("peak", "rms")

#: `PHASE_UNWRAP` adımının `unit` parametresi için geçerli değerler ve
#: her birinin tam periyodu (bir sarım). `discontinuity` bu periyottan
#: küçük olmalıdır.
PHASE_UNWRAP_UNITS: tuple[str, ...] = ("radians", "degrees")
PHASE_UNWRAP_PERIOD: dict[str, float] = {
    "radians": 2.0 * math.pi,
    "degrees": 360.0,
}


@dataclass(frozen=True)
class ParamSpec:
    """Bir parametrenin adı, tipi ve varsayılanı."""

    name: str
    kind: type
    default: object
    #: Boş değilse `value` bu kümede olmalı (örn. `DETREND` mode seçenekleri).
    choices: tuple[object, ...] = ()

    def coerce(self, value: object) -> object:
        """`value`'yu bu parametrenin tipine getirir; uyuşmaz ya da seçenek dışıysa hata."""
        coerced = self._coerce_type(value)
        if self.choices and coerced not in self.choices:
            raise StepValidationError(
                f"'{self.name}' şunlardan biri olmalı: {list(self.choices)}; {coerced!r} geldi"
            )
        return coerced

    def _coerce_type(self, value: object) -> object:
        if self.kind is float and isinstance(value, int) and not isinstance(value, bool):
            return float(value)
        if isinstance(value, self.kind) and not (self.kind is not bool and isinstance(value, bool)):
            return value
        raise StepValidationError(
            f"'{self.name}' {self.kind.__name__} olmalı, {type(value).__name__} geldi"
        )


def _empty_params() -> dict[str, object]:
    return {}


#: Her işlem türünün parametre sözleşmesi.
PARAMETER_SPECS: dict[StepKind, tuple[ParamSpec, ...]] = {
    StepKind.SCALE: (ParamSpec("factor", float, 1.0),),
    StepKind.OFFSET: (ParamSpec("delta", float, 0.0),),
    StepKind.ABS: (),
    StepKind.CLIP: (ParamSpec("lo", float, 0.0), ParamSpec("hi", float, 1.0)),
    StepKind.MOVING_AVERAGE: (ParamSpec("window", int, 3),),
    StepKind.DETREND: (ParamSpec("mode", str, "constant", choices=DETREND_MODES),),
    StepKind.NORMALIZE: (
        ParamSpec("mode", str, "peak", choices=NORMALIZE_MODES),
        ParamSpec("reference", float, 1.0),
    ),
    StepKind.WINDOWED_RMS: (ParamSpec("window", int, 5),),
    StepKind.ENVELOPE: (ParamSpec("window", int, 5),),
    StepKind.PHASE_UNWRAP: (
        ParamSpec("unit", str, "radians", choices=PHASE_UNWRAP_UNITS),
        ParamSpec("discontinuity", float, math.pi),
    ),
}


@dataclass(frozen=True)
class ProcessingStep:
    """Bir kanala uygulanacak tek DSP işlemi — sürümlenebilir, tekrar üretilebilir."""

    kind: StepKind
    input_channel_id: str
    parameters: dict[str, object] = field(default_factory=_empty_params)
    enabled: bool = True

    def __post_init__(self) -> None:
        if not self.input_channel_id.strip():
            raise StepValidationError("İşlem adımının girdi kanalı boş olamaz")
        specs = PARAMETER_SPECS[self.kind]
        allowed = {spec.name for spec in specs}
        extra = set(self.parameters) - allowed
        if extra:
            raise StepValidationError(f"{self.kind.value}: tanımsız parametre {sorted(extra)}")
        resolved: dict[str, object] = {}
        for spec in specs:
            if spec.name not in self.parameters:
                raise StepValidationError(f"{self.kind.value}: '{spec.name}' parametresi eksik")
            resolved[spec.name] = spec.coerce(self.parameters[spec.name])
        if self.kind is StepKind.CLIP and resolved["lo"] > resolved["hi"]:  # type: ignore[operator]
            raise StepValidationError("clip: lo, hi'den büyük olamaz")
        if self.kind in WINDOWED_KINDS:
            window = cast("int", resolved["window"])
            if window < 1:
                raise StepValidationError(f"{self.kind.value}: window >= 1 olmalı")
            if window > MAX_MOVING_AVERAGE_WINDOW:
                raise StepValidationError(
                    f"{self.kind.value}: window <= {MAX_MOVING_AVERAGE_WINDOW} olmalı "
                    f"(aşırı pencere): {window}"
                )
        if self.kind is StepKind.NORMALIZE and cast("float", resolved["reference"]) <= 0.0:
            raise StepValidationError("normalize: reference > 0 olmalı")
        if self.kind is StepKind.PHASE_UNWRAP:
            unit = cast("str", resolved["unit"])
            discontinuity = cast("float", resolved["discontinuity"])
            period = PHASE_UNWRAP_PERIOD[unit]
            if discontinuity <= 0.0:
                raise StepValidationError("phase_unwrap: discontinuity > 0 olmalı")
            if discontinuity >= period:
                raise StepValidationError(
                    f"phase_unwrap: discontinuity < tam periyot ({period:.6g} {unit}) olmalı; "
                    f"verilen {discontinuity:.6g}"
                )
        # frozen dataclass: normalize edilmiş parametreleri geri yaz.
        object.__setattr__(self, "parameters", resolved)

    # -- tekrar üretilebilirlik ------------------------------------

    def signature(self) -> str:
        """Aynı girdi her zaman aynı stabil imzayı verir (önbellek anahtarı)."""
        ordered = [
            [name, self.parameters[name]]
            for name in (spec.name for spec in PARAMETER_SPECS[self.kind])
        ]
        payload = [self.kind.value, self.input_channel_id, ordered]
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    # -- serileştirme --------------------------------------------

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "input_channel_id": self.input_channel_id,
            "parameters": dict(self.parameters),
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: object) -> ProcessingStep:
        if not isinstance(data, dict):
            raise StepValidationError("İşlem adımı bir nesne olmalı")
        record = cast("dict[str, object]", data)
        try:
            kind = StepKind(str(record["kind"]))
        except (KeyError, ValueError) as exc:
            raise StepValidationError(f"Tanınmayan işlem türü: {record.get('kind')!r}") from exc
        channel = record.get("input_channel_id")
        if not isinstance(channel, str):
            raise StepValidationError("input_channel_id metin olmalı")
        raw_params = record.get("parameters", {})
        if not isinstance(raw_params, dict):
            raise StepValidationError("parameters bir nesne olmalı")
        return cls(
            kind=kind,
            input_channel_id=channel,
            parameters={str(k): v for k, v in cast("dict[str, object]", raw_params).items()},
            enabled=bool(record.get("enabled", True)),
        )

    # -- kolaylık -----------------------------------------------

    @classmethod
    def default(cls, kind: StepKind, input_channel_id: str) -> ProcessingStep:
        """`kind` için tüm parametreleri varsayılanla dolu bir adım."""
        params = {spec.name: spec.default for spec in PARAMETER_SPECS[kind]}
        return cls(kind=kind, input_channel_id=input_channel_id, parameters=params)

    def with_parameters(self, **changes: object) -> ProcessingStep:
        """Bazı parametreleri değiştirilmiş yeni bir adım döndürür."""
        merged = {**self.parameters, **changes}
        return ProcessingStep(
            kind=self.kind,
            input_channel_id=self.input_channel_id,
            parameters=merged,
            enabled=self.enabled,
        )

    def with_input(self, channel_id: str) -> ProcessingStep:
        return ProcessingStep(
            kind=self.kind,
            input_channel_id=channel_id,
            parameters=dict(self.parameters),
            enabled=self.enabled,
        )
