"""Faz 7 ve Faz 8 açık kararlarının kütüğü — `F7-002`.

Kabul: **10 dk tavan, kayma kabulü, `complex64` ve C++ sahipliği
`open-decisions.md`'de `D-26`…`D-31` olarak izlenir.**

Bir açık karar kütüğünün tek işi vardır: cevabı bilinen ile bilinmeyeni
**ayrı tutmak**. Bu ayrım bozulduğunda iki yönde de zarar verir. Açık bir
soru kapalı görünürse, ekip bir varsayımı cevap sanıp üzerine iş kurar.
Kapalı bir soru açık görünürse, verilmiş bir karar tekrar tartışılır.

Bu yüzden testler her kimliğin **durumunu** doğrular, varlığını değil.
Ayrıca kapalı kararların cevabının gerçekten yazılı olduğunu ve açık
kararların cevap yerine **varsayım** taşıdığını kontrol eder.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "notes" / "open-decisions.md"

#: Proje sahibinin cevapladigi kararlar ve cevabin icinde gecmesi gereken ifade.
CLOSED: dict[str, str] = {
    "D-26": "10 dakika",
    "D-27": "820 örnek bağlayıcı",
    "D-28": "complex64",
    "D-29": "C++ tarafı",
}

#: Cevabi bilinmeyen, varsayimla ilerlenen kararlar.
OPEN_IDS = ("D-30", "D-31", "D-32", "D-34", "D-35", "D-36", "D-37", "D-38", "D-39", "D-40", "D-41")


@pytest.fixture(scope="module")
def text() -> str:
    assert DOC.is_file(), f"kutuk yok: {DOC}"
    return DOC.read_text(encoding="utf-8")


def _row(text: str, identifier: str) -> str:
    """Bir kimliğin satırını döndürür; yoksa testi düşürür."""
    for line in text.splitlines():
        if line.startswith(f"| {identifier} |"):
            return line
    raise AssertionError(f"{identifier} kutukte yok")


# --------------------------------------------------------------------------- #
# KAPALI KARARLAR
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(("identifier", "answer"), sorted(CLOSED.items()))
def test_an_answered_decision_is_marked_closed(text: str, identifier: str, answer: str) -> None:
    """Asıl kabul: cevaplanan dört karar KAPALI görünmeli."""
    row = _row(text, identifier)
    assert "**KAPALI**" in row, f"{identifier} kapalı işaretlenmemiş"
    assert answer in row, f"{identifier} satırında cevap ({answer!r}) yazılı değil"


def test_a_closed_decision_names_who_answered(text: str) -> None:
    """Cevabın kimden geldiği yazılmazsa, karar sonradan sahipsiz kalır."""
    for identifier in CLOSED:
        assert "Proje sahibi" in _row(text, identifier)


def test_the_ten_minute_ceiling_records_what_it_changed(text: str) -> None:
    """Bir kararın etkisi yazılmazsa, neden verildiği unutulur."""
    row = _row(text, "D-26")
    assert "28.800" in row, "eski dosya sayısı yazılı değil"
    assert "600" in row


def test_the_drift_decision_records_the_real_frame_duration(text: str) -> None:
    row = _row(text, "D-27")
    assert "100,0977 ms" in row
    assert "0,586 s" in row


def test_the_dtype_decision_records_the_mat_consequence(text: str) -> None:
    """`complex64` seçimi tek başına bir bağımlılığı belirliyor; bu yazılı olmalı."""
    row = _row(text, "D-28")
    assert "1,173 GiB" in row
    assert "2,346 GiB" in row
    assert "h5py" in row


def test_the_cpp_ownership_decision_states_python_only_reads(text: str) -> None:
    """Bu karar Faz 7'nin bütün çerçevesini belirliyor."""
    row = _row(text, "D-29")
    assert "yalnız okur" in row
    assert "tarifidir" in row


# --------------------------------------------------------------------------- #
# ACIK KARARLAR
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("identifier", OPEN_IDS)
def test_an_unanswered_decision_is_marked_open(text: str, identifier: str) -> None:
    """Cevabı bilinmeyen soru kapalı görünürse, varsayım cevap sanılır."""
    row = _row(text, identifier)
    assert "**AÇIK**" in row, f"{identifier} açık işaretlenmemiş"


@pytest.mark.parametrize("identifier", OPEN_IDS)
def test_an_open_decision_carries_an_assumption(text: str, identifier: str) -> None:
    """Varsayımsız bir açık karar, o işi başlatılamaz kılar."""
    row = _row(text, identifier)
    assumption = row.rsplit("|", 2)[-2].strip()
    assert len(assumption) >= 60, f"{identifier} varsayımı çok kısa: {assumption!r}"


def test_the_time_axis_decision_is_closed_by_this_project(text: str) -> None:
    """`D-33` cevap bekleyen bir soru değildi; `F7-005` ile bu proje karar verdi."""
    row = _row(text, "D-33")
    assert "**KAPALI**" in row
    assert "Bu proje" in row
    assert "F7-005" in row


