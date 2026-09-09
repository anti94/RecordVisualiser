"""Tekli ve çoklu `.bin` dosya seçicisi — `F3-001`.

Seçici **yükleme yapmaz**: yalnız kullanıcının seçtiği yolları toplar ve bir
*yükleme talebi* üretir (`FileOpenController.load_requested`). Gerçek okuma,
worker altyapısı geldiğinde (`F3-002`) bu talebe bağlanır; böylece seçim
mantığı Qt diyaloğundan ve okuyucudan ayrı test edilebilir.

İptal davranışı sözleşmedir (kabul kriteri): diyalog iptal edilirse hiçbir
sinyal yayılmaz ve **mevcut oturum korunur** — açık kayıt, paneller ve seçili
kanal olduğu gibi kalır. Bu yüzden iptal "boş liste ile talep" değildir; hiç
talep değildir.

Diyaloğu açan çağrı `_dialog` seçiciyle dışarıdan verilebilir; testler yerel
dosya diyaloğunu açmak zorunda kalmaz (offscreen Qt'de yerel diyalog
sürücülenemez).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QFileDialog, QWidget

#: `.bin` uzantısı sözleşme değil **alışkanlıktır**; kullanıcı başka uzantılı
#: bir kayıt seçebilsin diye "tüm dosyalar" süzgeci de sunulur.
FILE_FILTER = "SONAR kaydi (*.bin);;Tum dosyalar (*)"
DIALOG_TITLE = "Kayit dosyasi ac"

#: Seçiciyi çağıran taraf yerine geçebilecek imza: (üst pencere, başlangıç
#: klasörü) -> seçilen yollar. Boş dizi "iptal" demektir.
#: `Optional[...]` bilinçli: tip takma adı çalışma anında değerlendirildiği için
#: Python 3.9'da `QWidget | None` yazımı `TypeError` veriyor (bkz. `F2-011`).
DialogCallable = Callable[[Optional[QWidget], str], Sequence[str]]


def _default_dialog(parent: QWidget | None, start_directory: str) -> Sequence[str]:
    """Qt'nin çoklu seçim yapabilen dosya diyaloğu."""
    paths, _selected_filter = QFileDialog.getOpenFileNames(
        parent, DIALOG_TITLE, start_directory, FILE_FILTER
    )
    return paths


class FileOpenController(QObject):
    """`action_open` eylemini dosya yükleme talebine çeviren seçici.

    Tek dosya da çoklu seçim de aynı yolu kullanır: sinyal her zaman bir
    **liste** taşır, böylece çağıran taraf iki ayrı akış yazmak zorunda
    kalmaz (`F2-036`'daki çoklu kayıt desteğiyle aynı biçim).
    """

    #: Kullanıcı en az bir dosya seçtiğinde yayılır; iptalde yayılmaz.
    load_requested = Signal(list)

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        dialog: DialogCallable | None = None,
    ) -> None:
        super().__init__(parent)
        # None saklanir ve `_default_dialog` cagri aninda cozulur: boylece
        # modul global'ini degistiren bir yama (testlerdeki guvenlik agi,
        # bkz. tests/conftest.py) denetleyici kurulduktan SONRA da etkili
        # olur. Kurucuda baglanirsa yama sirasi sessizce onemli hale gelir.
        self._dialog: DialogCallable | None = dialog
        self._last_directory = ""

    @property
    def last_directory(self) -> str:
        """Son başarılı seçimin klasörü; `F3-008` bunu ayarlara taşıyacak."""
        return self._last_directory

    def set_last_directory(self, directory: str) -> None:
        self._last_directory = directory

    def request_open(self, parent: QWidget | None = None) -> tuple[Path, ...]:
        """Diyaloğu açar; seçim varsa talebi yayar ve seçilen yolları döner.

        İptalde boş demet döner ve **hiçbir sinyal yayılmaz** — çağıran
        tarafın mevcut oturumu değiştirmesi için bir neden oluşmaz.
        Yinelenen seçimler (aynı dosya iki kez) sıra korunarak teklenir.
        """
        dialog = self._dialog or _default_dialog
        selected = dialog(parent, self._last_directory)
        if not selected:
            return ()

        unique: list[Path] = []
        seen: set[Path] = set()
        for raw in selected:
            path = Path(raw)
            if path not in seen:
                seen.add(path)
                unique.append(path)

        self._last_directory = str(unique[0].parent)
        self.load_requested.emit([str(path) for path in unique])
        return tuple(unique)
