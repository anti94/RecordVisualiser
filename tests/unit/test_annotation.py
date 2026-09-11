"""Annotation ve bookmark modeli — `F4-074`.

Kabul: zaman veya aralık, etiket ve metin kayıpsız taşınır.

"Kayıpsız" burada ölçülebilir: `int64` sınırındaki zaman damgaları,
satır sonu ve unicode taşıyan metin, boş metin ve `None` alanlar
JSON turundan **bit düzeyinde** aynı geri gelir. Ayrıca nokta ve aralık
ayrımının hiçbir adımda kaybolmadığı denetlenir.
"""

from __future__ import annotations

import json

import pytest

from sonar_analyzer.domain.annotation import (
    ANNOTATION_SCHEMA_VERSION,
    MAX_LABEL_LENGTH,
    MAX_TEXT_LENGTH,
    Annotation,
    AnnotationError,
    AnnotationKind,
    AnnotationSet,
    new_annotation_id,
)
from sonar_analyzer.domain.time_range import TimeRange

#: `int64` sınırları — kanonik zaman bunları taşıyabilmeli (ADR-003).
INT64_MAX = 2**63 - 1
INT64_MIN = -(2**63)

T0 = 1_788_901_200_000_000_000
SPAN = TimeRange(T0, T0 + 3_000_000_000)


def _point(label: str = "TX başlangıcı", start: int = T0, **extra: object) -> Annotation:
    return Annotation(id="a1", label=label, start_ns=start, **extra)  # type: ignore[arg-type]


def _range(label: str = "Gürültü", span: TimeRange = SPAN) -> Annotation:
    return Annotation(id="a2", label=label, start_ns=span.start_ns, end_ns=span.end_ns)


# --------------------------------------------------------------------------- #
# nokta / aralik ayrimi
# --------------------------------------------------------------------------- #


def test_a_bookmark_marks_a_single_moment() -> None:
    mark = Annotation.bookmark("TX", T0, annotation_id="b1")
    assert mark.kind is AnnotationKind.POINT
    assert mark.is_point and not mark.is_range
    assert mark.end_ns is None
    assert mark.duration_ns == 0
    assert mark.start_ns == T0


def test_an_annotation_marks_a_range() -> None:
    mark = Annotation.over("Gürültü", SPAN, annotation_id="r1")
    assert mark.kind is AnnotationKind.RANGE
    assert mark.is_range and not mark.is_point
    assert (mark.start_ns, mark.end_ns) == (SPAN.start_ns, SPAN.end_ns)
    assert mark.duration_ns == 3_000_000_000


def test_the_span_of_a_point_is_zero_length() -> None:
    assert _point().span == TimeRange(T0, T0)


def test_the_span_of_a_range_matches_the_source() -> None:
    assert _range().span == SPAN


def test_a_generated_id_is_unique() -> None:
    assert new_annotation_id() != new_annotation_id()
    assert len(new_annotation_id()) == 32


def test_the_constructors_generate_an_id_when_none_is_given() -> None:
    assert Annotation.bookmark("x", T0).id
    assert Annotation.over("x", SPAN).id != Annotation.over("x", SPAN).id


# --------------------------------------------------------------------------- #
# gecerlilik
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("bad", ["", "   "])
def test_a_blank_label_is_refused(bad: str) -> None:
    with pytest.raises(AnnotationError, match="etiketi boş olamaz"):
        _point(label=bad)


@pytest.mark.parametrize("bad", ["", "   "])
def test_a_blank_id_is_refused(bad: str) -> None:
    with pytest.raises(AnnotationError, match="kimliği boş olamaz"):
        Annotation(id=bad, label="x", start_ns=T0)


def test_an_overlong_label_is_refused() -> None:
    with pytest.raises(AnnotationError, match="etiket en fazla"):
        _point(label="x" * (MAX_LABEL_LENGTH + 1))


def test_a_label_exactly_at_the_limit_is_accepted() -> None:
    assert len(_point(label="x" * MAX_LABEL_LENGTH).label) == MAX_LABEL_LENGTH


def test_an_overlong_text_is_refused() -> None:
    with pytest.raises(AnnotationError, match="metin en fazla"):
        _point(text="x" * (MAX_TEXT_LENGTH + 1))


