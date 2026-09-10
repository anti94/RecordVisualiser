"""Formül değerlendirmesi kanal dizilerine bağlı — `F4-071`.

Kabul: basit kanal toplamı referansla eşleşir; zaman hizası uyuşmazlığı
açıklanır.

"Referansla eşleşir": sonuç, formülden bağımsız olarak NumPy ile
hesaplanan diziyle bit düzeyinde karşılaştırılır. "Açıklanır": dört ayrı
uyuşmazlık biçimi (uzunluk, başlangıç, adım, tek damga) için hatanın
**nedeni adlandırılır** — sessiz kırpma, doldurma veya enterpolasyon yok.
"""

from __future__ import annotations

import numpy as np
import pytest
from numpy.typing import NDArray

from sonar_analyzer.analysis.formula import aliases_for, parse_formula
from sonar_analyzer.analysis.formula_eval import (
    FormulaAlignmentError,
    FormulaInputError,
    describe_misalignment,
    evaluate_formula,
)
from sonar_analyzer.domain.data_chunk import DataChunk, Quality

STEP_NS = 1_000_000
COUNT = 8
ALIASES = aliases_for(["ch0", "ch1", "ch2"])


def _times(count: int = COUNT, start: int = 0, step: int = STEP_NS) -> NDArray[np.int64]:
    return start + np.arange(count, dtype=np.int64) * step


#: Elle yazılmış, tekrar üretilebilir referans diziler.
VALUES_0 = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
VALUES_1 = np.array([10.0, -20.0, 30.0, -40.0, 50.0, -60.0, 70.0, -80.0])


def _chunk(
    channel_id: str,
    values: NDArray[np.float64],
    times: NDArray[np.int64] | None = None,
    quality: NDArray[np.uint8] | None = None,
) -> DataChunk:
    return DataChunk(
        channel_id=channel_id,
        timestamps_ns=_times(values.size) if times is None else times,
        values=values,
        quality=quality,
    )


@pytest.fixture()
def chunks() -> dict[str, DataChunk]:
    return {"ch0": _chunk("ch0", VALUES_0), "ch1": _chunk("ch1", VALUES_1)}


def _evaluate(text: str, chunks: dict[str, DataChunk]) -> DataChunk:
    return evaluate_formula(parse_formula(text, ALIASES), chunks)


# --------------------------------------------------------------------------- #
# referansla esitlik
# --------------------------------------------------------------------------- #


def test_a_simple_channel_sum_matches_the_reference(chunks: dict[str, DataChunk]) -> None:
    """Kabul kriterinin kendisi: `ch0 + ch1` referansla aynı."""
    result = _evaluate("ch0 + ch1", chunks)
    assert np.array_equal(result.values, VALUES_0 + VALUES_1)
    assert result.values.dtype == np.float64


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("ch0 - ch1", VALUES_0 - VALUES_1),
        ("ch0 * ch1", VALUES_0 * VALUES_1),
        ("ch0 / ch1", VALUES_0 / VALUES_1),
        ("ch0 ** 2", VALUES_0**2),
        ("-ch0", -VALUES_0),
        ("+ch0", VALUES_0),
        ("ch0 * 2 + 1", VALUES_0 * 2 + 1),
        ("(ch0 - ch1) / 2", (VALUES_0 - VALUES_1) / 2),
        ("ch0 + ch0", VALUES_0 + VALUES_0),
        ("2 * ch0 - 0.5 * ch1", 2 * VALUES_0 - 0.5 * VALUES_1),
    ],
)
def test_each_operator_matches_the_numpy_reference(
    chunks: dict[str, DataChunk], text: str, expected: NDArray[np.float64]
) -> None:
    assert np.array_equal(_evaluate(text, chunks).values, expected)


def test_precedence_follows_arithmetic_not_left_to_right(
    chunks: dict[str, DataChunk],
) -> None:
    assert np.array_equal(_evaluate("ch0 + ch1 * 2", chunks).values, VALUES_0 + VALUES_1 * 2)
    assert np.array_equal(_evaluate("(ch0 + ch1) * 2", chunks).values, (VALUES_0 + VALUES_1) * 2)


def test_the_result_keeps_the_shared_timestamps(chunks: dict[str, DataChunk]) -> None:
    result = _evaluate("ch0 + ch1", chunks)
    assert np.array_equal(result.timestamps_ns, _times())
    assert len(result) == COUNT


def test_the_result_channel_id_can_be_named(chunks: dict[str, DataChunk]) -> None:
    formula = parse_formula("ch0", ALIASES)
    assert evaluate_formula(formula, chunks).channel_id == "formula"
    assert evaluate_formula(formula, chunks, channel_id="derived:x").channel_id == "derived:x"


