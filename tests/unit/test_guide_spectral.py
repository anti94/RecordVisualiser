"""Filtre ve spektral analiz kullanım örneği — `F6-025`.

Kabul: **Birim, sample rate, ROI ve işlem geçmişi örnekte açıktır.**

Bu dördü, spektral analizde sessiz yanlışın en sık dört kaynağıdır:
birim karışırsa grafik yine makul görünür, örnekleme hızı okunmazsa
Nyquist üstü bir şey aranır, ROI değişirse spektrumlar karşılaştırılamaz,
işlem geçmişi yoksa sonuç savunulamaz.

Testler dördünün de örnekte **somut sayılarla** geçtiğini denetler; genel
bir cümle ("birimlere dikkat edin") kabul kriterini karşılamaz.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "docs" / "guide" / "filtre-ve-spektral-analiz.md"


def _guide() -> str:
    return GUIDE.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# BIRIM
# --------------------------------------------------------------------------- #


def test_the_guide_exists() -> None:
    assert GUIDE.is_file()


def test_the_channel_unit_is_stated_concretely() -> None:
    """Birim somut olmalı; "birim" demek yetmez."""
    text = _guide()
    assert "bar" in text
    assert "birim" in text.lower()


def test_the_spectrum_axis_unit_is_explained() -> None:
    """Y ekseninin dB mi yoksa kanal birimi mi olduğu belirsiz kalmamalı."""
    text = _guide()
    assert "Y ekseni" in text
    assert "dB" in text


# --------------------------------------------------------------------------- #
# SAMPLE RATE ve NYQUIST
# --------------------------------------------------------------------------- #


def test_the_sample_rate_is_stated_concretely() -> None:
    text = _guide()
    assert "8 Hz" in text
    assert "125 ms" in text


def test_nyquist_is_explained_with_its_number() -> None:
    """Nyquist yalnız anılmamalı; bu örnekteki değeri yazılmalı."""
    text = _guide()
    assert "Nyquist" in text
    assert "4 Hz" in text


def test_the_guide_refuses_to_invent_an_answer_beyond_nyquist() -> None:
    """8 Hz'lik kanaldan 50 Hz hakkında kesin bir şey söylenemez."""
    text = _guide()
    assert "uydurmaz" in text or "söylenemez" in text


def test_the_cutoff_rule_is_stated() -> None:
    """Kesim frekansı Nyquist'i aşamaz ve uygulama bunu reddeder."""
    text = _guide()
    assert "aşamaz" in text
    assert "reddeder" in text
    assert "kırpmaz" in text


# --------------------------------------------------------------------------- #
# ROI
# --------------------------------------------------------------------------- #


def test_the_roi_is_given_as_a_concrete_range() -> None:
    assert "120" in _guide() and "180" in _guide()


def test_the_guide_says_the_roi_changes_the_spectrum() -> None:
    """Asıl tuzak bu: farklı ROI'lerin spektrumları karşılaştırılamaz."""
    text = _guide()
    assert "yalnız görünen" in text
    assert "karşılaştır" in text


def test_the_guide_warns_about_comparing_different_rois() -> None:
    text = _guide()
    assert "aynı ROI" in text or "Farklı aralıkların" in text


# --------------------------------------------------------------------------- #
# ISLEM GECMISI
# --------------------------------------------------------------------------- #


def test_the_processing_chain_is_shown_with_order_and_parameters() -> None:
    """Zincir soyut değil, parametreli ve sıralı verilmeli."""
    text = _guide()
    assert "detrend" in text
    assert "bandpass" in text
    assert "order=4" in text


def test_the_guide_explains_why_the_order_matters() -> None:
    text = _guide()
    assert "sıra" in text.lower()
    assert "ters olsaydı" in text or "sırayla" in text


def test_the_history_is_undoable_and_saved() -> None:
    text = _guide()
    assert "Ctrl+Z" in text
    assert "workspace" in text.lower()


def test_the_guide_states_the_reproducibility_guarantee() -> None:
    """`F4-088` aynı workspace'in aynı sonucu verdiğini kanıtladı."""
    text = _guide()
    assert "aynı sonuç" in text
    assert "F4-088" in text


def test_the_export_carries_the_history() -> None:
    text = _guide()
    assert "JSON" in text
    assert "raw" in text


# --------------------------------------------------------------------------- #
# ORNEK GERCEKTEN BIR ORNEK
# --------------------------------------------------------------------------- #


def test_the_guide_walks_one_concrete_question() -> None:
    """Özellik listesi değil, baştan sona bir örnek olmalı."""
    text = _guide()
    assert "Soru:" in text
    assert "50 Hz" in text


def test_the_guide_lists_common_mistakes() -> None:
    text = _guide()
    assert "hata" in text.lower()
    assert "Detrend" in text or "detrend" in text


def test_the_guide_links_the_related_documents() -> None:
    text = _guide()
    assert "ana-ekran.md" in text
    assert "profile-b.md" in text
