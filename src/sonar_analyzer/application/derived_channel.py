"""İşlem zincirinden türetilmiş kanal metadata'sı — `F4-026`.

Bir `ProcessingChain` bir kanalın örnek dizisini dönüştürür; çoğu adım
kanalın **tanımını** (sample rate, birim) değiştirmez, ama `RESAMPLE`
adımı sample rate'i değiştirir. Bu modül zinciri yürüterek türetilmiş
kanalın `ChannelMetadata`'sını hesaplar — özellikle **yeni sample
rate**'in metadata'da görünmesini sağlar.

Saf veri — Qt yok, `GUI olmadan` doğrulanır.
"""

from __future__ import annotations

from dataclasses import replace
from typing import cast

from sonar_analyzer.domain.channel import ChannelMetadata, ChannelSource
from sonar_analyzer.processing.chain import ProcessingChain
from sonar_analyzer.processing.steps import StepKind


def chain_changes_sample_rate(chain: ProcessingChain) -> bool:
    """Zincirde etkin en az bir `RESAMPLE` adımı var mı?"""
    return any(step.kind is StepKind.RESAMPLE for step in chain.enabled_steps)


def derived_sample_rate(base_rate_hz: float, chain: ProcessingChain) -> float:
    """Zincir uygulandıktan sonraki sample rate.

    Etkin her `RESAMPLE` adımı çalışan oranı kendi `target_rate_hz`'ine
    çeker (zincirlenirse son adım kazanır). `RESAMPLE` yoksa `base_rate_hz`.
    """
    rate = base_rate_hz
    for step in chain.enabled_steps:
        if step.kind is StepKind.RESAMPLE:
            rate = float(cast("float", step.parameters["target_rate_hz"]))
    return rate


def derive_channel_metadata(base: ChannelMetadata, chain: ProcessingChain) -> ChannelMetadata:
    """`base` kanalının zincir uygulandıktan sonraki metadata'sı.

    Zincir sample rate'i değiştirmiyorsa `base` aynen döner. Değiştiriyorsa
    yeni bir `ChannelMetadata` döner: `source=DERIVED`, ayrı bir `id`/`path`
    ve **yeni sample rate** `sample_rate_hz`'de.
    """
    if not chain_changes_sample_rate(chain):
        return base

    base_rate = base.sample_rate_hz or 0.0
    new_rate = derived_sample_rate(base_rate, chain)
    return replace(
        base,
        id=f"{base.id}#resampled",
        path=f"{base.path} (resampled)",
        name=f"{base.name} · {new_rate:g} Hz",
        source=ChannelSource.DERIVED,
        sample_rate_hz=new_rate if new_rate > 0 else None,
    )
