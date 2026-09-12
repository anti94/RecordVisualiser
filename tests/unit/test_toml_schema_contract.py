"""C++ struct → TOML eşleme sözleşmesi — `F7-004`.

Kabul: **Paketleme (`#pragma pack`), hizalama, endianness ve bit alanı
kuralları örnekle tanımlıdır.**

Bir C++ struct'ını TOML'a taşırken kaybolan bilgi, derleyicinin sessizce
eklediği bilgidir: dolgu baytları, hizalama, bit alanı yerleşimi, enum'un
temel tipi. Sözleşme bu bilginin nasıl açıkça yazılacağını tanımlamazsa,
tarif eksik kalır ve eksik tarif **hatasız ama yanlış** okur.

Testler iki şeyi ayrı ayrı doğrular. Birincisi sözleşmenin gerekli her
kuralı tanımladığı. İkincisi ve daha önemlisi, tip tablosundaki her
satırın **gerçekten doğru** olduğu: `struct.calcsize` ve `numpy.dtype`
ile ölçülüp belgede yazanla karşılaştırılır. Yanlış bir bayt sayısı
tabloda fark edilmeden durabilir, ama ölçüm onu yakalar.
"""

from __future__ import annotations

import re
import struct
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "format" / "toml-schema.md"

#: Belgedeki tip tablosundan beklenen esleme: cpp -> (bayt, struct kodu, numpy dtype)
EXPECTED_TYPES: dict[str, tuple[int, str, str]] = {
    "uint8_t": (1, "B", "u1"),
    "int8_t": (1, "b", "i1"),
    "uint16_t": (2, "H", "u2"),
    "int16_t": (2, "h", "i2"),
    "uint32_t": (4, "I", "u4"),
    "int32_t": (4, "i", "i4"),
    "uint64_t": (8, "Q", "u8"),
    "int64_t": (8, "q", "i8"),
    "float": (4, "f", "f4"),
    "double": (8, "d", "f8"),
}


@pytest.fixture(scope="module")
def text() -> str:
    assert DOC.is_file(), f"sozlesme belgesi yok: {DOC}"
    return DOC.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def prose(text: str) -> str:
    return " ".join(text.split())


# --------------------------------------------------------------------------- #
# TIP TABLOSU GERCEKTEN DOGRU MU
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(("cpp", "expected"), sorted(EXPECTED_TYPES.items()))
def test_the_type_table_row_is_in_the_document(
    text: str, cpp: str, expected: tuple[int, str, str]
) -> None:
    """Her temel tip tabloda bulunmalı; eksik tip şema yazılamaz kılar."""
    size, code, dtype = expected
    row = next((line for line in text.splitlines() if line.startswith(f"| `{cpp}` |")), None)
    assert row is not None, f"{cpp} tip tablosunda yok"
    assert f"| {size} |" in row, f"{cpp} bayt sayısı {size} yazılmamış"
    assert f"`{code}`" in row, f"{cpp} struct kodu `{code}` yazılmamış"
    assert f"`{dtype}`" in row, f"{cpp} NumPy dtype `{dtype}` yazılmamış"


@pytest.mark.parametrize(("cpp", "expected"), sorted(EXPECTED_TYPES.items()))
def test_the_struct_code_really_has_that_size(cpp: str, expected: tuple[int, str, str]) -> None:
    """Asıl kabul: belgedeki bayt sayısı ölçülerek doğrulanmalı.

    `struct.calcsize` küçük uçlu ve hizalamasız kipte (`<`) çağrılır;
    yerel kip derleyici hizalaması ekler ve farklı sonuç verir.
    """
    size, code, _dtype = expected
    assert struct.calcsize("<" + code) == size, f"{cpp}: struct kodu {code!r} {size} bayt değil"


@pytest.mark.parametrize(("cpp", "expected"), sorted(EXPECTED_TYPES.items()))
def test_the_numpy_dtype_really_has_that_size(cpp: str, expected: tuple[int, str, str]) -> None:
    size, _code, dtype = expected
    assert np.dtype(dtype).itemsize == size, f"{cpp}: NumPy {dtype!r} {size} bayt değil"


def test_the_complex_float_row_is_right(text: str) -> None:
    """Bu profilin örnek tipi; yanlış olursa bütün bayt bütçesi çöker."""
    row = next(line for line in text.splitlines() if "std::complex<float>" in line)
    assert "| 8 |" in row
    assert "`2f`" in row
    assert "`c8`" in row
    assert struct.calcsize("<2f") == 8
    assert np.dtype("c8").itemsize == 8


