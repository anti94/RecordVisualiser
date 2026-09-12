"""C++ tipi → Python `struct` kodu → NumPy dtype eşlemesi — `F7-007`.

Üç gösterim **tek kaynaktan** gelir. Ayrı yerlerde yazılsalardı biri
güncellenip ötekiler unutulurdu ve aradaki fark ancak yanlış okunan bir
kayıtta ortaya çıkardı.

Eşlemenin doğruluğu varsayılmaz: `TYPES` sözlüğündeki bayt sayıları
`struct.calcsize` ve `numpy.dtype` ile **ölçülerek** sınanır (testlerde).
Elle yazılmış bir bayt sayısı tabloda fark edilmeden durabilir.

İki tip bilinçli olarak yasaktır:

* `bool` — boyutu derleyiciye bağlıdır.
* `long` — platforma bağlıdır (Windows'ta 4, Linux'ta 8 bayt).

İkisi de `SchemaTypeError` verir ve hata mesajı yerine ne yazılması
gerektiğini söyler. Sessizce bir boyut varsaymak, yanlış offsetlerle
okunan bir dosya demektir.
"""

from __future__ import annotations

from dataclasses import dataclass

from sonar_analyzer.io.schema.errors import SchemaTypeError

#: Dizi uzunlugu tasiyan tip adi. `count` alaniyla birlikte kullanilir.
CHAR_ARRAY = "char[N]"

#: Bu profilin ornek tipi (D-28).
COMPLEX_FLOAT = "std::complex<float>"

#: Tamsayi tabanli complex; NumPy'da dogrudan karsiligi YOKTUR.
COMPLEX_INT16 = "std::complex<int16_t>"


@dataclass(frozen=True)
class CppType:
    """Bir C++ tipinin üç gösterimi ve bayt boyutu."""

    cpp: str
    size: int
    struct_code: str
    numpy_dtype: str
    signed: bool
    #: NumPy dtype dogrudan kullanilabiliyor mu. `std::complex<int16_t>`
    #: icin False: NumPy'da tamsayi tabanli complex dtype yoktur ve veri
    #: `i2` ciftleri olarak okunup elle birlestirilmelidir.
    numpy_direct: bool = True

    def format_for(self, count: int) -> str:
        """`count` elemanlı bir alan için `struct` biçim parçası.

        `char[N]` tek bir `Ns` alanıdır, N ayrı karakter değil: `struct`
        onu tek bir bayt dizisi olarak döndürür ve alan adı tek değer
        taşır.
        """
        if count < 1:
            raise ValueError(f"{self.cpp}: eleman sayisi >= 1 olmali, verilen {count}")
        if self.cpp == CHAR_ARRAY:
            return f"{count}s"
        if count == 1:
            return self.struct_code
        return f"{count}{self.struct_code}"


def _entry(
    cpp: str, size: int, code: str, dtype: str, signed: bool, direct: bool = True
) -> CppType:
    return CppType(
        cpp=cpp, size=size, struct_code=code, numpy_dtype=dtype, signed=signed, numpy_direct=direct
    )


#: Sozlesmedeki tip tablosunun kod karsiligi.
#: docs/format/toml-schema.md Bolum 2 ile birebir ayni olmalidir; bir test
#: iki tarafi karsilastirir.
TYPES: dict[str, CppType] = {
    "uint8_t": _entry("uint8_t", 1, "B", "u1", signed=False),
    "int8_t": _entry("int8_t", 1, "b", "i1", signed=True),
    "uint16_t": _entry("uint16_t", 2, "H", "u2", signed=False),
    "int16_t": _entry("int16_t", 2, "h", "i2", signed=True),
    "uint32_t": _entry("uint32_t", 4, "I", "u4", signed=False),
    "int32_t": _entry("int32_t", 4, "i", "i4", signed=True),
    "uint64_t": _entry("uint64_t", 8, "Q", "u8", signed=False),
    "int64_t": _entry("int64_t", 8, "q", "i8", signed=True),
    "float": _entry("float", 4, "f", "f4", signed=True),
    "double": _entry("double", 8, "d", "f8", signed=True),
    CHAR_ARRAY: _entry(CHAR_ARRAY, 1, "s", "S1", signed=False),
    COMPLEX_FLOAT: _entry(COMPLEX_FLOAT, 8, "2f", "c8", signed=True),
    COMPLEX_INT16: _entry(COMPLEX_INT16, 4, "2h", "i2", signed=True, direct=False),
}

#: Bilincli olarak reddedilen tipler ve yerine ne yazilmasi gerektigi.
FORBIDDEN: dict[str, str] = {
    "bool": "boyutu derleyiciye bagli; `uint8_t` yazin",
    "long": "boyutu platforma bagli (Windows 4, Linux 8); `int32_t` ya da `int64_t` yazin",
    "unsigned long": "boyutu platforma bagli; `uint32_t` ya da `uint64_t` yazin",
    "size_t": "boyutu platforma bagli; `uint32_t` ya da `uint64_t` yazin",
    "int": "genisligi garantili degil; `int32_t` yazin",
    "unsigned": "genisligi garantili degil; `uint32_t` yazin",
    "short": "genisligi garantili degil; `int16_t` yazin",
    "char": "isaretliligi derleyiciye bagli; `int8_t`, `uint8_t` ya da `char[N]` yazin",
}


def resolve(cpp_type: str, *, field: str | None = None) -> CppType:
    """Bir C++ tip adını çözer.

    Bilinmeyen ya da yasaklı tip `SchemaTypeError` verir. Yasaklı tipler
    için mesaj **yerine ne yazılacağını** söyler; yalnız "desteklenmiyor"
    demek kullanıcıyı belgede aratır.
    """
    if cpp_type in TYPES:
        return TYPES[cpp_type]
    raise SchemaTypeError(cpp_type, field=field, hint=FORBIDDEN.get(cpp_type.strip()))


def size_of(cpp_type: str, count: int = 1, *, field: str | None = None) -> int:
    """Bir alanın kapladığı bayt sayısı."""
    resolved = resolve(cpp_type, field=field)
    if count < 1:
        raise ValueError(f"{cpp_type}: eleman sayisi >= 1 olmali, verilen {count}")
    return resolved.size * count


def is_supported(cpp_type: str) -> bool:
    """Tip tabloda var mı."""
    return cpp_type in TYPES
