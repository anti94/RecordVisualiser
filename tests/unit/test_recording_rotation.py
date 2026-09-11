"""Boyut ve isim sınırında yeni dosyaya geçiş — `F5-031`.

Kabul: **Yeni dosyanın başlangıç zamanı ve sıra başlangıcı kendi içinde
tutarlıdır.**

"Kendi içinde tutarlı" burada ölçülebilir bir şeye indirgenir: her dosya
**tek başına**, önceki dosyaya hiç bakmadan üretim okuyucusuyla açılır ve

    header.start_time_utc_ns + record.elapsed_us × 1000

her kayıt için o kaydın **gerçek** mutlak zamanını verir. Gerçek zaman
testin kendi ürettiği paketlerden bilinir, yazıcıdan değil — yoksa test
yalnız kodun kendisiyle tutarlı olduğunu söylerdi.

Ayrıca ızgara sürekliliği ayrıca doğrulanır: dosyalar birleştirildiğinde
zaman dizisi 125 ms'lik tek bir ızgarada kalır, dosya başına kaymaz.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.time_range import RECORD_PERIOD_NS
from sonar_analyzer.io.live.protocol import LivePacket
from sonar_analyzer.io.profile_a_format import DATA_RECORD_V2, FILE_HEADER_V2
from sonar_analyzer.io.readers.binary_reader import read_data_record_v2
from sonar_analyzer.io.readers.recording_reader import read_validated_header
from sonar_analyzer.recording.rotation import (
    MAX_SEQUENCE_NO,
    RotatingRecorder,
    RotationPolicy,
)
from sonar_analyzer.recording.session import RecordingSession

START_NS = 1_788_901_200_000_000_000
CHANNELS = [f"ch{index}" for index in range(8)]
HEADER_BYTES = FILE_HEADER_V2.size  # 36
RECORD_BYTES = DATA_RECORD_V2.size  # 68


def _packet(window: int) -> LivePacket:
    """`window`. 125 ms penceresinde 8 kanaldan birer örnek taşıyan paket."""
    at_ns = START_NS + window * RECORD_PERIOD_NS
    chunks = [
        DataChunk(
            channel_id,
            np.array([at_ns], dtype=np.int64),
            np.array([float(window)], dtype=np.float64),
        )
        for channel_id in CHANNELS
    ]
    return LivePacket(sequence_no=window, received_ns=at_ns, chunks=chunks)


def _recorder(tmp_path: Path, policy: RotationPolicy) -> RotatingRecorder:
    """Boş alan kontrolünü sabitlenmiş, gerçek diske yazan yazıcı."""

    def session_factory(path: Path) -> RecordingSession:
        return RecordingSession(path, free_space=lambda _p: 1 << 40)

    return RotatingRecorder(
        tmp_path, "kayit", CHANNELS, policy=policy, session_factory=session_factory
    )


def _absolute_times(path: Path) -> list[int]:
    """Dosyayı **tek başına** okuyup her kaydın mutlak zamanını hesaplar.

    Kullanılan tek girdi dosyanın kendisidir: başlıktaki başlangıç zamanı
    artı kaydın `elapsed_us`'u. Başka bir dosyaya ya da yazıcının iç
    durumuna bakılmaz.
    """
    raw = path.read_bytes()
    header = read_validated_header(raw)
    body = len(raw) - HEADER_BYTES
    assert body % RECORD_BYTES == 0
    times: list[int] = []
    for index in range(body // RECORD_BYTES):
        record = read_data_record_v2(raw, HEADER_BYTES + index * RECORD_BYTES)
        times.append(header.start_time_utc_ns + record.elapsed_us * 1000)
    return times


def _sequences(path: Path) -> list[int]:
    raw = path.read_bytes()
    body = len(raw) - HEADER_BYTES
    return [
        read_data_record_v2(raw, HEADER_BYTES + index * RECORD_BYTES).sequence_no
        for index in range(body // RECORD_BYTES)
    ]


def _names(path: Path) -> list[str]:
    raw = path.read_bytes()
    body = len(raw) - HEADER_BYTES
    return [
        read_data_record_v2(raw, HEADER_BYTES + index * RECORD_BYTES)
        .name.rstrip(b"\x00")
        .decode("ascii")
        for index in range(body // RECORD_BYTES)
    ]


# --------------------------------------------------------------------------- #
# BOYUT SINIRI
# --------------------------------------------------------------------------- #


def test_the_file_never_grows_past_the_size_limit(tmp_path: Path) -> None:
    """Sınır aşılmadan önce geçilir; hiçbir dosya sınırı aşmaz."""
    limit = HEADER_BYTES + 5 * RECORD_BYTES
    recorder = _recorder(tmp_path, RotationPolicy(max_bytes=limit))
    for window in range(23):
        recorder.accept(_packet(window))
    recorder.stop()

    for path in recorder.paths:
        assert path.stat().st_size <= limit


def test_the_size_limit_splits_the_run_into_the_expected_files(tmp_path: Path) -> None:
    limit = HEADER_BYTES + 5 * RECORD_BYTES
    recorder = _recorder(tmp_path, RotationPolicy(max_bytes=limit))
    for window in range(23):
        recorder.accept(_packet(window))
    recorder.stop()

    assert len(recorder.paths) == 5  # 5+5+5+5+3
    counts = [(path.stat().st_size - HEADER_BYTES) // RECORD_BYTES for path in recorder.paths]
    assert counts == [5, 5, 5, 5, 3]
    assert recorder.rotation_count == 4


def test_no_record_is_lost_across_the_rotation(tmp_path: Path) -> None:
    """Bölünme veri kaybettirmez: toplam kayıt sayısı üretilenle aynı."""
    recorder = _recorder(tmp_path, RotationPolicy(max_bytes=HEADER_BYTES + 4 * RECORD_BYTES))
    for window in range(30):
        recorder.accept(_packet(window))
    recorder.stop()

    total = sum(len(_absolute_times(path)) for path in recorder.paths)
    assert total == 30


# --------------------------------------------------------------------------- #
# YENI DOSYA KENDI ICINDE TUTARLIDIR
# --------------------------------------------------------------------------- #


def test_each_file_starts_at_sequence_zero(tmp_path: Path) -> None:
    recorder = _recorder(tmp_path, RotationPolicy(max_bytes=HEADER_BYTES + 4 * RECORD_BYTES))
    for window in range(14):
        recorder.accept(_packet(window))
    recorder.stop()

    for path in recorder.paths:
        assert _sequences(path)[0] == 0
        assert _names(path)[0] == "Data00000"


def test_every_file_resolves_its_own_records_to_the_right_absolute_time(
    tmp_path: Path,
) -> None:
    """Asıl kabul: her dosya tek başına doğru mutlak zamanları verir."""
    recorder = _recorder(tmp_path, RotationPolicy(max_bytes=HEADER_BYTES + 4 * RECORD_BYTES))
    for window in range(14):
        recorder.accept(_packet(window))
    recorder.stop()

    # Testin kendi urettigi gercek zamanlar — yaziciya sorulmadi.
    expected = [START_NS + window * RECORD_PERIOD_NS for window in range(14)]
    decoded: list[int] = []
    for path in recorder.paths:
        decoded.extend(_absolute_times(path))
    assert decoded == expected


def test_the_new_file_header_time_is_the_window_start_of_its_first_record(
    tmp_path: Path,
) -> None:
    """Başlangıç zamanı 125 ms ızgarasının bir noktasıdır, paket varış anı değil."""
    recorder = _recorder(tmp_path, RotationPolicy(max_bytes=HEADER_BYTES + 4 * RECORD_BYTES))
    for window in range(12):
        recorder.accept(_packet(window))
    recorder.stop()

    starts = [read_validated_header(path.read_bytes()).start_time_utc_ns for path in recorder.paths]
    assert starts == [START_NS + offset * RECORD_PERIOD_NS for offset in (0, 4, 8)]
    for start in starts:
        assert (start - START_NS) % RECORD_PERIOD_NS == 0  # izgara kaymadi


def test_a_gap_does_not_shift_the_new_file_off_the_grid(tmp_path: Path) -> None:
    """Paket kaybı olsa da yeni dosyanın çapası ızgarada kalır."""
    recorder = _recorder(tmp_path, RotationPolicy(max_bytes=HEADER_BYTES + 3 * RECORD_BYTES))
    for window in (0, 1, 2, 7, 8, 9, 20):  # 3..6 ve 10..19 hic gelmedi
        recorder.accept(_packet(window))
    recorder.stop()

    expected = [START_NS + window * RECORD_PERIOD_NS for window in (0, 1, 2, 7, 8, 9, 20)]
    decoded: list[int] = []
    for path in recorder.paths:
        decoded.extend(_absolute_times(path))
    assert decoded == expected


def test_a_gap_inside_a_file_keeps_the_sequence_derived_from_time(tmp_path: Path) -> None:
    """Dosya içindeki boşluk sırayı atlatır; sayaç gibi 1'er artmaz."""
    recorder = _recorder(tmp_path, RotationPolicy(max_bytes=HEADER_BYTES + 10 * RECORD_BYTES))
    for window in (0, 1, 5):
        recorder.accept(_packet(window))
    recorder.stop()

    assert _sequences(recorder.paths[0]) == [0, 1, 5]
    assert _names(recorder.paths[0])[2] == "Data00005"