def test_a_backwards_range_is_refused() -> None:
    with pytest.raises(AnnotationError, match="büyük olmalı"):
        Annotation(id="a", label="x", start_ns=T0 + 10, end_ns=T0)


def test_a_zero_length_range_is_refused_and_says_what_to_do() -> None:
    """Sessizce noktaya çevirmek yanlış girdiyi gizlerdi."""
    with pytest.raises(AnnotationError, match="end_ns=None"):
        Annotation(id="a", label="x", start_ns=T0, end_ns=T0)


@pytest.mark.parametrize("bad", [True, 1.5, "100", None])
def test_a_non_integer_start_is_refused(bad: object) -> None:
    with pytest.raises(AnnotationError, match="tam sayı ns"):
        Annotation(id="a", label="x", start_ns=bad)  # type: ignore[arg-type]


@pytest.mark.parametrize("bad", [True, 1.5, "100"])
def test_a_non_integer_end_is_refused(bad: object) -> None:
    with pytest.raises(AnnotationError, match="tam sayı ns"):
        Annotation(id="a", label="x", start_ns=T0, end_ns=bad)  # type: ignore[arg-type]


def test_a_blank_channel_id_is_refused() -> None:
    with pytest.raises(AnnotationError, match="kanal kimliği"):
        _point(channel_id="  ")


def test_a_channel_bound_mark_keeps_its_channel() -> None:
    assert _point(channel_id="ch0").channel_id == "ch0"
    assert _point().channel_id is None


# --------------------------------------------------------------------------- #
# zaman sorgulari
# --------------------------------------------------------------------------- #


def test_a_point_contains_only_its_own_instant() -> None:
    mark = _point()
    assert mark.contains(T0)
    assert not mark.contains(T0 - 1)
    assert not mark.contains(T0 + 1)


def test_a_range_is_half_open() -> None:
    mark = _range()
    assert mark.contains(SPAN.start_ns)
    assert mark.contains(SPAN.end_ns - 1)
    assert not mark.contains(SPAN.end_ns)
    assert not mark.contains(SPAN.start_ns - 1)


def test_a_point_overlaps_a_window_that_holds_it() -> None:
    mark = _point()
    assert mark.overlaps(TimeRange(T0 - 10, T0 + 10))
    assert mark.overlaps(TimeRange(T0, T0 + 1))
    assert not mark.overlaps(TimeRange(T0 + 1, T0 + 10))
    assert not mark.overlaps(TimeRange(T0 - 10, T0))  # yari acik


def test_a_range_overlaps_when_the_windows_touch_inside() -> None:
    mark = _range()
    assert mark.overlaps(TimeRange(SPAN.end_ns - 1, SPAN.end_ns + 100))
    assert mark.overlaps(TimeRange(SPAN.start_ns - 100, SPAN.start_ns + 1))
    assert not mark.overlaps(TimeRange(SPAN.end_ns, SPAN.end_ns + 100))
    assert not mark.overlaps(TimeRange(SPAN.start_ns - 100, SPAN.start_ns))


# --------------------------------------------------------------------------- #
# duzenleme kimligi korur
# --------------------------------------------------------------------------- #


def test_renaming_keeps_the_identity_and_the_time() -> None:
    mark = _point(text="not")
    renamed = mark.renamed("Yeni etiket")
    assert renamed.id == mark.id
    assert renamed.label == "Yeni etiket"
    assert (renamed.start_ns, renamed.end_ns, renamed.text) == (
        mark.start_ns,
        mark.end_ns,
        mark.text,
    )


def test_editing_the_text_keeps_everything_else() -> None:
    mark = _range()
    edited = mark.with_text("uzun\nnot")
    assert edited.id == mark.id
    assert edited.text == "uzun\nnot"
    assert edited.span == mark.span


def test_a_range_can_be_narrowed_to_a_point_without_losing_identity() -> None:
    mark = _range()
    point = mark.moved_to(T0 + 5)
    assert point.id == mark.id
    assert point.is_point
    assert point.start_ns == T0 + 5


def test_a_point_can_be_widened_to_a_range_without_losing_identity() -> None:
    mark = _point(text="not")
    widened = mark.widened_to(SPAN)
    assert widened.id == mark.id
    assert widened.is_range
    assert widened.span == SPAN
    assert widened.text == "not"


# --------------------------------------------------------------------------- #
# KAYIPSIZ tasima
# --------------------------------------------------------------------------- #