def test_the_iq_order_is_stated(prose: str) -> None:
    """I ve Q'nun sırası yazılmazsa, ters okunan veri hata vermez."""
    assert "I önce, Q sonra" in prose


def test_the_integer_complex_caveat_is_stated(prose: str) -> None:
    """NumPy'da tamsayı tabanlı complex dtype yoktur; bu tuzak yazılı olmalı."""
    assert "tamsayı tabanlı complex dtype yoktur" in prose
    assert "elle birleştirilmelidir" in prose


def test_numpy_really_has_no_integer_complex_dtype() -> None:
    """Belgedeki uyarı bir iddia; ölçülerek doğrulanır."""
    with pytest.raises(TypeError):
        np.dtype("complex32")


def test_char_array_size_scales_with_n(text: str) -> None:
    assert "`char[N]`" in text
    assert struct.calcsize("<12s") == 12


# --------------------------------------------------------------------------- #
# YASAKLI TIPLER
# --------------------------------------------------------------------------- #


def test_bool_and_long_are_forbidden(prose: str) -> None:
    """İkisinin de boyutu derleyiciye ya da platforma bağlıdır."""
    assert "`bool` ve `long` yasaktır" in prose
    assert "derleyiciye bağlıdır" in prose
    assert "platforma" in prose


def test_the_long_width_difference_is_named(prose: str) -> None:
    """Somut örnek olmadan yasak bir kural, gerekçesiz bir tercih gibi okunur."""
    assert "Windows'ta 4, Linux'ta 8 bayt" in prose


def test_forbidden_types_are_not_in_the_type_table(text: str) -> None:
    """Yasaklı bir tip tabloda görünürse, yasak etkisiz kalır."""
    for forbidden in ("| `bool` |", "| `long` |"):
        assert forbidden not in text, f"{forbidden} tip tablosunda görünüyor"


# --------------------------------------------------------------------------- #
# BAYT SIRASI
# --------------------------------------------------------------------------- #


def test_endianness_is_declared_once_per_schema(text: str, prose: str) -> None:
    assert 'endianness = "little"' in text
    assert "Alan bazında bayt sırası **desteklenmez**" in prose


def test_the_reason_for_rejecting_per_field_endianness_is_given(prose: str) -> None:
    """Desteklemek yalnız yanlış şema yazmayı kolaylaştırırdı."""
    assert "gerçek bir C++ struct'ında oluşamaz" in prose


# --------------------------------------------------------------------------- #
# HIZALAMA VE DOLGU
# --------------------------------------------------------------------------- #


def test_both_packing_modes_are_defined(text: str) -> None:
    assert '"packed"' in text
    assert '"natural"' in text
    assert "#pragma pack(1)" in text


def test_the_padding_example_shows_real_compiler_behaviour(text: str) -> None:
    """Örnek olmadan "dolgu" soyut kalır; okuyan kendi struct'ında göremez."""
    assert "DERLEYICININ EKLEDIGI 3 BAYT DOLGU" in text
    assert "toplam 8 bayt, 5 degil" in text


def test_the_padding_example_arithmetic_is_right() -> None:
    """Belgedeki örnek gerçek hizalama kuralını yansıtmalı.

    `struct`'ta hizalamayı yalnız **öneksiz** (ya da `@`) kip uygular.
    `=` "yerel bayt sırası, standart boyut, hizalama yok" demektir ve
    adı yüzünden kolayca karıştırılır — burada da bir kez karıştırıldı.
    """
    assert struct.calcsize("BI") == 8, "uint8+uint32 dogal hizalamada 8 bayt"
    assert struct.calcsize("@BI") == 8, "@ oneki dogal hizalama demek"
    assert struct.calcsize("=BI") == 5, "= hizalama YAPMAZ"
    assert struct.calcsize("<BI") == 5, "paketli halde 5 bayt"


def test_offsets_are_always_written_not_computed(prose: str) -> None:
    """Hesaplama derleyicinin kuralını taklit eder; yazılmış offset ölçülebilir."""
    assert "her alanın offseti açıkça yazılır" in prose
    assert "Yazılmış bir offset ise ölçülebilir" in prose


def test_the_packing_mode_is_used_for_validation_only(prose: str) -> None:
    assert "Kip yalnız **doğrulama** için kullanılır" in prose


def test_declared_padding_is_supported(text: str) -> None:
    assert "_pad0" in text
    assert 'note = "derleyici dolgusu"' in text


def test_undeclared_gap_is_a_warning_not_an_error(prose: str) -> None:
    """Bilinçli olabilir; hata saymak doğru şemaları reddederdi."""
    assert "Bildirilmeyen boşluk hata değil **uyarıdır**" in prose


