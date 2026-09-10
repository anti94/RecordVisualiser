"""Pencere üretimi ve normalizasyon katsayıları — `F4-039`.

Kabul: seçili pencerenin genlik/enerji katsayıları referansla eşleşir.

Referanslar iki yönden bağımsız doğrulanır:

1. `REFERENCE_*` tabloları — kapalı formdan elle türetilen değerler
   (periyodik Hann için ``mean(w)=0.5``, ``mean(w^2)=0.375`` gibi).
2. `numpy.hanning` / `numpy.hamming` / `numpy.blackman` simetrik
   biçimleriyle karşılaştırma (``periodic=False`` yolu).
"""

from __future__ import annotations

import numpy as np
import pytest

from sonar_analyzer.analysis.windows import (
    REFERENCE_COHERENT_GAIN,
    REFERENCE_ENBW,
    REFERENCE_MEAN_SQUARE,
    WINDOW_KINDS,
    WINDOW_NORMALIZATIONS,
    WindowError,
    WindowKind,
    WindowNormalization,
    amplitude_correction,
    coherent_gain,
    correction_factor,
    energy_correction,
    equivalent_noise_bandwidth,
    mean_square,
    normalized_window,
    resolve_kind,
    window_values,
)

LENGTH = 1024
ALL_KINDS = list(WindowKind)


# --------------------------------------------------------------------------- #
# üretim
# --------------------------------------------------------------------------- #


def test_kind_list_matches_the_enum() -> None:
    assert WINDOW_KINDS == ("rectangular", "hann", "hamming", "blackman")
    assert WINDOW_NORMALIZATIONS == ("none", "amplitude", "energy")


@pytest.mark.parametrize("kind", ALL_KINDS)
def test_window_has_the_requested_length_and_dtype(kind: WindowKind) -> None:
    w = window_values(kind, LENGTH)
    assert w.shape == (LENGTH,)
    assert w.dtype == np.float64


def test_rectangular_window_is_all_ones() -> None:
    assert np.array_equal(window_values(WindowKind.RECTANGULAR, 8), np.ones(8))


def test_periodic_hann_starts_at_zero_and_is_not_symmetric() -> None:
    w = window_values(WindowKind.HANN, 8)
    assert w[0] == 0.0
    # Periyodik biçimde son örnek ilkin aynası DEĞİLDİR.
    assert w[-1] != w[0]


def test_symmetric_forms_match_numpy() -> None:
    n = 65
    assert np.allclose(window_values(WindowKind.HANN, n, periodic=False), np.hanning(n))
    assert np.allclose(window_values(WindowKind.HAMMING, n, periodic=False), np.hamming(n))
    assert np.allclose(window_values(WindowKind.BLACKMAN, n, periodic=False), np.blackman(n))


def test_length_one_is_a_single_unit_sample() -> None:
    for kind in ALL_KINDS:
        assert np.array_equal(window_values(kind, 1), np.ones(1))


# --------------------------------------------------------------------------- #
# katsayılar referansla eşleşir
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("kind", ALL_KINDS)
def test_coherent_gain_matches_the_reference(kind: WindowKind) -> None:
    w = window_values(kind, LENGTH)
    assert abs(coherent_gain(w) - REFERENCE_COHERENT_GAIN[kind]) < 1e-12


@pytest.mark.parametrize("kind", ALL_KINDS)
def test_mean_square_matches_the_reference(kind: WindowKind) -> None:
    w = window_values(kind, LENGTH)
    assert abs(mean_square(w) - REFERENCE_MEAN_SQUARE[kind]) < 1e-12


@pytest.mark.parametrize("kind", ALL_KINDS)
def test_enbw_matches_the_reference(kind: WindowKind) -> None:
    w = window_values(kind, LENGTH)
    assert abs(equivalent_noise_bandwidth(w) - REFERENCE_ENBW[kind]) < 1e-12


def test_the_reference_table_carries_the_textbook_values() -> None:
    assert REFERENCE_COHERENT_GAIN[WindowKind.HANN] == 0.5
    assert REFERENCE_MEAN_SQUARE[WindowKind.HANN] == 0.375
    assert abs(REFERENCE_ENBW[WindowKind.HANN] - 1.5) < 1e-12
    assert abs(REFERENCE_ENBW[WindowKind.HAMMING] - 1.362825) < 1e-6
    assert abs(REFERENCE_ENBW[WindowKind.BLACKMAN] - 1.726757) < 1e-6
    assert REFERENCE_ENBW[WindowKind.RECTANGULAR] == 1.0


