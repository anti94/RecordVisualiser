"""İşlem zinciri ve işaretler için undo/redo — `F4-079`.

`ViewHistory` (`F3-041`) görünüm değişikliklerini **komut** olarak tutar:
her değişiklik kendi `revert()`'ini taşır. Burada düzenlenen şey farklı
bir cins — `ProcessingChain` ve `AnnotationSet` **değişmez değerlerdir**
ve onlarca yoldan değişirler (adım ekle / sil / taşı / parametre değiştir,
işaret ekle / yeniden adlandır / notunu düzenle / sil). Her yol için ayrı
bir `revert` yazmak hem tekrar hem de hata kaynağı olurdu.

Bu yüzden geçmiş **anlık görüntü** tutar: her düzenlemeden sonra o anki
`(zincir, işaretler)` çifti yığına konur, geri alma önceki çifti aynen
geri yükler. Değerler değişmez olduğu için anlık görüntü ucuzdur ve
paylaşılan durum sızdırmaz.

İki kural davranışı belirler:

* **Aynı durum yığına girmez.** Kullanıcı bir parametreyi eski değerine
  geri yazarsa boş bir geri alma adımı oluşmaz.
* **Yeni düzenleme redo kuyruğunu siler.** Geri alıp sonra başka bir şey
  yapmak, ileri alınacak eski dalı geçersiz kılar.

Saf veri — Qt yok, `GUI olmadan` doğrulanır.
"""

from __future__ import annotations

from dataclasses import dataclass

from sonar_analyzer.domain.annotation import AnnotationSet
from sonar_analyzer.processing.chain import ProcessingChain

#: Yığında tutulacak en fazla anlık görüntü; eskiler düşer.
MAX_EDIT_HISTORY = 100


class EditHistoryError(ValueError):
    """Geçmiş yapılandırması geçersiz."""


@dataclass(frozen=True)
class EditSnapshot:
    """Düzenlenebilir oturum durumunun tamamı, tek bir an."""

    chain: ProcessingChain
    annotations: AnnotationSet
    #: Bu duruma **götüren** düzenlemenin adı ("Adım taşındı" gibi).
    label: str = ""

    def same_state_as(self, other: EditSnapshot) -> bool:
        """Etiket dışında aynı durumu mu gösteriyor."""
        return (
            self.chain.to_list() == other.chain.to_list() and self.annotations == other.annotations
        )


class EditHistory:
    """`(zincir, işaretler)` anlık görüntülerinin doğrusal undo/redo yığını."""

    def __init__(self, initial: EditSnapshot, *, max_history: int = MAX_EDIT_HISTORY) -> None:
        if max_history < 1:
            raise EditHistoryError(f"Geçmiş sınırı en az 1 olmalı: {max_history}")
        self._max = max_history
        #: Her zaman en az bir öğe taşır; son öğe **şu anki** durumdur.
        self._states: list[EditSnapshot] = [initial]
        self._index = 0

    # -- sorgular ----------------------------------------------------------

    @property
    def current(self) -> EditSnapshot:
        return self._states[self._index]

    @property
    def can_undo(self) -> bool:
        return self._index > 0

    @property
    def can_redo(self) -> bool:
        return self._index < len(self._states) - 1

    @property
    def undo_label(self) -> str | None:
        """Geri alınacak düzenlemenin adı; geri alınacak bir şey yoksa `None`."""
        return self.current.label if self.can_undo else None

    @property
    def redo_label(self) -> str | None:
        """İleri alınacak düzenlemenin adı; yoksa `None`."""
        return self._states[self._index + 1].label if self.can_redo else None

    def __len__(self) -> int:
        """Yığındaki anlık görüntü sayısı (başlangıç dahil)."""
        return len(self._states)

    # -- duzenleme ---------------------------------------------------------

    def record(self, snapshot: EditSnapshot) -> bool:
        """Yeni durumu yığına koyar; durum değişmediyse `False` döner.

        Geri alınmış bir daldayken kayıt yapmak, ileri alınacak eski dalı
        **siler** — o dal artık ulaşılamaz bir geçmiştir.
        """
        if snapshot.same_state_as(self.current):
            return False
        del self._states[self._index + 1 :]
        self._states.append(snapshot)
        if len(self._states) > self._max:
            del self._states[0]
        self._index = len(self._states) - 1
        return True

    def undo(self) -> EditSnapshot | None:
        """Bir adım geri gider ve o durumu döndürür; yoksa `None`."""
        if not self.can_undo:
            return None
        self._index -= 1
        return self.current

    def redo(self) -> EditSnapshot | None:
        """Bir adım ileri gider ve o durumu döndürür; yoksa `None`."""
        if not self.can_redo:
            return None
        self._index += 1
        return self.current

    def reset(self, initial: EditSnapshot) -> None:
        """Geçmişi tek bir başlangıç durumuna indirir (yeni kayıt açılınca)."""
        self._states = [initial]
        self._index = 0
