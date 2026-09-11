"""Ayırıcı ve ondalık biçimi tutarlılığı — `F4-085`.

Kabul: zaman ve ondalık biçimi seçilen ayırıcıyla tutarlıdır.

Tutarlılık burada tek bir değişmeze iner: **hiçbir alan, alan ayırıcısını
içeremez.** Sayı alanı için bu, ondalık ayıracının alan ayırıcısından
farklı olmasını; zaman alanı için ise ayırıcının ISO-8601 damgasında
geçmemesini gerektirir. İkisi de burada zorlanır.
"""

from __future__ import annotations

import pytest

from sonar_analyzer.export.text_format import (
    DEFAULT_DECIMAL,
    Delimiter,
    TextFormat,
    TextFormatError,
    resolve_format,
)

# --------------------------------------------------------------------------- #
# ayirici secenekleri
# --------------------------------------------------------------------------- #


def test_the_supported_delimiters_are_comma_tab_and_semicolon() -> None:
    assert {item.value for item in Delimiter} == {",", "\t", ";"}


def test_every_delimiter_has_a_readable_label() -> None:
    for delimiter in Delimiter:
        assert delimiter.label


def test_each_delimiter_has_a_conventional_decimal() -> None:
    assert DEFAULT_DECIMAL[Delimiter.COMMA] == "."
    assert DEFAULT_DECIMAL[Delimiter.TAB] == "."
    # `;` Avrupa CSV gelenegidir ve tam da virgullu ondalik icindir.
    assert DEFAULT_DECIMAL[Delimiter.SEMICOLON] == ","


def test_resolving_without_a_choice_uses_the_convention() -> None:
    assert resolve_format(Delimiter.SEMICOLON).decimal_separator == ","
    assert resolve_format(Delimiter.TAB).decimal_separator == "."


def test_the_default_format_is_plain_csv() -> None:
    fmt = resolve_format()
    assert fmt.delimiter is Delimiter.COMMA
    assert fmt.decimal_separator == "."


# --------------------------------------------------------------------------- #
# CAKISMA reddedilir
# --------------------------------------------------------------------------- #


def test_a_comma_decimal_in_a_comma_file_is_refused() -> None:
    """Kabul kriterinin çekirdeği: sayı satırı bölemez."""
    with pytest.raises(TextFormatError, match="alan ayırıcısıyla aynı olamaz"):
        resolve_format(Delimiter.COMMA, ",")


def test_a_comma_decimal_is_fine_with_a_tab_delimiter() -> None:
    assert resolve_format(Delimiter.TAB, ",").decimal_separator == ","


def test_a_comma_decimal_is_fine_with_a_semicolon_delimiter() -> None:
    assert resolve_format(Delimiter.SEMICOLON, ",").decimal_separator == ","


def test_a_dot_decimal_is_fine_everywhere() -> None:
    for delimiter in Delimiter:
        assert resolve_format(delimiter, ".").decimal_separator == "."


@pytest.mark.parametrize("bad", ["", " ", "·", "..", "x"])
def test_an_unsupported_decimal_separator_is_refused(bad: str) -> None:
    with pytest.raises(TextFormatError, match="Ondalık ayıracı"):
        resolve_format(Delimiter.TAB, bad)


def test_a_conflict_is_never_silently_corrected() -> None:
    """Sessizce düzeltmek kullanıcıya yanlış dosya verirdi."""
    with pytest.raises(TextFormatError):
        TextFormat(delimiter=Delimiter.COMMA, decimal_separator=",")


# --------------------------------------------------------------------------- #
# ZAMAN alani ile tutarlilik
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("delimiter", list(Delimiter))
def test_no_delimiter_can_appear_in_an_iso_timestamp(delimiter: Delimiter) -> None:
    """Desteklenen hiçbir ayırıcı ISO damgasını bölemez."""
    sample = "2026-09-11T08:30:12.500000+00:00"
    assert delimiter.value not in sample


def test_a_delimiter_that_collides_with_the_timestamp_is_refused() -> None:
    """`:` seçilebilseydi tarih alanı ikiye bölünürdü."""

    class _Colon(str):
        value = ":"

    with pytest.raises(TextFormatError, match="zaman damgasında geçiyor"):
        TextFormat(delimiter=_Colon(":"), decimal_separator=".")  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# sayi bicimi
# --------------------------------------------------------------------------- #


def test_a_dot_format_writes_numbers_unchanged() -> None:
    fmt = resolve_format(Delimiter.COMMA)
    assert fmt.format_value(1.5) == "1.5"
    assert fmt.format_value(-0.25) == "-0.25"
    assert fmt.format_value(3.0) == "3.0"


def test_a_comma_format_swaps_only_the_separator() -> None:
    fmt = resolve_format(Delimiter.TAB, ",")
    assert fmt.format_value(1.5) == "1,5"
    assert fmt.format_value(-0.25) == "-0,25"


def test_the_precision_is_not_reduced_by_the_comma_format() -> None:
    """Virgüllü biçim veriyi yuvarlamamalı."""
    value = 1.234567890123456
    assert resolve_format(Delimiter.TAB, ",").format_value(value) == repr(value).replace(".", ",")


def test_special_floats_keep_their_spelling() -> None:
    fmt = resolve_format(Delimiter.TAB, ",")
    assert fmt.format_value(float("inf")) == "inf"
    assert fmt.format_value(float("-inf")) == "-inf"
    assert fmt.format_value(float("nan")) == "nan"


def test_a_formatted_number_never_contains_the_delimiter() -> None:
    """Değişmezin kendisi: hiçbir sayı alanı satırı bölemez."""
    for delimiter in Delimiter:
        for decimal in (".", ","):
            if decimal == delimiter.value:
                continue
            fmt = resolve_format(delimiter, decimal)
            for value in (0.0, 1.5, -1234.5678, 1e-9, 1e21):
                assert delimiter.value not in fmt.format_value(value)


# --------------------------------------------------------------------------- #
# dosyaya yazilan ozet
# --------------------------------------------------------------------------- #


def test_the_format_describes_itself_for_the_metadata_header() -> None:
    assert resolve_format(Delimiter.COMMA).describe() == "delimiter=, decimal=."
    assert resolve_format(Delimiter.TAB, ",").describe() == "delimiter=tab decimal=,"
    assert resolve_format(Delimiter.SEMICOLON).describe() == "delimiter=; decimal=,"


def test_the_comma_decimal_flag_matches_the_separator() -> None:
    assert resolve_format(Delimiter.TAB, ",").uses_comma_decimal
    assert not resolve_format(Delimiter.TAB, ".").uses_comma_decimal
