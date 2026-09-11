"""Ana ekran kullanım kılavuzu — `F6-024`.

Kabul: **Dokuz bölge ve dosyadan analize ana akış ekranla eşleşir.**

Bir kılavuzun sessiz bozulma biçimi, anlattığı ekranın değişmesidir:
metin aynı kalır, uygulama başka bir şey yapar ve kullanıcı yanlış yere
bakar. Bu testler kılavuzu **uygulamanın kendi tanımlarına** bağlar —
bölge adları `docs/ui/layout-map.md` ve `F3-079`'un bölge testiyle aynı
kaynaktan gelir.

Testler metnin *iyi yazıldığını* iddia etmez; **ekranla aynı şeyi
söylediğini** denetler.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "docs" / "guide" / "ana-ekran.md"
LAYOUT_MAP = ROOT / "docs" / "ui" / "layout-map.md"
REGION_TEST = ROOT / "tests" / "gui" / "test_mvp_mockup_regions.py"

#: `docs/ui/layout-map.md` §2 ve `F3-079`'un testiyle AYNI dokuz bolge.
NINE_REGIONS: tuple[str, ...] = (
    "Dosya ve Veri Yönetimi",
    "Hızlı Araçlar",
    "Görselleştirme Alanı",
    "Donanım/BIT Durumu",
    "Hesaplamalar ve Analiz",
    "Çoklu Görünüm",
    "Zaman Kontrolü",
    "Log / Mesajlar",
    "Ayarlar ve Dışa Aktarma",
)


def _guide() -> str:
    return GUIDE.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# DOKUZ BOLGE
# --------------------------------------------------------------------------- #


def test_the_guide_exists() -> None:
    assert GUIDE.is_file()


def test_every_region_number_is_explained() -> None:
    """Dokuz bölgenin hepsi numarasıyla anlatılmalı."""
    text = _guide()
    for number in range(1, 10):
        assert f"| {number} |" in text, f"bolge {number} kilavuzda yok"


def test_every_region_name_appears() -> None:
    """Adlar yerleşim haritasıyla aynı olmalı; farklı ad, yanlış yer demektir."""
    text = _guide()
    for name in NINE_REGIONS:
        # "Donanım/BIT" haritada bolusuz da yazilabiliyor; ilk kelime yeter.
        key = name.split("/")[0].strip()
        assert key in text, f"{name} kilavuzda gecmiyor"


def test_the_region_names_match_the_layout_map() -> None:
    """Kılavuz ile yerleşim haritası ayrışmamalı."""
    layout = LAYOUT_MAP.read_text(encoding="utf-8")
    for name in NINE_REGIONS:
        key = name.split("/")[0].strip()
        assert key in layout, f"{name} yerlesim haritasinda yok"


def test_the_region_set_matches_the_acceptance_test() -> None:
    """`F3-079`'un bölge testiyle aynı dokuz ad kullanılmalı."""
    region_test = REGION_TEST.read_text(encoding="utf-8")
    for name in NINE_REGIONS:
        assert name in region_test, f"{name} bolge testinde yok"


def test_the_guide_says_the_layout_does_not_change() -> None:
    """`F5-040` bunu kanıtladı; kılavuz da aynısını söylemeli."""
    text = _guide()
    assert "canlı akış" in text and "değişmez" in text


# --------------------------------------------------------------------------- #
# DOSYADAN ANALIZE ANA AKIS
# --------------------------------------------------------------------------- #


def test_the_main_flow_covers_every_step() -> None:
    """Akış eksiksiz olmalı: aç → kanal → aralık → analiz → dışa aktar."""
    text = _guide()
    for step in ("Kayıt açma", "Kanal seçme", "Zaman aralığı", "Analiz", "Dışa aktarma"):
        assert step in text, f"akista '{step}' adimi yok"


def test_the_flow_names_the_open_shortcut() -> None:
    assert "Ctrl+O" in _guide()


def test_the_guide_explains_double_click_to_plot() -> None:
    """Kanal çizmenin asıl yolu budur; yazılmazsa kullanıcı arar."""
    assert "çift" in _guide() and "tıkla" in _guide()


def test_the_guide_mentions_the_shared_time_axis() -> None:
    assert "aynı zaman eksenini" in _guide()


def test_the_guide_explains_the_second_y_axis() -> None:
    """Farklı birimler karışmasın diye ikinci eksen var; bu açıklanmalı."""
    text = _guide()
    assert "ikinci" in text and "Y ekseni" in text


def test_the_guide_explains_x_sync() -> None:
    assert "Sync" in _guide()


# --------------------------------------------------------------------------- #
# DURUSTLUK: uygulama ne yapiyorsa o yazili
# --------------------------------------------------------------------------- #


def test_the_guide_says_a_corrupt_file_is_refused() -> None:
    """Uygulama bozuk kaydı reddeder; kılavuz bunu gizlememeli."""
    text = _guide()
    assert "reddeder" in text
    assert "sessizce yanlış veri" in text


def test_the_guide_says_analysis_does_not_change_the_source() -> None:
    assert "ham veriyi değiştirmez" in _guide()


def test_the_guide_describes_the_status_bar_fields() -> None:
    """`F5-032` durum çubuğuna kayıt alanı ekledi; kılavuz da anmalı."""
    text = _guide()
    assert "bağlantı" in text.lower()
    assert "kayıt durumu" in text


def test_the_guide_links_the_other_guides() -> None:
    text = _guide()
    for target in (
        "filtre-ve-spektral-analiz.md",
        "canli-baglanti.md",
        "klavye-ve-olcekleme.md",
        "bilinen-sorunlar.md",
    ):
        assert target in text, f"{target} baglantisi yok"
