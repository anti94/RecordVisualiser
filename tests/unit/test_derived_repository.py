"""Türetilmiş kanallar repository'de — `F4-069`.

Kabul: Derived ağacında yeni kanal sorgulanır; ham kaynak korunur.

İki söz de sayıyla denetlenir. "Sorgulanır": türetilmiş kanal `channels()`
içinde `Derived/` altında görünür ve `query()` zinciri uygulanmış **elle
doğrulanabilir** veriyi döndürür. "Ham kaynak korunur": taban repository'nin
kanalları, verisi ve dizileri türetilmiş kanal eklendikten, sorgulandıktan
ve kaldırıldıktan sonra bit düzeyinde aynıdır.

Ayrıca nokta bütçesinin **zincirden sonra** uygulandığı ayrıca denetlenir:
tersi yapılsaydı kayan pencere işlemleri indirgenmiş veriyi işleyip yanlış
sonuç verirdi.
"""

from __future__ import annotations

import numpy as np
import pytest

from sonar_analyzer.analysis.downsampling import downsample_chunk
from sonar_analyzer.domain.channel import ChannelSource
from sonar_analyzer.domain.derived_channel_definition import DerivedChannelDefinition
from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.processing.chain import ProcessingChain
from sonar_analyzer.processing.steps import ProcessingStep, StepKind
from sonar_analyzer.repository.derived_repository import (
    DERIVED_ROOT,
    DerivedChannelError,
    DerivedChannelRepository,
)
from sonar_analyzer.repository.mock_repository import MockRecordingRepository
from sonar_analyzer.repository.protocol import EventFilter, RecordingRepository

DURATION_S = 4.0
RATE_HZ = 100.0


@pytest.fixture()
def base() -> MockRecordingRepository:
    return MockRecordingRepository(duration_s=DURATION_S, sample_rate_hz=RATE_HZ)


@pytest.fixture()
def repo(base: MockRecordingRepository) -> DerivedChannelRepository:
    return DerivedChannelRepository(base)


@pytest.fixture()
def span(base: MockRecordingRepository) -> TimeRange:
    return base.metadata().time_range


def _scaled(
    factor: float = 2.0, channel: str = "ch0", name: str = "Ölçekli"
) -> DerivedChannelDefinition:
    step = ProcessingStep.default(StepKind.SCALE, channel).with_parameters(factor=factor)
    return DerivedChannelDefinition(name=name, inputs=(channel,), chain=ProcessingChain([step]))


def _smoothed(window: int = 5, channel: str = "ch0") -> DerivedChannelDefinition:
    step = ProcessingStep.default(StepKind.MOVING_AVERAGE, channel).with_parameters(window=window)
    return DerivedChannelDefinition(
        name="Yumuşatılmış", inputs=(channel,), chain=ProcessingChain([step])
    )


# --------------------------------------------------------------------------- #
# sozlesme ve Derived agaci
# --------------------------------------------------------------------------- #


def test_the_wrapper_still_satisfies_the_repository_contract(
    repo: DerivedChannelRepository,
) -> None:
    assert isinstance(repo, RecordingRepository)


def test_a_new_repository_has_no_derived_channels(
    repo: DerivedChannelRepository, base: MockRecordingRepository
) -> None:
    assert repo.definitions() == ()
    assert [c.id for c in repo.channels()] == [c.id for c in base.channels()]


def test_a_derived_channel_appears_under_the_derived_root(
    repo: DerivedChannelRepository,
) -> None:
    metadata = repo.add(_scaled())
    assert metadata.path == f"{DERIVED_ROOT}/Ölçekli"
    assert metadata.source is ChannelSource.DERIVED
    assert metadata.name == "Ölçekli"
    assert metadata.dtype == "float64"
    assert metadata.id.startswith("derived:")


def test_derived_channels_come_after_the_raw_ones(
    repo: DerivedChannelRepository, base: MockRecordingRepository
) -> None:
    raw_ids = [c.id for c in base.channels()]
    metadata = repo.add(_scaled())
    listed = [c.id for c in repo.channels()]
    assert listed[: len(raw_ids)] == raw_ids
    assert listed[len(raw_ids) :] == [metadata.id]


def test_the_derived_channel_inherits_the_source_unit_and_rate(
    repo: DerivedChannelRepository, base: MockRecordingRepository
) -> None:
    source = next(c for c in base.channels() if c.id == "ch0")
    metadata = repo.add(_scaled())
    assert metadata.unit == source.unit
    assert metadata.sample_rate_hz == source.sample_rate_hz == RATE_HZ
    assert metadata.time_base_id == source.time_base_id


def test_an_explicit_unit_overrides_the_inherited_one(repo: DerivedChannelRepository) -> None:
    definition = DerivedChannelDefinition(
        name="Oran", inputs=("ch0",), chain=ProcessingChain(), unit="%"
    )
    assert repo.add(definition).unit == "%"


