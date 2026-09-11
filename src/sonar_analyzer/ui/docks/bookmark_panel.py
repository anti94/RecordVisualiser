"""Bookmark / annotation paneli — `F4-075`.

Alt panelin üçüncü sekmesi. Kullanıcı işaretlerini (`F4-074`) listeler ve
üç eylemi sunar: **ekle**, **düzenle**, **sil**. Bir satır seçildiğinde
`selected` yayılır; pencere o zamana gider ve işaret grafikte görünür.

Panel hiçbir şey saklamaz ve hiçbir şeye karar vermez: yalnız görünen
listeyi çizer ve niyet yayar. İşaretlerin sahibi `MainWindow`'dur; hangi
zamanın kullanılacağı (imleç mi seçili aralık mı) da orada belirlenir.

Düzenleme **satır içidir**: kullanıcı bir satır seçer, etiket/not
alanlarını değiştirir ve `Güncelle`'ye basar. Modal pencere yok; böylece
akış klavyeyle tamamlanabilir ve otomatik sınanabilir.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from sonar_analyzer.domain.annotation import Annotation, AnnotationSet
from sonar_analyzer.domain.time_range import NS_PER_SECOND

BOOKMARKS_TAB_TITLE = "Bookmarks"
COLUMNS: tuple[str, ...] = ("Zaman", "Süre", "Etiket", "Not")
EMPTY_HINT = "Henüz işaret yok. Grafikte bir an ya da aralık seçip ekleyin."
#: Aralık olmayan işaretin süre sütununda görünen metin.
POINT_DURATION = "—"


def format_offset(offset_ns: int) -> str:
    """Kayıt başlangıcına göre saniye cinsinden okunur zaman."""
    return f"{offset_ns / NS_PER_SECOND:.3f} s"


def format_duration(duration_ns: int) -> str:
    return POINT_DURATION if duration_ns == 0 else f"{duration_ns / NS_PER_SECOND:.3f} s"


class BookmarkPanel(QWidget):
    """İşaret listesi + ekle/güncelle/sil denetimleri."""

    #: Yeni işaret istendi — `(etiket, not)`.
    add_requested = Signal(str, str)
    #: Seçili işaret güncellensin — `(id, etiket, not)`.
    edit_requested = Signal(str, str, str)
    #: Seçili işaret silinsin — `(id,)`.
    remove_requested = Signal(str)
    #: Bir satır seçildi — `(id,)`; seçim kalkarsa boş metin.
    selected = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("panel_bookmarks")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        self.table = QTableWidget(0, len(COLUMNS), self)
        self.table.setObjectName("table_bookmarks")
        self.table.setHorizontalHeaderLabels(list(COLUMNS))
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(len(COLUMNS) - 1, QHeaderView.ResizeMode.Stretch)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.table, 1)

        self.hint = QLabel(EMPTY_HINT, self)
        self.hint.setObjectName("label_bookmark_hint")
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)

        row = QHBoxLayout()
        self.label_input = QLineEdit(self)
        self.label_input.setObjectName("input_bookmark_label")
        self.label_input.setPlaceholderText("Etiket")
        self.label_input.textChanged.connect(self._refresh_buttons)
        self.text_input = QLineEdit(self)
        self.text_input.setObjectName("input_bookmark_text")
        self.text_input.setPlaceholderText("Not (isteğe bağlı)")
        row.addWidget(self.label_input, 1)
        row.addWidget(self.text_input, 2)
        layout.addLayout(row)

        buttons = QHBoxLayout()
        self.add_button = QPushButton("Ekle", self)
        self.add_button.setObjectName("button_bookmark_add")
        self.add_button.clicked.connect(self._on_add)
        self.edit_button = QPushButton("Güncelle", self)
        self.edit_button.setObjectName("button_bookmark_edit")
        self.edit_button.clicked.connect(self._on_edit)
        self.remove_button = QPushButton("Sil", self)
        self.remove_button.setObjectName("button_bookmark_remove")
        self.remove_button.clicked.connect(self._on_remove)
        for button in (self.add_button, self.edit_button, self.remove_button):
            buttons.addWidget(button)
        layout.addLayout(buttons)

        self._annotations = AnnotationSet()
        self._start_ns = 0
        self._suppress_selection = False
        self._refresh_buttons()

    # -- goruntuleme -------------------------------------------------------

    def set_annotations(self, annotations: AnnotationSet, start_ns: int = 0) -> None:
        """Listeyi yeniden çizer; olabiliyorsa seçili satırı korur."""
        previous = self.selected_id()
        self._annotations = annotations
        self._start_ns = start_ns

        self._suppress_selection = True
        try:
            self.table.setRowCount(len(annotations))
            for row, item in enumerate(annotations):
                self._fill_row(row, item)
        finally:
            self._suppress_selection = False

        self.hint.setVisible(len(annotations) == 0)
        if previous and previous in annotations:
            self.select(previous)
        else:
            self._refresh_buttons()

    def _fill_row(self, row: int, annotation: Annotation) -> None:
        values = (
            format_offset(annotation.start_ns - self._start_ns),
            format_duration(annotation.duration_ns),
            annotation.label,
            annotation.text.replace("\n", " ⏎ "),
        )
        for column, value in enumerate(values):
            cell = QTableWidgetItem(value)
            cell.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            if column == 0:
                cell.setData(Qt.ItemDataRole.UserRole, annotation.id)
            self.table.setItem(row, column, cell)

    # -- secim -------------------------------------------------------------

    def selected_id(self) -> str:
        """Seçili işaretin kimliği; seçim yoksa boş metin."""
        row = self.table.currentRow()
        if row < 0:
            return ""
        cell = self.table.item(row, 0)
        if cell is None:
            return ""
        value = cell.data(Qt.ItemDataRole.UserRole)
        return value if isinstance(value, str) else ""

    def select(self, annotation_id: str) -> bool:
        """Kimliği verilen satırı seçer; bulunamazsa `False`."""
        for row in range(self.table.rowCount()):
            cell = self.table.item(row, 0)
            if cell is not None and cell.data(Qt.ItemDataRole.UserRole) == annotation_id:
                self.table.selectRow(row)
                return True
        return False

    def clear_selection(self) -> None:
        """Seçimi kaldırır ve **bir kez** boş seçim yayar.

        `clearSelection()` tek başına, geçerli satır hâlâ dururken sinyal
        yayar; o an `selected_id()` eski kimliği verir ve pencere o zamana
        giderdi. Bu yüzden iki adım susturulup sonuç tek seferde bildirilir.
        """
        self._suppress_selection = True
        try:
            self.table.clearSelection()
            self.table.setCurrentCell(-1, -1)
        finally:
            self._suppress_selection = False
        self._refresh_buttons()
        self.selected.emit("")

    def row_count(self) -> int:
        return self.table.rowCount()

    def row_texts(self, row: int) -> list[str]:
        """Bir satırın görünen hücreleri — testler için."""
        texts: list[str] = []
        for column in range(self.table.columnCount()):
            cell = self.table.item(row, column)
            texts.append("" if cell is None else cell.text())
        return texts

    def _on_selection_changed(self) -> None:
        if self._suppress_selection:
            return
        annotation_id = self.selected_id()
        self._load_fields(annotation_id)
        self._refresh_buttons()
        self.selected.emit(annotation_id)

    def _load_fields(self, annotation_id: str) -> None:
        """Seçilen işaretin etiketi/notu düzenleme alanlarına gelir."""
        annotation = self._annotations.get(annotation_id) if annotation_id else None
        if annotation is None:
            return
        self.label_input.setText(annotation.label)
        self.text_input.setText(annotation.text)
        self._refresh_buttons()

    def _refresh_buttons(self) -> None:
        """Etiketsiz işaret eklenemez; seçim yokken düzenleme/silme kapalı."""
        has_selection = bool(self.selected_id())
        has_label = bool(self.label_input.text().strip())
        self.add_button.setEnabled(has_label)
        self.edit_button.setEnabled(has_selection and has_label)
        self.remove_button.setEnabled(has_selection)

    # -- eylemler ----------------------------------------------------------

    def _on_add(self) -> None:
        label = self.label_input.text().strip()
        if label:
            self.add_requested.emit(label, self.text_input.text())

    def _on_edit(self) -> None:
        annotation_id = self.selected_id()
        label = self.label_input.text().strip()
        if annotation_id and label:
            self.edit_requested.emit(annotation_id, label, self.text_input.text())

    def _on_remove(self) -> None:
        annotation_id = self.selected_id()
        if annotation_id:
            self.remove_requested.emit(annotation_id)
