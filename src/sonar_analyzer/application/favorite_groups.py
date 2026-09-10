"""Favori kanal grupları listesi — `F3-017`.

Gruplar `AppSettings.favorite_groups` içinde saklanır (`F1-009`'un sürümlü
ayar dosyası, şema v2); bu modül yalnız **liste kuralını** tutar, dosya
G/Ç yapmaz:

* grup adı benzersizdir (aynı ada ikinci kez kaydetmek üzerine yazar),
* kanal kimlikleri grup içinde tekilleştirilir, ilk görülme sırası korunur,
* adı boş/yalnızca boşluk olan grup reddedilir.

Bir grup **kayıttan bağımsızdır**: o an açık olmayan, hatta artık var
olmayan kanalları içerebilir. `resolve()`, grubu güncel bir kanal kümesine
karşı çözer ve bulunanları bulunamayanlardan **ayrı** raporlar (kabul
kriteri: "bulunamayan kanal ayrı raporlanır").
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from sonar_analyzer.settings.store import FavoriteGroup


def _dedupe(channel_ids: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for channel_id in channel_ids:
        if channel_id and channel_id not in seen:
            seen.add(channel_id)
            result.append(channel_id)
    return result


def save(
    existing: Sequence[FavoriteGroup], name: str, channel_ids: Iterable[str]
) -> list[FavoriteGroup]:
    """`name` grubunu ekler ya da **üzerine yazar**; grup sırası korunur.

    Yeni bir ad listenin sonuna eklenir; var olan bir ad yerinde
    güncellenir. Boş/yalnızca boşluk ad `ValueError` verir — sessizce
    adsız grup oluşturmak ileride karışıklık yaratır.
    """
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Favori grup adi bos olamaz.")

    group = FavoriteGroup(name=clean_name, channel_ids=_dedupe(channel_ids))
    replaced = False
    result: list[FavoriteGroup] = []
    for current in existing:
        if current.name == clean_name:
            result.append(group)
            replaced = True
        else:
            result.append(current)
    if not replaced:
        result.append(group)
    return result


def remove(existing: Sequence[FavoriteGroup], name: str) -> list[FavoriteGroup]:
    """Bir grubu ada göre çıkarır; yoksa liste değişmeden döner."""
    clean_name = name.strip()
    return [group for group in existing if group.name != clean_name]


def get(existing: Sequence[FavoriteGroup], name: str) -> FavoriteGroup | None:
    """Adı verilen grubu döndürür; yoksa `None`."""
    clean_name = name.strip()
    for group in existing:
        if group.name == clean_name:
            return group
    return None


def names(existing: Sequence[FavoriteGroup]) -> list[str]:
    """Kayıtlı grup adları, saklanma sırasıyla."""
    return [group.name for group in existing]


@dataclass(frozen=True)
class Resolution:
    """Bir grubun güncel kanal kümesine karşı çözümü — `F3-017`.

    `found` ve `missing`, grubun **kendi sırasını** korur. `missing` boş
    değilse çağıran taraf bunu kullanıcıya ayrı bir satırda bildirir.
    """

    found: list[str]
    missing: list[str]

    @property
    def has_missing(self) -> bool:
        return bool(self.missing)


def resolve(group: FavoriteGroup, available_channel_ids: Iterable[str]) -> Resolution:
    """Grubu `available_channel_ids` kümesine karşı çözer.

    Grup sırası korunur; küme üyeliği hızlı olsun diye `set`'e alınır.
    """
    available = set(available_channel_ids)
    found = [channel_id for channel_id in group.channel_ids if channel_id in available]
    missing = [channel_id for channel_id in group.channel_ids if channel_id not in available]
    return Resolution(found=found, missing=missing)
