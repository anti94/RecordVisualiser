"""Şemadan çalışma zamanı okuma yapıları — `F7-014`…`F7-017`.

Şema doğrulanmış bir tanımdır; bu modül onu **okuyan** nesnelere çevirir:
`struct.Struct`, NumPy structured dtype ve bir parmak izi.

Üretim yükleme anında bir kez yapılır. Her frame için yeniden `Struct`
kurmak, 6.000 frame'lik bir kayıtta 6.000 gereksiz derleme demektir.

Parmak izi (`fingerprint`) şemanın **anlamını** özetler, metnini değil:
açıklama satırı değişince parmak izi değişmez, bir offset değişince
değişir. Metni özetleseydi bir yazım düzeltmesi bütün önbellekleri
geçersiz kılardı.
"""

from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

from sonar_analyzer.io.schema.errors import SchemaMismatchError, SchemaTypeError
from sonar_analyzer.io.schema.model import FieldDef, Schema, StructDef
from sonar_analyzer.io.schema.types import CHAR_ARRAY, COMPLEX_FLOAT

#: Parmak izinin kac karakteri tasinacak. Tam SHA-256 gereksiz uzun;
#: 16 karakter (64 bit) kaza eseri cakisma icin fazlasiyla yeterli.
FINGERPRINT_LENGTH = 16


def _value_count(field: FieldDef) -> int:
    """Bir alanın `struct.unpack` çıktısında kaç değer tuttuğu.

    `char[N]` tek bayt dizisi olarak gelir; başka her dizi alanı `count`
    kadar ayrı değer üretir.
    """
    if field.cpp_type.cpp == CHAR_ARRAY:
        return 1
    return field.count


@dataclass(frozen=True)
class StructReader:
    """Bir struct'ı baytlardan okuyan derlenmiş yapı."""

    definition: StructDef
    compiled: struct.Struct
    #: Alan adlari, `struct.unpack` ciktisiyla ayni sirada.
    names: tuple[str, ...]

    @property
    def size(self) -> int:
        return self.compiled.size

    def unpack(self, data: bytes, offset: int = 0) -> dict[str, Any]:
        """Baytlardan alan adı → değer sözlüğü üretir.

        Dizi alanları `struct`'ta **tek değer değildir**: `16B` biçimi on
        altı ayrı değer döndürür. Alanları çıktıyla birebir eşleştirmek bu
        yüzden yanlıştır — bir dizi alanından sonraki her şey kayar ve
        hiçbir istisna oluşmaz. Her alan kendi değer sayısı kadar tüketir.

        `char[N]` bunun istisnasıdır: `12s` tek bir bayt dizisi döndürür.

        Dolgu alanları çıktıya konmaz: anlamları yoktur ve kullanıcıya
        gösterilseler gürültü olurlar.
        """
        if len(data) - offset < self.compiled.size:
            raise SchemaMismatchError(
                f"{self.definition.name} icin yeterli bayt yok",
                expected=self.compiled.size,
                found=len(data) - offset,
            )
        values = self.compiled.unpack_from(data, offset)
        ordered = sorted(self.definition.fields, key=lambda f: f.offset)

        result: dict[str, Any] = {}
        cursor = 0
        for field in ordered:
            taken = _value_count(field)
            chunk = values[cursor : cursor + taken]
            cursor += taken
            if field.is_padding:
                continue
            result[field.name] = chunk[0] if taken == 1 else chunk

        if cursor != len(values):
            raise SchemaMismatchError(
                f"{self.definition.name}: alanlar cozulen deger sayisini tuketmedi",
                expected=len(values),
                found=cursor,
            )
        return result

    def decode_bits(self, field_name: str, raw_value: int) -> dict[str, int]:
        """Bir bit alanı taşıyan alanın maskelerini çözer."""
        field = self.definition.field(field_name)
        return {bit.name: bit.extract(raw_value) for bit in field.bits}


def _numpy_field(field: FieldDef) -> tuple[str, str] | tuple[str, str, int]:
    """Bir alanın NumPy structured dtype girdisi."""
    if field.cpp_type.cpp == CHAR_ARRAY:
        return (field.name, f"S{field.count}")
    if not field.cpp_type.numpy_direct:
        raise SchemaTypeError(
            field.cpp_type.cpp,
            field=field.name,
            hint="NumPy'da dogrudan karsiligi yok; i2 ciftleri olarak okunup elle birlestirilmeli",
        )
    if field.count > 1:
        return (field.name, field.cpp_type.numpy_dtype, field.count)
    return (field.name, field.cpp_type.numpy_dtype)


def build_reader(definition: StructDef, endianness: str) -> StructReader:
    """Bir struct tanımından derlenmiş okuyucu üretir — `F7-014`."""
    fmt = definition.struct_format(endianness)
    compiled = struct.Struct(fmt)
    if compiled.size != definition.size:
        raise SchemaMismatchError(
            f"{definition.name}: uretilen bicim bildirilen boyutu vermiyor",
            expected=definition.size,
            found=compiled.size,
        )
    ordered = sorted(definition.fields, key=lambda f: f.offset)
    return StructReader(
        definition=definition, compiled=compiled, names=tuple(f.name for f in ordered)
    )


