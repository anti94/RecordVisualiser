"""Annotation ve bookmark modeli — `F4-074`.

Kullanıcı bir kayıtta iki tür işaret bırakır:

* **bookmark** — tek bir zaman noktası ("burada TX başladı"),
* **annotation** — bir zaman aralığı ("bu 3 saniyede gürültü var").

İkisi aynı modeldir; fark yalnız `end_ns`'in olup olmamasıdır. Böylece
bir bookmark'ı aralığa genişletmek ya da bir aralığı noktaya daraltmak
veri kaybı olmadan yapılabilir ve iki ayrı liste tutmak gerekmez.

Her işaret üç şey taşır ve üçü de **kayıpsız** saklanır:

* **zaman ya da aralık** — kanonik `int64` UTC ns (ADR-003); aralık
  `[start_ns, end_ns)` yarı-açıktır, `TimeRange` ile aynı sözleşme.
* **etiket** — listede ve grafikte görünen kısa ad; boş olamaz.
* **metin** — serbest not; boş olabilir, satır sonu ve unicode korunur.

Kimlik kullanıcıya aittir: etiketi ya da metni düzenlemek `id`'yi
değiştirmez, çünkü aynı işaretin düzenlenmiş hâlidir. Bu yüzden kimlik
içerikten türetilmez (`F4-068`'in tersine — orada kimlik tarifi
tanımlıyordu, burada kimlik bir **nesneyi** tanımlıyor).

Saf veri — Qt yok, `GUI olmadan` doğrulanır. Kullanıcı arayüzü `F4-075`,
çalışma alanına yazılması `F4-076`.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from dataclasses import dataclass, replace
from enum import Enum
from typing import cast

from sonar_analyzer.domain.time_range import TimeRange

#: Şema sürümü; `to_dict()` çıktısına yazılır (göç için).
ANNOTATION_SCHEMA_VERSION = 1

#: Etiket tek satırdır ve listede sığmalıdır.
MAX_LABEL_LENGTH = 200
#: Serbest not; makul bir üst sınır, aşırı girdiyi reddeder.
MAX_TEXT_LENGTH = 10_000


class AnnotationError(ValueError):
    """İşaret geçersiz (boş etiket, ters aralık, bozuk kayıt vb.)."""


class AnnotationKind(str, Enum):
    """İşaretin bir noktayı mı yoksa bir aralığı mı gösterdiği."""

    POINT = "point"
    RANGE = "range"


def new_annotation_id() -> str:
    """Yeni bir işaret kimliği; içerikten **bağımsızdır**."""
    return uuid.uuid4().hex


@dataclass(frozen=True)
class Annotation:
    """Bir zaman noktası ya da aralığı üzerindeki kullanıcı işareti."""

    id: str
    label: str
    start_ns: int
    end_ns: int | None = None
    text: str = ""
    #: İşaret bir kanala bağlıysa kimliği; kayıt geneli ise `None`.
    channel_id: str | None = None

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise AnnotationError("İşaret kimliği boş olamaz")
        if not self.label.strip():
            raise AnnotationError(f"{self.id}: işaret etiketi boş olamaz")
        if len(self.label) > MAX_LABEL_LENGTH:
            raise AnnotationError(
                f"{self.id}: etiket en fazla {MAX_LABEL_LENGTH} karakter olabilir, "
                f"verilen {len(self.label)}"
            )
        if len(self.text) > MAX_TEXT_LENGTH:
            raise AnnotationError(
                f"{self.id}: metin en fazla {MAX_TEXT_LENGTH} karakter olabilir, "
                f"verilen {len(self.text)}"
            )
        if isinstance(self.start_ns, bool) or not isinstance(cast("object", self.start_ns), int):
            raise AnnotationError(f"{self.id}: başlangıç zamanı tam sayı ns olmalı")
        if self.end_ns is not None:
            if isinstance(self.end_ns, bool) or not isinstance(cast("object", self.end_ns), int):
                raise AnnotationError(f"{self.id}: bitiş zamanı tam sayı ns olmalı")
            if self.end_ns <= self.start_ns:
                # Sıfır uzunluklu "aralık" bir noktadır; sessizce noktaya
                # çevirmek kullanıcının yanlış girdisini gizlerdi.
                raise AnnotationError(
                    f"{self.id}: aralık bitişi ({self.end_ns}) başlangıçtan "
                    f"({self.start_ns}) büyük olmalı; nokta için `end_ns=None` verin"
                )
        if self.channel_id is not None and not self.channel_id.strip():
            raise AnnotationError(f"{self.id}: kanal kimliği boş metin olamaz")

    # -- kurucular ---------------------------------------------------------

    @classmethod
    def bookmark(
        cls,
        label: str,
        timestamp_ns: int,
        *,
        text: str = "",
        channel_id: str | None = None,
        annotation_id: str | None = None,
    ) -> Annotation:
        """Tek bir zaman noktasını işaretler."""
        return cls(
            id=annotation_id or new_annotation_id(),
            label=label,
            start_ns=timestamp_ns,
            end_ns=None,
            text=text,
            channel_id=channel_id,
        )

    @classmethod
    def over(
        cls,
        label: str,
        span: TimeRange,
        *,
        text: str = "",
        channel_id: str | None = None,
        annotation_id: str | None = None,
    ) -> Annotation:
        """Bir zaman aralığını işaretler."""
        return cls(
            id=annotation_id or new_annotation_id(),
            label=label,
            start_ns=span.start_ns,
            end_ns=span.end_ns,
            text=text,
            channel_id=channel_id,
        )

    # -- sorgular ----------------------------------------------------------

    @property
    def kind(self) -> AnnotationKind:
        return AnnotationKind.POINT if self.end_ns is None else AnnotationKind.RANGE

    @property
    def is_point(self) -> bool:
        return self.end_ns is None

    @property
    def is_range(self) -> bool:
        return self.end_ns is not None

    @property
    def duration_ns(self) -> int:
        """Aralığın süresi; nokta için 0."""
        return 0 if self.end_ns is None else self.end_ns - self.start_ns

    @property
    def span(self) -> TimeRange:
        """İşaretin kapladığı aralık; nokta için sıfır uzunluklu."""
        return TimeRange(self.start_ns, self.start_ns if self.end_ns is None else self.end_ns)

    def contains(self, timestamp_ns: int) -> bool:
        """`timestamp_ns` işaretin içinde mi (aralık yarı-açık)."""
        if self.end_ns is None:
            return timestamp_ns == self.start_ns
        return self.start_ns <= timestamp_ns < self.end_ns

    def overlaps(self, span: TimeRange) -> bool:
        """İşaret verilen aralığa düşüyor mu."""
        if self.end_ns is None:
            return span.start_ns <= self.start_ns < span.end_ns
        return self.start_ns < span.end_ns and span.start_ns < self.end_ns

    # -- duzenleme ---------------------------------------------------------

    def renamed(self, label: str) -> Annotation:
        """Etiketi değişmiş kopya; `id` **korunur**."""
        return replace(self, label=label)

    def with_text(self, text: str) -> Annotation:
        """Notu değişmiş kopya; `id` korunur."""
        return replace(self, text=text)

    def moved_to(self, timestamp_ns: int) -> Annotation:
        """Noktaya çevirir ve taşır; `id` korunur."""
        return replace(self, start_ns=timestamp_ns, end_ns=None)

    def widened_to(self, span: TimeRange) -> Annotation:
        """Aralığa genişletir; `id` korunur."""
        return replace(self, start_ns=span.start_ns, end_ns=span.end_ns)

    # -- serilestirme ------------------------------------------------------

    def to_dict(self) -> dict[str, object]:
        """Çalışma alanına yazılabilir, kayıpsız gösterim."""
        return {
            "schema_version": ANNOTATION_SCHEMA_VERSION,
            "id": self.id,
            "label": self.label,
            "start_ns": self.start_ns,
            "end_ns": self.end_ns,
            "text": self.text,
            "channel_id": self.channel_id,
        }

    @classmethod
    def from_dict(cls, data: object) -> Annotation:
        """`to_dict()` çıktısını geri okur; bilinmeyen şema reddedilir."""
        if not isinstance(data, dict):
            raise AnnotationError("İşaret bir nesne olmalı")
        record = cast("dict[str, object]", data)
        version = record.get("schema_version", ANNOTATION_SCHEMA_VERSION)
        if version != ANNOTATION_SCHEMA_VERSION:
            raise AnnotationError(
                f"Desteklenmeyen işaret şeması: {version!r}; beklenen {ANNOTATION_SCHEMA_VERSION}"
            )
        return cls(
            id=_text(record, "id"),
            label=_text(record, "label"),
            start_ns=_integer(record, "start_ns"),
            end_ns=_optional_integer(record, "end_ns"),
            text=_text(record, "text", default=""),
            channel_id=_optional_text(record, "channel_id"),
        )


def _text(record: dict[str, object], key: str, *, default: str | None = None) -> str:
    value = record.get(key, default)
    if not isinstance(value, str):
        raise AnnotationError(f"{key} metin olmalı, verilen: {value!r}")
    return value


def _optional_text(record: dict[str, object], key: str) -> str | None:
    value = record.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise AnnotationError(f"{key} metin ya da boş olmalı, verilen: {value!r}")
    return value


def _integer(record: dict[str, object], key: str) -> int:
    value = record.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise AnnotationError(f"{key} tam sayı ns olmalı, verilen: {value!r}")
    return value


def _optional_integer(record: dict[str, object], key: str) -> int | None:
    value = record.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise AnnotationError(f"{key} tam sayı ns ya da boş olmalı, verilen: {value!r}")
    return value


@dataclass(frozen=True)
class AnnotationSet:
    """Bir kaydın işaretleri; **zamana göre sıralı**, kimliğe göre tekil.

    Değişmezdir: her düzenleme yeni bir küme döndürür. Sıra zaman,
    eşitlikte etiket ve kimliktir; böylece aynı içerik her zaman aynı
    listeyi verir ve çalışma alanı dosyası kararlı kalır.
    """

    items: tuple[Annotation, ...] = ()

    def __post_init__(self) -> None:
        seen: set[str] = set()
        for item in self.items:
            if item.id in seen:
                raise AnnotationError(f"Aynı işaret kimliği iki kez: {item.id!r}")
            seen.add(item.id)
        object.__setattr__(self, "items", tuple(sorted(self.items, key=_order_key)))

    def __len__(self) -> int:
        return len(self.items)

    def __iter__(self) -> Iterator[Annotation]:
        return iter(self.items)

    def __contains__(self, annotation_id: object) -> bool:
        return any(item.id == annotation_id for item in self.items)

    # -- sorgular ----------------------------------------------------------

    def get(self, annotation_id: str) -> Annotation | None:
        return next((item for item in self.items if item.id == annotation_id), None)

    def bookmarks(self) -> tuple[Annotation, ...]:
        """Yalnız nokta işaretleri."""
        return tuple(item for item in self.items if item.is_point)

    def ranges(self) -> tuple[Annotation, ...]:
        """Yalnız aralık işaretleri."""
        return tuple(item for item in self.items if item.is_range)

    def in_range(self, span: TimeRange) -> tuple[Annotation, ...]:
        """Verilen aralığa düşen işaretler, zamana göre sıralı."""
        return tuple(item for item in self.items if item.overlaps(span))

    def at(self, timestamp_ns: int) -> tuple[Annotation, ...]:
        """Verilen anı kapsayan işaretler."""
        return tuple(item for item in self.items if item.contains(timestamp_ns))

    def for_channel(self, channel_id: str | None) -> tuple[Annotation, ...]:
        """Bir kanalın işaretleri; `None` kayıt geneli olanları verir."""
        return tuple(item for item in self.items if item.channel_id == channel_id)

    # -- duzenleme ---------------------------------------------------------

    def added(self, annotation: Annotation) -> AnnotationSet:
        """İşareti ekler; aynı kimlik varsa **değiştirir** (düzenleme)."""
        kept = [item for item in self.items if item.id != annotation.id]
        return AnnotationSet((*kept, annotation))

    def removed(self, annotation_id: str) -> AnnotationSet:
        """Kimliği verilen işareti çıkarır; yoksa küme aynen döner."""
        return AnnotationSet(tuple(item for item in self.items if item.id != annotation_id))

    def cleared(self) -> AnnotationSet:
        return AnnotationSet()

    # -- serilestirme ------------------------------------------------------

    def to_list(self) -> list[dict[str, object]]:
        return [item.to_dict() for item in self.items]

    @classmethod
    def from_list(cls, data: object) -> AnnotationSet:
        if not isinstance(data, list):
            raise AnnotationError("İşaret listesi bir dizi olmalı")
        return cls(tuple(Annotation.from_dict(entry) for entry in cast("list[object]", data)))


def _order_key(annotation: Annotation) -> tuple[int, int, str, str]:
    """Zaman, sonra bitiş, sonra etiket, sonra kimlik — kararlı sıra."""
    end = annotation.start_ns if annotation.end_ns is None else annotation.end_ns
    return (annotation.start_ns, end, annotation.label, annotation.id)
