"""C++ tip eşleme tablosu — `F7-007`.

Kabul: **13 temel cpp tipi için üç gösterim de tanımlı; bilinmeyen tip
`SchemaTypeError` verir.**

Bir eşleme tablosunun bayt sayıları elle yazılır ve elle yazılan bir sayı
sessizce yanlış olabilir. `uint32_t` için 2 yazılsaydı tablo makul
görünürdü; hata ancak yanlış offsetle okunan bir kayıtta ortaya çıkardı.

Bu yüzden testler tablodaki her satırı **ölçer**: `struct.calcsize` ve
`numpy.dtype().itemsize` ile. Ayrıca tablo ile sözleşme belgesini
karşılaştırır — ikisi ayrışırsa hangisinin doğru olduğu belirsizleşir.
"""

from __future__ import annotations

import struct
from pathlib import Path

import numpy as np
import pytest

from sonar_analyzer.io.schema.errors import SchemaTypeError
from sonar_analyzer.io.schema.types import (
    CHAR_ARRAY,
    COMPLEX_FLOAT,
    COMPLEX_INT16,
    FORBIDDEN,
    TYPES,
    is_supported,
    resolve,
    size_of,
)

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "format" / "toml-schema.md"


# --------------------------------------------------------------------------- #
# TABLO TAM MI
# --------------------------------------------------------------------------- #


def test_all_thirteen_types_are_defined() -> None:
    """Asıl kabul: sözleşmedeki 13 tipin hepsi tabloda olmalı."""
    assert len(TYPES) == 13, f"13 tip bekleniyordu, {len(TYPES)} var: {sorted(TYPES)}"


def test_every_entry_carries_all_three_representations() -> None:
    """Bir gösterim eksikse, o tip için okuma ya da doğrulama yapılamaz."""
    for name, entry in TYPES.items():
        assert entry.cpp == name
        assert entry.struct_code, f"{name}: struct kodu yok"
        assert entry.numpy_dtype, f"{name}: NumPy dtype yok"
        assert entry.size > 0, f"{name}: boyut pozitif olmalı"


# --------------------------------------------------------------------------- #
# BOYUTLAR OLCULEREK DOGRULANIYOR
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("name", sorted(set(TYPES) - {CHAR_ARRAY}))
def test_the_struct_code_really_produces_that_size(name: str) -> None:
    """Asıl kabul: elle yazılmış bayt sayısı ölçülerek sınanmalı."""
    entry = TYPES[name]
    measured = struct.calcsize("<" + entry.struct_code)
    assert measured == entry.size, f"{name}: struct {measured} bayt, tabloda {entry.size}"


@pytest.mark.parametrize("name", sorted(TYPES))
def test_the_numpy_dtype_is_resolvable(name: str) -> None:
    """Çözülemeyen bir dtype, okuma anında patlar."""
    entry = TYPES[name]
    assert np.dtype(entry.numpy_dtype).itemsize > 0


@pytest.mark.parametrize("name", sorted(set(TYPES) - {CHAR_ARRAY, COMPLEX_INT16}))
def test_the_numpy_dtype_size_matches_the_table(name: str) -> None:
    """`char[N]` ve tamsayı complex dışında dtype boyutu tipin boyutudur."""
    entry = TYPES[name]
    assert np.dtype(entry.numpy_dtype).itemsize == entry.size


def test_the_char_array_is_one_byte_per_element() -> None:
    """`char[N]` tek elemanı 1 bayttır; N ile çarpılır."""
    assert TYPES[CHAR_ARRAY].size == 1
    assert size_of(CHAR_ARRAY, 12) == 12


def test_the_integer_complex_is_not_directly_usable_in_numpy() -> None:
    """NumPy'da tamsayı tabanlı complex dtype yoktur; bayrak bunu söyler."""
    assert TYPES[COMPLEX_INT16].numpy_direct is False
    assert TYPES[COMPLEX_FLOAT].numpy_direct is True


def test_numpy_really_lacks_an_integer_complex_dtype() -> None:
    """Bayrağın dayandığı iddia ölçülerek doğrulanır."""
    with pytest.raises(TypeError):
        np.dtype("complex32")


def test_the_profile_sample_type_is_eight_bytes() -> None:
    """Bütün bayt bütçesi bu sayıya dayanıyor (`D-28`)."""
    assert TYPES[COMPLEX_FLOAT].size == 8
    assert np.dtype("c8").itemsize == 8
    assert struct.calcsize("<2f") == 8


# --------------------------------------------------------------------------- #
# ISARETLILIK
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("name", "signed"),
    [
        ("uint8_t", False),
        ("int8_t", True),
        ("uint16_t", False),
        ("int16_t", True),
        ("uint32_t", False),
        ("int32_t", True),
        ("uint64_t", False),
        ("int64_t", True),
    ],
)
def test_signedness_is_recorded_correctly(name: str, signed: bool) -> None:
    """İşaretlilik yanlışsa, negatif bir değer devasa bir pozitife döner."""
    assert TYPES[name].signed is signed


@pytest.mark.parametrize("name", ["uint8_t", "uint16_t", "uint32_t", "uint64_t"])
def test_unsigned_struct_codes_are_uppercase(name: str) -> None:
    """`struct`'ta büyük harf işaretsiz demektir; tablo bunu izlemeli."""
    assert TYPES[name].struct_code.isupper()


@pytest.mark.parametrize("name", ["int8_t", "int16_t", "int32_t", "int64_t"])
def test_signed_integer_struct_codes_are_lowercase(name: str) -> None:
    assert TYPES[name].struct_code.islower()


@pytest.mark.parametrize("name", ["uint8_t", "uint16_t", "uint32_t", "uint64_t"])
def test_unsigned_numpy_dtypes_start_with_u(name: str) -> None:
    assert TYPES[name].numpy_dtype.startswith("u")


