"""Sınırlı aritmetik formül ayrıştırıcısı — `F4-070`.

Kabul: yalnız izinli kanal, sabit ve aritmetik düğümleri kabul edilir.

Kabul edilenler tek tek ve **ürettikleri ağaçla** denetlenir; reddedilenler
Python dilbilgisinin geri kalanını temsil eden geniş bir listeyle taranır.
Ayrıştırıcı kullanıcı metnini hiçbir zaman çalıştırmaz — `eval`/`exec`
kullanılmadığı da ayrıca sınanır (`F4-072` sınırları derinleştirir).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sonar_analyzer.analysis import formula as formula_module
from sonar_analyzer.analysis.formula import (
    MAX_DEPTH,
    MAX_FORMULA_LENGTH,
    MAX_NODE_COUNT,
    MAX_POWER_EXPONENT,
    BinaryOp,
    ChannelRef,
    Formula,
    FormulaError,
    Literal,
    UnaryOp,
    aliases_for,
    parse_formula,
)

ALLOWED = {"ch0": "ch0", "ch1": "ch1", "a": "derived:ab12"}


def _parse(text: str) -> Formula:
    return parse_formula(text, ALLOWED)


# --------------------------------------------------------------------------- #
# izinli adlar
# --------------------------------------------------------------------------- #


def test_a_channel_name_becomes_a_channel_reference() -> None:
    assert _parse("ch0").root == ChannelRef(name="ch0", channel_id="ch0")


def test_an_alias_resolves_to_its_channel_id() -> None:
    """Kanal kimliği tanımlayıcı olmasa da takma adla kullanılabilir."""
    assert _parse("a").root == ChannelRef(name="a", channel_id="derived:ab12")
    assert _parse("a").channel_ids == ("derived:ab12",)


def test_an_unknown_name_is_refused_and_lists_the_allowed_ones() -> None:
    with pytest.raises(FormulaError, match="İzinli olmayan ad: 'ch9'") as error:
        _parse("ch9")
    assert "ch0, ch1" in str(error.value)


def test_with_no_allowed_names_only_constant_arithmetic_is_possible() -> None:
    assert parse_formula("2 * 3", {}).channel_ids == ()
    with pytest.raises(FormulaError, match=r"\(yok\)"):
        parse_formula("ch0", {})


def test_an_allowed_name_that_is_not_an_identifier_is_refused() -> None:
    """Çağıran hatalı bir eşleme verirse ayrıştırıcı sessiz kalmaz."""
    with pytest.raises(FormulaError, match="geçerli bir tanımlayıcı değil"):
        parse_formula("ch0", {"derived:ab": "derived:ab"})


@pytest.mark.parametrize("reserved", ["True", "False", "None"])
def test_a_reserved_word_cannot_be_an_allowed_name(reserved: str) -> None:
    with pytest.raises(FormulaError, match="tanımlayıcı"):
        parse_formula("1", {reserved: "ch0"})


def test_aliases_for_maps_identifier_ids_to_themselves() -> None:
    assert aliases_for(["ch0", "ch1"]) == {"ch0": "ch0", "ch1": "ch1"}


def test_aliases_for_skips_ids_that_cannot_be_written_in_a_formula() -> None:
    assert aliases_for(["ch0", "derived:ab12", "ch0#resampled", "", "2ch"]) == {"ch0": "ch0"}


# --------------------------------------------------------------------------- #
# sabitler
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(("text", "value"), [("2", 2.0), ("2.5", 2.5), ("1e3", 1000.0), ("0", 0.0)])
def test_a_number_becomes_a_float_literal(text: str, value: float) -> None:
    root = _parse(text).root
    assert root == Literal(value=value)
    assert isinstance(root.value, float)  # type: ignore[union-attr]


@pytest.mark.parametrize("text", ["True", "False", "None", '"metin"', "'x'", "b'x'"])
def test_a_non_numeric_constant_is_refused(text: str) -> None:
    with pytest.raises(FormulaError):
        _parse(text)


def test_a_boolean_is_not_accepted_as_a_number() -> None:
    """`bool` `int`'in alt sınıfıdır; sessizce 1.0 olmamalı."""
    with pytest.raises(FormulaError, match="Yalnız sayı sabitine"):
        _parse("True")


# --------------------------------------------------------------------------- #
# aritmetik dugumler
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("op", ["+", "-", "*", "/"])
def test_each_allowed_binary_operator_is_accepted(op: str) -> None:
    root = _parse(f"ch0 {op} ch1")
    assert root.root == BinaryOp(
        op=op,
        left=ChannelRef("ch0", "ch0"),
        right=ChannelRef("ch1", "ch1"),
    )


