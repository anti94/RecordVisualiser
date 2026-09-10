"""Formül ifade ve kaynak sınırları — `F4-072`.

Kabul: dosya erişimi, keyfi çağrı ve aşırı ifade reddedilir; eval kullanılmaz.

`F4-070` dilbilgisini, `F4-071` değerlendirmeyi kurdu. Bu dosya aynı yolu
**düşmanca** sınar: kaçış girişimleri, kaynak tüketimi ve "gerçekten
çalıştırmıyor mu" sorusu. Denetim iki düzeyde yapılır — kaynak düzeyinde
(modüllerde `eval`/`exec`/`compile` çağrısı yok) ve **davranış** düzeyinde
(`builtins.eval`, `exec`, `__import__`, `open` patlayacak biçimde
değiştirilir; formül yolu yine de çalışır).

Bu koşu iki gerçek açık buldu ve `F4-070` ayrıştırıcısı ona göre
düzeltildi: büyük bir tamsayı sabiti `OverflowError` sızdırıyordu ve
`1e400` sessizce `inf` sabitine dönüşüp tüm seriyi zehirliyordu. İkisi de
artık `FormulaError`'dur ve aşağıda kayıtlıdır.
"""

from __future__ import annotations

import builtins
import sys
import tracemalloc
from collections.abc import Callable, Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from sonar_analyzer.analysis import formula as formula_module
from sonar_analyzer.analysis import formula_eval as formula_eval_module
from sonar_analyzer.analysis.formula import (
    MAX_DEPTH,
    MAX_FORMULA_LENGTH,
    MAX_NODE_COUNT,
    MAX_POWER_EXPONENT,
    FormulaError,
    parse_formula,
)
from sonar_analyzer.analysis.formula_eval import evaluate_formula
from sonar_analyzer.domain.data_chunk import DataChunk

ALLOWED = {"ch0": "ch0", "ch1": "ch1"}


def _parse(text: str) -> object:
    return parse_formula(text, ALLOWED)


def _chunks(count: int = 16) -> dict[str, DataChunk]:
    times = np.arange(count, dtype=np.int64) * 1_000_000
    return {name: DataChunk(name, times, np.linspace(1.0, 2.0, count)) for name in ("ch0", "ch1")}


# --------------------------------------------------------------------------- #
# dosya erisimi reddedilir
# --------------------------------------------------------------------------- #

#: Dosya sistemine ya da yorumlayıcı içine ulaşmayı deneyen ifadeler.
ESCAPE_ATTEMPTS = [
    'open("/etc/passwd")',
    'open("/etc/passwd").read()',
    '__import__("os").system("echo x")',
    '__import__("subprocess").run("ls")',
    "__builtins__",
    '__builtins__["open"]',
    "__import__",
    "globals()",
    "locals()",
    "vars()",
    'getattr(ch0, "__class__")',
    "ch0.__class__",
    "ch0.__class__.__bases__",
    "().__class__.__base__.__subclasses__()",
    "(1).__class__.__mro__",
    "ch0.__reduce__()",
    "ch0.tobytes()",
    "ch0.__array_interface__",
    'exec("import os")',
    'eval("1+1")',
    'compile("1", "x", "eval")',
    "breakpoint()",
    "input()",
    "help()",
    'Path("x")',
    "os.path",
    "sys.modules",
]


@pytest.mark.parametrize("text", ESCAPE_ATTEMPTS)
def test_no_escape_attempt_is_accepted(text: str) -> None:
    with pytest.raises(FormulaError):
        _parse(text)


def test_parsing_escape_attempts_creates_no_file(tmp_path: Path) -> None:
    """Metin çalıştırılsaydı bu dosyalar oluşurdu."""
    target = tmp_path / "sizinti.txt"
    for template in (
        'open({path!r}, "w").write("x")',
        '__import__("pathlib").Path({path!r}).touch()',
        '__import__("os").mknod({path!r})',
    ):
        with pytest.raises(FormulaError):
            _parse(template.format(path=str(target)))
    assert not target.exists()
    assert list(tmp_path.iterdir()) == []


