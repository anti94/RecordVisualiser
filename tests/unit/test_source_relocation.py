"""Taşınmış kaynakların yeniden konumlandırılması — `F4-078`.

Kabul: yeni konum seçimi kaynak kimliğini doğrular; yanlış dosya sessizce
bağlanmaz.

"Doğrular" ölçülebilir: aynı dosyanın kopyası kabul edilir; boyutu,
başlangıcı ya da sonu farklı bir dosya **her biri için ayrı bir nedenle**
reddedilir. "Sessizce bağlanmaz" da ölçülebilir: red bir istisnadır,
nedeni mesajda yazar ve model hiç değişmez.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from sonar_analyzer.workspace.source_identity import (
    DEFAULT_SAMPLE_BYTES,
    IDENTITY_SCHEMA_VERSION,
    RelocationError,
    SourceIdentity,
    identity_for_path,
    verify_relocation,
)

SAMPLE = 64


def _write(path: Path, data: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def _recording(tmp_path: Path, name: str = "kayit.bin", *, seed: int = 0) -> Path:
    """Baş ve son bölümleri ayırt edilebilir sahte bir kayıt."""
    body = bytes((index + seed) % 256 for index in range(1024))
    return _write(tmp_path / name, body)


# --------------------------------------------------------------------------- #
# kimlik olcusu
# --------------------------------------------------------------------------- #


def test_an_identity_records_size_and_two_digests(tmp_path: Path) -> None:
    identity = identity_for_path(_recording(tmp_path), sample_bytes=SAMPLE)
    assert identity.size_bytes == 1024
    assert len(identity.head_sha256) == 64
    assert len(identity.tail_sha256) == 64
    assert identity.sample_bytes == SAMPLE


def test_the_digests_cover_the_first_and_last_bytes(tmp_path: Path) -> None:
    """Ölçünün ne olduğu belgelenmiş: baştan ve sondan `sample_bytes`."""
    source = _recording(tmp_path)
    data = source.read_bytes()
    identity = identity_for_path(source, sample_bytes=SAMPLE)
    assert identity.head_sha256 == hashlib.sha256(data[:SAMPLE]).hexdigest()
    assert identity.tail_sha256 == hashlib.sha256(data[-SAMPLE:]).hexdigest()


def test_the_cost_does_not_depend_on_the_file_size(tmp_path: Path) -> None:
    """Büyük dosyada da yalnız `2 * sample_bytes` okunur."""
    big = _write(tmp_path / "buyuk.bin", b"A" * SAMPLE + b"B" * 100_000 + b"C" * SAMPLE)
    identity = identity_for_path(big, sample_bytes=SAMPLE)
    assert identity.head_sha256 == hashlib.sha256(b"A" * SAMPLE).hexdigest()
    assert identity.tail_sha256 == hashlib.sha256(b"C" * SAMPLE).hexdigest()
    # Ortadaki 100 KB hic hash'lenmedi: ayni uclarla farkli orta ayni kimligi verir.
    other = _write(tmp_path / "baska.bin", b"A" * SAMPLE + b"X" * 100_000 + b"C" * SAMPLE)
    assert identity_for_path(other, sample_bytes=SAMPLE).head_sha256 == identity.head_sha256


def test_a_short_file_overlaps_its_samples_without_error(tmp_path: Path) -> None:
    short = _write(tmp_path / "kisa.bin", b"abc")
    identity = identity_for_path(short, sample_bytes=SAMPLE)
    assert identity.size_bytes == 3
    assert identity.head_sha256 == identity.tail_sha256 == hashlib.sha256(b"abc").hexdigest()


def test_an_empty_file_still_has_an_identity(tmp_path: Path) -> None:
    identity = identity_for_path(_write(tmp_path / "bos.bin", b""), sample_bytes=SAMPLE)
    assert identity.size_bytes == 0


def test_a_missing_file_is_reported(tmp_path: Path) -> None:
    with pytest.raises(RelocationError, match="Kaynak okunamadı"):
        identity_for_path(tmp_path / "yok.bin", sample_bytes=SAMPLE)


@pytest.mark.parametrize("bad", [0, -1])
def test_a_nonpositive_sample_size_is_refused(tmp_path: Path, bad: int) -> None:
    with pytest.raises(RelocationError, match="Örnek boyutu pozitif"):
        identity_for_path(_recording(tmp_path), sample_bytes=bad)


def test_the_default_sample_is_one_mebibyte() -> None:
    assert DEFAULT_SAMPLE_BYTES == 1024 * 1024


# --------------------------------------------------------------------------- #
# esitlik ve uyusmazlik nedeni
# --------------------------------------------------------------------------- #


def test_a_copy_of_the_same_file_matches(tmp_path: Path) -> None:
    source = _recording(tmp_path)
    moved = _write(tmp_path / "yeni" / "kayit.bin", source.read_bytes())
    expected = identity_for_path(source, sample_bytes=SAMPLE)
    assert expected.matches(identity_for_path(moved, sample_bytes=SAMPLE))
    assert expected.describe_mismatch(identity_for_path(moved, sample_bytes=SAMPLE)) == ""


def test_a_different_size_is_explained(tmp_path: Path) -> None:
    expected = identity_for_path(_recording(tmp_path), sample_bytes=SAMPLE)
    other = identity_for_path(_write(tmp_path / "kisa.bin", b"\x00" * 512), sample_bytes=SAMPLE)
    assert not expected.matches(other)
    assert "dosya boyutu farklı" in expected.describe_mismatch(other)
    assert "1024" in expected.describe_mismatch(other)


def test_a_different_head_is_explained(tmp_path: Path) -> None:
    source = _recording(tmp_path)
    data = bytearray(source.read_bytes())
    data[0] ^= 0xFF
    other = identity_for_path(_write(tmp_path / "b.bin", bytes(data)), sample_bytes=SAMPLE)
    expected = identity_for_path(source, sample_bytes=SAMPLE)
    assert "dosya başlangıcı farklı" in expected.describe_mismatch(other)


def test_a_different_tail_is_explained(tmp_path: Path) -> None:
    source = _recording(tmp_path)
    data = bytearray(source.read_bytes())
    data[-1] ^= 0xFF
    other = identity_for_path(_write(tmp_path / "b.bin", bytes(data)), sample_bytes=SAMPLE)
    expected = identity_for_path(source, sample_bytes=SAMPLE)
    assert "dosya sonu farklı" in expected.describe_mismatch(other)


def test_identities_sampled_differently_cannot_be_compared(tmp_path: Path) -> None:
    source = _recording(tmp_path)
    assert "karşılaştırılamaz" in identity_for_path(source, sample_bytes=32).describe_mismatch(
        identity_for_path(source, sample_bytes=64)
    )


# --------------------------------------------------------------------------- #
# dogrulama: yanlis dosya SESSIZCE baglanmaz
# --------------------------------------------------------------------------- #


def test_the_same_recording_in_a_new_folder_is_accepted(tmp_path: Path) -> None:
    source = _recording(tmp_path)
    expected = identity_for_path(source, sample_bytes=SAMPLE)
    moved = _write(tmp_path / "arsiv" / "kayit.bin", source.read_bytes())
    assert verify_relocation(expected, moved).matches(expected)


def test_a_renamed_but_identical_file_is_accepted(tmp_path: Path) -> None:
    """Ad değil, içerik önemlidir."""
    source = _recording(tmp_path)
    expected = identity_for_path(source, sample_bytes=SAMPLE)
    renamed = _write(tmp_path / "bambaska-ad.bin", source.read_bytes())
    assert verify_relocation(expected, renamed) is not None


def test_a_wrong_file_is_refused_with_a_reason(tmp_path: Path) -> None:
    expected = identity_for_path(_recording(tmp_path), sample_bytes=SAMPLE)
    wrong = _recording(tmp_path, "baska.bin", seed=7)
    with pytest.raises(RelocationError) as error:
        verify_relocation(expected, wrong)
    message = str(error.value)
    assert "baska.bin" in message
    assert "yerine konamaz" in message
    assert "farklı" in message


def test_a_truncated_file_is_refused(tmp_path: Path) -> None:
    source = _recording(tmp_path)
    expected = identity_for_path(source, sample_bytes=SAMPLE)
    truncated = _write(tmp_path / "kirpik.bin", source.read_bytes()[:-1])
    with pytest.raises(RelocationError, match="dosya boyutu farklı"):
        verify_relocation(expected, truncated)


def test_a_file_that_is_not_there_is_refused(tmp_path: Path) -> None:
    expected = identity_for_path(_recording(tmp_path), sample_bytes=SAMPLE)
    with pytest.raises(RelocationError, match="Kaynak okunamadı"):
        verify_relocation(expected, tmp_path / "hic-yok.bin")


def test_verification_uses_the_recorded_sample_size(tmp_path: Path) -> None:
    """Doğrulama kaydedilmiş ölçüyle yapılır; aksi hâlde hep uyuşmazdı."""
    source = _recording(tmp_path)
    expected = identity_for_path(source, sample_bytes=32)
    moved = _write(tmp_path / "yeni.bin", source.read_bytes())
    assert verify_relocation(expected, moved).sample_bytes == 32


# --------------------------------------------------------------------------- #
# gecerlilik ve serilestirme
# --------------------------------------------------------------------------- #


def test_an_identity_round_trips(tmp_path: Path) -> None:
    identity = identity_for_path(_recording(tmp_path), sample_bytes=SAMPLE)
    restored = SourceIdentity.from_dict(json.loads(json.dumps(identity.to_dict())))
    assert restored == identity


def test_the_serialised_form_names_its_schema_version(tmp_path: Path) -> None:
    payload = identity_for_path(_recording(tmp_path), sample_bytes=SAMPLE).to_dict()
    assert payload["schema_version"] == IDENTITY_SCHEMA_VERSION == 1
    assert set(payload) == {
        "schema_version",
        "size_bytes",
        "head_sha256",
        "tail_sha256",
        "sample_bytes",
    }


def test_an_unknown_identity_schema_is_refused(tmp_path: Path) -> None:
    payload = identity_for_path(_recording(tmp_path), sample_bytes=SAMPLE).to_dict()
    payload["schema_version"] = 99
    with pytest.raises(RelocationError, match="Desteklenmeyen kaynak kimliği şeması"):
        SourceIdentity.from_dict(payload)


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("size_bytes", "1024", "size_bytes tam sayı"),
        ("size_bytes", True, "size_bytes tam sayı"),
        ("head_sha256", 5, "head_sha256 metin"),
        ("tail_sha256", None, "tail_sha256 metin"),
        ("sample_bytes", "64", "sample_bytes tam sayı"),
    ],
)
def test_a_malformed_identity_field_is_refused(
    tmp_path: Path, field_name: str, value: object, message: str
) -> None:
    payload = identity_for_path(_recording(tmp_path), sample_bytes=SAMPLE).to_dict()
    payload[field_name] = value
    with pytest.raises(RelocationError, match=message):
        SourceIdentity.from_dict(payload)


def test_a_non_object_identity_is_refused() -> None:
    with pytest.raises(RelocationError, match="bir nesne olmalı"):
        SourceIdentity.from_dict(["not", "an", "object"])


def test_a_negative_size_is_refused() -> None:
    with pytest.raises(RelocationError, match="negatif olamaz"):
        SourceIdentity(size_bytes=-1, head_sha256="a" * 64, tail_sha256="b" * 64)


@pytest.mark.parametrize("digest", ["", "abc", "z" * 63])
def test_a_malformed_digest_is_refused(digest: str) -> None:
    with pytest.raises(RelocationError, match="64 haneli sha256"):
        SourceIdentity(size_bytes=1, head_sha256=digest, tail_sha256="b" * 64)
