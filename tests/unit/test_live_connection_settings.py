"""Canlı bağlantı ve tampon ayarları — `F5-018`.

Kabul: geçersiz adres, port veya kapasite **bağlantıdan önce** açıklanır.

"Açıklanır" burada "bir istisna fırlatılır" değil: `validate()` insan
okunur cümleler döndürür ve kurucu hiçbir zaman hata vermez (kullanıcı
ayar alanına yazarken her tuşta istisna almamalı).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sonar_analyzer.io.live.connection_settings import (
    MAX_PORT,
    MAX_RING_CAPACITY,
    LiveConnectionSettings,
)
from sonar_analyzer.io.live.packet_queue import DropPolicy
from sonar_analyzer.settings.store import AppSettings, load_settings, save_settings


def _udp(**overrides: object) -> LiveConnectionSettings:
    base: dict[str, object] = {"protocol": "udp", "host": "127.0.0.1", "port": 51000}
    base.update(overrides)
    return LiveConnectionSettings(**base)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# gecerli yapilandirmalar
# --------------------------------------------------------------------------- #


def test_the_defaults_are_valid() -> None:
    settings = LiveConnectionSettings()
    assert settings.validate() == []
    assert settings.is_valid is True


@pytest.mark.parametrize(
    "host", ["127.0.0.1", "192.168.1.50", "10.0.0.1", "::1", "localhost", "sonar-01.local"]
)
def test_valid_addresses_are_accepted(host: str) -> None:
    assert _udp(host=host).validate() == []


@pytest.mark.parametrize("port", [0, 1, 1024, 51000, MAX_PORT])
def test_valid_udp_ports_are_accepted(port: int) -> None:
    """UDP'de 0 geçerlidir: "işletim sistemi boş bir port seçsin"."""
    assert _udp(port=port).validate() == []


def test_a_replay_source_needs_no_address_or_port() -> None:
    settings = LiveConnectionSettings(protocol="replay", host="", port=0)
    assert settings.validate() == []


def test_a_valid_serial_configuration_is_accepted() -> None:
    settings = LiveConnectionSettings(protocol="serial", serial_port="COM3", baud_rate=115200)
    assert settings.validate() == []


# --------------------------------------------------------------------------- #
# gecersiz ADRES aciklanir
# --------------------------------------------------------------------------- #


def test_an_empty_address_is_explained() -> None:
    problems = _udp(host="   ").validate()
    assert len(problems) == 1
    assert "Adres bos olamaz" in problems[0]


@pytest.mark.parametrize("host", ["999.999.999.999 ", "iki kelime", "bos!luk", "-basta-tire"])
def test_a_malformed_address_is_explained_with_the_value(host: str) -> None:
    problems = _udp(host=host).validate()
    assert len(problems) == 1
    assert "Adres bir IP ya da ana makine adi olmali" in problems[0]
    assert repr(host) in problems[0]  # kullanici ne yazdigini gorur


# --------------------------------------------------------------------------- #
# gecersiz PORT aciklanir
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("port", [-1, MAX_PORT + 1, 100_000])
def test_an_out_of_range_port_is_explained(port: int) -> None:
    problems = _udp(port=port).validate()
    assert len(problems) == 1
    assert "Port araligi disinda" in problems[0]
    assert str(port) in problems[0]


def test_tcp_rejects_port_zero_because_it_means_nothing_when_connecting() -> None:
    problems = LiveConnectionSettings(protocol="tcp", host="127.0.0.1", port=0).validate()
    assert len(problems) == 1
    assert "Port araligi disinda" in problems[0]


def test_udp_accepts_port_zero_but_tcp_does_not() -> None:
    assert LiveConnectionSettings(protocol="udp", port=0).validate() == []
    assert LiveConnectionSettings(protocol="tcp", port=0).validate() != []


# --------------------------------------------------------------------------- #
# gecersiz KAPASITE aciklanir
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("capacity", [0, -1, -480_000])
def test_a_non_positive_capacity_is_explained(capacity: int) -> None:
    problems = _udp(ring_capacity_samples=capacity).validate()
    assert any("Tampon kapasitesi pozitif olmali" in problem for problem in problems)


def test_an_absurd_capacity_is_explained_with_its_memory_cost() -> None:
    """Mesaj kaç MiB isteyeceğini söyler — kullanıcı sayının anlamını görür."""
    capacity = MAX_RING_CAPACITY * 4
    problems = _udp(ring_capacity_samples=capacity).validate()
    assert len(problems) == 1
    assert "cok buyuk" in problems[0]
    assert "MiB" in problems[0]


def test_the_capacity_limit_boundary_is_inclusive() -> None:
    assert _udp(ring_capacity_samples=MAX_RING_CAPACITY).validate() == []
    assert _udp(ring_capacity_samples=MAX_RING_CAPACITY + 1).validate() != []


def test_the_memory_cost_matches_the_ring_buffer_footprint() -> None:
    """`F5-014`'ün ölçülen bütçesiyle aynı: (8 + 8 + 1) bayt/örnek."""
    settings = _udp(ring_capacity_samples=1000)
    assert settings.ring_bytes_per_channel() == 1000 * 17


# --------------------------------------------------------------------------- #
# kuyruk ve politika
# --------------------------------------------------------------------------- #


def test_a_non_positive_queue_limit_is_explained() -> None:
    problems = _udp(queue_maxsize=0).validate()
    assert any("Kuyruk siniri pozitif olmali" in problem for problem in problems)


