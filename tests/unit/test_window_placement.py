"""Pencere konumlarının ekranlara sınırlanması — `F4-083`.

Kabul: monitör çıkartılınca pencere görünür alana geri gelir.

Geometri saf olduğu için ekran listesi elle kurulur: iki monitörlü bir
masaüstü, ikincisi sökülür ve kaydedilen konumun ne olduğu tek tek
denetlenir. Beklenen koordinatlar elle hesaplanmıştır.
"""

from __future__ import annotations

import pytest

from sonar_analyzer.ui.window_placement import (
    MIN_VISIBLE_FRACTION,
    MIN_VISIBLE_PIXELS,
    PlacementError,
    Rect,
    clamp_to_screens,
    decode_geometry,
    encode_geometry,
    is_visible_enough,
    visible_area,
)

#: Birincil monitör: 1920x1080, sol üstte.
PRIMARY = Rect(0, 0, 1920, 1080)
#: İkinci monitör: sağda, aynı boyut.
SECONDARY = Rect(1920, 0, 1920, 1080)
BOTH = (PRIMARY, SECONDARY)
ONLY_PRIMARY = (PRIMARY,)


# --------------------------------------------------------------------------- #
# dikdortgen
# --------------------------------------------------------------------------- #


def test_a_rect_knows_its_edges_and_area() -> None:
    rect = Rect(10, 20, 100, 50)
    assert (rect.right, rect.bottom) == (110, 70)
    assert rect.area == 5_000
    assert rect.to_tuple() == (10, 20, 100, 50)


@pytest.mark.parametrize(("width", "height"), [(0, 10), (10, 0), (-1, 10)])
def test_a_rect_needs_a_positive_size(width: int, height: int) -> None:
    with pytest.raises(PlacementError, match="pozitif olmalı"):
        Rect(0, 0, width, height)


def test_overlapping_rects_report_their_shared_area() -> None:
    assert Rect(0, 0, 100, 100).intersection_area(Rect(50, 50, 100, 100)) == 2_500


def test_touching_rects_do_not_overlap() -> None:
    """Kenar kenara duran iki dikdörtgenin kesişimi sıfırdır."""
    assert Rect(0, 0, 100, 100).intersection_area(Rect(100, 0, 100, 100)) == 0


def test_disjoint_rects_have_no_shared_area() -> None:
    assert Rect(0, 0, 10, 10).intersection_area(Rect(500, 500, 10, 10)) == 0


# --------------------------------------------------------------------------- #
# gorunurluk
# --------------------------------------------------------------------------- #


def test_a_window_inside_a_screen_is_fully_visible() -> None:
    window = Rect(100, 100, 800, 600)
    assert visible_area(window, BOTH) == window.area
    assert is_visible_enough(window, BOTH)


def test_a_window_on_the_second_monitor_is_visible_while_it_exists() -> None:
    window = Rect(2200, 200, 800, 600)
    assert is_visible_enough(window, BOTH)


def test_the_same_window_is_invisible_once_that_monitor_is_gone() -> None:
    """Kabul kriterinin başlangıç durumu."""
    window = Rect(2200, 200, 800, 600)
    assert visible_area(window, ONLY_PRIMARY) == 0
    assert not is_visible_enough(window, ONLY_PRIMARY)


def test_a_window_half_off_the_edge_still_counts_as_visible() -> None:
    """Kullanıcının kendi taşırdığı pencere geri zıplamamalı."""
    window = Rect(1520, 100, 800, 600)  # 400 px ekranda
    assert is_visible_enough(window, ONLY_PRIMARY)


def test_a_window_with_only_a_sliver_showing_is_not_enough() -> None:
    window = Rect(1915, 100, 800, 600)  # 5 px ekranda = 3000 px^2
    assert visible_area(window, ONLY_PRIMARY) == 5 * 600
    assert not is_visible_enough(window, ONLY_PRIMARY)


def test_the_visible_area_never_exceeds_the_window() -> None:
    """Çakışan ekranlarda çifte sayım olmamalı."""
    overlapping = (Rect(0, 0, 1920, 1080), Rect(0, 0, 1920, 1080))
    window = Rect(100, 100, 200, 200)
    assert visible_area(window, overlapping) == window.area


def test_the_thresholds_are_documented() -> None:
    assert MIN_VISIBLE_FRACTION == 0.25
    assert MIN_VISIBLE_PIXELS == 10_000