def test_parsing_escape_attempts_imports_no_module() -> None:
    before = set(sys.modules)
    for text in ESCAPE_ATTEMPTS:
        with pytest.raises(FormulaError):
            _parse(text)
    # `os`/`sys` zaten yuklu olabilir; yeni bir sey yuklenmemis olmali.
    assert set(sys.modules) - before == set()


def test_a_hostile_formula_cannot_reach_the_filesystem_even_as_a_name() -> None:
    """`open` sadece bilinmeyen bir addır; çağrı düğümü zaten reddedilir."""
    with pytest.raises(FormulaError, match="İzinli olmayan ad: 'open'"):
        _parse("open")
    with pytest.raises(FormulaError, match="İzinli olmayan ifade: Call"):
        _parse('open("x")')


# --------------------------------------------------------------------------- #
# keyfi cagri reddedilir
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "text",
    [
        "abs(ch0)",
        "min(ch0, ch1)",
        "sum([ch0])",
        "float(ch0)",
        "int(ch0)",
        "round(ch0)",
        "ch0.mean()",
        "ch0.sum()",
        "(ch0)(ch1)",
        "ch0(*ch1)",
        "ch0(**{})",
        "print(ch0)",
        "type(ch0)",
        "id(ch0)",
        "repr(ch0)",
        "dir(ch0)",
        "setattr(ch0, 'x', 1)",
    ],
)
def test_every_call_shape_is_refused(text: str) -> None:
    with pytest.raises(FormulaError):
        _parse(text)


def test_even_a_harmless_looking_call_is_refused() -> None:
    """Beyaz liste kapalıdır: 'zararsız' fonksiyon diye istisna yok."""
    with pytest.raises(FormulaError, match="İzinli olmayan ifade: Call"):
        _parse("abs(ch0)")


# --------------------------------------------------------------------------- #
# asiri ifade reddedilir
# --------------------------------------------------------------------------- #


def test_a_formula_longer_than_the_limit_is_refused() -> None:
    with pytest.raises(FormulaError, match="çok uzun"):
        _parse("1+" * MAX_FORMULA_LENGTH + "1")


def test_a_very_long_formula_is_refused_before_parsing() -> None:
    """Uzunluk denetimi `ast.parse`'tan **önce** gelir; 1 MB metin ayrıştırılmaz."""
    with pytest.raises(FormulaError, match="çok uzun"):
        _parse("1+" * 500_000 + "1")


def test_redundant_parentheses_do_not_count_as_depth() -> None:
    """Parantez AST düğümü üretmez; derinlik sınırı **işleçlere** bakar.

    `((((ch0))))` tek bir `Name` düğümüdür. İç içe parantezle derinlik
    sınırını zorlamak mümkün değildir; uzunluk sınırı da metni zaten
    500 karakterde keser.
    """
    depth = MAX_DEPTH + 2
    formula = _parse("(" * depth + "ch0" + ")" * depth)
    assert formula.depth == 1  # type: ignore[union-attr]


def test_deeply_nested_operators_are_refused() -> None:
    """Gerçek derinlik iç içe **işlemlerden** gelir."""
    text = "ch0"
    for _ in range(MAX_DEPTH + 1):
        text = f"({text}+1)"
    with pytest.raises(FormulaError, match="çok derin"):
        _parse(text)


def test_deep_unary_nesting_is_refused() -> None:
    with pytest.raises(FormulaError, match="çok derin"):
        _parse("-" * (MAX_DEPTH + 1) + "ch0")


def test_an_exploding_power_tower_is_refused() -> None:
    """`2**2**2**...` değerlendirmede belleği tüketirdi."""
    with pytest.raises(FormulaError):
        _parse("2**" * 10 + "2")


@pytest.mark.parametrize("text", ["2 ** 9", "ch0 ** 100", "ch0 ** -50"])
def test_an_oversized_exponent_is_refused(text: str) -> None:
    with pytest.raises(FormulaError, match="üssü"):
        _parse(text)


def test_the_exponent_limit_is_exactly_at_the_constant() -> None:
    _parse(f"ch0 ** {MAX_POWER_EXPONENT}")
    with pytest.raises(FormulaError, match="çok büyük"):
        _parse(f"ch0 ** {MAX_POWER_EXPONENT + 1}")


