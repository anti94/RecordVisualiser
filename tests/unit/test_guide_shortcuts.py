"""Klavye, mouse ve ölçekleme kılavuzu — `F6-028`.

Kabul: **Bölüm 16 kısayolları paketli uygulamadaki davranışla eşleşir.**

Kısayol belgeleri en hızlı eskiyen belgelerdir: tuş bağlaması kodda
değişir, tablo yerinde kalır. Yanlış bir kısayol tablosu, kullanıcıyı
çalışmayan bir tuşa basmaya yollar ve uygulamanın bozuk olduğunu
düşündürür.

Bu yüzden test **çift yönlü** eşleşme arar:

* kılavuzda yazan her kısayol uygulamada gerçekten bağlıdır,
* uygulamada bağlı her kısayol kılavuzda yazar.

Yalnız ilk yön denetlenseydi, belgede hiç anılmayan bir kısayolun
sessizce eklenmesi yakalanmazdı.

Kısayollar kaynaktaki iki kayıttan okunur (`MENU_SPECS`, `SHORTCUTS`),
kılavuzdan ise Markdown tablolarındaki `` `...` `` hücreleri
ayrıştırılır — yani test, belgenin *insan tarafından okunan* hâlini
denetler, ayrıca tutulan bir listeyi değil.
"""

from __future__ import annotations

import re
from pathlib import Path

from sonar_analyzer.ui.actions import MENU_SPECS
from sonar_analyzer.ui.shortcuts import SHORTCUTS

ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "docs" / "guide" / "klavye-ve-mouse.md"
PLAN = ROOT / "plan.md"

#: Plan Bölüm 16 tablosundaki kısayollar (belge ile aynı sırada).
PLAN_SECTION_16: tuple[tuple[str, str], ...] = (
    ("Ctrl+O", "Dosya aç"),
    ("Ctrl+S", "Workspace kaydet"),
    ("Space", "Play/Pause"),
    ("Home", "Görünümü sıfırla"),
    ("X", "X zoom modu"),
    ("Y", "Y zoom modu"),
    ("B", "XY zoom modu"),
    ("C", "Cursor modu"),
    ("R", "Region selection"),
    ("Ctrl+E", "Event paneline odaklan"),
    ("F4", "Sonraki event"),
    ("Shift+F4", "Önceki event"),
    ("Ctrl+K", "Command palette"),
)

#: Bölüm 16'da olup bu sürümde farklı uygulanan maddeler.
DIVERGENCES: frozenset[str] = frozenset({"Ctrl+E", "Ctrl+K"})


def _guide() -> str:
    return GUIDE.read_text(encoding="utf-8")


def _flat() -> str:
    """Kılavuz metni, satır sarmaları kaldırılmış hâlde.

    Markdown 80 sütuna sarılır; bir cümlenin iki satıra bölünmesi onu
    yazılmamış saymaz. Cümle aramaları bu düzleştirilmiş metinde yapılır.
    """
    return " ".join(_guide().split())


def _app_shortcuts() -> set[str]:
    """Uygulamanın gerçekten bağladığı tüm tuş dizileri."""
    bound = {spec.shortcut for menu in MENU_SPECS for spec in menu.actions if spec.shortcut}
    bound |= {spec.key for spec in SHORTCUTS}
    return bound


def _documented_shortcuts() -> set[str]:
    """Kılavuzun tablolarındaki ilk sütunda geçen tuş dizileri.

    Yalnız satır başındaki `| \\`...\\` |` hücreleri sayılır; gövde
    metnindeki anmalar (örneğin bir cümlenin içindeki `Ctrl+E`) tablo
    sözleşmesi değildir.
    """
    found: set[str] = set()
    for line in _guide().splitlines():
        match = re.match(r"^\|\s*`([^`]+)`\s*\|", line)
        if match:
            found.add(match.group(1))
    return found


# --------------------------------------------------------------------------- #
# BELGE VAR
# --------------------------------------------------------------------------- #


def test_the_guide_exists() -> None:
    assert GUIDE.is_file()