@pytest.mark.parametrize("text", ["ch0", "+ch0", "ch0 * 1"])
def test_a_result_never_aliases_an_input_array(chunks: dict[str, DataChunk], text: str) -> None:
    """Çıplak `ch0` bile kopya vermeli; sonucu değiştirmek kaynağı bozmamalı."""
    result = _evaluate(text, chunks)
    assert result.values is not chunks["ch0"].values
    result.values[0] = 999.0
    assert chunks["ch0"].values[0] == VALUES_0[0]


def test_an_empty_chunk_yields_an_empty_result() -> None:
    empty = _chunk("ch0", np.empty(0, dtype=np.float64), np.empty(0, dtype=np.int64))
    result = _evaluate("ch0 * 2", {"ch0": empty})
    assert result.is_empty


# --------------------------------------------------------------------------- #
# gecersiz veri yayilir (F4-005 politikasi)
# --------------------------------------------------------------------------- #


def test_division_by_zero_produces_infinity_not_an_exception() -> None:
    values = np.array([1.0, 2.0, 3.0])
    zeros = np.array([1.0, 0.0, -1.0])
    result = _evaluate("ch0 / ch1", {"ch0": _chunk("ch0", values), "ch1": _chunk("ch1", zeros)})
    assert result.values[0] == 1.0
    assert np.isinf(result.values[1])
    assert result.values[2] == -3.0


def test_zero_over_zero_produces_nan() -> None:
    zeros = np.array([0.0, 1.0])
    result = _evaluate("ch0 / ch1", {"ch0": _chunk("ch0", zeros), "ch1": _chunk("ch1", zeros)})
    assert np.isnan(result.values[0])
    assert result.values[1] == 1.0


def test_nan_in_the_input_propagates() -> None:
    values = np.array([1.0, np.nan, 3.0])
    result = _evaluate("ch0 * 2 + 1", {"ch0": _chunk("ch0", values)})
    assert result.values[0] == 3.0
    assert np.isnan(result.values[1])


def test_non_finite_results_are_flagged_suspect() -> None:
    result = _evaluate(
        "ch0 / ch1",
        {
            "ch0": _chunk("ch0", np.array([1.0, 1.0])),
            "ch1": _chunk("ch1", np.array([1.0, 0.0])),
        },
    )
    assert result.quality is not None
    assert not result.quality[0] & Quality.SUSPECT
    assert result.quality[1] & Quality.SUSPECT


def test_input_quality_flags_are_combined() -> None:
    flags_a = np.array([Quality.GAP_BEFORE, 0], dtype=np.uint8)
    flags_b = np.array([0, Quality.CRC_ERROR], dtype=np.uint8)
    result = _evaluate(
        "ch0 + ch1",
        {
            "ch0": _chunk("ch0", np.array([1.0, 2.0]), quality=flags_a),
            "ch1": _chunk("ch1", np.array([3.0, 4.0]), quality=flags_b),
        },
    )
    assert result.quality is not None
    assert result.quality[0] & Quality.GAP_BEFORE
    assert result.quality[1] & Quality.CRC_ERROR


def test_clean_inputs_leave_the_quality_unset(chunks: dict[str, DataChunk]) -> None:
    assert _evaluate("ch0 + ch1", chunks).quality is None


# --------------------------------------------------------------------------- #
# zaman hizasi uyusmazligi ACIKLANIR
# --------------------------------------------------------------------------- #


def test_different_lengths_are_explained(chunks: dict[str, DataChunk]) -> None:
    chunks["ch1"] = _chunk("ch1", VALUES_1[:4])
    with pytest.raises(FormulaAlignmentError) as error:
        _evaluate("ch0 + ch1", chunks)
    message = str(error.value)
    assert "farklı örnek sayısı" in message
    assert "ch0 8" in message and "ch1 4" in message


def test_a_different_start_time_is_explained(chunks: dict[str, DataChunk]) -> None:
    chunks["ch1"] = _chunk("ch1", VALUES_1, _times(start=7_000))
    with pytest.raises(FormulaAlignmentError) as error:
        _evaluate("ch0 + ch1", chunks)
    message = str(error.value)
    assert "farklı başlangıç" in message
    assert "fark 7000 ns" in message


def test_a_different_sample_step_is_explained(chunks: dict[str, DataChunk]) -> None:
    chunks["ch1"] = _chunk("ch1", VALUES_1, _times(step=STEP_NS * 2))
    with pytest.raises(FormulaAlignmentError) as error:
        _evaluate("ch0 + ch1", chunks)
    message = str(error.value)
    assert "farklı örnekleme adımı" in message
    assert "1000 Hz" in message and "500 Hz" in message


