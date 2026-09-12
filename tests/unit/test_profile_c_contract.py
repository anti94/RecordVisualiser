"""Profil C klasör ve dosya sözleşmesi — `F7-001`.

Kabul: **Tarih klasörü, `Tx/` ve `Rx/` alt klasörleri, `TxData00000.bin`
adlandırması ve sayaç sarması belgede tanımlıdır.**

Bir format belgesinin en tehlikeli hâli, içindeki sayıların birbirini
tutmamasıdır: okuyan kişi hangisinin doğru olduğunu bilemez ve yanlış
olana göre kod yazar. Bu yüzden testler belgedeki her türetilmiş sayıyı
**bağımsız olarak yeniden hesaplar** ve belgede yazanla karşılaştırır.

Düz metin iddiaları `prose` üzerinden kurulur. Markdown'da bir cümle
satır sonunda bölünebilir; ham metinde alt dize araması o zaman belge
doğru olduğu hâlde kırılır. Anlam satırın nerede bittiğine bağlı
değildir, bu yüzden boşluklar normalleştirilir. Tablo hücreleri ve kod
parçaları ham metinde aranır, çünkü orada biçim anlamın parçasıdır.

Henüz çözücü kodu yok; sözleşme önce yazılır, kod ona göre kurulur. Kod
geldiğinde bu testler belge ile kodun ayrışmasını da yakalayacak biçimde
genişletilecektir (`F7-019`+).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "format" / "profile-c.md"

# Sistem tanimindan gelen degerler; belge bunlari tekrar etmek zorunda.
SAMPLE_RATE_HZ = 8192
FRAME_SAMPLES = 820
SENSOR_COUNT = 32
BYTES_PER_COMPLEX64 = 8
FRAMES_PER_SECOND = 10
MAX_DURATION_S = 600


@pytest.fixture(scope="module")
def text() -> str:
    assert DOC.is_file(), f"sozlesme belgesi yok: {DOC}"
    return DOC.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def prose(text: str) -> str:
    """Satır sonlarını tek boşluğa indirger."""
    return " ".join(text.split())


# --------------------------------------------------------------------------- #
# KLASOR VE DOSYA ADLANDIRMA
# --------------------------------------------------------------------------- #


def test_the_recording_is_a_folder_not_a_file(prose: str) -> None:
    """Profil C'yi A ve B'den ayıran tek şey bu; belge bunu söylemeli."""
    assert "klasör ağacıdır" in prose


def test_the_date_folder_format_is_defined(text: str) -> None:
    assert "YYYY-MM-DDTHH-MM-SSZ" in text


def test_the_date_folder_avoids_the_colon(prose: str) -> None:
    """Windows dosya adında `:` yasaktır; belge bunu gerekçe olarak yazmalı."""
    assert "iki nokta üst üste yasaktır" in prose
    assert "Windows" in prose


def test_the_date_folder_is_utc(prose: str) -> None:
    """Yerel saatte yaz saati dönüşü aynı adı iki kez üretirdi."""
    assert "UTC" in prose
    assert "yaz saati geri alındığında" in prose


def test_the_name_collision_rule_is_defined(prose: str) -> None:
    """Üzerine yazmak bir kaydı sessizce yok ederdi."""
    assert "_2" in prose and "_3" in prose
    assert "sessizce yok ederdi" in prose


def test_both_stream_folders_are_named(text: str) -> None:
    assert "`Tx/`" in text
    assert "`Rx/`" in text


def test_the_tx_rx_split_is_described_as_complementary(prose: str) -> None:
    """Tx ve Rx kopya değil tamamlayıcıdır; bu bayt bütçesini belirler."""
    assert "tamamlayıcıdır" in prose
    assert "ikisine birden değil" in prose


def test_the_file_naming_pattern_is_defined(text: str) -> None:
    assert "TxData00000.bin" in text
    assert "RxData00000.bin" in text


def test_the_counter_is_five_digits_zero_padded(prose: str) -> None:
    assert "beş haneli" in prose
    assert "sıfır dolgulu" in prose


def test_one_file_is_one_second(prose: str) -> None:
    assert "bir saniyeye" in prose


def test_the_tx_and_rx_counters_mean_the_same_second(prose: str) -> None:
    """Aynı sayaç aynı saniyeyi göstermezse iki akım hizalanamaz."""
    assert "aynı saniyeye aittir" in prose


def test_a_missing_tx_second_is_information_not_an_error(prose: str) -> None:
    assert "boşluk bir hata değil" in prose


def test_the_sort_order_rule_is_stated(text: str) -> None:
    """Dolgu olmasaydı `TxData10` `TxData9`'dan önce gelirdi."""
    assert "TxData10.bin" in text
    assert "TxData9.bin" in text


