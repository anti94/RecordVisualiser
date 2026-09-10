"""Türetilmiş kanal tanımı — `F4-068`.

Kabul: giriş kimlikleri ve işlem zinciri yeniden üretilebilir tanım oluşturur.

"Yeniden üretilebilir" burada üç somut söz demektir ve üçü de denetlenir:

1. Aynı girişler + aynı etkin zincir **her zaman** aynı kimliği verir —
   sözlük sırası, nesne kimliği veya adlandırma fark etmez.
2. Sonucu değiştiren her şey kimliği değiştirir; değiştirmeyen hiçbir şey
   değiştirmez.
3. Tanım kayıpsız yazılıp geri okunur; geri okunan tanımın kimliği aynıdır.
"""

from __future__ import annotations

import json

import pytest

from sonar_analyzer.domain.derived_channel_definition import (
    DEFINITION_SCHEMA_VERSION,
    DerivedChannelDefinition,
    DerivedChannelError,
)
from sonar_analyzer.processing.chain import ProcessingChain
from sonar_analyzer.processing.steps import ProcessingStep, StepKind


def _step(kind: StepKind = StepKind.SCALE, channel: str = "ch0") -> ProcessingStep:
    return ProcessingStep.default(kind, channel)


def _definition(
    name: str = "Ölçekli basınç",
    inputs: tuple[str, ...] = ("ch0",),
    steps: tuple[ProcessingStep, ...] = (),
    **extra: object,
) -> DerivedChannelDefinition:
    return DerivedChannelDefinition(
        name=name,
        inputs=inputs,
        chain=ProcessingChain(list(steps) or [_step()]),
        **extra,  # type: ignore[arg-type]
    )


# --------------------------------------------------------------------------- #
# tanimin gecerliligi
# --------------------------------------------------------------------------- #


def test_a_definition_carries_its_inputs_and_chain() -> None:
    definition = _definition()
    assert definition.inputs == ("ch0",)
    assert len(definition.chain.steps) == 1
    assert definition.chain.steps[0].kind is StepKind.SCALE


def test_a_definition_without_inputs_is_refused() -> None:
    with pytest.raises(DerivedChannelError, match="en az bir giriş"):
        DerivedChannelDefinition(name="x", inputs=())


def test_a_blank_name_is_refused() -> None:
    with pytest.raises(DerivedChannelError, match="adı boş"):
        _definition(name="   ")


@pytest.mark.parametrize("bad", ["", "   "])
def test_a_blank_input_id_is_refused(bad: str) -> None:
    with pytest.raises(DerivedChannelError, match="boş olamaz"):
        DerivedChannelDefinition(name="x", inputs=(bad,))


def test_repeated_input_ids_are_refused() -> None:
    with pytest.raises(DerivedChannelError, match="tekrar edemez"):
        DerivedChannelDefinition(name="x", inputs=("ch0", "ch1", "ch0"))


def test_a_chain_step_must_read_a_declared_input() -> None:
    """Tanım kendi kaynağını taşımalı: bildirilmemiş kanal reddedilir."""
    with pytest.raises(DerivedChannelError, match="ch9"):
        DerivedChannelDefinition(
            name="x", inputs=("ch0",), chain=ProcessingChain([_step(channel="ch9")])
        )


def test_a_multi_input_definition_accepts_steps_from_any_declared_input() -> None:
    definition = DerivedChannelDefinition(
        name="Fark",
        inputs=("ch0", "ch1"),
        chain=ProcessingChain([_step(channel="ch1"), _step(StepKind.ABS, "ch0")]),
    )
    assert definition.inputs == ("ch0", "ch1")


def test_a_definition_with_an_empty_chain_is_valid() -> None:
    """Zincirsiz tanım kanalın kendisini yeniden adlandırır; geçerlidir."""
    definition = DerivedChannelDefinition(name="Takma ad", inputs=("ch0",))
    assert definition.chain.steps == []
    assert definition.derived_id.startswith("derived:")


def test_a_list_of_inputs_is_stored_as_a_tuple() -> None:
    definition = DerivedChannelDefinition(name="x", inputs=["ch0", "ch1"])  # type: ignore[arg-type]
    assert definition.inputs == ("ch0", "ch1")