def test_a_point_round_trips_through_a_dict() -> None:
    mark = Annotation.bookmark("TX", T0, text="not", channel_id="ch0", annotation_id="b1")
    assert Annotation.from_dict(mark.to_dict()) == mark


def test_a_range_round_trips_through_a_dict() -> None:
    mark = Annotation.over("Gürültü", SPAN, text="not", annotation_id="r1")
    assert Annotation.from_dict(mark.to_dict()) == mark


def test_the_point_range_distinction_survives_the_round_trip() -> None:
    point = Annotation.from_dict(_point().to_dict())
    ranged = Annotation.from_dict(_range().to_dict())
    assert point.is_point and point.end_ns is None
    assert ranged.is_range and ranged.end_ns == SPAN.end_ns


@pytest.mark.parametrize("start", [0, 1, -1, INT64_MAX, INT64_MIN, T0])
def test_extreme_timestamps_survive_json(start: int) -> None:
    """Kanonik zaman `int64`'tür; JSON turunda tam sayı kalmalı."""
    mark = Annotation(id="a", label="x", start_ns=start)
    restored = Annotation.from_dict(json.loads(json.dumps(mark.to_dict())))
    assert restored.start_ns == start
    assert isinstance(restored.start_ns, int)


def test_the_largest_representable_range_survives_json() -> None:
    mark = Annotation(id="a", label="x", start_ns=INT64_MIN, end_ns=INT64_MAX)
    restored = Annotation.from_dict(json.loads(json.dumps(mark.to_dict())))
    assert (restored.start_ns, restored.end_ns) == (INT64_MIN, INT64_MAX)
    assert restored.duration_ns == INT64_MAX - INT64_MIN


@pytest.mark.parametrize(
    "text",
    [
        "",
        "tek satır",
        "iki\nsatır",
        "CRLF\r\nsatır",
        "sekme\tvar",
        "Türkçe ğüşiöç ĞÜŞİÖÇ",
        "emoji 🐬 ve ölçü µs",
        "tırnak \"çift\" ve 'tek'",
        "ters bölü \\ ve {süslü}",
        " baştaki ve sondaki boşluk ",
    ],
)
def test_text_content_survives_json_byte_for_byte(text: str) -> None:
    mark = Annotation(id="a", label="x", start_ns=T0, text=text)
    restored = Annotation.from_dict(json.loads(json.dumps(mark.to_dict())))
    assert restored.text == text


def test_a_label_with_unicode_survives_json() -> None:
    label = "Hidrofon 1 — ölçüm · 🐬"
    mark = Annotation(id="a", label=label, start_ns=T0)
    assert Annotation.from_dict(json.loads(json.dumps(mark.to_dict()))).label == label


def test_the_serialised_form_names_its_schema_version() -> None:
    payload = _point().to_dict()
    assert payload["schema_version"] == ANNOTATION_SCHEMA_VERSION == 1
    assert set(payload) == {
        "schema_version",
        "id",
        "label",
        "start_ns",
        "end_ns",
        "text",
        "channel_id",
    }


def test_an_unknown_schema_version_is_refused() -> None:
    payload = _point().to_dict()
    payload["schema_version"] = 99
    with pytest.raises(AnnotationError, match="Desteklenmeyen işaret şeması"):
        Annotation.from_dict(payload)


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("id", 5, "id metin"),
        ("label", None, "label metin"),
        ("start_ns", "100", "start_ns tam sayı"),
        ("start_ns", 1.5, "start_ns tam sayı"),
        ("end_ns", "100", "end_ns tam sayı"),
        ("text", 7, "text metin"),
        ("channel_id", 7, "channel_id metin"),
    ],
)
def test_a_malformed_field_is_refused(field_name: str, value: object, message: str) -> None:
    payload = _point().to_dict()
    payload[field_name] = value
    with pytest.raises(AnnotationError, match=message):
        Annotation.from_dict(payload)


def test_a_non_object_payload_is_refused() -> None:
    with pytest.raises(AnnotationError, match="bir nesne olmalı"):
        Annotation.from_dict([1, 2, 3])


# --------------------------------------------------------------------------- #
# kume
# --------------------------------------------------------------------------- #