# --------------------------------------------------------------------------- #
# ISIM SINIRI
# --------------------------------------------------------------------------- #


def test_the_name_limit_triggers_a_new_file(tmp_path: Path) -> None:
    """Sıra numarası ad sınırını aşacaksa yeni dosyaya geçilir."""
    policy = RotationPolicy(max_bytes=1 << 30, max_sequence_no=3)
    recorder = _recorder(tmp_path, policy)
    for window in range(9):
        recorder.accept(_packet(window))
    recorder.stop()

    assert len(recorder.paths) == 3  # 0..3, 4..7, 8
    assert _sequences(recorder.paths[0]) == [0, 1, 2, 3]
    assert _sequences(recorder.paths[1]) == [0, 1, 2, 3]
    assert _sequences(recorder.paths[2]) == [0]


def test_the_name_limit_keeps_absolute_time_correct(tmp_path: Path) -> None:
    policy = RotationPolicy(max_bytes=1 << 30, max_sequence_no=3)
    recorder = _recorder(tmp_path, policy)
    for window in range(9):
        recorder.accept(_packet(window))
    recorder.stop()

    decoded: list[int] = []
    for path in recorder.paths:
        decoded.extend(_absolute_times(path))
    assert decoded == [START_NS + window * RECORD_PERIOD_NS for window in range(9)]


