"""İşlem zincirinden türetilmiş kanal metadata'sı — `F4-026`.

Kabul: yeni sample rate türetilmiş kanal metadata'sında görünür.
"""

from __future__ import annotations

from sonar_analyzer.application.derived_channel import (
    chain_changes_sample_rate,
    derive_channel_metadata,
    derived_sample_rate,
)
from sonar_analyzer.domain.channel import ChannelMetadata, ChannelSource
from sonar_analyzer.processing.chain import ProcessingChain
from sonar_analyzer.processing.steps import ProcessingStep, StepKind

BASE = ChannelMetadata(
    id="ch0",
    path="Acoustic/Hydrophone 1",
    name="Hydrophone 1",
    dtype="int16",
    source=ChannelSource.ACOUSTIC,
    unit="Pa",
    sample_rate_hz=48_000.0,
)


def _resample(source_hz: float, target_hz: float, *, enabled: bool = True) -> ProcessingStep:
    return ProcessingStep(
        StepKind.RESAMPLE,
        "ch0",
        {"source_rate_hz": source_hz, "target_rate_hz": target_hz},
        enabled=enabled,
    )


def _scale(factor: float) -> ProcessingStep:
    return ProcessingStep(StepKind.SCALE, "ch0", {"factor": factor})


def test_no_resample_returns_the_base_unchanged() -> None:
    chain = ProcessingChain([_scale(2.0)])
    assert derive_channel_metadata(BASE, chain) is BASE
    assert not chain_changes_sample_rate(chain)


def test_resample_surfaces_the_new_rate_in_metadata() -> None:
    chain = ProcessingChain([_resample(48_000.0, 12_000.0)])
    derived = derive_channel_metadata(BASE, chain)

    assert derived.sample_rate_hz == 12_000.0
    assert derived.source is ChannelSource.DERIVED
    assert derived.id != BASE.id
    assert "12000" in derived.name
    # Diğer alanlar korunur.
    assert derived.unit == BASE.unit
    assert derived.dtype == BASE.dtype


def test_disabled_resample_does_not_change_the_rate() -> None:
    chain = ProcessingChain([_resample(48_000.0, 12_000.0, enabled=False)])
    assert derive_channel_metadata(BASE, chain) is BASE
    assert derived_sample_rate(48_000.0, chain) == 48_000.0


def test_chained_resamples_take_the_last_target() -> None:
    chain = ProcessingChain([_resample(48_000.0, 24_000.0), _resample(24_000.0, 8_000.0)])
    assert derived_sample_rate(48_000.0, chain) == 8_000.0
    assert derive_channel_metadata(BASE, chain).sample_rate_hz == 8_000.0


def test_resample_after_another_step_still_derives() -> None:
    chain = ProcessingChain([_scale(3.0), _resample(48_000.0, 16_000.0)])
    assert derive_channel_metadata(BASE, chain).sample_rate_hz == 16_000.0


def test_base_without_a_known_rate_still_gets_the_target() -> None:
    base = ChannelMetadata(id="c", path="p", name="n", dtype="float32")
    chain = ProcessingChain([_resample(1_000.0, 250.0)])
    assert derive_channel_metadata(base, chain).sample_rate_hz == 250.0


def test_derived_sample_rate_without_resample_is_the_base() -> None:
    assert derived_sample_rate(48_000.0, ProcessingChain([_scale(2.0)])) == 48_000.0
