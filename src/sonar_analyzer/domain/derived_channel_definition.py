"""Türetilmiş kanalın yeniden üretilebilir tanımı — `F4-068`.

Bir türetilmiş kanal, sonucu **saklanan** bir dizi değil, sonucu
**yeniden üretebilen** bir tarifdir. Tarif iki şeyden oluşur:

* **giriş kimlikleri** — hangi ham/türetilmiş kanallardan beslenir,
* **işlem zinciri** — o girişlere hangi DSP adımları hangi sırayla ve
  hangi parametrelerle uygulanır (`ProcessingChain`, `F4-002`).

Bu ikisi bir arada tanımın **kimliğini** belirler: aynı girişler ve aynı
etkin zincir her zaman aynı `signature()` ve `fingerprint()` değerini
verir. Görünen ad, açıklama ve birim tarifin sonucunu değiştirmediği için
kimliğe girmez — kullanıcı adı değiştirdiğinde kanal yeniden hesaplanmaz.

Kimlik iki işe yarar: bir çalışma alanı dosyadan geri yüklendiğinde aynı
kanal aynı `derived_id` ile geri gelir, ve önbellek anahtarı olarak
kullanıldığında zincir veya giriş değişince eski sonuç kullanılmaz
(`F4-060` `CacheIdentity` ile aynı ilke).

Saf veri — Qt yok, `GUI olmadan` doğrulanır. Repository'ye bağlanması
`F4-069`, formül girişi `F4-070`+.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import cast

from sonar_analyzer.processing.chain import ProcessingChain
from sonar_analyzer.processing.steps import ProcessingStep

#: Tanım şemasının sürümü; `to_dict()` çıktısına yazılır (göç için).
DEFINITION_SCHEMA_VERSION = 1

#: `derived_id`'nin parmak izinden alınan bölümünün uzunluğu.
FINGERPRINT_PREFIX = "derived"
FINGERPRINT_LENGTH = 16


class DerivedChannelError(ValueError):
    """Tanım yeniden üretilebilir değil (eksik giriş, bildirilmemiş kanal vb.)."""


def _empty_inputs() -> tuple[str, ...]:
    return ()


@dataclass(frozen=True)
class DerivedChannelDefinition:
    """Bir türetilmiş kanalı yeniden üretmeye yeten tarif.

    `inputs` sırası anlamlıdır (formül `F4-070`+ konumla eşler) ve
    tekrar içeremez; zincirdeki her adım **bildirilmiş** bir girişe
    bakmak zorundadır, yoksa tanım kendi kaynağını taşımıyor demektir.
    """

    name: str
    inputs: tuple[str, ...] = field(default_factory=_empty_inputs)
    chain: ProcessingChain = field(default_factory=ProcessingChain)
    unit: str | None = None
    description: str = ""
    #: Varsa seriyi **üreten** aritmetik ifade (`F4-070`); zincir onun
    #: çıktısını işler. Boşsa kaynak doğrudan `inputs[0]`'dır.
    expression: str = ""

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise DerivedChannelError("Türetilmiş kanalın adı boş olamaz")
        inputs = tuple(self.inputs)
        if not inputs:
            raise DerivedChannelError("Türetilmiş kanal en az bir giriş kanalı bildirmeli")
        # Tip denetlenmemiş çağıran da temiz bir hata almalı, `AttributeError` değil.
        for channel_id in cast("tuple[object, ...]", inputs):
            if not isinstance(channel_id, str) or not channel_id.strip():
                raise DerivedChannelError(f"Giriş kanalı kimliği boş olamaz: {channel_id!r}")
        if len(set(inputs)) != len(inputs):
            raise DerivedChannelError(f"Giriş kanalı kimlikleri tekrar edemez: {list(inputs)}")
        undeclared = sorted({step.input_channel_id for step in self.chain.steps} - set(inputs))
        if undeclared:
            raise DerivedChannelError(
                f"Zincir bildirilmemiş kanala bakıyor: {undeclared}; bildirilenler {list(inputs)}"
            )
        if self.expression.strip():
            # İfade sorgu anında yeniden ayrıştırılır; bunun için giriş
            # kimliklerinin formülde yazılabilir olması şarttır.
            unwritable = sorted(cid for cid in inputs if not cid.isidentifier())
            if unwritable:
                raise DerivedChannelError(
                    f"İfadeli tanımın girişleri formülde yazılabilir olmalı; "
                    f"şunlar tanımlayıcı değil: {unwritable}"
                )
        object.__setattr__(self, "inputs", inputs)

    # -- yeniden uretilebilirlik ------------------------------------

    def signature(self) -> str:
        """Sonucu belirleyen her şeyin **kararlı** metin gösterimi.

        Kimliğe yalnız girişler ve **etkin** adımlar girer; kapalı bir
        adım kimlik açısından hiç yokmuş gibi davranır. Buradan iki sonuç
        çıkar: zincire kapalı bir adım eklemek `derived_id`'yi değiştirmez,
        ama var olan bir adımı kapatmak değiştirir — çünkü artık
        uygulanmıyordur.

        Ad, açıklama ve birim sonucu değiştirmediği için kimliğe girmez;
        tanım eşitliği (`==`) ise bunları da kapsar.
        """
        payload = {
            "inputs": list(self.inputs),
            "chain": cast("list[str]", json.loads(self.chain.signature())),
            "expression": self.expression.strip(),
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    def fingerprint(self) -> str:
        """`signature()`'in sha256 özeti — sabit uzunlukta kimlik."""
        return hashlib.sha256(self.signature().encode("utf-8")).hexdigest()

    @property
    def derived_id(self) -> str:
        """Bu tarifin ürettiği kanalın kimliği; tarif aynıysa hep aynıdır."""
        return f"{FINGERPRINT_PREFIX}:{self.fingerprint()[:FINGERPRINT_LENGTH]}"

    def produces_same_data_as(self, other: DerivedChannelDefinition) -> bool:
        """İki tarif aynı veriyi mi üretir (ad/açıklama farkı önemsiz)."""
        return self.signature() == other.signature()

    # -- duzenleme --------------------------------------------------

    def renamed(self, name: str) -> DerivedChannelDefinition:
        """Adı değişmiş yeni tanım; `derived_id` **değişmez**."""
        return DerivedChannelDefinition(
            name=name,
            inputs=self.inputs,
            chain=self.chain,
            unit=self.unit,
            description=self.description,
            expression=self.expression,
        )

    def with_chain(self, chain: ProcessingChain) -> DerivedChannelDefinition:
        """Zinciri değişmiş yeni tanım; `derived_id` değişir."""
        return DerivedChannelDefinition(
            name=self.name,
            inputs=self.inputs,
            chain=chain,
            unit=self.unit,
            description=self.description,
            expression=self.expression,
        )

    def with_step(self, step: ProcessingStep) -> DerivedChannelDefinition:
        """Zincire bir adım ekler; adımın girişi bildirilmiş olmalıdır."""
        return self.with_chain(self.chain.with_step(step))

    # -- serilestirme -----------------------------------------------

    def to_dict(self) -> dict[str, object]:
        """Çalışma alanına yazılabilir, kayıpsız gösterim."""
        return {
            "schema_version": DEFINITION_SCHEMA_VERSION,
            "name": self.name,
            "inputs": list(self.inputs),
            "chain": self.chain.to_list(),
            "unit": self.unit,
            "description": self.description,
            "expression": self.expression,
        }

    @classmethod
    def from_dict(cls, data: object) -> DerivedChannelDefinition:
        """`to_dict()` çıktısını geri okur; bilinmeyen şema sürümü reddedilir."""
        if not isinstance(data, dict):
            raise DerivedChannelError("Türetilmiş kanal tanımı bir nesne olmalı")
        record = cast("dict[str, object]", data)
        version = record.get("schema_version", DEFINITION_SCHEMA_VERSION)
        if version != DEFINITION_SCHEMA_VERSION:
            raise DerivedChannelError(
                f"Desteklenmeyen tanım şeması: {version!r}; beklenen {DEFINITION_SCHEMA_VERSION}"
            )
        name = record.get("name")
        if not isinstance(name, str):
            raise DerivedChannelError("name metin olmalı")
        raw_inputs = record.get("inputs", [])
        if not isinstance(raw_inputs, list):
            raise DerivedChannelError("inputs bir dizi olmalı")
        inputs: list[str] = []
        for entry in cast("list[object]", raw_inputs):
            if not isinstance(entry, str):
                raise DerivedChannelError(f"Giriş kanalı kimliği metin olmalı: {entry!r}")
            inputs.append(entry)
        raw_chain = record.get("chain", [])
        if not isinstance(raw_chain, list):
            raise DerivedChannelError("chain bir dizi olmalı")
        unit = record.get("unit")
        if unit is not None and not isinstance(unit, str):
            raise DerivedChannelError("unit metin ya da boş olmalı")
        description = record.get("description", "")
        if not isinstance(description, str):
            raise DerivedChannelError("description metin olmalı")
        expression = record.get("expression", "")
        if not isinstance(expression, str):
            raise DerivedChannelError("expression metin olmalı")
        return cls(
            name=name,
            inputs=tuple(inputs),
            chain=ProcessingChain.from_list(cast("list[object]", raw_chain)),
            unit=unit,
            description=description,
            expression=expression,
        )
