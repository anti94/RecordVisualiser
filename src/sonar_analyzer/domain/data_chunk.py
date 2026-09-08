"""Zaman serisi veri parçası ve kalite bayrakları — `F1-012`.

`DataChunk`, bir kanalın belirli bir aralıktaki örneklerini taşır. Zaman ve değer
dizileri **aynı uzunlukta** olmak zorundadır; tutarsızlık kurucuda yakalanır,
çünkü bu hatanın grafik çizim anında ortaya çıkması teşhisi imkânsızlaştırır.

Zaman birimi kanoniktir: `int64` UTC nanosaniye (`docs/adr/ADR-003-time-base.md`).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntFlag
from typing import Any

import numpy as np
from numpy.typing import NDArray


class Quality(IntFlag):
    """Örnek başına kalite bayrakları. Birden fazlası aynı anda geçerli olabilir."""

    OK = 0
    GAP_BEFORE = 1  # bu ornekten once kayip periyot var
    CRC_ERROR = 2  # kaydin butunluk kontrolu basarisiz
    JITTER = 4  # zaman damgasi nominal izgaradan sapti
    CLOCK_UNLOCKED = 8  # saat kaynagi disiplinsiz
    SUSPECT = 16  # deger fiziksel olarak siradisi


@dataclass(frozen=True)
class DataChunk:
    """Tek kanalın zaman/değer dizisi."""

    channel_id: str
    timestamps_ns: NDArray[np.int64]
    values: NDArray[Any]
    quality: NDArray[np.uint8] | None = None

    def __post_init__(self) -> None:
        if not self.channel_id.strip():
            raise ValueError("Kanal kimligi bos olamaz")

        if self.timestamps_ns.ndim != 1:
            raise ValueError(
                f"{self.channel_id}: zaman dizisi tek boyutlu olmali, "
                f"verilen boyut {self.timestamps_ns.ndim}"
            )
        if self.values.ndim != 1:
            raise ValueError(
                f"{self.channel_id}: deger dizisi tek boyutlu olmali, "
                f"verilen boyut {self.values.ndim}"
            )

        if self.timestamps_ns.shape[0] != self.values.shape[0]:
            raise ValueError(
                f"{self.channel_id}: zaman ve deger uzunluklari farkli "
                f"({self.timestamps_ns.shape[0]} zaman, {self.values.shape[0]} deger)"
            )

        if self.timestamps_ns.dtype != np.int64:
            raise ValueError(
                f"{self.channel_id}: zaman dizisi int64 olmali, verilen {self.timestamps_ns.dtype}"
            )

        if self.quality is not None:
            if self.quality.ndim != 1:
                raise ValueError(f"{self.channel_id}: kalite dizisi tek boyutlu olmali")
            if self.quality.shape[0] != self.values.shape[0]:
                raise ValueError(
                    f"{self.channel_id}: kalite uzunlugu deger uzunlugundan farkli "
                    f"({self.quality.shape[0]} kalite, {self.values.shape[0]} deger)"
                )

    def __len__(self) -> int:
        return int(self.values.shape[0])

    @property
    def is_empty(self) -> bool:
        return len(self) == 0

    @property
    def start_ns(self) -> int | None:
        """İlk örneğin zamanı; parça boşsa `None`."""
        if self.is_empty:
            return None
        return int(self.timestamps_ns[0])

    @property
    def end_ns(self) -> int | None:
        """Son örneğin zamanı; parça boşsa `None`."""
        if self.is_empty:
            return None
        return int(self.timestamps_ns[-1])

    @property
    def is_monotonic(self) -> bool:
        """Zaman damgaları azalmıyor mu?"""
        if len(self) < 2:
            return True
        return bool(np.all(np.diff(self.timestamps_ns) >= 0))

    def has_flag(self, flag: Quality) -> bool:
        """Parçada verilen kalite bayrağını taşıyan örnek var mı?"""
        if self.quality is None or self.is_empty:
            return False
        return bool(np.any(self.quality & np.uint8(int(flag))))

    def flagged_indices(self, flag: Quality) -> NDArray[np.int64]:
        """Verilen bayrağı taşıyan örneklerin konumları."""
        if self.quality is None:
            return np.empty(0, dtype=np.int64)
        return np.flatnonzero(self.quality & np.uint8(int(flag))).astype(np.int64)

    @classmethod
    def empty(cls, channel_id: str, dtype: str = "float32") -> DataChunk:
        """Boş ama geçerli bir parça — sorgu sonucu boş olduğunda kullanılır."""
        return cls(
            channel_id=channel_id,
            timestamps_ns=np.empty(0, dtype=np.int64),
            values=np.empty(0, dtype=np.dtype(dtype)),
        )
