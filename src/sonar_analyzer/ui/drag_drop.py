"""Kanal sürükle-bırak MIME sözleşmesi — `F3-015`.

Kaynak (`DataExplorerDock`'un ağaçları) ve hedef (`PlotPanel`) bu tek sabiti
paylaşır; ikisi ayrı dosyalarda literal string tekrarlarsa bir yazım hatası
sürüklemeyi sessizce kırar ve hiçbir yerde hata vermez (sürükleme başlar,
bırakma hiçbir şey yapmaz). Tek kaynak bu riski ortadan kaldırır.
"""

from __future__ import annotations

#: Sürüklenen verinin taşıdığı MIME türü; değeri UTF-8 kodlu `channel.id`'dir.
CHANNEL_MIME_TYPE = "application/x-sonar-channel-id"


def encode_channel_id(channel_id: str) -> bytes:
    return channel_id.encode("utf-8")


def decode_channel_id(data: bytes) -> str:
    return bytes(data).decode("utf-8")