@pytest.mark.parametrize("op", ["+", "-"])
def test_each_allowed_unary_operator_is_accepted(op: str) -> None:
    assert _parse(f"{op}ch0").root == UnaryOp(op=op, operand=ChannelRef("ch0", "ch0"))


def test_precedence_and_parentheses_are_preserved() -> None:
    flat = _parse("ch0 + ch1 * 2").root
    assert isinstance(flat, BinaryOp) and flat.op == "+"
    assert isinstance(flat.right, BinaryOp) and flat.right.op == "*"

    grouped = _parse("(ch0 + ch1) * 2").root
    assert isinstance(grouped, BinaryOp) and grouped.op == "*"
    assert isinstance(grouped.left, BinaryOp) and grouped.left.op == "+"


@pytest.mark.parametrize("text", ["ch0 // 2", "ch0 % 2", "ch0 @ ch1"])
def test_an_arithmetic_operator_outside_the_list_is_refused(text: str) -> None:
    with pytest.raises(FormulaError, match="İzinli olmayan işleç"):
        _parse(text)


@pytest.mark.parametrize("text", ["ch0 << 2", "ch0 & ch1", "ch0 | ch1", "ch0 ^ ch1"])
def test_bitwise_operators_are_refused(text: str) -> None:
    with pytest.raises(FormulaError, match="İzinli olmayan işleç"):
        _parse(text)


def test_bitwise_not_is_refused() -> None:
    with pytest.raises(FormulaError, match="tekli işleç"):
        _parse("~ch0")


def test_logical_not_is_refused() -> None:
    with pytest.raises(FormulaError, match="tekli işleç"):
        _parse("not ch0")


# --------------------------------------------------------------------------- #
# ust alma sinirli
# --------------------------------------------------------------------------- #


def test_a_small_constant_exponent_is_accepted() -> None:
    assert _parse("ch0 ** 2").root == BinaryOp(
        op="**", left=ChannelRef("ch0", "ch0"), right=Literal(2.0)
    )


def test_a_negative_constant_exponent_is_accepted() -> None:
    root = _parse("ch0 ** -2").root
    assert isinstance(root, BinaryOp)
    assert root.right == UnaryOp(op="-", operand=Literal(2.0))


def test_a_large_exponent_is_refused() -> None:
    with pytest.raises(FormulaError, match="üssü çok büyük"):
        _parse(f"2 ** {MAX_POWER_EXPONENT + 1}")


def test_a_large_negative_exponent_is_refused() -> None:
    with pytest.raises(FormulaError, match="üssü çok büyük"):
        _parse(f"2 ** -{MAX_POWER_EXPONENT + 1}")


def test_the_exponent_limit_is_inclusive() -> None:
    assert _parse(f"ch0 ** {MAX_POWER_EXPONENT}") is not None


def test_a_non_constant_exponent_is_refused() -> None:
    """`ch0 ** ch1` değerlendirme sırasında sınırsız büyüyebilirdi."""
    with pytest.raises(FormulaError, match="üssü sabit"):
        _parse("ch0 ** ch1")


def test_a_computed_exponent_is_refused() -> None:
    with pytest.raises(FormulaError, match="üssü sabit"):
        _parse("2 ** (3 * 4)")


# --------------------------------------------------------------------------- #
# Python'un geri kalani reddedilir
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "text",
    [
        '__import__("os")',
        'open("/etc/passwd")',
        "eval('1')",
        "print(ch0)",
        "abs(ch0)",
        "ch0.real",
        "ch0.__class__",
        "ch0[0]",
        "ch0[0:2]",
        "ch0 and ch1",
        "ch0 or ch1",
        "ch0 > 1",
        "ch0 == ch1",
        "lambda: 1",
        "ch0 if ch0 else ch1",
        "[c for c in ch0]",
        "{ch0: ch1}",
        "{ch0, ch1}",
        "(ch0, ch1)",
        "[ch0, ch1]",
        'f"{ch0}"',
        "...",
        "*ch0",
        "await ch0",
        "yield ch0",
    ],
)
def test_anything_outside_the_allowed_grammar_is_refused(text: str) -> None:
    with pytest.raises(FormulaError):
        _parse(text)


@pytest.mark.parametrize("text", ["ch0 = 1", "ch0; ch1", "import os", "del ch0", "ch0 += 1"])
def test_statements_are_refused_by_the_parser(text: str) -> None:
    with pytest.raises(FormulaError):
        _parse(text)


def test_a_walrus_assignment_is_refused() -> None:
    with pytest.raises(FormulaError):
        _parse("(x := ch0)")


def test_dunder_names_are_just_unknown_names() -> None:
    with pytest.raises(FormulaError, match="İzinli olmayan ad"):
        _parse("__builtins__")


