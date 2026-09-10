"""Sınırlı aritmetik formül ayrıştırıcısı — `F4-070`.

Kullanıcı bir türetilmiş kanalı `ch0 * 2 - ch1` gibi bir ifadeyle
tanımlayabilir. Bu modül o metni **çalıştırmadan** ayrıştırır ve yalnız
üç şeye izin verir:

* **izinli kanal** adları (çağıranın verdiği ad → kanal kimliği eşlemesi),
* **sayı sabitleri** (`int` / `float`; `bool` değil),
* **aritmetik düğümler** (`+ - * / **` ve tekli `+ -`).

Başka her şey reddedilir: fonksiyon çağrısı, öznitelik erişimi, indeksleme,
karşılaştırma, mantıksal işlem, metin, atama, lambda, comprehension, walrus,
bilinmeyen ad. **`eval` / `exec` kullanılmaz**; `ast.parse` yalnız sözdizimi
ağacı üretir, ağaç kendi düğüm tiplerimize çevrilir ve yorumlama `F4-071`'in
işidir. Böylece ayrıştırma aşamasında kullanıcı metni hiçbir zaman kod
olarak çalışmaz.

Kaynak sınırları da burada uygulanır (`F4-072` bunları ayrıca sınar): metin
uzunluğu, düğüm sayısı, ağaç derinliği ve `**` üssünün büyüklüğü.

Saf Python — Qt yok, `GUI olmadan` doğrulanır.
"""

from __future__ import annotations

import ast
import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Union, cast

#: Kabul edilen ikili işleçler ve `ast` düğümleri.
BINARY_OPERATORS: dict[type[ast.operator], str] = {
    ast.Add: "+",
    ast.Sub: "-",
    ast.Mult: "*",
    ast.Div: "/",
    ast.Pow: "**",
}
#: Kabul edilen tekli işleçler.
UNARY_OPERATORS: dict[type[ast.unaryop], str] = {ast.UAdd: "+", ast.USub: "-"}

#: Kaynak sınırları — aşırı ifade reddedilir (`F4-072`).
MAX_FORMULA_LENGTH = 500
MAX_NODE_COUNT = 200
MAX_DEPTH = 20
#: `**` üssü sabit olmalı ve bu aralıkta kalmalı; `2 ** 10**9` reddedilir.
MAX_POWER_EXPONENT = 8


class FormulaError(ValueError):
    """Formül izin verilen dilbilgisinin dışında veya sınırları aşıyor."""


@dataclass(frozen=True)
class ChannelRef:
    """Bir kanal değerine başvuru."""

    name: str
    channel_id: str


@dataclass(frozen=True)
class Literal:
    """Sayı sabiti; her zaman `float` olarak taşınır."""

    value: float


@dataclass(frozen=True)
class UnaryOp:
    """Tekli `+` veya `-`."""

    op: str
    operand: Node


@dataclass(frozen=True)
class BinaryOp:
    """İkili aritmetik işlem."""

    op: str
    left: Node
    right: Node


Node = Union[ChannelRef, Literal, UnaryOp, BinaryOp]


@dataclass(frozen=True)
class Formula:
    """Ayrıştırılmış, doğrulanmış ve **çalıştırılmamış** formül."""

    text: str
    root: Node
    #: Formülde ilk görülme sırasıyla, tekrarsız kanal kimlikleri.
    channel_ids: tuple[str, ...]
    #: Formülde geçen adlar, ilk görülme sırasıyla.
    names: tuple[str, ...]

    @property
    def node_count(self) -> int:
        return _count(self.root)

    @property
    def depth(self) -> int:
        return _depth(self.root)


def aliases_for(channel_ids: Iterable[str]) -> dict[str, str]:
    """Formülde doğrudan yazılabilen kanal kimlikleri için birebir eşleme.

    `ch0` gibi geçerli Python tanımlayıcısı olan kimlikler kendi adlarıyla
    kullanılabilir. `derived:ab12` gibi kimlikler tanımlayıcı olmadığı için
    atlanır; onlara bir takma ad verilmelidir (`{"a": "derived:ab12"}`).
    """
    return {
        channel_id: channel_id
        for channel_id in channel_ids
        if channel_id.isidentifier() and not _is_reserved(channel_id)
    }


def _is_reserved(name: str) -> bool:
    """Sabitlerle karışan adlar kanal adı olamaz."""
    return name in {"True", "False", "None"}


