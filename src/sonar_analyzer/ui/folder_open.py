"""Kayıt klasörü seçicisi — `F7-045`, `F7-051`.

Profil C kayıtları klasördür, dosya değil (`docs/format/profile-c.md` §2).
Bu seçici `Open Recording Folder` eylemini bir **yükleme talebine** çevirir;
yükleme yapmaz.

`file_open.FileOpenController` ile aynı sözleşmeyi izler ve bilerek ayrı
durur: dosya seçimi bozulmadan kalmalı. Profil A ve B kayıtları dosya
olarak açılmaya devam ediyor (`docs/format/profile-c.md` §8) ve tek bir
diyaloğu iki kipe zorlamak, ikisini de kötüleştirirdi.

İptal davranışı sözleşmedir: diyalog iptal edilirse **hiçbir sinyal
yayılmaz** ve mevcut oturum korunur. İptal "boş yol ile talep" değildir;
hiç talep değildir.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QFileDialog, QWidget

from sonar_analyzer.io.decoders.profile_c_folder import Stream

DIALOG_TITLE = "Kayit klasoru ac"

#: Seciciyi cagiran taraf yerine gecebilecek imza: (ust pencere, baslangic
#: klasoru) -> secilen yol. Bos dizge "iptal" demektir.
#: `Optional[...]` bilincli: tip takma adi calisma aninda degerlendirildigi
#: icin Python 3.9'da `QWidget | None` yazimi `TypeError` veriyor.
FolderDialogCallable = Callable[[Optional[QWidget], str], str]


def _default_dialog(parent: QWidget | None, start_directory: str) -> str:
    """Qt'nin klasör seçme diyaloğu."""
    return QFileDialog.getExistingDirectory(
        parent, DIALOG_TITLE, start_directory, QFileDialog.Option.ShowDirsOnly
    )


def looks_like_recording_folder(path: Path) -> bool:
    """Yol bir Profil C kayıt klasörüne benziyor mu.

    Tam doğrulama `discover()` işidir; bu yalnız **ucuz** bir ön elemedir:
    sürükle bırakta her bırakılan klasörü açmaya çalışmak, büyük bir
    ağaçta gereksiz tarama demektir.

    İki akımdan **biri** yeterlidir: yayın yapılmadan sadece dinlenen bir
    oturumda `Tx/` bulunmaz (§2.2).
    """
    if not path.is_dir():
        return False
    return any((path / stream.value).is_dir() for stream in Stream)


class FolderOpenController(QObject):
    """`action_open_folder` eylemini kayıt klasörü yükleme talebine çevirir."""

    #: Kullanici bir klasor sectiginde yayilir; iptalde yayilmaz.
    load_requested = Signal(Path)

    #: Secilen yol bir kayit klasorune benzemiyorsa yayilir. Sessizce
    #: yutmak, kullanicinin dogru klasoru sectigini sanmasina yol acardi.
    rejected = Signal(str)

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        dialog: FolderDialogCallable | None = None,
        start_directory: str = "",
    ) -> None:
        super().__init__(parent)
        self._dialog = dialog or _default_dialog
        self._start_directory = start_directory

    @property
    def start_directory(self) -> str:
        return self._start_directory

    def set_start_directory(self, value: str) -> None:
        """Bir sonraki diyaloğun açılacağı klasör."""
        self._start_directory = value

    def request(self, parent: QWidget | None = None) -> Path | None:
        """Diyaloğu açar ve seçilen klasörü döndürür.

        İptalde `None` döner ve hiçbir sinyal yayılmaz. Seçilen yol bir
        kayıt klasörüne benzemiyorsa `rejected` yayılır ve yine `None`
        dönülür — yanlış klasörle açma denemesi, kullanıcıya anlamsız bir
        çözümleme hatası gösterirdi.
        """
        raw = self._dialog(parent, self._start_directory)
        if not raw:
            return None

        path = Path(raw)
        if not looks_like_recording_folder(path):
            self.rejected.emit(
                f"{path} bir kayit klasoru gibi gorunmuyor: altinda Tx/ ya da Rx/ yok"
            )
            return None

        self._start_directory = str(path.parent)
        self.load_requested.emit(path)
        return path

    def accept_dropped(self, path: Path) -> bool:
        """Sürükle bırakla gelen bir yolu kabul eder — `F7-051`.

        Dosya bırakma davranışı bozulmaz: bu yöntem yalnız **klasör**
        kabul eder ve dosya bırakıldığında `False` döner. Çağıran taraf
        o durumda dosya yoluna devam eder.
        """
        if not looks_like_recording_folder(path):
            return False
        self._start_directory = str(path.parent)
        self.load_requested.emit(path)
        return True
