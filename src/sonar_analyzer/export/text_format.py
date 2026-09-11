"""Metin tablo dışa aktarımının ayırıcı ve sayı biçimi — `F4-085`.

CSV ve TSV aynı yazıcıyı paylaşır; fark yalnız **alan ayırıcısıdır**. Ama
ayırıcıyı değiştirmek sayı biçimini de ilgilendirir: bazı yerelleştirmeler
ondalık ayıracı olarak virgül kullanır ve virgülle ayrılmış bir dosyada
virgüllü bir sayı satırı bozar.

Bu modül o tutarlılığı **zorunlu** kılar:

* Ondalık ayıracı alan ayırıcısıyla **aynı olamaz**. `;` ile ayrılmış bir
  dosyada `1,5` yazmak güvenlidir; `,` ile ayrılmış dosyada değildir ve
  reddedilir.
* Alan ayırıcısı, yazılan **zaman** gösterimlerinde geçemez. Kanonik ns
  düz bir tam sayıdır; UTC damgası ISO-8601'dir ve `-`, `:`, `.`, `T`,
  `+` taşır. Bu yüzden `:` gibi bir ayırıcı reddedilir — tarih alanını
  ikiye bölerdi.

ISO damgasının saniye kesri **her zaman** nokta ile yazılır; ondalık
ayıracı virgül olsa bile değişmez. ISO-8601 ikisine de izin verir ama
ayıracı değiştirmek okuyucuların çoğunu bozar; sayı alanı ile zaman alanı
burada bilinçli olarak ayrı sözleşmelere tabidir ve bu belgelenmiştir.

Saf Python — Qt yok, `GUI olmadan` doğrulanır.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

#: ISO-8601 damgasında geçebilen karakterler; ayırıcı bunlardan olamaz.
ISO_TIMESTAMP_CHARACTERS = frozenset("0123456789-:.T+Z")


class TextFormatError(ValueError):
    """Ayırıcı ve sayı biçimi birlikte tutarsız."""


class Delimiter(str, Enum):
    """Desteklenen alan ayırıcıları."""

    COMMA = ","
    TAB = "\t"
    SEMICOLON = ";"

    @property
    def label(self) -> str:
        return {"COMMA": "Virgül (,)", "TAB": "Sekme (TSV)", "SEMICOLON": "Noktalı virgül (;)"}[
            self.name
        ]


#: Her ayırıcının geleneksel ondalık ayıracı.
DEFAULT_DECIMAL: dict[Delimiter, str] = {
    Delimiter.COMMA: ".",
    Delimiter.TAB: ".",
    # `;` Avrupa CSV geleneğidir ve tam da virgüllü ondalık için kullanılır.
    Delimiter.SEMICOLON: ",",
}


@dataclass(frozen=True)
class TextFormat:
    """Doğrulanmış ayırıcı + ondalık ayıracı çifti."""

    delimiter: Delimiter
    decimal_separator: str

    def __post_init__(self) -> None:
        if self.decimal_separator not in {".", ","}:
            raise TextFormatError(
                f"Ondalık ayıracı '.' ya da ',' olmalı; verilen {self.decimal_separator!r}"
            )
        if self.decimal_separator == self.delimiter.value:
            raise TextFormatError(
                f"Ondalık ayıracı alan ayırıcısıyla aynı olamaz ({self.delimiter.value!r}); "
                f"sayılar satırı bölerdi"
            )
        if set(self.delimiter.value) & ISO_TIMESTAMP_CHARACTERS:
            raise TextFormatError(
                f"Alan ayırıcısı {self.delimiter.value!r} zaman damgasında geçiyor; "
                f"tarih alanı bölünürdü"
            )

    @property
    def uses_comma_decimal(self) -> bool:
        return self.decimal_separator == ","

    def format_value(self, value: float) -> str:
        """Bir ölçüm değerini seçilen ondalık ayıracıyla yazar.

        Hassasiyet korunur: `repr` ile tam gösterim üretilir, yalnız
        ayıraç değiştirilir. Böylece virgüllü biçim veriyi yuvarlamaz.
        """
        text = repr(float(value))
        return text.replace(".", ",") if self.uses_comma_decimal else text

    def describe(self) -> str:
        """Metadata satırına yazılacak tek satırlık özet."""
        name = "tab" if self.delimiter is Delimiter.TAB else self.delimiter.value
        return f"delimiter={name} decimal={self.decimal_separator}"


def resolve_format(
    delimiter: Delimiter = Delimiter.COMMA,
    decimal_separator: str | None = None,
) -> TextFormat:
    """Ayırıcıya uygun, doğrulanmış bir biçim döndürür.

    `decimal_separator` verilmezse ayırıcının geleneksel karşılığı
    kullanılır; verilirse çakışma **reddedilir**, sessizce düzeltilmez.
    """
    chosen = DEFAULT_DECIMAL[delimiter] if decimal_separator is None else decimal_separator
    return TextFormat(delimiter=delimiter, decimal_separator=chosen)
