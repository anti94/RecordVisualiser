"""Çoklu kaydı ayrı kimliklerle yönetme — F2-036."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from sonar_analyzer.domain.channel import ChannelMetadata
from sonar_analyzer.domain.data_chunk import DataChunk
from sonar_analyzer.domain.event import Event
from sonar_analyzer.domain.recording import RecordingMetadata
from sonar_analyzer.domain.time_range import TimeRange
from sonar_analyzer.repository.file_repository import FileRecordingRepository
from sonar_analyzer.repository.protocol import EventFilter


@dataclass(frozen=True)
class RecordingEvent:
    """Olayın kendi source/kategori alanlarını değiştirmeden kaynak kaydı taşır."""

    recording_id: str
    event: Event

    @property
    def key(self) -> tuple[str, int, int | None, str, str, str]:
        return (
            self.recording_id,
            self.event.timestamp_ns,
            self.event.source_offset,
            self.event.source,
            self.event.code,
            self.event.message,
        )


class RecordingCollection:
    """Birden fazla dosyanın sahibi; tek dosya repository sözleşmesini değiştirmez."""

    def __init__(self) -> None:
        self._recordings: dict[str, FileRecordingRepository] = {}

    def open(self, path: Path) -> str:
        repository = FileRecordingRepository()
        repository.open(path)
        identifier = repository.metadata().recording_id
        previous = self._recordings.get(identifier)
        self._recordings[identifier] = repository
        if previous is not None:
            previous.close()
        return identifier

    def get(self, recording_id: str) -> FileRecordingRepository:
        try:
            return self._recordings[recording_id]
        except KeyError as exc:
            raise KeyError(f"Acik kayit bulunamadi: {recording_id}") from exc

    def recordings(self) -> tuple[RecordingMetadata, ...]:
        return tuple(repository.metadata() for repository in self._recordings.values())

    def channels(self) -> tuple[ChannelMetadata, ...]:
        return tuple(
            replace(channel, id=f"{identifier}:{channel.id}")
            for identifier, repository in self._recordings.items()
            for channel in repository.channels()
        )

    def query(
        self,
        channel_id: str,
        time_range: TimeRange,
        max_points: int | None = None,
    ) -> DataChunk:
        identifier, separator, local_id = channel_id.partition(":")
        if not separator or not local_id:
            raise KeyError(f"Kayit kimligi icermeyen kanal: {channel_id}")
        chunk = self.get(identifier).query(local_id, time_range, max_points)
        return replace(chunk, channel_id=channel_id)

    def events(
        self,
        time_range: TimeRange,
        filters: EventFilter | None = None,
    ) -> tuple[RecordingEvent, ...]:
        items = [
            RecordingEvent(identifier, event)
            for identifier, repository in self._recordings.items()
            for event in repository.events(time_range, filters)
        ]
        return tuple(sorted(items, key=lambda item: (item.event.timestamp_ns, item.recording_id)))

    def close(self, recording_id: str) -> None:
        repository = self.get(recording_id)
        repository.close()
        del self._recordings[recording_id]

    def close_all(self) -> None:
        for identifier in tuple(self._recordings):
            self.close(identifier)
