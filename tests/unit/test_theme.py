"""Koyu tema tokenları ve kontrast — `F1-029`.

Bu testler Qt gerektirmez: tokenlar ve kontrast hesabı saf Python'dur.
"""

from __future__ import annotations

import re

import pytest

from sonar_analyzer.ui.theme import (
    CHANNEL_COLORS,
    DARK,
    ON_ACCENT,
    Palette,
    build_stylesheet,
    contrast_ratio,
    relative_luminance,
)

#: WCAG 2.x normal metin esigi.
MIN_TEXT_CONTRAST = 4.5
#: Buyuk metin ve arayuz bilesenleri icin esik.
MIN_UI_CONTRAST = 3.0

HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


# -- tokenlar --------------------------------------------------------------


def test_tokens_match_plan_section_6_2() -> None:
    assert DARK.background == "#0B1118"
    assert DARK.surface == "#121B24"
    assert DARK.surface_elevated == "#182430"
    assert DARK.border == "#2B3A48"
    assert DARK.text_primary == "#E6EDF3"
    assert DARK.text_secondary == "#94A3B8"
    assert DARK.accent == "#1689F5"
    assert DARK.pass_ == "#39C77A"
    assert DARK.warning == "#F2B84B"
    assert DARK.error == "#EF5B5B"
    assert DARK.critical == "#D946EF"


def test_all_tokens_are_valid_hex() -> None:
    for name, value in DARK.as_dict().items():
        assert HEX.match(value), f"{name} gecersiz: {value}"


def test_channel_palette_has_at_least_eight_colors() -> None:
    """Plan Bölüm 6.3: en az 8 kanallı sabit palet."""
    assert len(CHANNEL_COLORS) >= 8
    assert len(set(CHANNEL_COLORS)) == len(CHANNEL_COLORS), "renkler benzersiz olmali"
    for color in CHANNEL_COLORS:
        assert HEX.match(color)


def test_xyz_colors_are_blue_orange_green() -> None:
    """Plan Bölüm 5.1: XYZ için mavi/turuncu/yeşil."""
    blue, orange, green = CHANNEL_COLORS[0], CHANNEL_COLORS[1], CHANNEL_COLORS[2]
    assert blue == "#4C9AFF"
    assert orange == "#F2994A"
    assert green == "#39C77A"


# -- kontrast --------------------------------------------------------------


def test_luminance_bounds() -> None:
    assert relative_luminance("#000000") == 0.0
    assert relative_luminance("#FFFFFF") == 1.0
    assert 0.0 < relative_luminance(DARK.accent) < 1.0


def test_invalid_color_is_rejected() -> None:
    with pytest.raises(ValueError, match="RRGGBB"):
        relative_luminance("#FFF")


def test_contrast_is_symmetric_and_bounded() -> None:
    assert contrast_ratio("#000000", "#FFFFFF") == 21.0
    assert contrast_ratio("#FFFFFF", "#000000") == 21.0
    assert contrast_ratio(DARK.accent, DARK.accent) == 1.0


@pytest.mark.parametrize(
    ("name", "foreground", "background"),
    [
        ("ana metin / arka plan", DARK.text_primary, DARK.background),
        ("ana metin / yuzey", DARK.text_primary, DARK.surface),
        ("ana metin / yukseltilmis yuzey", DARK.text_primary, DARK.surface_elevated),
        ("ikincil metin / yuzey", DARK.text_secondary, DARK.surface),
        ("vurgu / arka plan", DARK.accent, DARK.background),
        ("vurgu uzeri metin", ON_ACCENT, DARK.accent),
        ("pass / yuzey", DARK.pass_, DARK.surface),
        ("warning / yuzey", DARK.warning, DARK.surface),
        ("error / yuzey", DARK.error, DARK.surface),
        ("critical / yuzey", DARK.critical, DARK.surface),
    ],
)
def test_text_contrast_meets_wcag(name: str, foreground: str, background: str) -> None:
    ratio = contrast_ratio(foreground, background)
    assert ratio >= MIN_TEXT_CONTRAST, f"{name}: {ratio:.2f}:1 < {MIN_TEXT_CONTRAST}:1"


def test_white_on_accent_would_fail() -> None:
    """ON_ACCENT'in neden beyaz olmadığını sabitler."""
    assert contrast_ratio("#FFFFFF", DARK.accent) < MIN_TEXT_CONTRAST
    assert contrast_ratio(ON_ACCENT, DARK.accent) >= MIN_TEXT_CONTRAST
    assert DARK.background == ON_ACCENT


def test_on_accent_follows_the_palette() -> None:
    """Koyu bir vurgu renginde beyaz metin seçilmeli."""
    dark_accent = Palette(accent="#0A2540")
    assert dark_accent.on_accent == "#FFFFFF"
    assert contrast_ratio(dark_accent.on_accent, dark_accent.accent) >= MIN_TEXT_CONTRAST


#: Ayirici cizgiler bilerek dusuk kontrastlidir; olculen degerlerin altina
#: dusmemesi yeterli. Metin esikleriyle karistirilmamali.
MIN_BORDER_CONTRAST = 1.4


def test_borders_are_visible_against_surfaces() -> None:
    """Panel sınırları ayırt edilebilmeli (mockup'ta kartlar çerçeveli).

    Sınırlar metin değildir; koyu temada bilerek düşük kontrastlıdır. Burada
    aranan, sınırın yüzeyden **ayırt edilebilir** olması: ölçülen değerler
    1.49 (yüzey) ve 1.63 (arka plan).
    """
    assert contrast_ratio(DARK.border, DARK.surface) >= MIN_BORDER_CONTRAST
    assert contrast_ratio(DARK.border, DARK.background) >= MIN_BORDER_CONTRAST
    assert contrast_ratio(DARK.border, DARK.surface) > contrast_ratio(
        DARK.surface, DARK.background
    ), "sinir, iki yuzey arasindaki farktan daha belirgin olmali"


def test_channel_colors_are_readable_on_plot_background() -> None:
    for color in CHANNEL_COLORS:
        ratio = contrast_ratio(color, DARK.surface)
        assert ratio >= MIN_UI_CONTRAST, f"{color}: {ratio:.2f}:1"


# -- stil sayfasi ----------------------------------------------------------


def test_stylesheet_uses_tokens_not_literals() -> None:
    sheet = build_stylesheet()
    assert DARK.background in sheet
    assert DARK.accent in sheet
    assert "#FFFFFF" not in sheet, "vurgu uzerine beyaz metin yazilmamali"


def test_selected_tab_is_marked_with_accent() -> None:
    """Kabul kriteri: seçili sekmeler referansla tutarlı."""
    sheet = build_stylesheet()
    selected = sheet[sheet.index("QTabBar::tab:selected") :]
    block = selected[: selected.index("}")]
    assert DARK.accent in block, "secili sekme vurgu rengiyle isaretlenmeli"
    assert DARK.text_primary in block


def test_stylesheet_follows_custom_palette() -> None:
    custom = Palette(background="#101010", accent="#FF00FF")
    sheet = build_stylesheet(custom)
    assert "#101010" in sheet
    assert "#FF00FF" in sheet
    assert DARK.background not in sheet
