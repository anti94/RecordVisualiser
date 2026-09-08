"""LiveSource sözleşmesi testleri — `F1-017`."""

from __future__ import annotations

import subprocess
import sys
import textwrap
from collections.abc import Iterator, Sequence

import numpy as np
import pytest

from sonar_analyzer.domain.channel import ChannelMetadata, ChannelSource
from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.io.live.protocol import (
    ConnectionState,
    LivePacket,
    LiveSource,
    LiveStats,
)

PERIOD_NS = 125_000_000


class FakeLiveSource:
    """Sözleşmeyi karşılayan en küçük gerçekleme."""

    def __init__(self, packet_count: int = 3, drop_after: int | None = None) -> None:
        self._state = ConnectionState.DISCONNECTED
        self._packet_count = packet_count
        self._drop_after = drop_after
        self._received = 0
        self._dropped = 0
        self._last_sequence: int | None = None

    @property
    def state(self) -> ConnectionState:
        return self._state

    def connect(self) -> None:
        self._state = ConnectionState.CONNECTED

    def disconnect(self) -> None:
        self._state = ConnectionState.DISCONNECTED

    def channels(self) -> Sequence[ChannelMetadata]:
        return [
            ChannelMetadata(
                id="ch0",
                path="Acoustic/Hydrophone 1",
                name="Hydrophone 1",
                dtype="float32",
                source=ChannelSource.ACOUSTIC,
                sample_rate_hz=8.0,
            )
        ]

    def packets(self) -> Iterator[LivePacket]:
        for index in range(self._packet_count):
            if self._drop_after is not None and index >= self._drop_after:
                self._dropped += 1
                continue
            self._received += 1
            self._last_sequence = index
            stamps = np.array([index * PERIOD_NS], dtype=np.int64)
            yield LivePacket(
                sequence_no=index,
                received_ns=index * PERIOD_NS,
                chunks=[
                    DataChunk(
                        channel_id="ch0",
                        timestamps_ns=stamps,
                        values=np.array([float(index)], dtype=np.float32),
                    )
                ],
            )

    def stats(self) -> LiveStats:
        return LiveStats(
            received_packets=self._received,
            dropped_packets=self._dropped,
            last_sequence_no=self._last_sequence,
        )


def test_fake_satisfies_protocol() -> None:
    assert isinstance(FakeLiveSource(), LiveSource)


def test_connection_lifecycle() -> None:
    source = FakeLiveSource()
    assert source.state is ConnectionState.DISCONNECTED
    assert not source.state.is_active

    source.connect()
    assert source.state is ConnectionState.CONNECTED
    assert source.state.is_active

    source.disconnect()
    assert source.state is ConnectionState.DISCONNECTED


def test_connect_and_disconnect_are_idempotent() -> None:
    source = FakeLiveSource()
    source.connect()
    source.connect()
    assert source.state is ConnectionState.CONNECTED
    source.disconnect()
    source.disconnect()
    assert source.state is ConnectionState.DISCONNECTED


def test_packets_yield_domain_chunks() -> None:
    source = FakeLiveSource(packet_count=3)
    source.connect()
    packets = list(source.packets())

    assert [p.sequence_no for p in packets] == [0, 1, 2]
    assert all(isinstance(chunk, DataChunk) for p in packets for chunk in p.chunks)
    assert packets[1].chunks[0].timestamps_ns[0] == PERIOD_NS


def test_dropped_packets_are_reported_not_hidden() -> None:
    source = FakeLiveSource(packet_count=5, drop_after=3)
    source.connect()
    packets = list(source.packets())

    stats = source.stats()
    assert len(packets) == 3
    assert stats.received_packets == 3
    assert stats.dropped_packets == 2
    assert stats.loss_ratio == 0.4  # 2/5 tam olarak 0.4 double'ina esit


def test_loss_ratio_without_traffic() -> None:
    assert LiveStats().loss_ratio == 0.0


def test_packet_rejects_negative_sequence() -> None:
    with pytest.raises(ValueError, match="Sira numarasi negatif"):
        LivePacket(sequence_no=-1, received_ns=0)


def test_empty_packet_is_detectable() -> None:
    assert LivePacket(sequence_no=0, received_ns=0).is_empty


def test_live_module_does_not_import_gui() -> None:
    """Sözleşme GUI bağımlılığı içermemeli (kabul kriteri)."""
    script = textwrap.dedent("""
        import importlib
        import sys

        importlib.import_module("sonar_analyzer.io.live.protocol")
        forbidden = ("PySide6", "PyQt5", "PyQt6", "shiboken6", "pyqtgraph")
        leaked = sorted(n for n in sys.modules if n.split(".")[0] in forbidden)
        print(";".join(leaked))
    """)
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "", f"GUI modulu yuklendi: {result.stdout}"