def test_a_single_shifted_timestamp_is_explained(chunks: dict[str, DataChunk]) -> None:
    """Uzunluk, başlangıç ve adım aynı olsa bile tek bir kayma yakalanır."""
    times = _times()
    times[5] += 1
    chunks["ch1"] = _chunk("ch1", VALUES_1, times)
    with pytest.raises(FormulaAlignmentError) as error:
        _evaluate("ch0 + ch1", chunks)
    message = str(error.value)
    assert "ilk fark 5. örnekte" in message


def test_the_error_names_the_formula_and_both_channels(chunks: dict[str, DataChunk]) -> None:
    chunks["ch1"] = _chunk("ch1", VALUES_1[:2])
    with pytest.raises(FormulaAlignmentError) as error:
        _evaluate("ch0 * 3 - ch1", chunks)
    message = str(error.value)
    assert "'ch0 * 3 - ch1'" in message
    assert "ch0 ve ch1" in message


def test_misaligned_data_is_never_silently_truncated(chunks: dict[str, DataChunk]) -> None:
    """Sessiz kırpma yanlış veriyi doğru gibi gösterirdi."""
    chunks["ch1"] = _chunk("ch1", VALUES_1[:4])
    with pytest.raises(FormulaAlignmentError):
        _evaluate("ch0 + ch1", chunks)


def test_a_channel_used_twice_needs_no_alignment(chunks: dict[str, DataChunk]) -> None:
    assert np.array_equal(_evaluate("ch0 - ch0", chunks).values, np.zeros(COUNT))


def test_three_channels_must_all_share_one_grid(chunks: dict[str, DataChunk]) -> None:
    chunks["ch2"] = _chunk("ch2", VALUES_0, _times(start=1))
    with pytest.raises(FormulaAlignmentError, match="ch0 ve ch2"):
        _evaluate("ch0 + ch1 + ch2", chunks)


def test_aligned_channels_that_merely_differ_in_values_are_fine(
    chunks: dict[str, DataChunk],
) -> None:
    chunks["ch2"] = _chunk("ch2", VALUES_0 * 3)
    result = _evaluate("ch0 + ch1 + ch2", chunks)
    assert np.array_equal(result.values, VALUES_0 + VALUES_1 + VALUES_0 * 3)


# --------------------------------------------------------------------------- #
# aciklama yardimcisi dogrudan
# --------------------------------------------------------------------------- #


def test_describe_misalignment_reports_the_first_difference() -> None:
    first = np.array([0, 10, 20, 30], dtype=np.int64)
    second = np.array([0, 10, 25, 30], dtype=np.int64)
    text = describe_misalignment("a", first, "b", second)
    assert "ilk fark 2. örnekte" in text


def test_describe_misalignment_prefers_the_coarsest_explanation() -> None:
    """Hem uzunluk hem damga farklıysa uzunluk söylenir; en anlaşılır olan o."""
    first = np.array([0, 10, 20], dtype=np.int64)
    second = np.array([5, 15], dtype=np.int64)
    assert "farklı örnek sayısı" in describe_misalignment("a", first, "b", second)


def test_a_single_sample_pair_cannot_differ_in_step() -> None:
    first = np.array([0], dtype=np.int64)
    second = np.array([5], dtype=np.int64)
    assert "farklı başlangıç" in describe_misalignment("a", first, "b", second)


# --------------------------------------------------------------------------- #
# eksik girdi ve zaman tabani
# --------------------------------------------------------------------------- #


def test_a_missing_channel_is_reported_by_name(chunks: dict[str, DataChunk]) -> None:
    del chunks["ch1"]
    with pytest.raises(FormulaInputError, match=r"\['ch1'\]"):
        _evaluate("ch0 + ch1", chunks)


def test_a_constant_only_formula_has_no_time_base_and_says_so() -> None:
    with pytest.raises(FormulaInputError, match="zaman tabanı yok"):
        _evaluate("2 * 3 + 1", {})


def test_the_constant_only_error_suggests_a_way_out() -> None:
    with pytest.raises(FormulaInputError, match=r"ch0 \* 0 \+ 5"):
        _evaluate("5", {})


def test_extra_unused_chunks_are_ignored(chunks: dict[str, DataChunk]) -> None:
    chunks["ch2"] = _chunk("ch2", VALUES_0, _times(start=999))  # hizasiz ama kullanilmiyor
    assert np.array_equal(_evaluate("ch0 + ch1", chunks).values, VALUES_0 + VALUES_1)