def test_the_guide_states_that_the_tables_come_from_the_source() -> None:
    """Kaynağı söylenmeyen bir tablo, doğrulanabilir bir söz vermez."""
    text = _guide()
    assert "ui/actions.py" in text
    assert "ui/shortcuts.py" in text


# --------------------------------------------------------------------------- #
# CIFT YONLU ESLESME
# --------------------------------------------------------------------------- #


def test_every_documented_shortcut_is_actually_bound() -> None:
    """Kılavuzda yazan bir tuş uygulamada yoksa, kullanıcı boşa basar."""
    undocumented = _documented_shortcuts() - _app_shortcuts()
    assert not undocumented, f"kilavuzda var, uygulamada yok: {sorted(undocumented)}"


def test_every_bound_shortcut_is_documented() -> None:
    """Uygulamada olup belgede olmayan bir kısayol sessizce eklenmiş olurdu."""
    missing = _app_shortcuts() - _documented_shortcuts()
    assert not missing, f"uygulamada var, kilavuzda yok: {sorted(missing)}"


def test_the_two_sets_are_not_trivially_empty() -> None:
    """Boş küme ile boş kümeyi karşılaştırmak her zaman geçerdi."""
    assert len(_app_shortcuts()) >= 20
    assert _documented_shortcuts() == _app_shortcuts()


# --------------------------------------------------------------------------- #
# BOLUM 16 KAPSAMI
# --------------------------------------------------------------------------- #


def test_the_plan_section_16_table_is_transcribed_correctly() -> None:
    """Testin dayandığı Bölüm 16 listesi plan'daki tabloyla aynı olmalı."""
    plan_text = PLAN.read_text(encoding="utf-8")
    start = plan_text.index("## 16. Klavye ve mouse etkileşimleri")
    section = plan_text[start : plan_text.index("## 17. Test stratejisi", start)]
    for key, label in PLAN_SECTION_16:
        if key == "F4":  # plan tek satirda "F4 / Shift+F4" yazar
            assert "`F4` / `Shift+F4`" in section
            continue
        if key == "Shift+F4":
            continue
        assert f"`{key}`" in section, f"{key} plan Bolum 16'da yok"
        assert label in section, f"{label} plan Bolum 16'da yok"


def test_every_non_divergent_section_16_shortcut_is_bound_as_stated() -> None:
    """Bölüm 16'nın sapma dışı on bir maddesi gerçekten çalışmalı."""
    bound = _app_shortcuts()
    kept = [key for key, _ in PLAN_SECTION_16 if key not in DIVERGENCES]
    assert len(kept) == 11
    for key in kept:
        assert key in bound, f"Bolum 16 kisayolu {key} baglanmamis"


def test_the_divergences_are_real_and_documented_as_such() -> None:
    """Sapmalar gizlenmemeli; çalışmayan bir tuşu denemek daha kötüdür."""
    text = _guide()
    assert "Bölüm 16 ile farklar" in text

    # Ctrl+E bagli ama BASKA bir ise: Export.
    assert "Ctrl+E" in _app_shortcuts()
    export = next(spec for menu in MENU_SPECS for spec in menu.actions if spec.shortcut == "Ctrl+E")
    assert export.name == "action_export"
    assert "Export Data..." in text

    # Ctrl+K hic bagli degil.
    assert "Ctrl+K" not in _app_shortcuts()
    assert "Command palette" in text
    assert "uygulanmadı" in text


def test_the_guide_counts_the_added_shortcuts_correctly() -> None:
    """ "On iki kısayol eklendi" iddiası sayılabilir olmalı."""
    section_16_keys = {key for key, _ in PLAN_SECTION_16}
    added = _app_shortcuts() - section_16_keys
    assert len(added) == 12
    assert "**on iki kısayol**" in _guide()


# --------------------------------------------------------------------------- #
# KAPSAM (window / plot) DOGRU ANLATILIYOR
# --------------------------------------------------------------------------- #


def test_single_letter_shortcuts_are_plot_scoped_in_both_code_and_guide() -> None:
    """Tek harfli kısayol pencere genelinde olsaydı arama kutusunu bozardı."""
    single_letters = {spec.key for spec in SHORTCUTS if len(spec.key) == 1}
    assert single_letters == {"X", "Y", "B", "C", "R"}
    for spec in SHORTCUTS:
        if spec.key in single_letters:
            assert spec.scope == "plot", f"{spec.key} pencere kapsaminda"
    text = _guide()
    assert "yalnız odak merkez grafikteyken" in text
    assert "WidgetWithChildrenShortcut" in text