# --------------------------------------------------------------------------- #
# ayni tarif -> ayni kimlik
# --------------------------------------------------------------------------- #


def test_two_definitions_built_the_same_way_share_one_identity() -> None:
    first, second = _definition(), _definition()
    assert first is not second
    assert first.signature() == second.signature()
    assert first.fingerprint() == second.fingerprint()
    assert first.derived_id == second.derived_id


def test_the_identity_is_stable_across_calls() -> None:
    definition = _definition()
    assert definition.derived_id == definition.derived_id
    assert definition.fingerprint() == definition.fingerprint()


def test_the_fingerprint_is_a_sha256_hex_digest() -> None:
    fingerprint = _definition().fingerprint()
    assert len(fingerprint) == 64
    assert set(fingerprint) <= set("0123456789abcdef")


def test_the_derived_id_is_a_short_prefixed_fingerprint() -> None:
    definition = _definition()
    prefix, _, digest = definition.derived_id.partition(":")
    assert prefix == "derived"
    assert digest == definition.fingerprint()[:16]


def test_the_signature_is_readable_json_of_inputs_and_chain() -> None:
    payload = json.loads(_definition().signature())
    assert set(payload) == {"inputs", "chain"}
    assert payload["inputs"] == ["ch0"]
    assert len(payload["chain"]) == 1


# --------------------------------------------------------------------------- #
# neyin kimligi degistirdigi
# --------------------------------------------------------------------------- #


def test_a_different_input_changes_the_identity() -> None:
    first = _definition(inputs=("ch0",), steps=(_step(channel="ch0"),))
    second = _definition(inputs=("ch1",), steps=(_step(channel="ch1"),))
    assert first.derived_id != second.derived_id


def test_input_order_changes_the_identity() -> None:
    """Sıra anlamlıdır: formül girişleri konumla eşler."""
    first = DerivedChannelDefinition(name="x", inputs=("ch0", "ch1"))
    second = DerivedChannelDefinition(name="x", inputs=("ch1", "ch0"))
    assert first.derived_id != second.derived_id


def test_a_different_step_kind_changes_the_identity() -> None:
    first = _definition(steps=(_step(StepKind.SCALE),))
    second = _definition(steps=(_step(StepKind.ABS),))
    assert first.derived_id != second.derived_id


def test_a_different_parameter_changes_the_identity() -> None:
    first = _definition(steps=(_step(StepKind.SCALE),))
    second = _definition(steps=(_step(StepKind.SCALE).with_parameters(factor=2.0),))
    assert first.derived_id != second.derived_id


def test_step_order_changes_the_identity() -> None:
    scale, absolute = _step(StepKind.SCALE), _step(StepKind.ABS)
    first = _definition(steps=(scale, absolute))
    second = _definition(steps=(absolute, scale))
    assert first.derived_id != second.derived_id


def test_disabling_a_step_changes_the_identity() -> None:
    """Kapalı adım sonucu değiştirir (uygulanmaz), dolayısıyla kimliği de."""
    enabled = _definition(steps=(_step(StepKind.ABS),))
    disabled_step = ProcessingStep(
        kind=StepKind.ABS, input_channel_id="ch0", parameters={}, enabled=False
    )
    disabled = _definition(steps=(disabled_step,))
    assert enabled.derived_id != disabled.derived_id


def test_adding_a_disabled_step_does_not_change_the_identity() -> None:
    """Kimlik açısından kapalı adım hiç yokmuş gibidir — ama tanımda saklanır."""
    plain = _definition(steps=(_step(StepKind.SCALE),))
    disabled = ProcessingStep(
        kind=StepKind.ABS, input_channel_id="ch0", parameters={}, enabled=False
    )
    with_disabled = plain.with_step(disabled)

    assert with_disabled.derived_id == plain.derived_id
    assert with_disabled.produces_same_data_as(plain)
    assert with_disabled != plain  # tanim esitligi kapali adimi da gorur
    assert len(with_disabled.chain.steps) == 2