def parse_formula(text: str, allowed_names: Mapping[str, str]) -> Formula:
    """`text`'i ayrıştırır; yalnız izinli kanal, sabit ve aritmetiğe izin verir.

    `allowed_names` formülde yazılabilecek **ad → kanal kimliği** eşlemesidir;
    burada olmayan hiçbir ad kabul edilmez (boş eşlemeyle yalnız sabit
    aritmetiği yazılabilir).
    """
    # Tip denetlenmemis cagiran da temiz bir hata almali.
    if not isinstance(cast("object", text), str):
        raise FormulaError(f"Formül metin olmalı, verilen: {type(text).__name__}")
    stripped = text.strip()
    if not stripped:
        raise FormulaError("Formül boş olamaz")
    if len(stripped) > MAX_FORMULA_LENGTH:
        raise FormulaError(
            f"Formül çok uzun: {len(stripped)} karakter, en fazla {MAX_FORMULA_LENGTH}"
        )
    for name in allowed_names:
        if not name.isidentifier() or _is_reserved(name):
            raise FormulaError(f"İzinli ad geçerli bir tanımlayıcı değil: {name!r}")

    try:
        tree = ast.parse(stripped, mode="eval")
    except (SyntaxError, ValueError, MemoryError) as exc:
        raise FormulaError(f"Formül ayrıştırılamadı: {exc}") from exc
    except RecursionError as exc:  # pragma: no cover - asiri ic ice parantez
        raise FormulaError("Formül çok derin iç içe geçmiş") from exc

    names: list[str] = []
    root = _convert(tree.body, allowed_names, names, depth=1)

    formula = Formula(
        text=stripped,
        root=root,
        channel_ids=tuple(dict.fromkeys(allowed_names[name] for name in names)),
        names=tuple(names),
    )
    if formula.node_count > MAX_NODE_COUNT:
        raise FormulaError(
            f"Formül çok karmaşık: {formula.node_count} düğüm, en fazla {MAX_NODE_COUNT}"
        )
    return formula


def _convert(
    node: ast.expr,
    allowed_names: Mapping[str, str],
    names: list[str],
    depth: int,
) -> Node:
    """Doğrulanmış `ast` düğümünü kendi düğümümüze çevirir."""
    if depth > MAX_DEPTH:
        raise FormulaError(f"Formül çok derin: en fazla {MAX_DEPTH} seviye")

    if isinstance(node, ast.Name):
        if not isinstance(node.ctx, ast.Load):
            raise FormulaError(f"Formülde atama yapılamaz: {node.id!r}")
        if node.id not in allowed_names:
            allowed = ", ".join(sorted(allowed_names)) or "(yok)"
            raise FormulaError(f"İzinli olmayan ad: {node.id!r}. İzinliler: {allowed}")
        if node.id not in names:
            names.append(node.id)
        return ChannelRef(name=node.id, channel_id=allowed_names[node.id])

    if isinstance(node, ast.Constant):
        value = node.value
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise FormulaError(f"Yalnız sayı sabitine izin verilir, verilen: {value!r}")
        try:
            number = float(value)
        except OverflowError as exc:
            # `9`*400 gibi bir tamsayı `float`'a sığmaz; çağıran `FormulaError`
            # bekler, `OverflowError` değil.
            raise FormulaError(f"Sayı sabiti çok büyük: {str(value)[:32]}…") from exc
        if not math.isfinite(number):
            # `1e400` sessizce `inf` olur ve tüm seriyi zehirlerdi.
            raise FormulaError(f"Sayı sabiti sonlu olmalı, verilen: {value!r}")
        return Literal(value=number)

    if isinstance(node, ast.UnaryOp):
        symbol = UNARY_OPERATORS.get(type(node.op))
        if symbol is None:
            raise FormulaError(f"İzinli olmayan tekli işleç: {type(node.op).__name__}")
        return UnaryOp(op=symbol, operand=_convert(node.operand, allowed_names, names, depth + 1))

    if isinstance(node, ast.BinOp):
        symbol = BINARY_OPERATORS.get(type(node.op))
        if symbol is None:
            raise FormulaError(f"İzinli olmayan işleç: {type(node.op).__name__}")
        left = _convert(node.left, allowed_names, names, depth + 1)
        right = _convert(node.right, allowed_names, names, depth + 1)
        if symbol == "**":
            _check_exponent(right)
        return BinaryOp(op=symbol, left=left, right=right)

    raise FormulaError(f"İzinli olmayan ifade: {type(node).__name__}")


def _check_exponent(exponent: Node) -> None:
    """`**` üssü sabit ve küçük olmalı; yoksa değerlendirme patlatılabilir."""
    value: float | None = None
    if isinstance(exponent, Literal):
        value = exponent.value
    elif isinstance(exponent, UnaryOp) and isinstance(exponent.operand, Literal):
        value = -exponent.operand.value if exponent.op == "-" else exponent.operand.value
    if value is None:
        raise FormulaError("`**` üssü sabit bir sayı olmalı")
    if abs(value) > MAX_POWER_EXPONENT:
        raise FormulaError(f"`**` üssü çok büyük: {value:g}, en fazla ±{MAX_POWER_EXPONENT}")


def _count(node: Node) -> int:
    if isinstance(node, (ChannelRef, Literal)):
        return 1
    if isinstance(node, UnaryOp):
        return 1 + _count(node.operand)
    return 1 + _count(node.left) + _count(node.right)


def _depth(node: Node) -> int:
    if isinstance(node, (ChannelRef, Literal)):
        return 1
    if isinstance(node, UnaryOp):
        return 1 + _depth(node.operand)
    return 1 + max(_depth(node.left), _depth(node.right))
