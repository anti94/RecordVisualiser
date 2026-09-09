"""Yükleme hatasının kullanıcıya gösterimi — `F3-006`.

Bildirim bir **çağrı** olarak ayrıldı (`LoadErrorNotifier`): öntanımlısı Qt
uyarı kutusu, ama pencere onu dışarıdan alabiliyor. İki nedeni var:

1. Modal kutu testte kullanıcı girdisi bekler ve paketi süresiz kilitler
   (`F3-001`'de dosya diyaloğuyla tam olarak bu yaşandı). Test bir kaydedici
   koyar; `tests/conftest.py` ayrıca öntanımlıyı yamalayarak ağ görevi görür.
2. İleride toplu/sessiz modda (rapor üretimi, betikle açma) kutu yerine
   log'a düşmek gerekebilir.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QMessageBox, QWidget

from sonar_analyzer.application.load_errors import LoadErrorMessage

#: (üst pencere, mesaj) -> None
LoadErrorNotifier = Callable[["QWidget | None", LoadErrorMessage], None]


def message_box_notifier(parent: QWidget | None, message: LoadErrorMessage) -> None:
    """Kullanıcıya uyarı kutusu gösterir; teknik ayrıntı 'Ayrıntılar' altında."""
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle(message.title)
    box.setText(message.user_text)
    box.setDetailedText(message.technical_text)
    box.exec()
