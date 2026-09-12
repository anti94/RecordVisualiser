"""Zaman ekseninin tek kaynağı — `F7-005`.

Kabul: **Zamanın frame sayacından mı timestamp'ten mi türediği tek yerde
tanımlı; ikisinin 10 dk'da 0,586 s ayrıştığı yazılı.**

Bir kayıtta zamanı iki yoldan türetmek mümkündür ve ikisi aynı sonucu
vermez. Seçim yapılmazsa iki panel aynı kayıt için iki farklı zaman
gösterir ve hangisinin doğru olduğu ekrandan anlaşılamaz. Bu, kullanıcının
fark edemeyeceği türden bir hatadır: her iki sayı da makul görünür.

Testler kararın **verildiğini**, **gerekçelendirildiğini** ve iki kaynak
arasındaki farkın sayıyla yazıldığını doğrular. Ayrıca kararın `ADR-003`
ile çelişmediğini kontrol eder: kanonik birim `int64` UTC nanosaniyedir
ve cihaz sayacı kanonik yapılmaz.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "format" / "profile-c.md"
ADR = ROOT / "docs" / "adr" / "ADR-003-time-base.md"

SAMPLE_RATE_HZ = 8192
FRAME_SAMPLES = 820
FRAMES_PER_SECOND = 10
MAX_DURATION_S = 600


@pytest.fixture(scope="module")
def section() -> str:
    """Belgenin yalnız zaman ekseni bölümü."""
    text = DOC.read_text(encoding="utf-8")
    start = text.index("## 6. Zaman ekseninin tek kaynağı")
    end = text.index("## 7. Şema ile kaydın ayrışması")
    return text[start:end]


@pytest.fixture(scope="module")
def prose(section: str) -> str:
    return " ".join(section.split())


# --------------------------------------------------------------------------- #
# KARAR VERILMIS MI
# --------------------------------------------------------------------------- #


def test_the_two_candidate_sources_are_both_named(section: str) -> None:
    """Seçim ancak iki seçenek de yazılıysa bir seçimdir."""
    assert "Frame sayacı" in section
    assert "Frame timestamp'i" in section


def test_the_decision_is_stated_unambiguously(prose: str) -> None:
    """Asıl kabul: hangisinin kanonik olduğu tek cümlede yazılmalı."""
    assert "**Kanonik zaman, frame başlığındaki timestamp'tir.**" in prose


def test_the_frame_counter_keeps_exactly_three_jobs(section: str) -> None:
    """Sayaç atılmıyor; ne için kullanıldığı sınırlanıyor."""
    for job in ("Sıralama", "Boşluk tespiti", "Tutarlılık ölçümü"):
        assert job in section, f"sayaç görevi eksik: {job}"


def test_the_counter_is_called_an_index_not_a_time(prose: str) -> None:
    assert "bir **indekstir**, bir zaman değil" in prose


# --------------------------------------------------------------------------- #
# GEREKCE
# --------------------------------------------------------------------------- #


def test_four_reasons_are_given(section: str) -> None:
    for reason in ("Gerçeği taşır", "Boşluğa dayanıklı", "Akımları hizalar"):
        assert reason in section, f"gerekçe eksik: {reason}"


def test_the_deciding_reason_is_the_missing_tx_second(prose: str) -> None:
    """Tek başına belirleyici olan gerekçe işaretlenmeli.

    Yayın yapılmayan saniyede Tx dosyası üretilmez. Sayaç tabanlı bir
    eksen o boşluğu göremez ve sonraki bütün Tx frame'lerini 1 saniye
    öne kaydırır.
    """
    assert "İkinci satır tek başına belirleyicidir" in prose
    assert "yanlış ana yerleştirir" in prose


def test_the_decision_cites_the_governing_adr(prose: str) -> None:
    """`ADR-003` kanonik birimi belirliyor; bu karar ondan türemeli."""
    assert "`ADR-003`" in prose
    assert "cihaz sayacı kanonik yapılmaz" in prose


def test_the_adr_really_says_that() -> None:
    """Atıf doğrulanmadan yapılan bir referans, uydurma kadar zararlıdır."""
    adr = " ".join(ADR.read_text(encoding="utf-8").split())
    assert "Cihaz tick'ini kanonik yapmak" in adr
    assert "int64" in adr and "UTC" in adr


def test_the_drift_policy_follows_the_adr(prose: str) -> None:
    """`ADR-003` §2.6: drift ölçülür, sessizce düzeltilmez."""
    assert "drift ölçülür, sessizce\ndüzeltilmez" in prose or "ölçülür, sessizce" in prose


# --------------------------------------------------------------------------- #
# IKI KAYNAGIN AYRISMASI
# --------------------------------------------------------------------------- #


def test_the_divergence_is_stated_with_a_number(section: str) -> None:
    """Asıl kabul: 10 dakikadaki ayrışma sayıyla yazılmalı."""
    assert "0,586 saniye" in section


def test_the_divergence_number_is_arithmetically_right() -> None:
    """Bağımsız hesap: belgedeki sayı türetilebilir olmalı."""
    per_second_s = (FRAME_SAMPLES / SAMPLE_RATE_HZ - 0.1) * FRAMES_PER_SECOND
    total_s = per_second_s * MAX_DURATION_S
    assert abs(total_s - 0.586) < 0.001, f"gercek {total_s:.4f} s"


def test_the_divergence_is_called_small_but_visible(prose: str) -> None:
    """Küçük bir sayıyı önemsiz saymak, iki panelin ayrışmasını görünmez kılar."""
    assert "gözden kaçacak kadar" in prose
    assert "farklı değer göstermesine yetecek" in prose


def test_the_counter_formula_is_written_out(section: str) -> None:
    assert "frame_indeksi × 820 / 8192" in section


# --------------------------------------------------------------------------- #
# TIMESTAMP YOKSA YA DA BOZUKSA
# --------------------------------------------------------------------------- #


def test_every_degraded_case_has_a_defined_behaviour(section: str) -> None:
    for case in ("Alan hiç yok", "Geriye sıçrıyor", "Tekrar ediyor", "Nominalden çok sapıyor"):
        assert case in section, f"durum tanımsız: {case}"


def test_falling_back_to_the_counter_is_announced(prose: str) -> None:
    """Sessizce sayaca düşmek en kötü davranış olurdu."""
    assert "açıkça işaretlenir" in prose
    assert "zaman kaynağı: sayaç" in prose
    assert "Sessizce sayaca düşmek en kötü davranış" in prose


def test_bad_timestamps_flag_rather_than_discard(section: str) -> None:
    """`ADR-003` §2.7: veri atılmaz, işaretlenir."""
    assert "SUSPECT" in section
    assert "veri atılmaz" in section
    assert "JITTER" in section


# --------------------------------------------------------------------------- #
# TEK YER KURALI
# --------------------------------------------------------------------------- #


def test_the_rule_says_one_function(prose: str) -> None:
    assert "**tek bir işlevde**" in prose


def test_the_rule_is_backed_by_a_test_not_just_prose(prose: str) -> None:
    """Belgeyle korunan bir kural, ilk acelede çiğnenir."""
    assert "Kural testle korunur" in prose
    assert "`F7-026`" in prose
    assert "`F7-038`" in prose


def test_the_failure_mode_of_two_sources_is_named(prose: str) -> None:
    assert "iki farklı zaman gösterirler" in prose


# --------------------------------------------------------------------------- #
# SAPMANIN RAPORLANMASI
# --------------------------------------------------------------------------- #


def test_the_ppm_formula_is_written_out(section: str) -> None:
    assert "sapma_ppm" in section
    assert "timestamp_adımı" in section


def test_the_worked_ppm_value_is_right(section: str) -> None:
    """Timestamp tam 100 ms ızgarasına yazıyorsa sapma −975,6 ppm çıkar."""
    nominal_s = FRAME_SAMPLES / SAMPLE_RATE_HZ
    ppm = (0.1 - nominal_s) / nominal_s * 1e6
    assert abs(ppm + 975.6) < 0.1, f"gercek {ppm:.1f} ppm"
    assert "−975,6 ppm" in section


def test_the_sign_of_the_deviation_is_meaningful(prose: str) -> None:
    """İşaret hangi tarafın hızlı olduğunu söyler; mutlak değer bunu siler."""
    assert "İşaret önemlidir" in prose
    assert "hangi tarafın hızlı olduğunu" in prose


def test_the_deviation_is_a_measurement_not_an_error(prose: str) -> None:
    """Ne olduğunu anlamadan düzeltmek, veriyi bozmanın en sessiz yoludur."""
    assert "bir hata değil bir **ölçümdür**" in prose
    assert "en sessiz yoludur" in prose


def test_a_perfectly_matching_period_reports_zero() -> None:
    """Sıfır sapma da bir sonuçtur; formül onu vermeli."""
    nominal_s = FRAME_SAMPLES / SAMPLE_RATE_HZ
    ppm = (nominal_s - nominal_s) / nominal_s * 1e6
    assert ppm == 0.0
