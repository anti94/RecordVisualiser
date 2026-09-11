"""TSV ayırıcısıyla tablo dışa aktarımı — `F4-085`.

Kabul: zaman ve ondalık biçimi seçilen ayırıcıyla tutarlıdır.

Yazıcı katmanında denetlenen şey: seçilen ayırıcı gerçekten kullanılıyor
mu, sayılar seçilen ondalık ayıracıyla mı yazılıyor, ve **hiçbir satır
beklenenden fazla alana bölünüyor mu**. Sonuncusu tutarlılığın ölçüsüdür.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from sonar_analyzer.domain.channel import ChannelMetadata, ChannelSource
from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.export.csv_export import DATA_COLUMNS, METADATA_PREFIX, write_channel_csv
from sonar_analyzer.export.text_format import Delimiter, TextFormatError

S = 1_000_000_000
T0 = 1_788_901_200_000_000_000

CHANNEL = ChannelMetadata(
    id="ch0",
    path="Acoustic/Hydrophone 1",
    name="Hydrophone 1",
    dtype="float64",
    source=ChannelSource.ACOUSTIC,
    unit="Pa",
    sample_rate_hz=100.0,
)
#: Ondalık ayıracının görüneceği değerler.
VALUES = np.array([1.5, -0.25, 3.0, 1234.5678])


def _chunk() -> DataChunk:
    times = T0 + np.arange(VALUES.size, dtype=np.int64) * (S // 100)
    return DataChunk("ch0", times, VALUES.copy())


def _rows(path: Path) -> list[str]:
    """Metadata yorumları hariç satırlar."""
    text = path.read_text(encoding="utf-8")
    return [line for line in text.splitlines() if line and not line.startswith(METADATA_PREFIX)]


def _write(tmp_path: Path, **kwargs: object) -> Path:
    target = tmp_path / "cikti.txt"
    write_channel_csv(_chunk(), CHANNEL, target, **kwargs)  # type: ignore[arg-type]
    return target


# --------------------------------------------------------------------------- #
# ayirici gercekten kullanilir
# --------------------------------------------------------------------------- #


def test_the_default_export_is_comma_separated(tmp_path: Path) -> None:
    rows = _rows(_write(tmp_path))
    assert rows[0] == ",".join(DATA_COLUMNS)


def test_a_tab_export_uses_tabs(tmp_path: Path) -> None:
    rows = _rows(_write(tmp_path, delimiter=Delimiter.TAB))
    assert rows[0] == "\t".join(DATA_COLUMNS)
    assert "," not in rows[0]


def test_a_semicolon_export_uses_semicolons(tmp_path: Path) -> None:
    rows = _rows(_write(tmp_path, delimiter=Delimiter.SEMICOLON))
    assert rows[0] == ";".join(DATA_COLUMNS)


# --------------------------------------------------------------------------- #
# ONDALIK bicimi ayiriciyla tutarli
# --------------------------------------------------------------------------- #


def test_a_comma_file_writes_dotted_decimals(tmp_path: Path) -> None:
    data = _rows(_write(tmp_path, delimiter=Delimiter.COMMA))[1]
    assert data.endswith(",1.5")


def test_a_tab_file_can_write_comma_decimals(tmp_path: Path) -> None:
    data = _rows(_write(tmp_path, delimiter=Delimiter.TAB, decimal_separator=","))[1]
    assert data.endswith("\t1,5")


def test_a_semicolon_file_writes_comma_decimals_by_default(tmp_path: Path) -> None:
    """`;` seçilince ondalık geleneksel olarak virgül olur."""
    data = _rows(_write(tmp_path, delimiter=Delimiter.SEMICOLON))[1]
    assert data.endswith(";1,5")


def test_a_comma_decimal_in_a_comma_file_is_refused(tmp_path: Path) -> None:
    with pytest.raises(TextFormatError, match="alan ayırıcısıyla aynı"):
        _write(tmp_path, delimiter=Delimiter.COMMA, decimal_separator=",")


def test_nothing_is_written_when_the_format_is_refused(tmp_path: Path) -> None:
    target = tmp_path / "cikti.txt"
    with pytest.raises(TextFormatError):
        write_channel_csv(
            _chunk(), CHANNEL, target, delimiter=Delimiter.COMMA, decimal_separator=","
        )
    assert not target.exists()


# --------------------------------------------------------------------------- #
# TUTARLILIGIN olcusu: hicbir satir fazla bolunmez
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("delimiter", "decimal"),
    [
        (Delimiter.COMMA, "."),
        (Delimiter.TAB, "."),
        (Delimiter.TAB, ","),
        (Delimiter.SEMICOLON, "."),
        (Delimiter.SEMICOLON, ","),
    ],
)
def test_every_row_has_exactly_three_fields(
    tmp_path: Path, delimiter: Delimiter, decimal: str
) -> None:
    """Zaman de sayı da ayırıcıyı içermez; satır tam üç alana bölünür."""
    rows = _rows(_write(tmp_path, delimiter=delimiter, decimal_separator=decimal))
    assert len(rows) == 1 + VALUES.size
    for row in rows:
        assert len(row.split(delimiter.value)) == len(DATA_COLUMNS)


def test_no_value_is_quoted_because_none_needs_it(tmp_path: Path) -> None:
    """Alanlar ayırıcı içermediği için `csv` tırnaklama yapmaz."""
    for delimiter, decimal in ((Delimiter.TAB, ","), (Delimiter.SEMICOLON, ",")):
        rows = _rows(_write(tmp_path, delimiter=delimiter, decimal_separator=decimal))
        assert all('"' not in row for row in rows)


def test_the_iso_timestamp_keeps_a_dot_fraction(tmp_path: Path) -> None:
    """ISO damgası ondalık ayıracından etkilenmez — okuyucular bozulmasın."""
    rows = _rows(_write(tmp_path, delimiter=Delimiter.TAB, decimal_separator=","))
    iso = rows[1].split("\t")[1]
    assert "T" in iso and iso.endswith("+00:00")
    assert "," not in iso


def test_the_canonical_ns_column_is_a_plain_integer(tmp_path: Path) -> None:
    rows = _rows(_write(tmp_path, delimiter=Delimiter.TAB, decimal_separator=","))
    assert rows[1].split("\t")[0] == str(T0)


# --------------------------------------------------------------------------- #
# metadata dosyanin bicimini soyler
# --------------------------------------------------------------------------- #


def test_the_metadata_records_the_chosen_format(tmp_path: Path) -> None:
    target = _write(tmp_path, delimiter=Delimiter.TAB, decimal_separator=",")
    text = target.read_text(encoding="utf-8")
    assert f"{METADATA_PREFIX}delimiter=tab decimal=," in text


def test_the_result_reports_the_format_it_used(tmp_path: Path) -> None:
    result = write_channel_csv(
        _chunk(),
        CHANNEL,
        tmp_path / "cikti.tsv",
        delimiter=Delimiter.TAB,
        decimal_separator=",",
    )
    assert result.text_format.delimiter is Delimiter.TAB
    assert result.text_format.decimal_separator == ","


def test_values_round_trip_through_the_comma_format(tmp_path: Path) -> None:
    """Yazılan sayılar geri okunduğunda aynı değeri verir."""
    rows = _rows(_write(tmp_path, delimiter=Delimiter.TAB, decimal_separator=","))
    parsed = [float(row.split("\t")[2].replace(",", ".")) for row in rows[1:]]
    assert parsed == VALUES.tolist()