# --------------------------------------------------------------------------- #
# SAYAC SARMASI
# --------------------------------------------------------------------------- #


def test_the_counter_capacity_is_stated_correctly(text: str) -> None:
    """Asıl kabul: sayaç kapasitesi belgede doğru yazılmalı."""
    assert "00000–99999" in text
    assert "100.000" in text


def test_the_counter_never_wraps_within_the_maximum_duration() -> None:
    """Bağımsız hesap: 10 dakikalık tavanda sarma gerçekleşemez."""
    assert MAX_DURATION_S < 100_000


def test_the_wrap_hours_claim_is_arithmetically_right(text: str) -> None:
    """Belge 27,8 saat diyor; bağımsız hesap bunu doğrulamalı."""
    hours = 100_000 / 3600
    assert abs(hours - 27.8) < 0.05, f"gercek {hours:.2f} sa"
    assert "27,8 saat" in text


def test_a_decreasing_counter_is_not_treated_as_a_wrap(prose: str) -> None:
    """Sessizce sarma varsaymak iki kaydı tek kayıt gibi okuturdu."""
    assert "tutarsızlık" in prose
    assert "Sessizce sarma varsaymak" in prose


# --------------------------------------------------------------------------- #
# SAYILAR BIRBIRINI TUTUYOR MU
# --------------------------------------------------------------------------- #


def test_the_frame_duration_is_not_one_hundred_milliseconds(text: str, prose: str) -> None:
    """Asıl kabul: 820/8192 tam 100 ms değildir ve belge bunu gizlememeli."""
    duration_ms = FRAME_SAMPLES / SAMPLE_RATE_HZ * 1000
    assert abs(duration_ms - 100.0977) < 0.0005, f"gercek {duration_ms:.4f} ms"
    assert "100,0977 ms" in text
    assert "Frame süresi tam olarak 100 ms değildir" in prose


def test_the_accumulated_drift_at_the_ceiling_is_right(text: str) -> None:
    """10 dakikada biriken kayma belgede yazandan farklı olamaz."""
    per_second_s = (FRAME_SAMPLES / SAMPLE_RATE_HZ - 0.1) * FRAMES_PER_SECOND
    total_s = per_second_s * MAX_DURATION_S
    assert abs(total_s - 0.586) < 0.001, f"gercek {total_s:.4f} s"
    assert "0,586 s" in text


def test_the_one_second_payload_size_is_right(text: str) -> None:
    """Bir saniyelik dosyanın yükü belgede yazandan farklı olamaz."""
    payload = FRAME_SAMPLES * SENSOR_COUNT * BYTES_PER_COMPLEX64 * FRAMES_PER_SECOND
    assert payload == 2_099_200
    assert "2.099.200 bayt" in text
    assert abs(payload / 1024 / 1024 - 2.002) < 0.001


def test_the_ten_minute_total_is_right(text: str) -> None:
    payload = FRAME_SAMPLES * SENSOR_COUNT * BYTES_PER_COMPLEX64 * FRAMES_PER_SECOND
    total_gib = payload * MAX_DURATION_S / 1024**3
    assert abs(total_gib - 1.173) < 0.001, f"gercek {total_gib:.4f} GiB"
    assert "1,173 GiB" in text