def test_reference_values_hold_for_a_short_window_too() -> None:
    # Kapalı form N >= 3 için tam; kısa pencerede de birebir tutmalı.
    for kind in ALL_KINDS:
        w = window_values(kind, 8)
        assert abs(coherent_gain(w) - REFERENCE_COHERENT_GAIN[kind]) < 1e-12
        assert abs(mean_square(w) - REFERENCE_MEAN_SQUARE[kind]) < 1e-12


# --------------------------------------------------------------------------- #
# düzeltme katsayıları
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("kind", ALL_KINDS)
def test_amplitude_correction_is_the_inverse_of_coherent_gain(kind: WindowKind) -> None:
    w = window_values(kind, LENGTH)
    assert abs(amplitude_correction(w) * coherent_gain(w) - 1.0) < 1e-12


@pytest.mark.parametrize("kind", ALL_KINDS)
def test_energy_correction_is_the_inverse_rms_of_the_window(kind: WindowKind) -> None:
    w = window_values(kind, LENGTH)
    assert abs(energy_correction(w) ** 2 * mean_square(w) - 1.0) < 1e-12


def test_hann_correction_factors_are_the_known_numbers() -> None:
    w = window_values(WindowKind.HANN, LENGTH)
    assert abs(amplitude_correction(w) - 2.0) < 1e-12  # 1 / 0.5
    assert abs(energy_correction(w) - 1.0 / np.sqrt(0.375)) < 1e-12


def test_rectangular_corrections_are_unity() -> None:
    w = window_values(WindowKind.RECTANGULAR, 32)
    assert amplitude_correction(w) == 1.0
    assert energy_correction(w) == 1.0


# --------------------------------------------------------------------------- #
# normalizasyon
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("kind", ALL_KINDS)
def test_amplitude_normalized_window_has_unit_mean(kind: WindowKind) -> None:
    w = normalized_window(kind, LENGTH, normalization=WindowNormalization.AMPLITUDE)
    assert abs(coherent_gain(w) - 1.0) < 1e-12


@pytest.mark.parametrize("kind", ALL_KINDS)
def test_energy_normalized_window_has_unit_mean_square(kind: WindowKind) -> None:
    w = normalized_window(kind, LENGTH, normalization=WindowNormalization.ENERGY)
    assert abs(mean_square(w) - 1.0) < 1e-12


def test_no_normalization_leaves_the_window_untouched() -> None:
    plain = window_values(WindowKind.BLACKMAN, 64)
    same = normalized_window(WindowKind.BLACKMAN, 64, normalization="none")
    assert np.allclose(same, plain)


def test_normalization_accepts_plain_strings() -> None:
    w = window_values(WindowKind.HANN, 64)
    assert abs(correction_factor(w, "amplitude") - 2.0) < 1e-12
    assert correction_factor(w, "none") == 1.0


def test_normalized_window_preserves_the_shape_up_to_a_scalar() -> None:
    plain = window_values(WindowKind.HAMMING, 128)
    scaled = normalized_window(WindowKind.HAMMING, 128, normalization="energy")
    ratio = scaled / plain
    assert np.allclose(ratio, ratio[0])


# --------------------------------------------------------------------------- #
# hata yolları
# --------------------------------------------------------------------------- #


def test_unknown_kind_is_rejected() -> None:
    with pytest.raises(WindowError, match="bilinmeyen pencere türü"):
        window_values("gaussian", 16)


def test_unknown_normalization_is_rejected() -> None:
    w = window_values(WindowKind.HANN, 16)
    with pytest.raises(WindowError, match="bilinmeyen normalizasyon"):
        correction_factor(w, "peak")


@pytest.mark.parametrize("bad", [0, -1, -100])
def test_nonpositive_length_is_rejected(bad: int) -> None:
    with pytest.raises(WindowError, match="uzunluğu"):
        window_values(WindowKind.HANN, bad)


def test_empty_window_metrics_are_rejected() -> None:
    empty = np.empty(0, dtype=np.float64)
    with pytest.raises(WindowError):
        coherent_gain(empty)
    with pytest.raises(WindowError):
        mean_square(empty)
    with pytest.raises(WindowError):
        equivalent_noise_bandwidth(empty)


def test_all_zero_window_corrections_are_rejected() -> None:
    zeros = np.zeros(8, dtype=np.float64)
    with pytest.raises(WindowError, match="coherent gain"):
        amplitude_correction(zeros)
    with pytest.raises(WindowError, match="pencere gücü"):
        energy_correction(zeros)
    with pytest.raises(WindowError, match="ENBW"):
        equivalent_noise_bandwidth(zeros)


def test_resolve_kind_round_trips_strings_and_enums() -> None:
    assert resolve_kind("hann") is WindowKind.HANN
    assert resolve_kind(WindowKind.BLACKMAN) is WindowKind.BLACKMAN