def test_a_disabled_step_survives_the_round_trip() -> None:
    disabled = ProcessingStep(
        kind=StepKind.ABS, input_channel_id="ch0", parameters={}, enabled=False
    )
    definition = _definition(steps=(_step(StepKind.SCALE), disabled))
    restored = DerivedChannelDefinition.from_dict(definition.to_dict())
    assert [step.enabled for step in restored.chain.steps] == [True, False]
    assert restored == definition


def test_the_name_does_not_change_the_identity() -> None:
    """Ad değişince kanal yeniden hesaplanmaz."""
    definition = _definition()
    renamed = definition.renamed("Yeni ad")
    assert renamed.name == "Yeni ad"
    assert renamed.derived_id == definition.derived_id
    assert renamed.produces_same_data_as(definition)


def test_the_unit_and_description_do_not_change_the_identity() -> None:
    plain = _definition()
    annotated = _definition(unit="Pa", description="hidrofon 1 ölçekli")
    assert annotated.unit == "Pa"
    assert annotated.derived_id == plain.derived_id
    assert annotated.produces_same_data_as(plain)


def test_replacing_the_chain_changes_the_identity() -> None:
    definition = _definition()
    changed = definition.with_step(_step(StepKind.ABS))
    assert changed.derived_id != definition.derived_id
    assert not changed.produces_same_data_as(definition)
    assert changed.name == definition.name


def test_adding_a_step_whose_input_is_undeclared_is_refused() -> None:
    with pytest.raises(DerivedChannelError, match="ch9"):
        _definition().with_step(_step(channel="ch9"))


# --------------------------------------------------------------------------- #
# kayipsiz yazma / geri okuma
# --------------------------------------------------------------------------- #


def test_a_definition_round_trips_through_a_dict() -> None:
    definition = _definition(
        steps=(_step(StepKind.SCALE), _step(StepKind.ABS)),
        unit="Pa",
        description="açıklama",
    )
    restored = DerivedChannelDefinition.from_dict(definition.to_dict())
    assert restored == definition
    assert restored.derived_id == definition.derived_id


def test_a_definition_round_trips_through_json_text() -> None:
    """Çalışma alanı dosyası JSON'dur: metin üzerinden de kayıpsız olmalı."""
    definition = _definition(unit="Pa")
    restored = DerivedChannelDefinition.from_dict(json.loads(json.dumps(definition.to_dict())))
    assert restored.derived_id == definition.derived_id
    assert restored.inputs == definition.inputs
    assert restored.unit == "Pa"


def test_the_serialised_form_names_its_schema_version() -> None:
    payload = _definition().to_dict()
    assert payload["schema_version"] == DEFINITION_SCHEMA_VERSION == 1
    assert set(payload) == {"schema_version", "name", "inputs", "chain", "unit", "description"}


def test_an_unknown_schema_version_is_refused() -> None:
    payload = _definition().to_dict()
    payload["schema_version"] = 99
    with pytest.raises(DerivedChannelError, match="Desteklenmeyen tanım şeması"):
        DerivedChannelDefinition.from_dict(payload)


def test_a_missing_schema_version_is_read_as_the_current_one() -> None:
    payload = _definition().to_dict()
    del payload["schema_version"]
    assert DerivedChannelDefinition.from_dict(payload).derived_id == _definition().derived_id


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("name", 5, "name metin"),
        ("inputs", "ch0", "inputs bir dizi"),
        ("chain", {}, "chain bir dizi"),
        ("unit", 3, "unit metin"),
        ("description", 7, "description metin"),
    ],
)
def test_a_malformed_field_is_refused(field_name: str, value: object, message: str) -> None:
    payload = _definition().to_dict()
    payload[field_name] = value
    with pytest.raises(DerivedChannelError, match=message):
        DerivedChannelDefinition.from_dict(payload)


def test_a_non_object_payload_is_refused() -> None:
    with pytest.raises(DerivedChannelError, match="bir nesne olmalı"):
        DerivedChannelDefinition.from_dict(["not", "an", "object"])


def test_a_non_string_input_id_is_refused() -> None:
    payload = _definition().to_dict()
    payload["inputs"] = ["ch0", 7]
    with pytest.raises(DerivedChannelError, match="metin olmalı"):
        DerivedChannelDefinition.from_dict(payload)
