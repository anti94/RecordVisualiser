"""Şema veri modeli — `F7-008`+.

TOML'dan okunan ham sözlükler doğrudan kullanılmaz. Ham bir sözlükte her
erişim bir `KeyError` riskidir ve hiçbir alan doğrulanmış değildir; bir
yazım hatası ancak o alan ilk kez okunduğunda ortaya çıkar.

Buradaki modeller **doğrulanmış** hâli taşır: bir `Schema` nesnesi
elinizdeyse offsetler çakışmıyor, tipler tanımlı ve boyutlar tutuyor
demektir. Doğrulama yükleme anında bir kez yapılır, her erişimde değil.

Modeller değişmezdir. Bir şema yüklendikten sonra değişirse, ondan
üretilmiş `struct.Struct` nesneleri sessizce eskir.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as dataclass_field

from sonar_analyzer.io.schema.types import CppType


def _trailing_zeros(mask: int) -> int:
    """Maskenin en düşük set bitinin konumu."""
    if mask == 0:
        return 0
    return (mask & -mask).bit_length() - 1


@dataclass(frozen=True)
class BitField:
    """Bir tamsayı alanının içindeki maske.

    `shift` verilmezse maskenin en düşük set bitinden türetilir. Bu, tek
    bitlik bir bayrağın 0/1 döndürmesini sağlar: `clock_locked` maskesi
    0x0002 ise kaydırmasız `extract` 2 döndürürdü ve `== 1` karşılaştıran
    her kod sessizce yanlış çalışırdı.
    """

    name: str
    mask: int
    shift: int = 0
    description: str = ""

    @property
    def effective_shift(self) -> int:
        """Uygulanan kaydırma: verilmişse o, yoksa maskeden türetilen."""
        return self.shift if self.shift else _trailing_zeros(self.mask)

    def extract(self, value: int) -> int:
        """Ham tamsayıdan bu bit alanının değerini çıkarır."""
        return (value & self.mask) >> self.effective_shift

    @property
    def width(self) -> int:
        """Maskenin kapsadığı bit sayısı."""
        return bin(self.mask).count("1")


@dataclass(frozen=True)
class EnumDef:
    """Bir enum tanımı ve temel tipi."""

    name: str
    underlying: CppType
    values: dict[str, int]
    description: str = ""

    @property
    def by_value(self) -> dict[int, str]:
        """Değerden isme eşleme."""
        return {value: key for key, value in self.values.items()}

    def name_of(self, value: int) -> str:
        """Değerin ismi; bilinmiyorsa ham değeri gösteren bir etiket.

        Bilinmeyen bir değeri sessizce `UNKNOWN`'a çevirmek, gerçekten
        `UNKNOWN` yazan bir kayıtla bozuk bir kaydı ayırt edilemez kılardı.
        """
        return self.by_value.get(value, f"<bilinmeyen: {value}>")


@dataclass(frozen=True)
class FieldDef:
    """Bir struct alanı: adı, tipi, offseti ve anlamı."""

    name: str
    cpp_type: CppType
    offset: int
    count: int = 1
    enum: str = ""
    unit: str = ""
    description: str = ""
    note: str = ""
    opaque: bool = False
    bits: tuple[BitField, ...] = ()

    @property
    def size(self) -> int:
        """Alanın kapladığı bayt sayısı."""
        return self.cpp_type.size * self.count

    @property
    def end(self) -> int:
        """Alanın bittiği offset (dâhil değil)."""
        return self.offset + self.size

    @property
    def is_padding(self) -> bool:
        """Alan bildirilmiş bir dolgu mu.

        Dolgu alanları okunur ama kullanıcıya gösterilmez; anlamları
        yoktur. Ada bakılır çünkü TOML'da ayrı bir bayrak tutmak, aynı
        bilgiyi iki yerde saklamak olurdu.
        """
        return self.name.startswith("_")

    @property
    def struct_format(self) -> str:
        """Bu alanın `struct` biçim parçası."""
        return self.cpp_type.format_for(self.count)


@dataclass(frozen=True)
class StructDef:
    """Bir struct tanımı: alanları ve bildirilen boyutu."""

    name: str
    size: int
    fields: tuple[FieldDef, ...]
    description: str = ""

    @property
    def measured_size(self) -> int:
        """Alanlardan hesaplanan boyut."""
        return max((f.end for f in self.fields), default=0)

    def field(self, name: str) -> FieldDef:
        """Adıyla bir alan; yoksa `KeyError`."""
        for candidate in self.fields:
            if candidate.name == name:
                return candidate

        raise KeyError(f"{self.name}: {name!r} adli alan yok")

    def struct_format(self, endianness: str) -> str:
        """Bütün struct için `struct` biçim dizgisi.

        Alanlar offset sırasına göre dizilir. Hizalama karakteri
        kullanılmaz: offsetler zaten açıkça yazılıdır ve `struct`'ın
        kendi hizalamasını uygulaması onları kaydırırdı.
        """
        prefix = "<" if endianness == "little" else ">"
        ordered = sorted(self.fields, key=lambda f: f.offset)
        return prefix + "".join(f.struct_format for f in ordered)


@dataclass(frozen=True)
class PayloadDef:
    """Frame yükünün yerleşimi."""

    sensor_count: int
    frame_samples: int
    sample_type: CppType
    layout: str
    description: str = ""

    @property
    def frame_bytes(self) -> int:
        """Bir frame'in yük boyutu."""
        return self.sensor_count * self.frame_samples * self.sample_type.size

    @property
    def sensor_major(self) -> bool:
        """Önce bir sensörün bütün örnekleri mi geliyor."""
        return self.layout == "sensor_major"


@dataclass(frozen=True)
class Schema:
    """Doğrulanmış bir Profil C şeması."""

    id: str
    version: int
    endianness: str
    packing: str
    enums: dict[str, EnumDef]
    structs: dict[str, StructDef]
    payload: PayloadDef
    description: str = ""
    #: Yuklerken uretilen, hata sayilmayan uyarilar (bildirilmemis bosluk gibi).
    warnings: tuple[str, ...] = dataclass_field(default_factory=tuple)

    @property
    def packed(self) -> bool:
        return self.packing == "packed"

    def struct(self, name: str) -> StructDef:
        """Adıyla bir struct; yoksa `KeyError`."""
        if name not in self.structs:
            raise KeyError(f"semada {name!r} adli struct yok: {sorted(self.structs)}")
        return self.structs[name]
