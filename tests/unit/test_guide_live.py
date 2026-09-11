"""Canlı bağlantı ve kayıt kullanım örneği — `F6-026`.

Kabul: **Üç protokol, bağlantı kesintisi ve kayıt tekrar açma
açıklanır.**

Kılavuz uygulamanın gerçek davranışını yazmalı, ideal hâlini değil. Bu
yüzden testler yalnız üç başlığın geçtiğini değil, **söz verilen
davranışların** da yazıldığını denetler: kesintide tam kayıtların
korunması, kapanış nedeninin loglanması, disk dolunca "başarılı" mesajı
verilmemesi.

Yanlış bir kılavuz, olmayan bir güvence verir; bu, eksik bir kılavuzdan
daha zararlıdır.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "docs" / "guide" / "canli-baglanti.md"
CONTRACT = ROOT / "docs" / "live" / "protocol-contract.md"


def _guide() -> str:
    return GUIDE.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# UC PROTOKOL
# --------------------------------------------------------------------------- #


def test_the_guide_exists() -> None:
    assert GUIDE.is_file()


def test_all_three_protocols_are_covered() -> None:
    text = _guide()
    for protocol in ("UDP", "TCP", "Seri port"):
        assert protocol in text, f"{protocol} anlatilmamis"


def test_each_protocol_has_its_own_behaviour_described() -> None:
    """Üçünü aynı cümleyle geçmek, farklarını gizlemek olurdu."""
    text = _guide()
    assert "500 ms" in text  # UDP parca zaman asimi
    assert "EOF" in text and "RST" in text  # TCP ayrimi
    assert "SYNC" in text and "CRC32" in text  # serial


def test_the_guide_says_the_consumer_does_not_know_the_transport() -> None:
    """Protokol değiştirmek arayüzü değiştirmez; bu bir tasarım sözü."""
    text = _guide()
    assert "hangisinin bağlı olduğunu bilmez" in text


def test_the_serial_extra_requirement_is_stated() -> None:
    """Kurulu değilse açık hata verilir; kullanıcı bunu önceden bilmeli."""
    text = _guide()
    assert "live" in text
    assert "açık bir hata" in text


# --------------------------------------------------------------------------- #
# BAGLANTI KESINTISI
# --------------------------------------------------------------------------- #


def test_the_three_kinds_of_disconnect_are_distinguished() -> None:
    text = _guide()
    assert "Disconnect" in text
    assert "kaynak hatası" in text.lower() or "Kaynak çöktü" in text
    assert "Yeniden bağlanma" in text


def test_reconnection_is_described_as_bounded_and_visible() -> None:
    """Sonsuza kadar denenmediği ve denemelerin görüldüğü yazılmalı."""
    text = _guide()
    assert "sonsuza kadar denenmez" in text
    assert "görünür" in text


def test_the_guide_states_that_complete_records_survive() -> None:
    """`F5-033`'ün kabulü buydu; kılavuz aynısını söylemeli."""
    text = _guide()
    assert "tam kayıtlar korunur" in text
    assert "fsync" in text


def test_the_closure_reason_is_explained_with_its_rationale() -> None:
    """Diskte dosyalar aynı görünür; neden yazılmazsa ayırt edilemez."""
    text = _guide()
    assert "kapanış nedeni" in text
    assert "birbirinin aynıdır" in text


def test_gaps_are_reported_with_range_and_count() -> None:
    text = _guide()
    assert "boşluk" in text.lower()
    assert "pencere gelmedi" in text


def test_the_guide_says_silence_does_not_mean_no_problem() -> None:
    text = _guide()
    assert "sessizlik" in text.lower()


# --------------------------------------------------------------------------- #
# KAYIT ve TEKRAR ACMA
# --------------------------------------------------------------------------- #


def test_recording_start_and_stop_are_documented() -> None:
    text = _guide()
    assert "Ctrl+R" in text
    assert "Ctrl+Shift+R" in text


def test_the_elapsed_time_is_explained_as_data_derived() -> None:
    """Duvar saatinden türetilseydi, olmayan saniyeler kaydedilmiş sanılırdı."""
    text = _guide()
    assert "veriden türetilir" in text
    assert "duvar saatinden değil" in text


def test_file_rotation_limits_are_documented() -> None:
    text = _guide()
    assert "Data9999999" in text
    assert "boyut" in text


def test_the_new_file_self_consistency_is_explained() -> None:
    """Her dosya tek başına doğru okunur; bu `F5-031`'in kabulüydü."""
    text = _guide()
    assert "kendi içinde tutarlıdır" in text
    assert "Data00000" in text


def test_the_disk_full_behaviour_is_honest() -> None:
    """Hata durumunda "başarılı kayıt" denmediği yazılmalı."""
    text = _guide()
    assert "başarılı kayıt" in text
    assert "silinmez" in text


def test_reopening_is_described_with_its_guarantees() -> None:
    text = _guide()
    assert "birebir" in text
    assert "125 ms" in text
    assert "F5-035" in text


def test_gaps_in_a_reopened_recording_are_not_called_corruption() -> None:
    """Eksik pencere bir bozulma değildir; kullanıcı paniklememeli."""
    text = _guide()
    assert "bozulma değildir" in text


# --------------------------------------------------------------------------- #
# TUTARLILIK
# --------------------------------------------------------------------------- #


def test_the_guide_points_at_the_wire_contract() -> None:
    assert "protocol-contract.md" in _guide()
    assert CONTRACT.is_file()


def test_the_guide_says_the_layout_does_not_change() -> None:
    """`F5-040` bunu kanıtladı."""
    text = _guide()
    assert "varsayılan yerleşim değişmez" in text or "değişmez" in text