def test_an_unknown_drop_policy_is_explained_with_the_valid_options() -> None:
    problems = _udp(drop_policy="rastgele").validate()
    assert len(problems) == 1
    assert "Bilinmeyen drop politikasi" in problems[0]
    for policy in DropPolicy:
        assert policy.value in problems[0]


@pytest.mark.parametrize("policy", [p.value for p in DropPolicy])
def test_every_real_drop_policy_is_accepted(policy: str) -> None:
    assert _udp(drop_policy=policy).validate() == []


def test_an_unknown_protocol_is_explained() -> None:
    problems = LiveConnectionSettings(protocol="carrier-pigeon").validate()
    assert any("Bilinmeyen protokol" in problem for problem in problems)


def test_an_invalid_serial_port_is_explained_by_the_shared_rule() -> None:
    """Kural `SerialPortConfig`'ten (`F5-009`) gelir — ayar katmanı kopya tutmaz."""
    problems = LiveConnectionSettings(protocol="serial", serial_port="USB0").validate()
    assert len(problems) == 1
    assert "bicimini izlemeli" in problems[0]


def test_an_invalid_baud_rate_is_explained_by_the_shared_rule() -> None:
    problems = LiveConnectionSettings(protocol="serial", serial_port="COM1", baud_rate=1234)
    assert any("Desteklenmeyen baud hizi" in problem for problem in problems.validate())


# --------------------------------------------------------------------------- #
# birden cok sorun birlikte bildirilir
# --------------------------------------------------------------------------- #


def test_multiple_problems_are_all_reported_not_just_the_first() -> None:
    """Kullanıcı üç kez deneyip üç ayrı hata görmemeli; hepsi bir arada."""
    settings = LiveConnectionSettings(
        protocol="tcp", host="", port=99_999, ring_capacity_samples=0, queue_maxsize=0
    )
    problems = settings.validate()
    assert len(problems) == 4
    assert any("Adres" in problem for problem in problems)
    assert any("Port" in problem for problem in problems)
    assert any("Tampon kapasitesi" in problem for problem in problems)
    assert any("Kuyruk" in problem for problem in problems)


def test_the_constructor_never_raises_on_invalid_values() -> None:
    """Kullanıcı ayar alanına yazarken her tuş vuruşunda istisna almamalı."""
    settings = LiveConnectionSettings(protocol="?", host="", port=-5, ring_capacity_samples=-1)
    assert settings.is_valid is False  # kurulabildi; gecerlilik ayri soruluyor


# --------------------------------------------------------------------------- #
# kalicilik (settings.store, sema v3)
# --------------------------------------------------------------------------- #


def test_live_settings_round_trip_through_the_settings_file(tmp_path: Path) -> None:
    target = tmp_path / "settings.json"
    live = LiveConnectionSettings(
        protocol="tcp",
        host="192.168.1.42",
        port=6000,
        ring_capacity_samples=96_000,
        queue_maxsize=64,
        drop_policy=DropPolicy.BLOCK.value,
        auto_reconnect=False,
    )
    save_settings(AppSettings(live_connection=live), target)

    loaded = load_settings(target)
    assert loaded.ok
    assert loaded.settings.live_connection == live


def test_a_settings_file_without_the_live_block_uses_defaults(tmp_path: Path) -> None:
    """Şema v2'den yükseltme: alan yoksa varsayılan, uyarı üretmeden."""
    target = tmp_path / "settings.json"
    target.write_text(json.dumps({"schema_version": 2, "theme": "dark"}), encoding="utf-8")

    loaded = load_settings(target)
    assert loaded.settings.live_connection == LiveConnectionSettings()
    assert loaded.warnings == []


def test_a_corrupt_live_block_falls_back_with_a_warning(tmp_path: Path) -> None:
    target = tmp_path / "settings.json"
    target.write_text(
        json.dumps({"schema_version": 3, "live_connection": "bu bir sozluk degil"}),
        encoding="utf-8",
    )

    loaded = load_settings(target)
    assert loaded.settings.live_connection == LiveConnectionSettings()
    assert any("live_connection" in warning for warning in loaded.warnings)


def test_a_single_corrupt_field_does_not_drop_the_whole_block(tmp_path: Path) -> None:
    target = tmp_path / "settings.json"
    target.write_text(
        json.dumps(
            {
                "schema_version": 3,
                "live_connection": {"host": "10.0.0.5", "port": "bes bin", "queue_maxsize": 32},
            }
        ),
        encoding="utf-8",
    )

    loaded = load_settings(target)
    live = loaded.settings.live_connection
    assert live.host == "10.0.0.5"  # saglam alan korundu
    assert live.port == LiveConnectionSettings().port  # bozuk alan varsayilana dondu
    assert live.queue_maxsize == 32
    assert any("live_connection.port" in warning for warning in loaded.warnings)


def test_an_invalid_but_readable_value_is_kept_and_explained_at_connect_time(
    tmp_path: Path,
) -> None:
    """Dosyadaki değer okunabilir ama geçersizse: yüklenir, `validate()` açıklar."""
    target = tmp_path / "settings.json"
    target.write_text(
        json.dumps({"schema_version": 3, "live_connection": {"port": 99_999}}), encoding="utf-8"
    )

    loaded = load_settings(target)
    assert loaded.settings.live_connection.port == 99_999  # sessizce degistirilmedi
    assert any("Port araligi disinda" in p for p in loaded.settings.live_connection.validate())
