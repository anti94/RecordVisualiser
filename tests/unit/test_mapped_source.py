"""Memory mapping üzerinden blok okuma — `F4-053`.

Kabul: seçili blok okunur; bütün dosya RAM'e kopyalanmaz.

İkinci yarı ölçülür, iddia edilmez: `tracemalloc` ile büyük bir dosyadan
küçük bir blok okurken ayrılan **Python belleği** dosya boyutunun çok
altında kalmalıdır. `mmap` sayfaları Python ayırması değildir; dosya
`read_bytes()` ile okunsaydı tepe ayırma dosya boyutu kadar olurdu.
"""

from __future__ import annotations

import struct
import tracemalloc
from pathlib import Path

import numpy as np
import pytest

from sonar_analyzer.io.readers.mapped_source import MappedSource, MappedSourceError

#: Ölçüm anlamlı olsun diye birkaç MB'lık bir kaynak.
LARGE_SIZE = 8 * 1024 * 1024
#: Okunacak blok — dosyanın yanında yok denecek kadar küçük.
BLOCK_SIZE = 4 * 1024


@pytest.fixture()
def small_file(tmp_path: Path) -> Path:
    path = tmp_path / "small.bin"
    path.write_bytes(bytes(range(256)) * 4)  # 1024 bayt, öngörülebilir içerik
    return path


@pytest.fixture()
def large_file(tmp_path: Path) -> Path:
    path = tmp_path / "large.bin"
    with path.open("wb") as handle:
        handle.write(b"\xa5" * LARGE_SIZE)
    return path


# --------------------------------------------------------------------------- #
# seçili blok okunur
# --------------------------------------------------------------------------- #


def test_the_whole_file_is_mapped(small_file: Path) -> None:
    with MappedSource(small_file) as source:
        assert source.size == 1024
        assert len(source) == 1024
        assert source.path == small_file
        assert not source.closed


def test_a_block_returns_the_requested_bytes(small_file: Path) -> None:
    expected = small_file.read_bytes()[100:164]
    with MappedSource(small_file) as source:
        block = source.block(100, 64)
        assert bytes(block) == expected
        assert len(block) == 64


def test_a_block_is_a_zero_copy_view(small_file: Path) -> None:
    with MappedSource(small_file) as source:
        block = source.block(0, 32)
        assert isinstance(block, memoryview)
        assert block.readonly
        # Görünüm dosyanın tamamını saran görünümün dilimidir — kopya değil.
        assert block.obj is source.data().obj


def test_blocks_can_be_read_out_of_order(small_file: Path) -> None:
    raw = small_file.read_bytes()
    with MappedSource(small_file) as source:
        for offset in (512, 0, 900, 256):
            assert bytes(source.block(offset, 16)) == raw[offset : offset + 16]


def test_a_block_feeds_struct_directly(small_file: Path) -> None:
    with MappedSource(small_file) as source:
        block = source.block(0, 8)
        # memoryview `unpack_from` ile doğrudan çalışır (ReadableBuffer sözleşmesi).
        first, second = struct.unpack_from("<II", block, 0)
        assert first == struct.unpack_from("<I", small_file.read_bytes(), 0)[0]
        assert second == struct.unpack_from("<I", small_file.read_bytes(), 4)[0]


def test_a_block_feeds_numpy_without_copying(small_file: Path) -> None:
    with MappedSource(small_file) as source:
        block = source.block(0, 16)
        values = np.frombuffer(block, dtype="<u1")
        assert values.shape == (16,)
        assert not values.flags.writeable  # salt okunur eşlemenin görünümü


def test_the_full_view_covers_the_file(small_file: Path) -> None:
    with MappedSource(small_file) as source:
        assert bytes(source.data()) == small_file.read_bytes()


# --------------------------------------------------------------------------- #
# bütün dosya RAM'e kopyalanmaz
# --------------------------------------------------------------------------- #