def test_a_resampling_chain_changes_the_reported_rate(repo: DerivedChannelRepository) -> None:
    step = ProcessingStep.default(StepKind.RESAMPLE, "ch0").with_parameters(
        source_rate_hz=RATE_HZ, target_rate_hz=25.0
    )
    definition = DerivedChannelDefinition(
        name="Desime", inputs=("ch0",), chain=ProcessingChain([step])
    )
    assert repo.add(definition).sample_rate_hz == 25.0


def test_definitions_are_listed_in_insertion_order(repo: DerivedChannelRepository) -> None:
    first = repo.add(_scaled(2.0, name="Iki"))
    second = repo.add(_scaled(3.0, name="Uc"))
    assert [d.name for d in repo.definitions()] == ["Iki", "Uc"]
    assert repo.definition(first.id) is not None
    assert repo.is_derived(second.id)
    assert not repo.is_derived("ch0")
    assert repo.definition("ch0") is None


# --------------------------------------------------------------------------- #
# turetilmis kanal sorgulanir
# --------------------------------------------------------------------------- #


def test_the_derived_query_applies_the_chain(
    repo: DerivedChannelRepository, span: TimeRange
) -> None:
    metadata = repo.add(_scaled(factor=2.0))
    raw = repo.query("ch0", span)
    derived = repo.query(metadata.id, span)

    assert derived.channel_id == metadata.id
    assert np.array_equal(derived.values, raw.values.astype(np.float64) * 2.0)


def test_the_derived_query_keeps_the_source_timestamps(
    repo: DerivedChannelRepository, span: TimeRange
) -> None:
    metadata = repo.add(_scaled())
    raw = repo.query("ch0", span)
    derived = repo.query(metadata.id, span)
    assert np.array_equal(derived.timestamps_ns, raw.timestamps_ns)
    assert len(derived) == len(raw)