def test_the_file_count_ceiling_uses_a_less_than_or_equal(text: str) -> None:
    """Yayın yapılmayan saniyede Tx dosyası üretilmez; tavan kesin sayı değildir."""
    assert MAX_DURATION_S == 600
    assert "**≤ 1.200**" in text
    assert "**≤ 600**" in text


def test_the_size_arithmetic_line_is_shown(text: str) -> None:
    """Sayı verip hesabı gizlemek, okuyanın doğrulamasını imkânsız kılar."""
    assert "= 820 × 32 × 8" in text
    assert "= 209.920 × 10" in text
    assert "= 2.099.200 × 600" in text


# --------------------------------------------------------------------------- #
# BAYT BUTCESI VE ZAMAN KAYMASI — F7-003
# --------------------------------------------------------------------------- #


def test_the_budget_section_defines_its_input_symbols(text: str) -> None:
    """Türetilmiş bir sayı, girdileri adlandırılmadan doğrulanamaz."""
    assert "### 3.1 Girdi büyüklükleri" in text
    for symbol in ("`fs`", "`N`", "`S`", "`B`", "`F`", "`T`"):
        assert symbol in text, f"{symbol} tanımlanmamış"


def test_the_frame_payload_is_right(text: str) -> None:
    payload = FRAME_SAMPLES * SENSOR_COUNT * BYTES_PER_COMPLEX64
    assert payload == 209_920
    assert "209.920 bayt" in text
    assert abs(payload / 1024 - 205.0) < 0.05
    assert "205,0 KiB" in text


def test_the_ten_minute_byte_count_is_right(text: str) -> None:
    total = FRAME_SAMPLES * SENSOR_COUNT * BYTES_PER_COMPLEX64 * FRAMES_PER_SECOND * MAX_DURATION_S
    assert total == 1_259_520_000
    assert "1.259.520.000 bayt" in text


def test_the_complex128_column_is_exactly_double(text: str) -> None:
    """Karşılaştırma sütunu yanlışsa, tip kararının gerekçesi çürür."""
    single = FRAME_SAMPLES * SENSOR_COUNT * 8 * FRAMES_PER_SECOND * MAX_DURATION_S
    double = FRAME_SAMPLES * SENSOR_COUNT * 16 * FRAMES_PER_SECOND * MAX_DURATION_S
    assert double == 2 * single
    assert abs(double / 1024**3 - 2.346) < 0.001, f"gercek {double / 1024**3:.4f} GiB"
    assert "2,346 GiB" in text
    assert "410,0 KiB" in text
    assert "4,004 MiB" in text


def test_the_one_minute_row_is_right(text: str) -> None:
    minute = FRAME_SAMPLES * SENSOR_COUNT * BYTES_PER_COMPLEX64 * FRAMES_PER_SECOND * 60
    assert abs(minute / 1024**2 - 120.1) < 0.1, f"gercek {minute / 1024**2:.2f} MiB"
    assert "120,1 MiB" in text


def test_the_total_belongs_to_both_streams_together(text: str, prose: str) -> None:
    """Tx ve Rx tamamlayıcıdır; toplamı iki kez saymak boyutu ikiye katlardı."""
    assert "**Tx ve Rx'in toplamıdır**" in prose
    assert "her biri için ayrı ayrı değil" in prose


# --------------------------------------------------------------------------- #
# MAT V5 ESIGI
# --------------------------------------------------------------------------- #


def test_the_mat_v5_threshold_percentages_are_right(text: str) -> None:
    """Asıl kabul: `.mat` kararı bu iki yüzdeye dayanıyor, doğru olmalılar."""
    limit = 2 * 1024**3
    per_second = FRAME_SAMPLES * SENSOR_COUNT * FRAMES_PER_SECOND
    single = per_second * 8 * MAX_DURATION_S
    double = per_second * 16 * MAX_DURATION_S

    assert abs(single / limit * 100 - 58.7) < 0.1, f"gercek %{single / limit * 100:.1f}"
    assert abs(double / limit * 100 - 117.3) < 0.1, f"gercek %{double / limit * 100:.1f}"
    assert "%58,7" in text
    assert "%117,3" in text