# -- bu kosunun buldugu iki acik ------------------------------------------- #


@pytest.mark.parametrize("text", ["1e400", "-1e400", "1e309 * ch0", "1e400 + ch0"])
def test_a_non_finite_literal_is_refused(text: str) -> None:
    """`1e400` sessizce `inf` olup tüm seriyi zehirliyordu (`F4-072` bulgusu)."""
    with pytest.raises(FormulaError, match="sonlu olmalı"):
        _parse(text)


def test_the_largest_finite_literal_is_still_accepted() -> None:
    assert _parse("1e308 * ch0") is not None


@pytest.mark.parametrize("digits", [400, 350])
def test_an_integer_literal_too_large_for_a_float_is_refused(digits: int) -> None:
    """`OverflowError` sızdırıyordu; artık `FormulaError` (`F4-072` bulgusu)."""
    with pytest.raises(FormulaError, match="çok büyük"):
        _parse("9" * digits)


def test_a_large_integer_inside_an_expression_is_also_refused() -> None:
    with pytest.raises(FormulaError, match="çok büyük"):
        _parse("ch0 * " + "9" * 400)


# --------------------------------------------------------------------------- #
# hicbir girdi beklenmeyen istisna uretmez
# --------------------------------------------------------------------------- #

#: Ayrıştırıcıyı `FormulaError` dışında bir istisnaya zorlama denemeleri.
HOSTILE_INPUTS = [
    "",
    " ",
    "\t\n",
    "\x00",
    "ch0\x00",
    "﻿ch0",
    "# yorum",
    "ch0 # yorum",
    "ch0\n+ch1",
    "ch0\\",
    "((((",
    "))))",
    "+",
    "**",
    "1 2",
    "1..2",
    "0x",
    "1e",
    "..",
    "ch0..ch1",
    "'''",
    '"""',
    "\\x63h0",
    "ch ",
    "𝕔𝕙𝟘",
    "ch0" * 200,
    "-" * 400,
    "(" * 400,
]


@pytest.mark.parametrize("text", HOSTILE_INPUTS)
def test_hostile_input_raises_only_a_formula_error(text: str) -> None:
    """Sözleşme: bu yol `FormulaError` dışında bir şey fırlatmaz."""
    try:
        parse_formula(text, ALLOWED)
    except FormulaError:
        return
    except Exception as exc:
        pytest.fail(f"{text!r} beklenmeyen istisna verdi: {type(exc).__name__}: {exc}")


def test_a_normalised_unicode_name_resolves_to_the_same_channel() -> None:
    """Python tanımlayıcıları NFKC normalize eder; `ｃｈ０` yine `ch0`'dır.

    Bu bir kaçış değil: sonuç yine **izinli** bir ada çözülür, yeni bir
    yetki açılmaz. Davranış kayda geçsin diye sınanır.
    """
    formula = parse_formula("ｃｈ０ + 1", ALLOWED)
    assert formula.channel_ids == ("ch0",)  # type: ignore[union-attr]


# --------------------------------------------------------------------------- #
# eval kullanilmaz — kaynak ve davranis kaniti
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("module", [formula_module, formula_eval_module])
def test_neither_module_calls_eval_exec_or_compile(module: Any) -> None:
    source = Path(module.__file__).read_text(encoding="utf-8")
    body = "\n".join(line for line in source.splitlines() if not line.lstrip().startswith("#"))
    for forbidden in ("eval(", "exec(", "compile(", "__import__("):
        assert forbidden not in body, f"{module.__name__} içinde {forbidden}"


@contextmanager
def watched_builtins() -> Generator[list[str], None, None]:
    """`eval`/`exec`/`__import__`/`open` çağrılarını **kaydeder**.

    Patlatmak yerine kaydetmek gerekir: patlayan bir `open`/`__import__`
    pytest'in kendi raporlamasını da bozar. Sarmalayıcılar asıl işlevi
    çağırdığı için ortam bozulmaz; kanıt, listenin boş kalmasıdır.

    `compile` **kasten** izlenmez: `ast.parse` onu `PyCF_ONLY_AST` kipinde
    çağırır ve o kip kod çalıştırmaz, yalnız sözdizimi ağacı üretir.
    """
    seen: list[str] = []
    originals = {name: getattr(builtins, name) for name in ("eval", "exec", "__import__", "open")}

    def wrap(name: str) -> Callable[..., Any]:
        original = originals[name]

        def recorder(*args: Any, **kwargs: Any) -> Any:
            seen.append(name)
            return original(*args, **kwargs)

        return recorder

    for name in originals:
        setattr(builtins, name, wrap(name))
    try:
        yield seen
    finally:
        for name, original in originals.items():
            setattr(builtins, name, original)