def test_reading_a_block_allocates_far_less_than_the_file(large_file: Path) -> None:
    tracemalloc.start()
    try:
        tracemalloc.reset_peak()
        with MappedSource(large_file) as source:
            block = source.block(LARGE_SIZE // 2, BLOCK_SIZE)
            assert len(block) == BLOCK_SIZE
            assert block[0] == 0xA5
            _current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    # Dosya 8 MB; blok okumak bunun yüzde birinden azını ayırmalı.
    assert peak < LARGE_SIZE // 100, f"tepe ayırma {peak} bayt, dosya {LARGE_SIZE}"


def test_read_bytes_would_allocate_the_whole_file(large_file: Path) -> None:
    """Karşılaştırma tabanı: kopyalayan yol gerçekten dosya kadar ayırıyor."""
    tracemalloc.start()
    try:
        tracemalloc.reset_peak()
        data = large_file.read_bytes()
        assert len(data) == LARGE_SIZE
        _current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    assert peak >= LARGE_SIZE


def test_many_blocks_still_allocate_little(large_file: Path) -> None:
    tracemalloc.start()
    try:
        tracemalloc.reset_peak()
        with MappedSource(large_file) as source:
            total = 0
            for index in range(64):
                block = source.block(index * BLOCK_SIZE, BLOCK_SIZE)
                total += len(block)
            assert total == 64 * BLOCK_SIZE
            _current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    assert peak < LARGE_SIZE // 100


# --------------------------------------------------------------------------- #
# sınırlar sessizce kırpılmaz
# --------------------------------------------------------------------------- #


def test_a_block_past_the_end_is_rejected(small_file: Path) -> None:
    with MappedSource(small_file) as source:
        with pytest.raises(MappedSourceError, match="dosya sonunu aşıyor"):
            source.block(1_000, 100)
        with pytest.raises(MappedSourceError, match="dosya sonunu aşıyor"):
            source.block(0, 2_000)


def test_the_last_byte_is_still_reachable(small_file: Path) -> None:
    with MappedSource(small_file) as source:
        block = source.block(source.size - 1, 1)
        assert len(block) == 1
        assert bytes(block) == small_file.read_bytes()[-1:]


def test_a_zero_length_block_is_allowed(small_file: Path) -> None:
    with MappedSource(small_file) as source:
        assert len(source.block(10, 0)) == 0


@pytest.mark.parametrize(("offset", "length"), [(-1, 4), (0, -4)])
def test_negative_bounds_are_rejected(small_file: Path, offset: int, length: int) -> None:
    with MappedSource(small_file) as source, pytest.raises(MappedSourceError, match="negatif"):
        source.block(offset, length)


# --------------------------------------------------------------------------- #
# yaşam döngüsü
# --------------------------------------------------------------------------- #


def test_closing_releases_the_mapping(small_file: Path) -> None:
    source = MappedSource(small_file)
    source.close()
    assert source.closed
    with pytest.raises(MappedSourceError, match="kapatıldı"):
        source.block(0, 4)
    with pytest.raises(MappedSourceError, match="kapatıldı"):
        _ = source.size


def test_closing_while_a_block_is_held_does_not_raise(small_file: Path) -> None:
    source = MappedSource(small_file)
    block = source.block(0, 16)

    source.close()  # dışarıda görünüm var; yine de hata vermemeli

    assert source.closed
    # Elde tutulan blok geçerli kalır: kapanış veriyi ayağın altından çekmez.
    assert bytes(block) == small_file.read_bytes()[:16]
    block.release()


def test_closing_twice_is_harmless(small_file: Path) -> None:
    source = MappedSource(small_file)
    source.close()
    source.close()
    assert source.closed


def test_the_context_manager_closes_on_exit(small_file: Path) -> None:
    with MappedSource(small_file) as source:
        assert not source.closed
    assert source.closed


def test_a_missing_file_is_reported(tmp_path: Path) -> None:
    with pytest.raises(MappedSourceError, match="açılamadı"):
        MappedSource(tmp_path / "yok.bin")


def test_an_empty_file_cannot_be_mapped(tmp_path: Path) -> None:
    empty = tmp_path / "empty.bin"
    empty.write_bytes(b"")
    with pytest.raises(MappedSourceError, match="haritalanamadı"):
        MappedSource(empty)
