"""Durum ikonları ve kanal paleti — `F1-030`.

Kabul: XYZ serileri mavi/turuncu/yeşildir; durumlar ikon ve metinle ayrılır.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="PySide6 kurulu degil")

from pytestqt.qtbot import QtBot

from sonar_analyzer.domain.event import BitState, Severity
from sonar_analyzer.ui.status_icons import (
    BIT_STYLES,
    ICON_SIZE,
    SEVERITY_STYLES,
    bit_style,
    channel_color,
    make_status_icon,
    severity_style,
)
from sonar_analyzer.ui.theme import CHANNEL_COLORS, DARK

pytestmark = pytest.mark.gui


# -- durum: ikon + metin ---------------------------------------------------


def test_every_bit_state_has_a_style() -> None:
    for state in BitState:
        assert state in BIT_STYLES, f"{state} icin stil yok"


def test_every_severity_has_a_style() -> None:
    for severity in Severity:
        assert severity in SEVERITY_STYLES


def test_states_are_distinguished_without_color() -> None:
    """Renk kaldırılsa bile durumlar ayırt edilebilmeli."""
    symbols = [style.symbol for style in BIT_STYLES.values()]
    labels = [style.label for style in BIT_STYLES.values()]

    assert len(set(symbols)) == len(symbols), f"simgeler benzersiz degil: {symbols}"
    assert len(set(labels)) == len(labels), f"metinler benzersiz degil: {labels}"


def test_severity_symbols_are_distinct() -> None:
    symbols = [style.symbol for style in SEVERITY_STYLES.values()]
    assert len(set(symbols)) == len(symbols)


def test_describe_contains_symbol_and_text() -> None:
    style = bit_style(BitState.FAIL)
    assert style.symbol in style.describe()
    assert style.label in style.describe()
    assert style.describe() == "✕ Fail"


def test_state_colors_use_theme_tokens() -> None:
    assert bit_style(BitState.PASS).color == DARK.pass_
    assert bit_style(BitState.WARN).color == DARK.warning
    assert bit_style(BitState.FAIL).color == DARK.error
    assert severity_style(Severity.CRITICAL).color == DARK.critical


def test_unknown_state_falls_back_without_claiming_pass() -> None:
    style = bit_style(BitState.UNKNOWN)
    assert style.label == "Unknown"
    assert style.color != DARK.pass_


# -- kanal renkleri --------------------------------------------------------


def test_xyz_series_are_blue_orange_green() -> None:
    """Kabul kriteri: XYZ mavi/turuncu/yeşil."""
    assert channel_color("ch2", index=0) == "#4C9AFF"
    assert channel_color("ch3", index=1) == "#F2994A"
    assert channel_color("ch4", index=2) == "#39C77A"


def test_channel_color_is_stable_for_the_same_id() -> None:
    """Aynı kanal çalışma alanı boyunca aynı rengi korumalı."""
    first = channel_color("Acoustic/Hydrophone 1")
    second = channel_color("Acoustic/Hydrophone 1")
    assert first == second
    assert first in CHANNEL_COLORS


def test_channel_colors_wrap_around_the_palette() -> None:
    count = len(CHANNEL_COLORS)
    assert channel_color("x", index=count) == CHANNEL_COLORS[0]
    assert channel_color("x", index=count + 2) == CHANNEL_COLORS[2]


def test_different_channels_can_get_different_colors() -> None:
    colors = {channel_color(f"ch{i}", index=i) for i in range(len(CHANNEL_COLORS))}
    assert len(colors) == len(CHANNEL_COLORS)


# -- ikon uretimi ----------------------------------------------------------


def test_icon_is_created_with_requested_size(qtbot: QtBot) -> None:
    del qtbot  # QApplication'in var olmasi yeterli
    icon = make_status_icon(bit_style(BitState.PASS))
    assert not icon.isNull()

    sizes = icon.availableSizes()
    assert sizes, "ikon bos"
    assert sizes[0].width() == ICON_SIZE


def test_icons_differ_between_states(qtbot: QtBot) -> None:
    del qtbot
    ok = make_status_icon(bit_style(BitState.PASS)).pixmap(ICON_SIZE, ICON_SIZE)
    fail = make_status_icon(bit_style(BitState.FAIL)).pixmap(ICON_SIZE, ICON_SIZE)

    assert ok.toImage() != fail.toImage(), "farkli durumlar ayni ikonu vermemeli"


def test_custom_size_is_respected(qtbot: QtBot) -> None:
    del qtbot
    icon = make_status_icon(bit_style(BitState.WARN), size=24)
    assert icon.availableSizes()[0].width() == 24
