"""Profil C şema katmanı — C++ struct tanımlarının TOML tarifi.

Kayıt dosyalarını C++ tarafı üretir (`D-29`). Bu paket o dosyaların
yerleşimini **tarif eden** TOML şemasını okur, doğrular ve çalışma
zamanında okuma yapıları üretir.

Şema yüklenirken doğrulanır, okunurken değil: bir yazım hatasının ancak
o alan ilk kez okunduğunda ortaya çıkması, saatler sonra yanlış sayılara
bakmak demektir.

Sözleşme: `docs/format/toml-schema.md`.
"""

from __future__ import annotations

from sonar_analyzer.io.schema._toml import load_path, loads
from sonar_analyzer.io.schema.errors import (
    SchemaError,
    SchemaLayoutError,
    SchemaMismatchError,
    SchemaTypeError,
    SchemaValueError,
)
from sonar_analyzer.io.schema.loader import build, load, load_text
from sonar_analyzer.io.schema.model import (
    BitField,
    EnumDef,
    FieldDef,
    PayloadDef,
    Schema,
    StructDef,
)
from sonar_analyzer.io.schema.types import TYPES, CppType, is_supported, resolve, size_of

__all__ = [
    "TYPES",
    "BitField",
    "CppType",
    "EnumDef",
    "FieldDef",
    "PayloadDef",
    "Schema",
    "SchemaError",
    "SchemaLayoutError",
    "SchemaMismatchError",
    "SchemaTypeError",
    "SchemaValueError",
    "StructDef",
    "build",
    "is_supported",
    "load",
    "load_path",
    "load_text",
    "loads",
    "resolve",
    "size_of",
]
