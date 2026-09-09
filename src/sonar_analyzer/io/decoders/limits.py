"""Header boyut ve sözleşme sınırları — `F2-004`.

`docs/format/profile-a.md` §3 doğrulama sırasının 1, 4 ve 6. adımları.

Bu kontroller **başka bir alan claim ettiği için** bir yapıyı okumaya
çalışmadan **önce** çalışır. Örneğin `header_size`/`record_size` beklenenden
farklıysa, o değerlere güvenip ileri okuma yapmıyoruz — sabit boyutlu
`struct.Struct` sözleşmesi kullanılıyor; kesik/tutarsız bir girdi bu yüzden
aşırı bellek ayırma veya sınır dışı okumaya yol açamaz.
"""

from __future__ import annotations

from sonar_analyzer.io.decoders.errors import HeaderContractError, TruncatedHeaderError
from sonar_analyzer.io.profile_a_format import (
    EXPECTED_CHANNEL_COUNT,
    EXPECTED_HEADER_SIZE_V1,
    EXPECTED_RECORD_SIZE_V1,
    FILE_HEADER_V1,
    FileHeaderV1,
)


def validate_buffer_has_header(buffer_length: int) -> None:
    """Adım 1: dosya en az 32 bayt mı?

    Bu kontrol `read_file_header_v1` çağrılmadan **önce** yapılmalıdır;
    aksi hâlde `struct.unpack_from` ham `struct.error` yükseltir — kullanıcıya
    "kesik header" gibi anlamlı bir teşhis vermez.
    """
    if buffer_length < FILE_HEADER_V1.size:
        raise TruncatedHeaderError(buffer_length, FILE_HEADER_V1.size)


def validate_header_contract(header: FileHeaderV1) -> None:
    """Adım 4 ve 6: `header_size`, `record_size`, `channel_count` sabit mi?

    Bu profilde alanlar sabittir (Profil A sürüm 1 genişletilmiyor); farklı
    bir değer, header'ın bu sözleşmeyle üretilmediğini gösterir ve okuma
    durdurulur — o değerlere güvenerek ileri okuma yapılmaz.
    """
    if header.header_size != EXPECTED_HEADER_SIZE_V1:
        raise HeaderContractError(
            f"header_size {header.header_size} != {EXPECTED_HEADER_SIZE_V1}",
            byte_offset=10,
        )
    if header.record_size != EXPECTED_RECORD_SIZE_V1:
        raise HeaderContractError(
            f"record_size {header.record_size} != {EXPECTED_RECORD_SIZE_V1}",
            byte_offset=12,
        )
    if header.channel_count != EXPECTED_CHANNEL_COUNT:
        raise HeaderContractError(
            f"channel_count {header.channel_count} != {EXPECTED_CHANNEL_COUNT} "
            "(sensor_values sabit 8 alan bekler)",
            byte_offset=20,
        )
