"""Formülü kanal dizilerine bağlar — `F4-071`.

`F4-070` metni ayrıştırdı ve doğruladı; bu modül o ağacı gerçek kanal
verisiyle **değerlendirir**. Değerlendirme saf NumPy'dir: ağaç düğüm düğüm
dolaşılır, `eval` yine kullanılmaz.

**Zaman hizası sözleşmesi.** Bir formüldeki kanallar aynı zaman ızgarasında
olmalıdır: `timestamps_ns` dizileri **birebir** eşit olmalıdır. Farklı
ızgaralardaki dizileri sessizce hizalamak (kırpmak, doldurmak, enterpole
etmek) kullanıcıya yanlış veriyi doğru gibi gösterirdi. Bu yüzden
uyuşmazlık bir hatadır — ama **açıklanan** bir hata: hangi iki kanalın
neden uyuşmadığı (uzunluk, başlangıç, adım ya da ilk farklı damganın
indeksi) mesajda yazar.

`F4-005` geçersiz veri politikası korunur: NaN/±Inf yayılır, sonuçtaki
sonlu olmayan örnekler `Quality.SUSPECT` ile işaretlenir ve girdilerin
kalite bayrakları birleştirilir.
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
from numpy.typing import NDArray

from sonar_analyzer.analysis.formula import (
    ChannelRef,
    Formula,
    FormulaError,
    Literal,
    Node,
    UnaryOp,
)
from sonar_analyzer.domain.data_chunk import DataChunk, Quality

Samples = NDArray[np.float64]


class FormulaAlignmentError(FormulaError):
    """Formüldeki kanallar aynı zaman ızgarasında değil."""


class FormulaInputError(FormulaError):
    """Formülün istediği bir kanal verilmedi ya da zaman tabanı yok."""


def describe_misalignment(
    first_id: str,
    first: NDArray[np.int64],
    second_id: str,
    second: NDArray[np.int64],
) -> str:
    """İki zaman dizisinin **neden** uyuşmadığını insan diliyle söyler."""
    if first.size != second.size:
        return (
            f"farklı örnek sayısı: {first_id} {first.size}, {second_id} {second.size}. "
            f"Aynı zaman aralığını aynı örnekleme hızında sorgulayın."
        )
    if first.size == 0:
        return "her ikisi de boş"  # pragma: no cover - esit ve bos ise uyusurlar
    if first[0] != second[0]:
        return (
            f"farklı başlangıç: {first_id} t={int(first[0])} ns, "
            f"{second_id} t={int(second[0])} ns (fark {int(second[0] - first[0])} ns)"
        )
    if first.size > 1:
        first_step = int(first[1] - first[0])
        second_step = int(second[1] - second[0])
        if first_step != second_step:
            return (
                f"farklı örnekleme adımı: {first_id} {first_step} ns, "
                f"{second_id} {second_step} ns "
                f"({_rate_text(first_step)} / {_rate_text(second_step)})"
            )
    index = int(np.flatnonzero(first != second)[0])
    return (
        f"aynı uzunluk ve başlangıç, ama zaman damgaları farklı; "
        f"ilk fark {index}. örnekte: {first_id} t={int(first[index])} ns, "
        f"{second_id} t={int(second[index])} ns"
    )


def _rate_text(step_ns: int) -> str:
    if step_ns <= 0:
        return "tanımsız hız"
    return f"{1e9 / step_ns:g} Hz"


def _aligned_timestamps(formula: Formula, chunks: Mapping[str, DataChunk]) -> NDArray[np.int64]:
    """Formülün kanallarının ortak zaman ızgarası; uyuşmazsa açıklar."""
    if not formula.channel_ids:
        raise FormulaInputError(
            f"'{formula.text}' hiçbir kanala bakmıyor, bu yüzden bir zaman tabanı yok. "
            f"Sabit bir seriye ihtiyaç varsa bir kanalla çarpın (örn. `ch0 * 0 + 5`)."
        )
    missing = [cid for cid in formula.channel_ids if cid not in chunks]
    if missing:
        raise FormulaInputError(
            f"Formülün istediği kanal verilmedi: {missing}; verilenler {sorted(chunks)}"
        )

    reference_id = formula.channel_ids[0]
    reference = chunks[reference_id].timestamps_ns
    for channel_id in formula.channel_ids[1:]:
        other = chunks[channel_id].timestamps_ns
        if other.shape != reference.shape or not np.array_equal(other, reference):
            raise FormulaAlignmentError(
                f"'{formula.text}' değerlendirilemedi: {reference_id} ve {channel_id} "
                f"aynı zaman ızgarasında değil — "
                f"{describe_misalignment(reference_id, reference, channel_id, other)}"
            )
    return reference


def evaluate_formula(
    formula: Formula,
    chunks: Mapping[str, DataChunk],
    *,
    channel_id: str = "formula",
) -> DataChunk:
    """Formülü verilen kanal parçalarıyla değerlendirir.

    Kanalların zaman dizileri birebir eşit olmalıdır; değilse
    `FormulaAlignmentError` **nedeni açıklayarak** yükselir.
    """
    timestamps = _aligned_timestamps(formula, chunks)
    arrays = {cid: np.asarray(chunks[cid].values, dtype=np.float64) for cid in formula.channel_ids}
    # Sıfıra bölme ve taşma NaN/Inf üretir; uyarı değil, veri olarak yayılır.
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        values = _evaluate(formula.root, arrays, timestamps.size)
    if any(values is array for array in arrays.values()):
        # Çıplak `ch0` girdinin kendisini döndürürdü; sonucu değiştirmek
        # kaynağı bozardı. Sonuç her zaman kendi dizisidir.
        values = values.copy()

    return DataChunk(
        channel_id=channel_id,
        timestamps_ns=timestamps,
        values=values,
        quality=_combined_quality(formula, chunks, values),
    )


def _combined_quality(
    formula: Formula,
    chunks: Mapping[str, DataChunk],
    values: Samples,
) -> NDArray[np.uint8] | None:
    """Girdi bayraklarının birleşimi + sonuçtaki sonlu olmayan örnekler."""
    combined = np.zeros(values.size, dtype=np.uint8)
    seen = False
    for channel_id in formula.channel_ids:
        quality = chunks[channel_id].quality
        if quality is not None:
            combined |= quality.astype(np.uint8)
            seen = True
    suspect = ~np.isfinite(values)
    if suspect.any():
        combined[suspect] |= np.uint8(Quality.SUSPECT)
        seen = True
    return combined if seen else None


def _evaluate(node: Node, arrays: Mapping[str, Samples], length: int) -> Samples:
    """Ağacı düğüm düğüm hesaplar; sabitler yayınlanır."""
    if isinstance(node, ChannelRef):
        return arrays[node.channel_id]
    if isinstance(node, Literal):
        return np.full(length, node.value, dtype=np.float64)
    if isinstance(node, UnaryOp):
        operand = _evaluate(node.operand, arrays, length)
        return operand.copy() if node.op == "+" else -operand
    left = _evaluate(node.left, arrays, length)
    right = _evaluate(node.right, arrays, length)
    if node.op == "+":
        return left + right
    if node.op == "-":
        return left - right
    if node.op == "*":
        return left * right
    if node.op == "/":
        return left / right
    return np.power(left, right)