def test_a_narrow_window_returns_only_that_window(
    repo: DerivedChannelRepository, span: TimeRange
) -> None:
    metadata = repo.add(_scaled())
    narrow = TimeRange(span.start_ns, span.start_ns + (span.end_ns - span.start_ns) // 4)
    derived = repo.query(metadata.id, narrow)
    assert len(derived) > 0
    assert derived.start_ns is not None and derived.start_ns >= narrow.start_ns
    assert derived.end_ns is not None and derived.end_ns < narrow.end_ns


def test_an_empty_window_returns_an_empty_but_valid_chunk(
    repo: DerivedChannelRepository, span: TimeRange
) -> None:
    metadata = repo.add(_scaled())
    far = TimeRange(span.end_ns + 1_000_000_000, span.end_ns + 2_000_000_000)
    derived = repo.query(metadata.id, far)
    assert derived.is_empty
    assert derived.channel_id == metadata.id


def test_a_raw_channel_query_still_passes_through(
    repo: DerivedChannelRepository, base: MockRecordingRepository, span: TimeRange
) -> None:
    repo.add(_scaled())
    assert np.array_equal(repo.query("ch1", span).values, base.query("ch1", span).values)


def test_a_derived_channel_can_read_another_derived_channel(
    repo: DerivedChannelRepository, span: TimeRange
) -> None:
    """`Derived` gerçekten bir ağaçtır."""
    doubled = repo.add(_scaled(factor=-2.0, name="Ters iki"))
    absolute = DerivedChannelDefinition(
        name="Mutlak",
        inputs=(doubled.id,),
        chain=ProcessingChain([ProcessingStep.default(StepKind.ABS, doubled.id)]),
    )
    leaf = repo.add(absolute)

    raw = repo.query("ch0", span).values.astype(np.float64)
    assert np.array_equal(repo.query(leaf.id, span).values, np.abs(raw * -2.0))


# --------------------------------------------------------------------------- #
# nokta butcesi zincirden SONRA
# --------------------------------------------------------------------------- #


def test_the_budget_is_applied_after_the_chain_not_before(
    repo: DerivedChannelRepository, span: TimeRange
) -> None:
    """Kayan pencere tam çözünürlüklü veriyi görmeli.

    Bütçe önce uygulansaydı 5'lik pencere indirgenmiş diziyi işler ve
    tamamen başka bir sonuç çıkardı.
    """
    metadata = repo.add(_smoothed(window=5))
    budget = 40

    actual = repo.query(metadata.id, span, budget)

    full = repo.query("ch0", span)
    expected_chunk = repo.query(metadata.id, span)  # butcesiz = tam zincir
    expected = downsample_chunk(expected_chunk, budget)
    assert np.array_equal(actual.values, expected.values)
    assert np.array_equal(actual.timestamps_ns, expected.timestamps_ns)

    # Ters sira gercekten farkli bir sonuc verirdi:
    wrong_input = downsample_chunk(full, budget)
    wrong = _smoothed(window=5).chain.run(wrong_input.values).values
    assert not np.array_equal(actual.values, wrong)


def test_the_budget_limits_the_returned_points(
    repo: DerivedChannelRepository, span: TimeRange
) -> None:
    metadata = repo.add(_scaled())
    assert len(repo.query(metadata.id, span, 30)) <= 30
    assert len(repo.query(metadata.id, span, None)) == len(repo.query("ch0", span))


# --------------------------------------------------------------------------- #
# ham kaynak korunur
# --------------------------------------------------------------------------- #


def test_adding_a_derived_channel_does_not_touch_the_base_channels(
    repo: DerivedChannelRepository, base: MockRecordingRepository
) -> None:
    before = tuple(base.channels())
    repo.add(_scaled())
    assert tuple(base.channels()) == before


def test_querying_a_derived_channel_does_not_change_the_raw_data(
    repo: DerivedChannelRepository, base: MockRecordingRepository, span: TimeRange
) -> None:
    before = base.query("ch0", span).values.copy()
    metadata = repo.add(_scaled(factor=7.0))
    repo.query(metadata.id, span)
    assert np.array_equal(base.query("ch0", span).values, before)


def test_the_derived_result_does_not_alias_the_source_arrays(
    repo: DerivedChannelRepository, span: TimeRange
) -> None:
    """Zincir çıktısı taban dizisinin üstüne yazmaz — `F4-002`."""
    metadata = repo.add(_scaled(factor=3.0))
    raw = repo.query("ch0", span)
    original = raw.values.copy()
    derived = repo.query(metadata.id, span)

    assert derived.values is not raw.values
    assert np.array_equal(raw.values, original)


def test_removing_a_derived_channel_leaves_the_base_intact(
    repo: DerivedChannelRepository, base: MockRecordingRepository, span: TimeRange
) -> None:
    before_ids = [c.id for c in base.channels()]
    before_values = base.query("ch0", span).values.copy()

    metadata = repo.add(_scaled())
    assert repo.remove(metadata.id)

    assert [c.id for c in repo.channels()] == before_ids
    assert np.array_equal(base.query("ch0", span).values, before_values)
    assert repo.definitions() == ()


def test_clearing_the_derived_channels_leaves_the_base_intact(
    repo: DerivedChannelRepository, base: MockRecordingRepository
) -> None:
    repo.add(_scaled(2.0, name="A"))
    repo.add(_scaled(3.0, name="B"))
    repo.clear_derived()
    assert [c.id for c in repo.channels()] == [c.id for c in base.channels()]


# --------------------------------------------------------------------------- #
# reddedilen durumlar
# --------------------------------------------------------------------------- #


def test_an_unknown_input_channel_is_refused(repo: DerivedChannelRepository) -> None:
    with pytest.raises(DerivedChannelError, match="Bilinmeyen giriş kanalı"):
        repo.add(_scaled(channel="yok"))
    assert repo.definitions() == ()


def test_a_multi_input_definition_is_refused_until_formulas_arrive(
    repo: DerivedChannelRepository,
) -> None:
    """Sessizce ilk girişi kullanmak yanlış veri üretirdi."""
    definition = DerivedChannelDefinition(name="Fark", inputs=("ch0", "ch1"))
    with pytest.raises(DerivedChannelError, match="F4-070"):
        repo.add(definition)


def test_removing_a_channel_that_others_depend_on_is_refused(
    repo: DerivedChannelRepository,
) -> None:
    doubled = repo.add(_scaled(name="Iki kat"))
    repo.add(
        DerivedChannelDefinition(
            name="Mutlak",
            inputs=(doubled.id,),
            chain=ProcessingChain([ProcessingStep.default(StepKind.ABS, doubled.id)]),
        )
    )
    with pytest.raises(DerivedChannelError, match="Mutlak"):
        repo.remove(doubled.id)
    assert repo.is_derived(doubled.id)


def test_removing_an_unknown_channel_reports_false(repo: DerivedChannelRepository) -> None:
    assert not repo.remove("ch0")
    assert not repo.remove("derived:yok")


def test_re_adding_the_same_recipe_keeps_one_channel(
    repo: DerivedChannelRepository, base: MockRecordingRepository
) -> None:
    """Kimlik içerikten türer: aynı tarif ikinci kez kanal çoğaltmaz."""
    first = repo.add(_scaled(2.0, name="Iki kat"))
    second = repo.add(_scaled(2.0, name="Yeni ad"))

    assert second.id == first.id
    assert second.name == "Yeni ad"  # gorunen bilgi tazelendi
    assert len(repo.channels()) == len(base.channels()) + 1


# --------------------------------------------------------------------------- #
# taban sozlesmesinin gerisi
# --------------------------------------------------------------------------- #


def test_metadata_and_event_queries_are_delegated(
    repo: DerivedChannelRepository, base: MockRecordingRepository, span: TimeRange
) -> None:
    repo.add(_scaled())
    assert repo.metadata() == base.metadata()
    assert list(repo.events(span)) == list(base.events(span))
    assert list(repo.events(span, EventFilter())) == list(base.events(span, EventFilter()))
    assert list(repo.bit_results(span)) == list(base.bit_results(span))
    assert list(repo.transmissions(span)) == list(base.transmissions(span))
    assert repo.base is base


def test_close_closes_the_base(
    repo: DerivedChannelRepository, base: MockRecordingRepository, span: TimeRange
) -> None:
    repo.add(_scaled())
    repo.close()
    with pytest.raises(RuntimeError, match="kapatildi"):
        base.query("ch0", span)
