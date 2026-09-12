"""Profil seçimi — `F7-027`.

`version_dispatch` bir **profil içindeki** sürümleri ayırır (Profil A v1
ile v2). Bu modül bir üst kattadır: elindeki baytların hangi **profile**
ait olduğunu söyler.

Profil A ve B'nin sihirli sayıları koda gömülüdür; ikisi de bu uygulama
tarafından tanımlanmıştır. Profil C öyle değil: onu C++ tarafı üretir
(`D-29`) ve sihirli sayısı da şemadan gelir. Bu yüzden Profil C ancak
**bir şema verilirse** tanınabilir.

Bu asimetri bilinçlidir ve gizlenmez. Şemasız bir çağrıda Profil C
dosyası `UNKNOWN` döner, "muhtemelen C" değil. Tahmin etmek, yanlış
çözücüyle okumanın en kısa yoludur.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from sonar_analyzer.io.profile_a_format import MAGIC as PROFILE_A_MAGIC
from sonar_analyzer.io.profile_b_format import MAGIC as PROFILE_B_MAGIC
from sonar_analyzer.io.schema.model import Schema

#: Sihirli sayilarin okunmasi icin gereken en az bayt.
MAGIC_LENGTH = 8


class Profile(Enum):
    """Tanınan kayıt profilleri."""

    A = "profile-a"
    B = "profile-b"
    C = "profile-c"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Detection:
    """Bir tanıma sonucu ve nasıl varıldığı."""

    profile: Profile
    magic: bytes
    #: Tanima nasil yapildi: "magic" ya da "schema".
    basis: str
    detail: str = ""

    @property
    def recognised(self) -> bool:
        return self.profile is not Profile.UNKNOWN


def schema_magic(schema: Schema) -> bytes | None:
    """Şemanın `FileHeader.magic` alanı için beklenen değer.

    Şema yalnız alanın **varlığını** ve boyutunu tarif eder, değerini
    değil. Beklenen değer bu yüzden `expected` notundan değil, dosyanın
    kendisinden okunur; burada yalnız alanın var olup olmadığı söylenir.
    """
    try:
        definition = schema.struct("FileHeader")
    except KeyError:
        return None
    field = next((f for f in definition.fields if f.name == "magic"), None)
    if field is None or field.offset != 0:
        return None
    return b"\x00" * field.size


def detect(data: bytes, schema: Schema | None = None) -> Detection:
    """Baytların hangi profile ait olduğunu söyler.

    Profil A ve B sihirli sayılarından tanınır. Profil C ancak bir şema
    verilirse tanınır: sihirli sayısı şemayla gelir, koda gömülü değildir.
    """
    if len(data) < MAGIC_LENGTH:
        return Detection(
            profile=Profile.UNKNOWN,
            magic=bytes(data),
            basis="magic",
            detail=f"sihirli sayi icin yeterli bayt yok: {len(data)} < {MAGIC_LENGTH}",
        )

    magic = bytes(data[:MAGIC_LENGTH])
    if magic == PROFILE_A_MAGIC:
        return Detection(profile=Profile.A, magic=magic, basis="magic")
    if magic == PROFILE_B_MAGIC:
        return Detection(profile=Profile.B, magic=magic, basis="magic")

    if schema is not None:
        expected = schema_magic(schema)
        if expected is not None and len(expected) == MAGIC_LENGTH:
            return Detection(
                profile=Profile.C,
                magic=magic,
                basis="schema",
                detail=f"sema {schema.id} v{schema.version} ile tanindi",
            )

    return Detection(
        profile=Profile.UNKNOWN,
        magic=magic,
        basis="magic",
        detail=(
            f"sihirli sayi {magic!r} taninmadi. Profil A ve B koda gomulu; "
            f"Profil C icin sema gerekir (D-29)."
            if schema is None
            else (
                f"sihirli sayi {magic!r} taninmadi ve verilen sema "
                f"bir FileHeader.magic alani tasimiyor"
            )
        ),
    )


def describe(detection: Detection) -> str:
    """Tanıma sonucunu kullanıcıya gösterilecek hâle çevirir."""
    if detection.recognised:
        tail = f" ({detection.detail})" if detection.detail else ""
        return f"{detection.profile.value}{tail}"
    return f"taninmayan bicim: {detection.detail}"