def test_a_long_gap_past_the_name_limit_rotates_immediately(tmp_path: Path) -> None:
    """Uzun bir boşluktan sonra sıra sınırı aşarsa hemen yeni dosya açılır."""
    policy = RotationPolicy(max_bytes=1 << 30, max_sequence_no=5)
    recorder = _recorder(tmp_path, policy)
    recorder.accept(_packet(0))
    recorder.accept(_packet(900))  # sira 900 > 5
    recorder.stop()

    assert len(recorder.paths) == 2
    assert _sequences(recorder.paths[1]) == [0]
    assert _absolute_times(recorder.paths[1]) == [START_NS + 900 * RECORD_PERIOD_NS]


def test_the_default_name_limit_matches_the_char12_field(tmp_path: Path) -> None:
    """`Data9999999` + sonlandırıcı sıfır tam 12 bayttır."""
    assert len(f"Data{MAX_SEQUENCE_NO:05d}") == 11
    assert RotationPolicy().max_sequence_no == MAX_SEQUENCE_NO


def test_a_name_limit_larger_than_the_field_is_refused() -> None:
    with pytest.raises(ValueError, match="ad alanina sigmaz"):
        RotationPolicy(max_sequence_no=MAX_SEQUENCE_NO + 1)


def test_a_non_positive_size_limit_is_refused() -> None:
    with pytest.raises(ValueError, match="max_bytes pozitif olmali"):
        RotationPolicy(max_bytes=0)


# --------------------------------------------------------------------------- #
# dosya adlari, sonuclar ve sinir durumlari
# --------------------------------------------------------------------------- #


def test_the_files_are_numbered_in_the_order_they_were_opened(tmp_path: Path) -> None:
    recorder = _recorder(tmp_path, RotationPolicy(max_bytes=HEADER_BYTES + 2 * RECORD_BYTES))
    for window in range(6):
        recorder.accept(_packet(window))
    recorder.stop()

    assert [path.name for path in recorder.paths] == [
        "kayit_001.bin",
        "kayit_002.bin",
        "kayit_003.bin",
    ]


def test_stop_reports_an_outcome_for_every_file(tmp_path: Path) -> None:
    recorder = _recorder(tmp_path, RotationPolicy(max_bytes=HEADER_BYTES + 2 * RECORD_BYTES))
    for window in range(6):
        recorder.accept(_packet(window))
    outcomes = recorder.stop()

    assert len(outcomes) == len(recorder.paths) == 3
    assert all(outcome.succeeded for outcome in outcomes)
    assert sum(outcome.record_count for outcome in outcomes) == 6


def test_an_empty_packet_opens_no_file(tmp_path: Path) -> None:
    """Örnek taşımayan paket kayıt üretmez ve dosya açtırmaz."""
    recorder = _recorder(tmp_path, RotationPolicy())
    assert recorder.accept(LivePacket(sequence_no=0, received_ns=START_NS)) is None

    assert recorder.paths == []
    assert recorder.current_path is None
    assert recorder.stop() == []


def test_the_recorder_reports_the_open_file_while_recording(tmp_path: Path) -> None:
    recorder = _recorder(tmp_path, RotationPolicy(max_bytes=HEADER_BYTES + 4 * RECORD_BYTES))
    try:
        for window in range(3):
            recorder.accept(_packet(window))
        assert recorder.current_path is not None
        assert recorder.current_path.name == "kayit_001.bin"
        assert recorder.current_start_time_utc_ns == START_NS
        assert recorder.current_record_count == 3
    finally:
        recorder.stop()
    assert recorder.current_path is None


def test_an_empty_base_name_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="base_name bos olamaz"):
        RotatingRecorder(tmp_path, "", CHANNELS)


def test_a_packet_before_the_file_anchor_is_refused(tmp_path: Path) -> None:
    """Saat geriye giderse sessizce yanlış dosyaya yazılmaz."""
    recorder = _recorder(tmp_path, RotationPolicy())
    recorder.accept(_packet(5))
    try:
        with pytest.raises(ValueError, match="Zaman kayit baslangicindan once"):
            recorder.accept(_packet(0))
    finally:
        recorder.stop()
