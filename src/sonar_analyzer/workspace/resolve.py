"""Workspace kaynak dosyalarını çözümleme — `F3-070`.

Bir workspace, kaydedildiği andaki `.bin` yollarını taşır. Yeniden
açılışta bu dosyalardan bazıları taşınmış / silinmiş olabilir. Bu
modül yalnız **hangileri var, hangileri yok** ayrımını yapar — saf
Python, dosya sistemi enjekte edilir, `GUI olmadan` doğrulanır.

Kabul (`F3-070`): eksik dosya bildirilir; sessizce atlanmaz.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

#: `exists(path) -> bool` — dosya sisteminden bağımsız test için.
PathExists = Callable[[str], bool]


@dataclass(frozen=True)
class SourceResolution:
    """Workspace kaynak yollarının çözümü — sıralı."""

    found: list[str]
    missing: list[str]

    @property
    def has_missing(self) -> bool:
        return bool(self.missing)

    @property
    def all_present(self) -> bool:
        return not self.missing

    def summary(self) -> str:
        if not self.missing:
            return f"{len(self.found)} kaynak dosyanın tümü bulundu"
        return f"{len(self.missing)} kaynak dosya bulunamadı: " + ", ".join(self.missing)


def resolve_sources(paths: Sequence[str], *, exists: PathExists) -> SourceResolution:
    """`paths`'i var olan / olmayan diye ikiye ayırır (giriş sırası korunur)."""
    found: list[str] = []
    missing: list[str] = []
    for path in paths:
        (found if exists(path) else missing).append(path)
    return SourceResolution(found=found, missing=missing)
