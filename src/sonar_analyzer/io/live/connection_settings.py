"""Canlı bağlantı ve tampon ayarları — `F5-018`.

Kabul kriterinin özü tek cümle: **geçersiz adres, port veya kapasite
bağlantıdan önce açıklanır.** Bağlantı denenip soket hatasıyla
karşılaşmak kullanıcıya "neden" demez; burada her kural kendi cümlesiyle
doğrulanır ve `validate()` insan okunur bir liste döndürür.

Kurallar mümkün olduğunca **tek yerden** gelir: seri port adı/hızı
`SerialPortConfig` (`F5-009`), drop politikası `DropPolicy` (`F5-016`)
üzerinden doğrulanır — ayar katmanı kendi kopyasını tutmaz.

Kalıcılık `settings.store` (`F1-009`) tarafındadır; bu modül yalnız
modeli ve doğrulamayı taşır.
"""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from typing import Any

from sonar_analyzer.io.live.packet_queue import DropPolicy
from sonar_analyzer.io.live.serial_connection import SerialPortConfig

#: Desteklenen canlı kaynak türleri.
PROTOCOLS = ("udp", "tcp", "serial", "replay")

MIN_PORT = 1
MAX_PORT = 65_535

#: Halka tamponun örnek başına maliyeti (`ChannelRing`: int64 + float64 + uint8).
BYTES_PER_SAMPLE = 8 + 8 + 1
#: Kanal başına üst sınır — 64 MiB'ı aşan bir kapasite kazayla girilmiş sayılır.
MAX_RING_BYTES = 64 * 1024 * 1024
MAX_RING_CAPACITY = MAX_RING_BYTES // BYTES_PER_SAMPLE

MAX_QUEUE_SIZE = 100_000

#: Basit ana makine adı (RFC 1123 alt kümesi) — IP değilse buna uyar.
_HOSTNAME = re.compile(r"[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?(\.[A-Za-z0-9-]{1,63})*")


@dataclass(frozen=True)
class LiveConnectionSettings:
    """Bir canlı oturumun kalıcı yapılandırması.

    Kurucu **hata fırlatmaz**: kullanıcı ayar ekranında yarım/yanlış değer
    girerken her tuş vuruşunda istisna almamalı. Geçerlilik `validate()`
    ile sorulur ve bağlantıdan **önce** gösterilir.
    """

    protocol: str = "udp"
    host: str = "127.0.0.1"
    port: int = 51000
    serial_port: str = "COM1"
    baud_rate: int = 115_200
    ring_capacity_samples: int = 480_000  # 48 kHz'de 10 saniye
    queue_maxsize: int = 256
    drop_policy: str = DropPolicy.DROP_OLDEST.value
    auto_reconnect: bool = True

    def validate(self) -> list[str]:
        """Bağlantıdan önce gösterilecek sorunlar; liste boşsa ayar geçerlidir."""
        problems: list[str] = []
        problems.extend(self._protocol_problems())
        problems.extend(self._buffer_problems())
        return problems

    @property
    def is_valid(self) -> bool:
        return not self.validate()

    def ring_bytes_per_channel(self) -> int:
        """Seçilen kapasitenin kanal başına ölçülen bellek maliyeti."""
        return max(0, self.ring_capacity_samples) * BYTES_PER_SAMPLE

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol": self.protocol,
            "host": self.host,
            "port": self.port,
            "serial_port": self.serial_port,
            "baud_rate": self.baud_rate,
            "ring_capacity_samples": self.ring_capacity_samples,
            "queue_maxsize": self.queue_maxsize,
            "drop_policy": self.drop_policy,
            "auto_reconnect": self.auto_reconnect,
        }

    # -- dogrulama parcalari --------------------------------------------

    def _protocol_problems(self) -> list[str]:
        if self.protocol not in PROTOCOLS:
            return [f"Bilinmeyen protokol {self.protocol!r}; beklenen: {', '.join(PROTOCOLS)}."]
        if self.protocol == "serial":
            return self._serial_problems()
        if self.protocol in ("udp", "tcp"):
            return self._network_problems()
        return []  # replay: adres/port gerektirmez

    def _serial_problems(self) -> list[str]:
        try:
            SerialPortConfig(port=self.serial_port, baud_rate=self.baud_rate)
        except ValueError as exc:
            return [f"{exc}"]
        return []

    def _network_problems(self) -> list[str]:
        problems: list[str] = []
        if not self.host.strip():
            problems.append("Adres bos olamaz.")
        elif not _is_address(self.host):
            problems.append(f"Adres bir IP ya da ana makine adi olmali: {self.host!r}.")

        # UDP alici portu 0 olabilir: "isletim sistemi bos bir port secsin".
        lowest = 0 if self.protocol == "udp" else MIN_PORT
        if not lowest <= self.port <= MAX_PORT:
            detail = (
                f"UDP icin 0 (isletim sistemi secsin) veya {MIN_PORT}-{MAX_PORT}"
                if self.protocol == "udp"
                else f"{MIN_PORT}-{MAX_PORT}"
            )
            problems.append(f"Port araligi disinda: {self.port} (beklenen {detail}).")
        return problems

    def _buffer_problems(self) -> list[str]:
        problems: list[str] = []
        if self.ring_capacity_samples < 1:
            problems.append(f"Tampon kapasitesi pozitif olmali: {self.ring_capacity_samples}.")
        elif self.ring_capacity_samples > MAX_RING_CAPACITY:
            needed_mb = self.ring_bytes_per_channel() / (1024 * 1024)
            problems.append(
                f"Tampon kapasitesi cok buyuk: {self.ring_capacity_samples} ornek "
                f"kanal basina {needed_mb:.0f} MiB ister; ust sinir "
                f"{MAX_RING_CAPACITY} ornek ({MAX_RING_BYTES // (1024 * 1024)} MiB)."
            )

        if self.queue_maxsize < 1:
            problems.append(f"Kuyruk siniri pozitif olmali: {self.queue_maxsize}.")
        elif self.queue_maxsize > MAX_QUEUE_SIZE:
            problems.append(
                f"Kuyruk siniri cok buyuk: {self.queue_maxsize} (ust sinir {MAX_QUEUE_SIZE})."
            )

        if self.drop_policy not in {policy.value for policy in DropPolicy}:
            expected = ", ".join(policy.value for policy in DropPolicy)
            problems.append(
                f"Bilinmeyen drop politikasi {self.drop_policy!r}; beklenen: {expected}."
            )
        return problems


def _is_address(host: str) -> bool:
    """IP adresi ya da makul bir ana makine adı mı?"""
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return bool(_HOSTNAME.fullmatch(host)) and len(host) <= 253
    return True