def test_the_window_scoped_shortcuts_match_the_guide_section() -> None:
    window_keys = {spec.key for spec in SHORTCUTS if spec.scope == "window"}
    assert window_keys == {"Ctrl+S", "Ctrl+Z", "Ctrl+Shift+Z"}
    text = _guide()
    assert "`Ctrl+Shift+Z`" in text
    assert "Ctrl+Y" not in text  # gercek redo Ctrl+Shift+Z


def test_the_redo_shortcut_is_not_misdocumented_anywhere_in_the_guides() -> None:
    """`Ctrl+Y` hiçbir yere bağlı değil; hiçbir kılavuzda geçmemeli."""
    for path in sorted((ROOT / "docs" / "guide").glob("*.md")):
        assert "Ctrl+Y" not in path.read_text(encoding="utf-8"), f"{path.name}"


def test_disabled_actions_are_described_as_inert() -> None:
    """Pasif eylemin kısayolu da pasiftir; boş çıktı üretmez."""
    disabled = {
        spec.shortcut
        for menu in MENU_SPECS
        for spec in menu.actions
        if spec.shortcut and not spec.enabled
    }
    assert "Ctrl+E" in disabled
    assert "hiçbir şey yapmaz" in _guide()


# --------------------------------------------------------------------------- #
# OLCEKLEME
# --------------------------------------------------------------------------- #


def test_the_three_zoom_modes_are_documented_with_their_keys() -> None:
    text = _guide()
    for key, mode in (("X", "yalnız zaman ekseni"), ("Y", "yalnız değer ekseni")):
        assert f"| `{key}` |" in text
        assert mode in text
    assert "iki eksen birden" in text


def test_the_guide_states_that_axis_restriction_is_strict() -> None:
    """ "Yalnız X" gerçekten yalnız X; aksi karşılaştırmayı bozar."""
    text = _guide()
    assert "gerçekten yalnız X" in text
    assert "karşılaştır" in text


def test_the_guide_states_that_zoom_does_not_change_data() -> None:
    assert "veriyi değiştirmez" in _guide()


def test_the_second_y_axis_behaviour_is_explained() -> None:
    text = _guide()
    assert "İkinci Y ekseni" in text
    assert "aynı oranda" in text


def test_the_toolbar_indicator_gap_is_declared_not_hidden() -> None:
    """Plan araç çubuğu göstergesi istiyor; bu sürümde yok — yazılmalı."""
    text = _guide()
    assert "araç çubuğunda kalıcı bir kip göstergesi" in text
    assert "**yoktur**" in text
    assert "Zoom modu: X" in text  # nerede gorundugu


# --------------------------------------------------------------------------- #
# MOUSE
# --------------------------------------------------------------------------- #


def test_the_default_mouse_mode_is_documented_as_pan() -> None:
    assert "pan" in _guide().lower()
    assert "seçim dikdörtgeni açmaz" in _flat()


def test_wheel_and_drag_follow_the_active_mode() -> None:
    text = _guide()
    assert "Tekerlek" in text
    assert "etkin kipin eksenlerinde" in text


def test_region_selection_is_described_as_two_axis_regardless_of_mode() -> None:
    flat = _flat()
    assert "iki eksenlidir" in flat
    assert "zoom kipi fark etmez" in flat


def test_the_channel_tree_mouse_actions_are_documented() -> None:
    text = _guide()
    for expected in ("Çift tık", "Sürükle", "Sağ tık", "Copy Path"):
        assert expected in text, expected


def test_the_tree_is_documented_as_drag_source_only() -> None:
    """Ağaç dışarıdan bir şey kabul etmez; bu bir tasarım kısıtıdır."""
    assert "yalnız **kaynaktır**" in _guide()


def test_live_follow_release_is_documented() -> None:
    text = _guide()
    assert "sona takip kapanır" in text