def test_single_precision_fits_and_double_does_not(text: str) -> None:
    """Eşiğin hangi yanına düştüğü bir bağımlılığı belirliyor."""
    limit = 2 * 1024**3
    per_second = FRAME_SAMPLES * SENSOR_COUNT * FRAMES_PER_SECOND
    assert per_second * 8 * MAX_DURATION_S < limit
    assert per_second * 16 * MAX_DURATION_S > limit


def test_the_scipy_limitation_is_stated(text: str, prose: str) -> None:
    assert "yalnız v4 ve v5 yazar" in prose
    assert "v7.3" in text


def test_the_mat_claim_is_sourced(text: str) -> None:
    """Bir bağımlılık kararına dayanak olan iddia kaynaksız kalamaz."""
    assert "docs.scipy.org" in text
    assert "mathworks.com" in text


def test_the_dependency_conclusion_is_conditional(text: str, prose: str) -> None:
    """Sonuç tek duyarlığa bağlı; koşulsuz yazmak sonradan yanlışa dönerdi."""
    assert "tek duyarlığa bağlıdır" in prose
    assert "`F7-070`" in text


# --------------------------------------------------------------------------- #
# ZAMAN KAYMASI TABLOSU
# --------------------------------------------------------------------------- #


def test_the_drift_arithmetic_is_written_out(text: str) -> None:
    assert "819,2 örnek" in text
    assert "97,66 µs" in text
    assert "0,9766 ms" in text


def test_the_per_minute_drift_is_right(text: str) -> None:
    per_second_s = (FRAME_SAMPLES / SAMPLE_RATE_HZ - 0.1) * FRAMES_PER_SECOND
    minute_ms = per_second_s * 60 * 1000
    assert abs(minute_ms - 58.6) < 0.1, f"gercek {minute_ms:.2f} ms"
    assert "58,6 ms" in text


def test_the_relative_drift_is_constant(text: str) -> None:
    """Bağıl kayma süreden bağımsızdır; tabloda üç kez aynı görünmeli."""
    relative = (FRAME_SAMPLES / SAMPLE_RATE_HZ - 0.1) / 0.1 * 100
    assert abs(relative - 0.0977) < 0.0005, f"gercek %{relative:.4f}"
    assert text.count("%0,0977") >= 3


def test_the_out_of_ceiling_row_is_marked_as_such(text: str, prose: str) -> None:
    """Tavan dışı bir satır tavanmış gibi okunursa, sınır yanlış anlaşılır."""
    hour_s = (FRAME_SAMPLES / SAMPLE_RATE_HZ - 0.1) * FRAMES_PER_SECOND * 3600
    assert abs(hour_s - 3.516) < 0.002, f"gercek {hour_s:.3f} s"
    assert "*(1 saat — tavan dışı)*" in text
    assert "Son satır tavanın dışındadır" in prose


def test_the_frequency_resolution_is_right(text: str) -> None:
    resolution = SAMPLE_RATE_HZ / FRAME_SAMPLES
    assert abs(resolution - 9.990) < 0.001, f"gercek {resolution:.4f} Hz"
    assert "9,990 Hz" in text


def test_the_index_is_justified_by_the_file_count(text: str, prose: str) -> None:
    """1.200 dosyayı tek tek açmak ilk açılış bütçesinin tamamını yer."""
    assert "1,2 saniye" in text
    assert "`F7-032`" in text
    assert "zorunludur" in prose


# --------------------------------------------------------------------------- #
# SESSIZ BOZULMAYA KARSI UC KAPI
# --------------------------------------------------------------------------- #


def test_the_silent_mismatch_risk_is_stated_up_front(prose: str) -> None:
    """Bu profilin en büyük riski; belgenin başında yazmalı."""
    assert "hatasız ama yanlış" in prose[:1400]