def test_parsing_never_touches_eval_exec_import_or_open() -> None:
    with watched_builtins() as seen:
        formula = parse_formula("ch0 * 2 + ch1", ALLOWED)
    assert seen == []
    assert formula.channel_ids == ("ch0", "ch1")


def test_evaluation_never_touches_eval_exec_import_or_open() -> None:
    chunks = _chunks()
    formula = parse_formula("ch0 + ch1", ALLOWED)
    # NumPy ilk kullanımda kendi alt modüllerini tembel yükler; o import
    # bizim kodumuz değil. Isınma koşusu ölçümü kendi yolumuza daraltır.
    evaluate_formula(formula, chunks)
    with watched_builtins() as seen:
        result = evaluate_formula(formula, chunks)
    assert seen == []
    assert np.array_equal(result.values, chunks["ch0"].values + chunks["ch1"].values)


@pytest.mark.parametrize("text", ['open("x")', '__import__("os")', 'eval("1")'])
def test_refusing_a_hostile_formula_never_touches_them_either(text: str) -> None:
    """Reddetme, adı çağırmaya hiç yaklaşmadan olmalı."""
    with watched_builtins() as seen, pytest.raises(FormulaError):
        parse_formula(text, ALLOWED)
    assert seen == []


# --------------------------------------------------------------------------- #
# degerlendirme de sinirli kalir
# --------------------------------------------------------------------------- #


def test_the_largest_allowed_formula_evaluates_within_a_bounded_footprint() -> None:
    """Sınırlar yalnız ayrıştırmayı değil, değerlendirmeyi de bağlar.

    Sınırdaki bir formül (`MAX_NODE_COUNT` düğüme yakın) 100.000 örneklik
    bir dizide çalıştırıldığında ayrılan bellek, düğüm sayısı × dizi
    boyutuyla orantılı bir üst sınırın altında kalır.
    """
    count = 100_000
    times = np.arange(count, dtype=np.int64) * 1_000
    chunks = {"ch0": DataChunk("ch0", times, np.ones(count))}
    text = "+".join(["ch0"] * (MAX_DEPTH - 1))
    formula = parse_formula(text, ALLOWED)
    array_bytes = count * 8

    tracemalloc.start()
    try:
        result = evaluate_formula(formula, chunks)
        _current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    assert np.array_equal(result.values, np.full(count, float(MAX_DEPTH - 1)))
    # Her ikili işlem en fazla bir geçici dizi üretir; ara sonuçlar birikmez.
    assert peak < array_bytes * 6


def test_the_node_limit_bounds_the_number_of_temporaries() -> None:
    """Düğüm sayısı sınırı değerlendirmedeki geçici dizi sayısını da bağlar."""
    with pytest.raises(FormulaError, match="çok karmaşık"):
        parse_formula(_balanced("1", 101), ALLOWED)  # 101 yaprak + 100 islec


def _balanced(leaf: str, count: int) -> str:
    parts = [leaf] * count
    while len(parts) > 1:
        parts = [
            f"({parts[i]}+{parts[i + 1]})" if i + 1 < len(parts) else parts[i]
            for i in range(0, len(parts), 2)
        ]
    return parts[0]


def test_the_documented_limits_are_the_enforced_ones() -> None:
    """Belgelenen sayı ile uygulanan sayı ayrışmasın."""
    assert MAX_FORMULA_LENGTH == 500
    assert MAX_NODE_COUNT == 200
    assert MAX_DEPTH == 20
    assert MAX_POWER_EXPONENT == 8
    with pytest.raises(FormulaError):
        _parse("1" * (MAX_FORMULA_LENGTH + 1))
