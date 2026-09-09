"""Geçerli örnek `.bin` fixture yazıcısı — `F2-016`.

Kabul: sekiz kayıt tam 544 byte üretir; ad ve zamanlar sözleşmeye uyar.
Gerçek dosya G/Ç içerdiği için `tests/unit/` yerine burada.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from tools.make_fixture import VALID_8RECORDS_SHA256, build_valid_fixture, main

from sonar_analyzer.io.decoders.profile_a import iter_records
from sonar_analyzer.io.profile_a_format import record_name
from sonar_analyzer.io.readers.binary_reader import read_file_header_v1


def test_default_eight_records_produce_exactly_544_bytes() -> None:
    """Kabul kriteri: sekiz kayıt tam 544 byte üretir."""
    data = build_valid_fixture()
    assert len(data) == 544
    assert hashlib.sha256(data).hexdigest() == VALID_8RECORDS_SHA256


def test_names_and_times_conform_to_contract() -> None:
    """Kabul kriteri: ad ve zamanlar sözleşmeye uyar (record_name formülü, 125ms periyot)."""
    data = build_valid_fixture()
    header = read_file_header_v1(data)
    assert header.period_us == 125_000

    for record in iter_records(data):
        assert record.name.rstrip(b"\x00").decode("ascii") == record_name(record.sequence_no)
        assert record.elapsed_us == record.sequence_no * header.period_us


def test_cli_writes_file_to_disk(tmp_path: Path) -> None:
    out_path = tmp_path / "valid_8records.bin"

    exit_code = main(["--out", str(out_path)])

    assert exit_code == 0
    assert out_path.exists()
    assert out_path.stat().st_size == 544
    assert hashlib.sha256(out_path.read_bytes()).hexdigest() == VALID_8RECORDS_SHA256


def test_cli_with_nondefault_record_count_still_writes_valid_structure(tmp_path: Path) -> None:
    out_path = tmp_path / "small.bin"

    exit_code = main(["--out", str(out_path), "--records", "3"])

    assert exit_code == 0
    data = out_path.read_bytes()
    assert len(data) == 32 + 3 * 64
    for record in iter_records(data):
        assert record.name.rstrip(b"\x00").decode("ascii") == record_name(record.sequence_no)


def test_committed_fixture_file_matches_the_documented_hash() -> None:
    """`tests/fixtures/valid_8records.bin` gerçekten diskte ve golden ile eşleşir."""
    fixture_path = Path(__file__).resolve().parent.parent / "fixtures" / "valid_8records.bin"
    assert fixture_path.exists(), "F2-016: tools/make_fixture.py ile uretilip commitlenmeli"
    data = fixture_path.read_bytes()
    assert len(data) == 544
    assert hashlib.sha256(data).hexdigest() == VALID_8RECORDS_SHA256
