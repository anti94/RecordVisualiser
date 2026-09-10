"""Görünüm ayarları için undo/redo yığını — `F3-041`.

Renk, eksen aralığı gibi **geri alınabilir görünüm değişiklikleri** bir
komut olarak (`ViewCommand`) sarılır: `apply()` uygular, `revert()` eski
duruma döndürür. `ViewHistory.push()` komutu çalıştırır ve yığına koyar;
`undo()`/`redo()` ileri geri gezinir.

Yalnız görünüm (sunum) durumu içindir — veri veya repository durumu bu
yığından etkilenmez.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

#: Yığında tutulacak en fazla komut; eski komutlar düşer.
MAX_HISTORY = 100


@dataclass(frozen=True)
class ViewCommand:
    """Geri alınabilir tek bir görünüm değişikliği.

    `label` kullanıcıya gösterilebilir (örn. "Renk değişikliği"). `apply`
    ve `revert` yan etkili, argümansız çağrılabilirlerdir.
    """

    label: str
    apply: Callable[[], None]
    revert: Callable[[], None]


class ViewHistory:
    """Görünüm komutlarının doğrusal undo/redo geçmişi."""

    def __init__(self, max_history: int = MAX_HISTORY) -> None:
        self._max = max(1, max_history)
        self._undo: list[ViewCommand] = []
        self._redo: list[ViewCommand] = []

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    @property
    def undo_label(self) -> str | None:
        return self._undo[-1].label if self._undo else None

    @property
    def redo_label(self) -> str | None:
        return self._redo[-1].label if self._redo else None

    def push(self, command: ViewCommand) -> None:
        """Komutu **çalıştırır** ve yığına ekler; redo geçmişini temizler."""
        command.apply()
        self._undo.append(command)
        del self._redo[:]
        if len(self._undo) > self._max:
            del self._undo[0]

    def undo(self) -> bool:
        """Son komutu geri alır; yapılacak bir şey yoksa `False`."""
        if not self._undo:
            return False
        command = self._undo.pop()
        command.revert()
        self._redo.append(command)
        return True

    def redo(self) -> bool:
        """Geri alınan son komutu yeniden uygular; yoksa `False`."""
        if not self._redo:
            return False
        command = self._redo.pop()
        command.apply()
        self._undo.append(command)
        return True

    def clear(self) -> None:
        del self._undo[:]
        del self._redo[:]