def test_three_independent_gates_are_defined(text: str) -> None:
    assert "Sihirli sayı" in text
    assert "Şema kimliği" in text
    assert "Akıl sağlığı" in text


def test_the_sanity_equation_is_written_out(text: str) -> None:
    """Denklem yazılmazsa akıl sağlığı denetimi bir niyet beyanı olur."""
    assert "dosya_boyutu = header + frame_sayısı" in text


def test_a_failed_gate_refuses_to_open_the_recording(prose: str) -> None:
    """Sessizce açmak, yanlış veriyle çalışılan bir oturum demektir."""
    assert "kayıt açılmaz" in prose
    assert "hangi kapının neden düştüğü" in prose


# --------------------------------------------------------------------------- #
# EKSIK KLASOR VE MANIFEST
# --------------------------------------------------------------------------- #


def test_a_missing_stream_folder_is_not_an_error(prose: str) -> None:
    """Yayın yapılmayan bir oturumda `Tx/` bulunmayabilir."""
    assert "Eksik klasör hata değildir" in prose


def test_the_manifest_may_be_absent(prose: str) -> None:
    assert "Manifest **bulunmayabilir**" in prose


def test_the_files_win_over_a_conflicting_manifest(prose: str) -> None:
    """Manifest bir özettir; veri kaynağın kendisidir."""
    assert "**dosyalar esas alınır**" in prose


def test_the_index_does_not_block_a_read_only_folder(prose: str) -> None:
    assert "salt okunursa indeks bellekte kurulur" in prose


# --------------------------------------------------------------------------- #
# PROFIL A VE B ILE ILISKI
# --------------------------------------------------------------------------- #


def test_the_older_profiles_are_not_retired(prose: str) -> None:
    assert "emekliye ayrılmaz" in prose


def test_the_comparison_table_names_all_three_profiles(text: str) -> None:
    assert "| | Profil A | Profil B | Profil C |" in text


def test_the_document_says_the_application_does_not_write_this_profile(prose: str) -> None:
    """Bu, kapsamı belirleyen en önemli cümle."""
    assert "uygulama Profil C **yazmaz**" in prose


def test_the_generator_is_marked_as_test_only(prose: str) -> None:
    assert "bir ürün özelliği değildir" in prose


# --------------------------------------------------------------------------- #
# ACIK KARARLAR
# --------------------------------------------------------------------------- #


def test_the_closed_decisions_are_listed_with_their_answers(text: str) -> None:
    for decision in ("D-26", "D-27", "D-28", "D-29"):
        assert decision in text, f"{decision} belgede yok"
        pattern = rf"\| `{decision}` \|[^|]+\| \*\*Kapalı\*\*"
        assert re.search(pattern, text), f"{decision} kapali olarak isaretlenmemis"


def test_the_open_decisions_are_not_quietly_answered(text: str) -> None:
    """Cevabı bilinmeyen soruyu varsayımla kapatmak, en pahalı hatadır."""
    for decision in ("D-30", "D-31", "D-32"):
        pattern = rf"\| `{decision}` \|[^|]+\| \*\*Açık\*\*"
        assert re.search(pattern, text), f"{decision} acik olarak isaretlenmemis"


def test_the_time_axis_decision_is_closed_with_its_answer(text: str) -> None:
    """`F7-005` ile kapandı; tabloda cevabı ve nereye bakılacağı yazılı olmalı."""
    row = next(line for line in text.splitlines() if line.startswith("| `D-33` |"))
    assert "**Kapalı**" in row
    assert "timestamp kanonik" in row
    assert "§6" in row


def test_the_document_does_not_invent_a_pri_value(text: str) -> None:
    """PRI bilinmiyor; belgede bir sayı görünmemeli."""
    assert not re.search(r"PRI\s*=\s*\d", text)
    assert not re.search(r"PRI[^.]{0,20}\d+\s*(ms|µs|us)\b", text)