# --------------------------------------------------------------------------- #
# MONITOR CIKARTILINCA geri gelir
# --------------------------------------------------------------------------- #


def test_a_window_on_a_removed_monitor_comes_back_onto_the_primary() -> None:
    """Kabul kriterinin kendisi."""
    saved = Rect(2200, 200, 800, 600)

    placed = clamp_to_screens(saved, ONLY_PRIMARY)

    assert placed != saved
    assert is_visible_enough(placed, ONLY_PRIMARY)
    assert visible_area(placed, ONLY_PRIMARY) == placed.area  # tamamen icerde


def test_the_recovered_window_keeps_its_size() -> None:
    saved = Rect(2200, 200, 800, 600)
    placed = clamp_to_screens(saved, ONLY_PRIMARY)
    assert (placed.width, placed.height) == (800, 600)


def test_the_recovered_window_lands_at_the_nearest_edge() -> None:
    """2200 -> ekranın sağ kenarına kenetlenir: 1920 - 800 = 1120."""
    placed = clamp_to_screens(Rect(2200, 200, 800, 600), ONLY_PRIMARY)
    assert (placed.x, placed.y) == (1120, 200)


def test_a_window_above_the_desktop_comes_down() -> None:
    placed = clamp_to_screens(Rect(100, -2000, 800, 600), ONLY_PRIMARY)
    assert (placed.x, placed.y) == (100, 0)


def test_a_window_below_the_desktop_comes_up() -> None:
    """1080 - 600 = 480."""
    placed = clamp_to_screens(Rect(100, 5000, 800, 600), ONLY_PRIMARY)
    assert (placed.x, placed.y) == (100, 480)


def test_a_window_larger_than_the_screen_is_shrunk_to_fit() -> None:
    placed = clamp_to_screens(Rect(4000, 4000, 3000, 2000), ONLY_PRIMARY)
    assert (placed.width, placed.height) == (1920, 1080)
    assert (placed.x, placed.y) == (0, 0)


def test_a_visible_window_is_left_exactly_where_it_is() -> None:
    """Gereksiz yeniden konumlandırma yok."""
    window = Rect(300, 300, 800, 600)
    assert clamp_to_screens(window, BOTH) is window


def test_a_window_on_the_second_monitor_stays_there_while_it_exists() -> None:
    window = Rect(2200, 200, 800, 600)
    assert clamp_to_screens(window, BOTH) == window


def test_a_partly_visible_window_prefers_the_screen_it_overlaps() -> None:
    """Çoğunlukla ikinci ekranda olan bir pencere birinciye atılmaz."""
    window = Rect(1900, 100, 800, 600)  # 20 px birincide, 780 px ikincide
    placed = clamp_to_screens(window, BOTH)
    assert placed == window  # zaten yeterince gorunuyor


def test_with_no_screens_the_call_is_refused() -> None:
    with pytest.raises(PlacementError, match="En az bir ekran"):
        clamp_to_screens(Rect(0, 0, 10, 10), ())


def test_the_window_returns_to_a_screen_that_is_not_at_the_origin() -> None:
    """Birincil monitör (0,0)'da olmayabilir (ör. soldaki ikinci ekran)."""
    left_screen = Rect(-1920, 0, 1920, 1080)
    placed = clamp_to_screens(Rect(5000, 5000, 400, 300), (left_screen,))
    assert placed.x >= left_screen.x
    assert placed.right <= left_screen.right
    assert visible_area(placed, (left_screen,)) == placed.area


# --------------------------------------------------------------------------- #
# kayit bicimi
# --------------------------------------------------------------------------- #


def test_a_placement_round_trips_through_text() -> None:
    rect = Rect(120, -40, 1024, 768)
    assert encode_geometry(rect) == "120,-40,1024,768"
    assert decode_geometry(encode_geometry(rect)) == rect


@pytest.mark.parametrize(
    "text", ["", "1,2,3", "1,2,3,4,5", "a,b,c,d", "1,2,0,4", "1,2,3,-4", "1;2;3;4"]
)
def test_a_broken_record_is_forgotten_not_fatal(text: str) -> None:
    """Bozuk kayıt uygulamayı açmayı engellememeli."""
    assert decode_geometry(text) is None


def test_whitespace_around_the_numbers_is_tolerated() -> None:
    assert decode_geometry(" 10 , 20 , 30 , 40 ") == Rect(10, 20, 30, 40)
