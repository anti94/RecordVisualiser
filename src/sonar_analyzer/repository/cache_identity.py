"""Kaynak, kalibrasyon ve işlem sözleşmesine bağlı cache kimliği — F4-060."""

from __future__ import annotations

from collections.abc import Hashable
from dataclasses import dataclass

from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.io.index.fingerprint import PARSER_VERSION

# İlgili sayısal davranış değiştiğinde artırılır; uygulama sürümünden bağımsızdır.
PROCESSING_VERSION = 1
SUMMARY_VERSION = 1


@dataclass(frozen=True)
class CacheIdentity:
    """Kaynak snapshot'ı ve sonucu etkileyen bütün kanal/işlem girdileri.

    Dosyada source, SourceFingerprint; simülasyonda üretici parametreleridir.
    İşlenmiş veri sağlayıcıları processing_signature için ProcessingChain.signature()
    verir. Repository'nin fiziksel ham verisinde boş zincir kullanılır.
    """

    source: Hashable
    channel: ChannelMetadata
    parser_version: int = PARSER_VERSION
    processing_version: int = PROCESSING_VERSION
    summary_version: int = SUMMARY_VERSION
    processing_signature: str = "[]"
