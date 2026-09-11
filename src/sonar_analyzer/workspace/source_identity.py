"""Taşınmış kaynakları yeniden konumlandırma — `F4-078`.

Bir çalışma alanı kaydedildiği andaki `.bin` yollarını taşır (`F3-070`).
Dosya taşınmışsa kullanıcı yeni konumu gösterebilmelidir — ama gösterilen
dosyanın **gerçekten aynı kayıt** olduğu doğrulanmadan bağlanırsa, tüm
analiz (işaretler, türetilmiş kanallar, eksen aralıkları) sessizce başka
bir veriye oturur. Bu modül o doğrulamayı yapar.

**Kimlik ölçüsü.** Kayıtlar çok GB olabildiği için tam dosya hash'i
(`SourceFingerprint`, `F2-030`) yeniden konumlandırma için fazla
pahalıdır — `F4-065` ölçümünde 1 GB dosya ~10 s sürüyor. Bunun yerine
`O(1)` bir ölçü kullanılır:

* dosya boyutu (bayt),
* **ilk** `sample_bytes` baytın sha256'sı (header, kanal tablosu, ilk
  kayıtlar — `t0_utc_ns` ve kayıt sayısı buradadır),
* **son** `sample_bytes` baytın sha256'sı.

Bunun ne olduğu açıkça söylenmelidir: üçü birden eşleşiyorsa dosya
pratikte aynı kayıttır, ama bu **tam içerik doğrulaması değildir**.
Kasıtlı olarak üretilmiş bir çakışma mümkündür; yanlışlıkla başka bir
dosyayı göstermek değildir. Tam doğrulama gerekiyorsa indeks katmanı
`SourceFingerprint` ile zaten dosyanın tamamını hash'ler.

Saf Python: dosya okuma enjekte edilebilir, `GUI olmadan` doğrulanır.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import cast

#: Baştan ve sondan okunan örnek boyutu.
DEFAULT_SAMPLE_BYTES = 1024 * 1024

IDENTITY_SCHEMA_VERSION = 1


class RelocationError(ValueError):
    """Gösterilen dosya kaydedilmiş kaynakla aynı değil."""


@dataclass(frozen=True)
class SourceIdentity:
    """Bir kaynak dosyanın ucuz ama ayırt edici kimliği."""

    size_bytes: int
    head_sha256: str
    tail_sha256: str
    sample_bytes: int = DEFAULT_SAMPLE_BYTES

    def __post_init__(self) -> None:
        if self.size_bytes < 0:
            raise RelocationError(f"Dosya boyutu negatif olamaz: {self.size_bytes}")
        if self.sample_bytes < 1:
            raise RelocationError(f"Örnek boyutu pozitif olmalı: {self.sample_bytes}")
        for name in ("head_sha256", "tail_sha256"):
            digest = getattr(self, name)
            if not isinstance(digest, str) or len(digest) != 64:
                raise RelocationError(f"{name} 64 haneli sha256 olmalı, verilen: {digest!r}")

    def matches(self, other: SourceIdentity) -> bool:
        """Üç ölçü de eşleşiyor mu (örnek boyutu farklıysa karşılaştırılamaz)."""
        return (
            self.sample_bytes == other.sample_bytes
            and self.size_bytes == other.size_bytes
            and self.head_sha256 == other.head_sha256
            and self.tail_sha256 == other.tail_sha256
        )

    def describe_mismatch(self, other: SourceIdentity) -> str:
        """Neden eşleşmediğini insan diliyle söyler; eşleşiyorsa boş metin."""
        if self.sample_bytes != other.sample_bytes:
            return (
                f"kimlik ölçüsü farklı örneklenmiş ({self.sample_bytes} / "
                f"{other.sample_bytes} bayt); karşılaştırılamaz"
            )
        if self.size_bytes != other.size_bytes:
            return (
                f"dosya boyutu farklı: beklenen {self.size_bytes} bayt, "
                f"seçilen {other.size_bytes} bayt"
            )
        if self.head_sha256 != other.head_sha256:
            return "dosya başlangıcı farklı (aynı boyut, başka içerik)"
        if self.tail_sha256 != other.tail_sha256:
            return "dosya sonu farklı (aynı boyut ve başlangıç, başka içerik)"
        return ""

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": IDENTITY_SCHEMA_VERSION,
            "size_bytes": self.size_bytes,
            "head_sha256": self.head_sha256,
            "tail_sha256": self.tail_sha256,
            "sample_bytes": self.sample_bytes,
        }

    @classmethod
    def from_dict(cls, data: object) -> SourceIdentity:
        if not isinstance(data, dict):
            raise RelocationError("Kaynak kimliği bir nesne olmalı")
        record = cast("dict[str, object]", data)
        version = record.get("schema_version", IDENTITY_SCHEMA_VERSION)
        if version != IDENTITY_SCHEMA_VERSION:
            raise RelocationError(
                f"Desteklenmeyen kaynak kimliği şeması: {version!r}; "
                f"beklenen {IDENTITY_SCHEMA_VERSION}"
            )
        return cls(
            size_bytes=_integer(record, "size_bytes"),
            head_sha256=_text(record, "head_sha256"),
            tail_sha256=_text(record, "tail_sha256"),
            sample_bytes=_integer(record, "sample_bytes", default=DEFAULT_SAMPLE_BYTES),
        )


def _text(record: dict[str, object], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str):
        raise RelocationError(f"{key} metin olmalı, verilen: {value!r}")
    return value


def _integer(record: dict[str, object], key: str, *, default: int | None = None) -> int:
    value = record.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise RelocationError(f"{key} tam sayı olmalı, verilen: {value!r}")
    return value


def identity_for_path(
    path: Path | str, *, sample_bytes: int = DEFAULT_SAMPLE_BYTES
) -> SourceIdentity:
    """Dosyanın kimliğini **boyutundan bağımsız** sabit maliyetle hesaplar.

    Dosya `2 * sample_bytes`'tan kısaysa baş ve son örnekleri örtüşür;
    bu doğruluğu bozmaz, yalnız aynı baytlar iki kez hash'lenir.
    """
    if sample_bytes < 1:
        raise RelocationError(f"Örnek boyutu pozitif olmalı: {sample_bytes}")
    target = Path(path)
    try:
        size = target.stat().st_size
        with target.open("rb") as stream:
            head = stream.read(sample_bytes)
            stream.seek(max(0, size - sample_bytes))
            tail = stream.read(sample_bytes)
    except OSError as exc:
        raise RelocationError(f"Kaynak okunamadı: {target} ({exc})") from exc

    return SourceIdentity(
        size_bytes=size,
        head_sha256=hashlib.sha256(head).hexdigest(),
        tail_sha256=hashlib.sha256(tail).hexdigest(),
        sample_bytes=sample_bytes,
    )


def verify_relocation(expected: SourceIdentity, candidate: Path | str) -> SourceIdentity:
    """`candidate` kaydedilmiş kimlikle eşleşiyorsa kimliğini döndürür.

    Eşleşmiyorsa `RelocationError` **nedeni söyleyerek** yükselir; yanlış
    dosya sessizce bağlanmaz (kabul kriteri).
    """
    actual = identity_for_path(candidate, sample_bytes=expected.sample_bytes)
    reason = expected.describe_mismatch(actual)
    if reason:
        raise RelocationError(f"{Path(candidate).name} bu kaynağın yerine konamaz: {reason}")
    return actual