def test_the_time_axis_answer_names_the_canonical_source(text: str) -> None:
    """Hangi kaynağın kanonik olduğu yazılmazsa karar uygulanamaz."""
    row = _row(text, "D-33")
    assert "timestamp'tir" in row
    assert "ADR-003" in row


def test_the_time_axis_answer_records_the_deciding_reason(text: str) -> None:
    """Gerekçe yazılmazsa karar sonradan keyfî görünür.

    Belirleyici olan şu: yayın yapılmayan saniyede Tx dosyası üretilmez.
    Sayaç tabanlı bir eksen o boşluğu göremez ve sonraki bütün Tx
    frame'lerini yanlış ana yerleştirir.
    """
    row = _row(text, "D-33")
    assert "boşluğu göremez" in row


def test_the_cit_field_is_not_quietly_interpreted(text: str) -> None:
    """CIT'in ne olduğu bilinmiyor; anlamını varsaymak sessiz bir hata olurdu."""
    row = _row(text, "D-30")
    assert "yorumlanmaz" in row
    assert "varsayılmaz" in row


def test_no_pri_value_is_invented(text: str) -> None:
    """PRI bilinmiyor; kütükte bir sayı görünmemeli."""
    row = _row(text, "D-31")
    assert "parametre" in row
    assert not re.search(r"\d+\s*(ms|µs|us)\b", row)


def test_the_tx_source_ambiguity_blocks_causal_language(text: str) -> None:
    """Aynı sayı ya projektör sağlığını ya alıcı kanalını anlatır; ikisi karıştırılamaz."""
    row = _row(text, "D-39")
    assert "kaynak belirsiz" in row
    assert "nedensel ifade kullanılmaz" in row


def test_the_agc_question_is_tested_not_assumed(text: str) -> None:
    """ "Uygulanmamıştır" varsaymak en riskli varsayımdır."""
    row = _row(text, "D-40")
    assert "varsayılmaz" in row
    assert "veriden test edilir" in row


# --------------------------------------------------------------------------- #
# DIS GIRDI
# --------------------------------------------------------------------------- #


def test_the_real_recording_is_tracked_as_an_external_dependency(text: str) -> None:
    row = _row(text, "E-11")
    assert "**AÇIK**" in row
    assert "F7-080" in row


def test_synthetic_evidence_is_not_presented_as_hardware_verification(text: str) -> None:
    row = _row(text, "E-11")
    assert "gerçek donanım doğrulaması sayılmaz" in row


# --------------------------------------------------------------------------- #
# KAPSAM DISINA CIKAN SORULAR
# --------------------------------------------------------------------------- #


def test_out_of_scope_questions_are_kept_with_their_reason(text: str) -> None:
    """Silinseydi, kapsam genişlediğinde sıfırdan keşfedilmeleri gerekirdi."""
    assert "Kapsam dışına çıkan sorular" in text
    for topic in ("Dizi geometrisi", "Ses hızı", "Taşıyıcı frekans", "Menzil ekseninin"):
        assert topic in text, f"{topic} kayıtta yok"


def test_the_out_of_scope_section_names_what_removed_them(text: str) -> None:
    """Kapsamı daraltan kararın kendisi yazılı olmalı."""
    prose = " ".join(text.split())
    assert "hüzmeleme, eşleştirilmiş filtre, TVG, normalizasyon, CFAR, tespit ve iz sürme" in prose


def test_out_of_scope_questions_can_be_reopened(text: str) -> None:
    prose = " ".join(text.split())
    assert "kapsam genişlerse yeniden açılır" in prose


# --------------------------------------------------------------------------- #
# KUTUGUN BUTUNLUGU
# --------------------------------------------------------------------------- #


def test_no_identifier_is_used_twice(text: str) -> None:
    """Aynı kimliğin iki satırı, hangisinin geçerli olduğunu belirsizleştirir."""
    found = re.findall(r"^\| (D-\d{2}|E-\d{2}) \|", text, flags=re.MULTILINE)
    assert len(found) == len(set(found)), f"yinelenen kimlik: {sorted(set(found))}"


def test_the_new_identifiers_do_not_collide_with_the_old_ones(text: str) -> None:
    """Yeni kararlar D-26'dan, dış girdi E-11'den başlar."""
    decisions = {int(m) for m in re.findall(r"^\| D-(\d{2}) \|", text, flags=re.MULTILINE)}
    assert decisions >= set(range(26, 42)), "D-26..D-41 aralığı eksik"
    assert 25 in decisions, "eski kararlar korunmalı"


def test_the_urgency_section_names_the_three_most_blocking(text: str) -> None:
    """Sıralama yoksa kütük bir liste olur, bir plan değil."""
    prose = " ".join(text.split())
    assert "Faz 7 ve Faz 8 için en erken gereken üçü" in prose
    for identifier in ("D-32", "E-11", "D-39"):
        assert f"**{identifier}" in prose, f"{identifier} aciliyet sırasında yok"


def test_the_document_records_when_it_was_last_touched(text: str) -> None:
    assert "Son güncelleme: 2026-09-12" in text