def test_an_empty_set_has_nothing() -> None:
    marks = AnnotationSet()
    assert len(marks) == 0
    assert list(marks) == []
    assert marks.get("yok") is None
    assert "yok" not in marks


def test_marks_are_kept_sorted_by_time() -> None:
    late = Annotation(id="c", label="geç", start_ns=T0 + 200)
    early = Annotation(id="a", label="erken", start_ns=T0)
    middle = Annotation(id="b", label="orta", start_ns=T0 + 100)
    marks = AnnotationSet((late, early, middle))
    assert [item.id for item in marks] == ["a", "b", "c"]


def test_marks_at_the_same_time_are_ordered_stably() -> None:
    first = Annotation(id="z", label="aaa", start_ns=T0)
    second = Annotation(id="y", label="bbb", start_ns=T0)
    assert [item.id for item in AnnotationSet((second, first))] == ["z", "y"]


def test_a_duplicate_id_is_refused() -> None:
    with pytest.raises(AnnotationError, match="iki kez"):
        AnnotationSet((_point(), _point()))


def test_adding_a_mark_returns_a_new_set() -> None:
    marks = AnnotationSet()
    added = marks.added(_point())
    assert len(marks) == 0
    assert len(added) == 1
    assert added.get("a1") is not None
    assert "a1" in added


def test_adding_the_same_id_replaces_the_mark() -> None:
    """Aynı kimlik düzenleme demektir, çoğaltma değil."""
    marks = AnnotationSet((_point(label="eski"),))
    updated = marks.added(_point(label="yeni"))
    assert len(updated) == 1
    mark = updated.get("a1")
    assert mark is not None and mark.label == "yeni"


def test_removing_a_mark_returns_a_new_set() -> None:
    marks = AnnotationSet((_point(), _range()))
    assert len(marks.removed("a1")) == 1
    assert len(marks) == 2
    assert len(marks.removed("yok")) == 2
    assert len(marks.cleared()) == 0


def test_bookmarks_and_ranges_are_listed_separately() -> None:
    marks = AnnotationSet((_point(), _range()))
    assert [item.id for item in marks.bookmarks()] == ["a1"]
    assert [item.id for item in marks.ranges()] == ["a2"]


def test_marks_can_be_filtered_by_window() -> None:
    marks = AnnotationSet(
        (
            Annotation(id="a", label="x", start_ns=T0),
            Annotation(id="b", label="y", start_ns=T0 + 1_000),
            Annotation(id="c", label="z", start_ns=T0 + 5_000, end_ns=T0 + 6_000),
        )
    )
    assert [item.id for item in marks.in_range(TimeRange(T0, T0 + 2_000))] == ["a", "b"]
    assert [item.id for item in marks.in_range(TimeRange(T0 + 5_500, T0 + 7_000))] == ["c"]
    assert marks.in_range(TimeRange(T0 + 100, T0 + 200)) == ()


def test_marks_can_be_found_at_an_instant() -> None:
    marks = AnnotationSet((_point(), _range()))
    assert [item.id for item in marks.at(T0)] == ["a1", "a2"]
    assert [item.id for item in marks.at(SPAN.end_ns - 1)] == ["a2"]
    assert marks.at(SPAN.end_ns) == ()


def test_marks_can_be_filtered_by_channel() -> None:
    marks = AnnotationSet(
        (
            Annotation(id="a", label="x", start_ns=T0, channel_id="ch0"),
            Annotation(id="b", label="y", start_ns=T0 + 1, channel_id="ch1"),
            Annotation(id="c", label="z", start_ns=T0 + 2),
        )
    )
    assert [item.id for item in marks.for_channel("ch0")] == ["a"]
    assert [item.id for item in marks.for_channel(None)] == ["c"]


def test_a_set_round_trips_through_json() -> None:
    marks = AnnotationSet(
        (
            Annotation.bookmark("TX", T0, text="not", annotation_id="b1"),
            Annotation.over("Gürültü", SPAN, text="iki\nsatır", annotation_id="r1"),
        )
    )
    restored = AnnotationSet.from_list(json.loads(json.dumps(marks.to_list())))
    assert restored == marks
    assert [item.id for item in restored] == ["b1", "r1"]


def test_a_non_list_payload_is_refused() -> None:
    with pytest.raises(AnnotationError, match="bir dizi olmalı"):
        AnnotationSet.from_list({"not": "a list"})