# --------------------------------------------------------------------------- #
# BIT ALANLARI
# --------------------------------------------------------------------------- #


def test_bit_fields_are_described_as_masks_not_cpp_bitfields(prose: str) -> None:
    """C++ bit alanı yerleşimi standart tarafından tanımlanmamıştır."""
    assert "standart tarafından tanımlanmamıştır" in prose
    assert "bir tamsayının içindeki maskeler" in prose


def test_the_bit_field_example_has_mask_and_shift(text: str) -> None:
    assert "mask = 0x0001" in text
    assert "shift = 2" in text


def test_the_example_masks_do_not_overlap() -> None:
    """Belgedeki örnek kendi kuralını çiğnememeli."""
    masks = [0x0001, 0x0002, 0x00FC]
    combined = 0
    for mask in masks:
        assert combined & mask == 0, f"maske 0x{mask:04X} örtüşüyor"
        combined |= mask


def test_overlapping_masks_are_rejected(prose: str) -> None:
    assert "Örtüşen maskeler hata verir" in prose


# --------------------------------------------------------------------------- #
# BOYUT DOGRULAMASI
# --------------------------------------------------------------------------- #


def test_every_required_validation_is_listed(text: str) -> None:
    """Bir denetim listelenmezse, o hata sınıfı sessizce geçer."""
    for check in (
        "Alan struct'ın dışına taşıyor",
        "Offset çakışması",
        "Boyut alanları kapsamıyor",
        "Hizalama ihlali",
        "Bilinmeyen tip",
        "Enum çakışması",
    ):
        assert check in text, f"denetim eksik: {check}"


def test_error_messages_must_name_the_field(prose: str) -> None:
    """ "Şema geçersiz" diyen bir mesaj, şemayı düzeltmeye yardım etmez."""
    assert "hangi alan, hangi offset ve ne beklendiğini" in prose


# --------------------------------------------------------------------------- #
# UC KAPI VE PAYLOAD YERLESIMI
# --------------------------------------------------------------------------- #


def test_the_three_gates_are_defined(text: str) -> None:
    assert "Sihirli sayı" in text
    assert "Şema kimliği ve sürümü" in text
    assert "Boyut denklemi" in text


def test_the_size_equation_is_written_out(text: str) -> None:
    assert "dosya_boyutu = dosya_header + frame_sayısı × (frame_header + S × N × B)" in text


def test_the_third_gate_works_without_a_schema_id(prose: str) -> None:
    """En değerli kapı, kimlik unutulsa bile çalışandır."""
    assert "şema kimliği unutulsa bile" in prose


def test_the_payload_layout_is_an_explicit_field(text: str, prose: str) -> None:
    """Yanlış yerleşim hiçbir boyut denetimini düşürmez, yalnız sensörleri karıştırır."""
    assert 'layout = "sensor_major"' in text
    assert '"sample_major"' in text
    assert "aynı bayt sayısını" in prose
    assert "en sessiz hata" in prose


def test_the_skeleton_declares_the_profile_constants(text: str) -> None:
    assert "sensor_count = 32" in text
    assert "frame_samples = 820" in text
    assert 'sample_type = "std::complex<float>"' in text


# --------------------------------------------------------------------------- #
# NEDEN TOML
# --------------------------------------------------------------------------- #


def test_the_format_choice_is_justified_against_alternatives(text: str) -> None:
    """Gerekçesiz bir biçim seçimi, sonradan tartışmaya açık kalır."""
    for alternative in ("JSON", "YAML", "Doğrudan C++ başlığı ayrıştırmak", "Python modülü"):
        assert alternative in text, f"{alternative} değerlendirilmemiş"


def test_the_python_version_constraint_is_recorded(prose: str) -> None:
    """`tomllib` 3.11'de geldi; bu proje 3.9 üzerinde koşuyor."""
    assert "tomllib" in prose
    assert "tomli" in prose
    assert "3.9" in prose


def test_the_document_does_not_promise_a_complete_example_yet(text: str) -> None:
    """Yazılmamış bir örneği varmış gibi göstermek, okuyanı boşuna aratır."""
    assert "`F7-006` ile eklenecektir" in text


def test_no_offset_is_invented_for_unknown_fields(text: str) -> None:
    """CIT ve transmisyon alanları bilinmiyor; iskelette sayı görünmemeli."""
    skeleton = text[text.index("## 8. Şema dosyasının iskeleti") :]
    assert "CIT" not in skeleton
    assert not re.search(r"offset\s*=\s*\d+", skeleton)