# --------------------------------------------------------------------------- #
# BICIM URETIMI
# --------------------------------------------------------------------------- #


def test_a_single_element_uses_the_bare_code() -> None:
    assert TYPES["uint32_t"].format_for(1) == "I"


def test_multiple_elements_are_prefixed_with_the_count() -> None:
    assert TYPES["uint8_t"].format_for(16) == "16B"
    assert struct.calcsize("<16B") == 16


def test_a_char_array_is_one_field_not_n_fields() -> None:
    """`12s` tek bayt dizisi döndürür; `12c` on iki ayrı değer döndürürdü."""
    assert TYPES[CHAR_ARRAY].format_for(12) == "12s"
    assert len(struct.unpack("<12s", b"x" * 12)) == 1


def test_a_zero_or_negative_count_is_rejected() -> None:
    """Sessizce 1'e yuvarlamak, bildirilen boyutu bozardı."""
    for count in (0, -1):
        with pytest.raises(ValueError, match="eleman sayisi"):
            TYPES["uint8_t"].format_for(count)


def test_size_of_multiplies_by_the_count() -> None:
    assert size_of("uint32_t", 4) == 16
    assert size_of("int64_t") == 8


def test_size_of_rejects_a_bad_count() -> None:
    with pytest.raises(ValueError, match="eleman sayisi"):
        size_of("uint8_t", 0)


# --------------------------------------------------------------------------- #
# BILINMEYEN VE YASAKLI TIPLER
# --------------------------------------------------------------------------- #


def test_an_unknown_type_raises() -> None:
    """Asıl kabul: bilinmeyen tip sessizce geçemez."""
    with pytest.raises(SchemaTypeError):
        resolve("uint128_t")


def test_the_error_names_the_field_when_given() -> None:
    """Hangi alanda olduğu yazılmazsa, büyük bir şemada aranması gerekir."""
    with pytest.raises(SchemaTypeError, match="frame_index"):
        resolve("widget_t", field="frame_index")


@pytest.mark.parametrize("name", sorted(FORBIDDEN))
def test_a_forbidden_type_raises(name: str) -> None:
    with pytest.raises(SchemaTypeError):
        resolve(name)


@pytest.mark.parametrize("name", sorted(FORBIDDEN))
def test_a_forbidden_type_says_what_to_write_instead(name: str) -> None:
    """Yalnız "desteklenmiyor" demek kullanıcıyı belgede aratır."""
    with pytest.raises(SchemaTypeError) as caught:
        resolve(name)
    assert caught.value.hint is not None, f"{name} icin ipucu yok"
    assert "yazin" in str(caught.value), f"{name} mesaji ne yazilacagini soylemiyor"


def test_bool_and_long_are_among_the_forbidden() -> None:
    """Sözleşmenin adıyla saydığı iki tip."""
    assert "bool" in FORBIDDEN
    assert "long" in FORBIDDEN


def test_the_long_hint_names_both_platforms() -> None:
    assert "Windows" in FORBIDDEN["long"]
    assert "Linux" in FORBIDDEN["long"]


def test_no_forbidden_type_is_also_supported() -> None:
    """Bir tip hem tabloda hem yasak listesinde olursa yasak etkisiz kalır."""
    assert not (set(FORBIDDEN) & set(TYPES))


def test_is_supported_agrees_with_resolve() -> None:
    for name in TYPES:
        assert is_supported(name)
    for name in FORBIDDEN:
        assert not is_supported(name)


# --------------------------------------------------------------------------- #
# TABLO ILE SOZLESME AYRISIYOR MU
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("name", sorted(set(TYPES) - {COMPLEX_INT16, CHAR_ARRAY}))
def test_the_document_lists_the_same_size(name: str) -> None:
    """Asıl kabul: kod tablosu ile belge tablosu ayrışmamalı."""
    text = DOC.read_text(encoding="utf-8")
    row = next((line for line in text.splitlines() if line.startswith(f"| `{name}` |")), None)
    assert row is not None, f"{name} sozlesme belgesinde yok"
    entry = TYPES[name]
    assert f"| {entry.size} |" in row, f"{name}: belgede farklı boyut"
    assert f"`{entry.struct_code}`" in row, f"{name}: belgede farklı struct kodu"


def test_the_char_array_row_matches_the_document() -> None:
    """Bu satır özel: belge **şablonu** yazar, kod **çıplak kodu** tutar.

    Belgede `Ns` görünür çünkü okuyan kişi N yerine sayıyı koyacaktır.
    Kodda `s` durur ve sayı `format_for` ile önüne eklenir. İkisi aynı
    şeyi anlatır; test bunu karıştırmamak için ayrı yazıldı.
    """
    text = DOC.read_text(encoding="utf-8")
    row = next(line for line in text.splitlines() if line.startswith(f"| `{CHAR_ARRAY}` |"))
    assert "| N |" in row, "belgede boyut N olarak yazılmalı"
    assert "`Ns`" in row
    assert TYPES[CHAR_ARRAY].struct_code == "s"
    assert TYPES[CHAR_ARRAY].format_for(12) == "12s"


def test_the_integer_complex_row_matches_the_document() -> None:
    """Bu satır özel: NumPy sütunu "okunamaz" diyor, bir dtype adı değil."""
    text = DOC.read_text(encoding="utf-8")
    row = next(line for line in text.splitlines() if COMPLEX_INT16 in line)
    assert "| 4 |" in row
    assert "`2h`" in row
    assert TYPES[COMPLEX_INT16].size == 4


def test_the_document_forbids_the_same_two_types() -> None:
    prose = " ".join(DOC.read_text(encoding="utf-8").split())
    assert "`bool` ve `long` yasaktır" in prose