# --------------------------------------------------------------------------- #
# kaynak sinirlari
# --------------------------------------------------------------------------- #


def test_an_empty_formula_is_refused() -> None:
    with pytest.raises(FormulaError, match="boş olamaz"):
        _parse("   ")


def test_a_non_string_formula_is_refused() -> None:
    with pytest.raises(FormulaError, match="metin olmalı"):
        parse_formula(123, ALLOWED)  # type: ignore[arg-type]


def test_an_overlong_formula_is_refused() -> None:
    text = "ch0 + " * (MAX_FORMULA_LENGTH // 6 + 1) + "ch0"
    assert len(text) > MAX_FORMULA_LENGTH
    with pytest.raises(FormulaError, match="çok uzun"):
        _parse(text)


def _balanced_sum(leaf_count: int) -> str:
    """`leaf_count` sabitin dengeli toplamı: geniş ama **sığ** bir ifade.

    Soldan birleşen `1+1+1...` zinciri derinlik sınırına önce takılır;
    düğüm sınırının kendi başına çalıştığını göstermek için ağacın
    dengeli olması gerekir.
    """
    parts = ["1"] * leaf_count
    while len(parts) > 1:
        parts = [
            f"({parts[i]}+{parts[i + 1]})" if i + 1 < len(parts) else parts[i]
            for i in range(0, len(parts), 2)
        ]
    return parts[0]


def test_a_formula_with_too_many_nodes_is_refused() -> None:
    """Uzunluk ve derinlik sınırına takılmadan düğüm sınırına takılan ifade."""
    text = _balanced_sum(101)  # 101 yaprak + 100 islec = 201 dugum
    assert len(text) <= MAX_FORMULA_LENGTH
    with pytest.raises(FormulaError, match="çok karmaşık"):
        _parse(text)


def test_a_formula_just_under_the_node_limit_is_accepted() -> None:
    result = _parse(_balanced_sum(64))
    assert result.node_count == 127 <= MAX_NODE_COUNT
    assert result.depth <= MAX_DEPTH


def test_a_deeply_nested_formula_is_refused() -> None:
    text = "-" * (MAX_DEPTH + 1) + "ch0"
    with pytest.raises(FormulaError, match="çok derin"):
        _parse(text)


def test_a_long_left_associative_chain_hits_the_depth_limit() -> None:
    """`a+a+a...` soldan birleşir; her terim bir seviye derinleştirir."""
    with pytest.raises(FormulaError, match="çok derin"):
        _parse("+".join(["ch0"] * (MAX_DEPTH + 2)))


def test_the_limits_are_documented_as_constants() -> None:
    assert (MAX_FORMULA_LENGTH, MAX_NODE_COUNT, MAX_DEPTH, MAX_POWER_EXPONENT) == (
        500,
        200,
        20,
        8,
    )


# --------------------------------------------------------------------------- #
# calistirilmaz
# --------------------------------------------------------------------------- #


def test_the_parser_module_never_calls_eval_or_exec() -> None:
    """Kaynak düzeyinde kanıt: modülde `eval`/`exec` çağrısı yok."""
    source = Path(formula_module.__file__).read_text(encoding="utf-8")
    code_lines = [line for line in source.splitlines() if not line.strip().startswith("#")]
    body = "\n".join(code_lines)
    assert "eval(" not in body
    assert "exec(" not in body
    assert "compile(" not in body


def test_parsing_a_hostile_formula_has_no_side_effect(tmp_path: Path) -> None:
    """Ayrıştırma metni çalıştırsaydı bu dosya oluşurdu."""
    target = tmp_path / "olusmamali.txt"
    hostile = f'open({str(target)!r}, "w").write("x")'
    with pytest.raises(FormulaError):
        _parse(hostile)
    assert not target.exists()


# --------------------------------------------------------------------------- #
# formul ozeti
# --------------------------------------------------------------------------- #


def test_the_formula_reports_its_channels_in_first_appearance_order() -> None:
    result = _parse("ch1 * 2 + ch0 - ch1")
    assert result.names == ("ch1", "ch0")
    assert result.channel_ids == ("ch1", "ch0")


def test_the_formula_keeps_its_trimmed_text() -> None:
    assert _parse("  ch0 + 1  ").text == "ch0 + 1"


def test_the_formula_reports_its_size() -> None:
    result = _parse("(ch0 + ch1) * 2")
    assert result.node_count == 5  # 2 kanal + 2 sabit/islec + kok
    assert result.depth == 3


def test_a_constant_only_formula_declares_no_channels() -> None:
    result = _parse("2 * 3 + 1")
    assert result.channel_ids == ()
    assert result.names == ()