def build_dtype(definition: StructDef, endianness: str) -> np.dtype[Any]:
    """Bir struct tanımından NumPy structured dtype üretir — `F7-015`.

    `itemsize` bildirilen boyuta eşit olmalıdır. NumPy kendi hizalamasını
    uygulasaydı offsetler kayardı; bu yüzden offsetler **açıkça** verilir
    ve `itemsize` elle sabitlenir.
    """
    byte_order = "<" if endianness == "little" else ">"
    names: list[str] = []
    formats: list[Any] = []
    offsets: list[int] = []
    for field in sorted(definition.fields, key=lambda f: f.offset):
        entry = _numpy_field(field)
        names.append(field.name)
        offsets.append(field.offset)
        if len(entry) == 3:
            formats.append((byte_order + entry[1], entry[2]))
        else:
            code = entry[1]
            formats.append(code if code.startswith("S") else byte_order + code)

    dtype = np.dtype(
        {"names": names, "formats": formats, "offsets": offsets, "itemsize": definition.size}
    )
    if dtype.itemsize != definition.size:
        raise SchemaMismatchError(
            f"{definition.name}: uretilen dtype bildirilen boyutu vermiyor",
            expected=definition.size,
            found=dtype.itemsize,
        )
    return dtype


def payload_dtype(schema: Schema) -> np.dtype[Any]:
    """Frame yükünün örnek dtype'ı."""
    sample = schema.payload.sample_type
    if sample.cpp != COMPLEX_FLOAT:
        raise SchemaTypeError(
            sample.cpp,
            hint=f"bu profilde yalniz {COMPLEX_FLOAT} destekleniyor (D-28)",
        )
    return np.dtype(("<" if schema.endianness == "little" else ">") + sample.numpy_dtype)


def read_payload(schema: Schema, data: bytes, offset: int = 0) -> NDArray[np.complex64]:
    """Bir frame'in yükünü (sensör, örnek) dizisine çevirir — `F7-016`.

    Kopya alınmaz: `np.frombuffer` doğrudan tampona bakar. Yerleşim
    `sensor_major` ise dizi (sensör, örnek) biçiminde; `sample_major` ise
    aktarılarak aynı biçime getirilir.

    Aktarma bir **görünüm** üretir, kopya değil; ama bitişik değildir.
    Çağıran taraf bitişiklik isterse kendi kopyasını almalıdır.
    """
    payload = schema.payload
    expected = payload.frame_bytes
    if len(data) - offset < expected:
        raise SchemaMismatchError(
            "frame yuku icin yeterli bayt yok", expected=expected, found=len(data) - offset
        )

    flat = np.frombuffer(
        data,
        dtype=payload_dtype(schema),
        count=payload.sensor_count * payload.frame_samples,
        offset=offset,
    )
    if payload.sensor_major:
        return flat.reshape(payload.sensor_count, payload.frame_samples)
    return flat.reshape(payload.frame_samples, payload.sensor_count).T


def fingerprint(schema: Schema) -> str:
    """Şemanın anlamını özetleyen kısa parmak izi — `F7-017`.

    Yalnız **davranışı belirleyen** alanlar özete girer: kimlik, sürüm,
    bayt sırası, paketleme, struct adları ve her alanın adı, tipi,
    offseti, eleman sayısı. Açıklama ve not alanları girmez.

    Bu ayrım bilinçlidir: bir yazım düzeltmesi parmak izini değiştirseydi
    bütün indeks önbellekleri gereksiz yere geçersizleşirdi.
    """
    parts: list[str] = [
        f"id={schema.id}",
        f"version={schema.version}",
        f"endianness={schema.endianness}",
        f"packing={schema.packing}",
        f"payload={schema.payload.sensor_count}x{schema.payload.frame_samples}"
        f":{schema.payload.sample_type.cpp}:{schema.payload.layout}",
    ]
    for enum_name in sorted(schema.enums):
        enum = schema.enums[enum_name]
        values = ",".join(f"{k}={v}" for k, v in sorted(enum.values.items()))
        parts.append(f"enum:{enum_name}:{enum.underlying.cpp}:{values}")
    for struct_name in sorted(schema.structs):
        definition = schema.structs[struct_name]
        parts.append(f"struct:{struct_name}:{definition.size}")
        for field in sorted(definition.fields, key=lambda f: f.offset):
            bits = ",".join(f"{b.name}@{b.mask:#x}>>{b.shift}" for b in field.bits)
            parts.append(
                f"  field:{field.name}:{field.cpp_type.cpp}:{field.offset}:{field.count}"
                f":{field.enum}:{bits}"
            )

    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
    return digest[:FINGERPRINT_LENGTH]
