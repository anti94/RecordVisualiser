"""Kayıt durumu kartı — `F5-032`.

Kabul: **aktif dosya, geçen süre ve kayıt durumu görünür.**

`LiveStatusCard` (`F5-020`) ile aynı ilke: kart hiçbir şeyi kendi
hesaplamaz, yalnız biçimlendirir. Değerler üretildikleri yerden gelir —
dosya ve süre `RotatingRecorder`'dan (`F5-031`), durum
`RecordingSession`'dan (`F5-030`). Ekranda görünen ile diske yazılan
ayrışabilseydi kullanıcı "kayıt sürüyor" yazısına bakıp kayıt
alamayabilirdi.

Durum metni **durumdan** üretilir, ayrı bir bayraktan değil; `F5-030`'un
"başarılı kayıt mesajı verilmez" kuralı burada da geçerlidir: `FAILED`
durumunda kartta hata yazar, kayıt sayısı ne olursa olsun.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtWidgets import QFormLayout, QGroupBox, QLabel, QWidget

from sonar_analyzer.recording.session import RecordingState

CARD_OBJECT_NAME = "card_recording_status"
CARD_TITLE = "Kayit Durumu"
EMPTY_VALUE = "—"

#: (alan adi, etiket) — yukaridan asagiya sabit sira.
FIELD_SPECS: tuple[tuple[str, str], ...] = (
    ("state", "Durum"),
    ("file", "Aktif dosya"),
    ("elapsed", "Gecen sure"),
    ("records", "Kayit sayisi"),
    ("dropped", "Dusen kayit"),
    ("files", "Dosya sayisi"),
)

#: Durum → ekranda görünecek metin. Bilinmeyen bir durum sessizce
#: "kayıt sürüyor" gibi görünmesin diye eşleme **açıkça** tanımlıdır.
STATE_LABELS: dict[RecordingState, str] = {
    RecordingState.IDLE: "Kayit yok",
    RecordingState.RECORDING: "Kayit suruyor",
    RecordingState.STOPPED: "Durduruldu",
    RecordingState.FAILED: "HATA",
}


@dataclass(frozen=True)
class RecordingStatus:
    """Karta verilecek anlık kayıt görüntüsü.

    `path` ve sayaçlar opsiyoneldir: kayıt hiç başlamadıysa `—` gösterilir,
    sıfır **gösterilmez** — "kayıt yok" ile "sıfır kayıt" farklıdır.
    """

    state: RecordingState = RecordingState.IDLE
    path: Path | None = None
    elapsed_ns: int | None = None
    record_count: int | None = None
    dropped_records: int | None = None
    file_count: int | None = None
    error: str | None = None


def format_elapsed(elapsed_ns: int) -> str:
    """Süreyi `s.ss` yerine `sa:dd:ss` olarak yazar — uzun kayıtlar okunur kalsın."""
    if elapsed_ns < 0:
        raise ValueError(f"elapsed_ns negatif olamaz: {elapsed_ns}")
    total_seconds = elapsed_ns // 1_000_000_000
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


class RecordingStatusCard(QGroupBox):
    """Kaydın durumunu, dosyasını ve süresini gösteren kart."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(CARD_TITLE, parent)
        self.setObjectName(CARD_OBJECT_NAME)

        layout = QFormLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        self._values: dict[str, QLabel] = {}
        for name, label_text in FIELD_SPECS:
            value = QLabel(EMPTY_VALUE, self)
            value.setObjectName(f"recording_status_{name}")
            self._values[name] = value
            layout.addRow(QLabel(label_text, self), value)

    def field_names(self) -> list[str]:
        return [name for name, _ in FIELD_SPECS]

    def field_value(self, name: str) -> str:
        """Alanın gösterilen metni — testler ve kabul için."""
        try:
            return self._values[name].text()
        except KeyError as exc:
            raise KeyError(f"Tanimsiz kayit durum alani: {name}") from exc

    def clear(self) -> None:
        for label in self._values.values():
            label.setText(EMPTY_VALUE)

    def update_status(self, status: RecordingStatus) -> None:
        """Kartı verilen görüntüden tazeler; hiçbir değeri kendi türetmez."""
        self._set("state", self._state_text(status))
        self._set("file", EMPTY_VALUE if status.path is None else status.path.name)
        self._set(
            "elapsed",
            EMPTY_VALUE if status.elapsed_ns is None else format_elapsed(status.elapsed_ns),
        )
        self._set("records", _count(status.record_count))
        self._set("dropped", _count(status.dropped_records))
        self._set("files", _count(status.file_count))

    def _set(self, name: str, text: str) -> None:
        self._values[name].setText(text or EMPTY_VALUE)

    def _state_text(self, status: RecordingStatus) -> str:
        label = STATE_LABELS.get(status.state, str(status.state.value))
        if status.state is RecordingState.FAILED and status.error:
            return f"{label}: {status.error}"
        return label


def _count(value: int | None) -> str:
    return EMPTY_VALUE if value is None else str(value)
