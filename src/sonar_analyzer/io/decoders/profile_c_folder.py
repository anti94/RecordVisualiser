"""Profil C kayıt klasörü keşfi — `F7-028`…`F7-031`.

Bir Profil C kaydı tek dosya değil, bir klasör ağacıdır: tarih klasörü
altında `Tx/` ve `Rx/` alt klasörleri, her birinde 1'er saniyelik
`TxData00000.bin` dosyaları (`docs/format/profile-c.md` §2).

Bu modül o ağacı **tanır ve okur**, açmaz. Dosyaların içeriğini
`profile_c.decode_file` çözer; burada yalnız hangi dosyaların bulunduğu,
sıralarının tutup tutmadığı ve klasörün kimliği belirlenir.

Eksik bir akım hata değildir. Yayın yapılmadan sadece dinlenen bir
oturumda `Tx/` bulunmaz; hangi akımın bulunmadığı söylenir ve kayıt
açılmaya devam eder.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from sonar_analyzer.io.schema._toml import load_path

#: Dosya adi kalibi: TxData00000.bin / RxData00599.bin
FILE_PATTERN = re.compile(r"^(?P<stream>Tx|Rx)Data(?P<counter>\d{5})\.bin$")

#: Tarih klasoru kalibi: 2026-09-12T14-30-00Z, istege bagli _2 soneki.
FOLDER_PATTERN = re.compile(
    r"^(?P<stamp>\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}Z)(?:_(?P<ordinal>\d+))?$"
)

MANIFEST_NAME = "manifest.toml"
INDEX_DIRNAME = ".sonar-index"

#: Sayacin kapasitesi: bes hane, 00000-99999.
COUNTER_CAPACITY = 100_000


class Stream(Enum):
    """Bir kayıttaki iki akım."""

    TX = "Tx"
    RX = "Rx"


class FolderError(Exception):
    """Kayıt klasörü okunamadı."""


@dataclass(frozen=True)
class StreamFile:
    """Bir akımdaki tek dosya."""

    path: Path
    stream: Stream
    counter: int

    @property
    def size_bytes(self) -> int:
        return self.path.stat().st_size


@dataclass(frozen=True)
class StreamListing:
    """Bir akımın dosyaları ve sıralarındaki sorunlar."""

    stream: Stream
    files: tuple[StreamFile, ...]
    #: Eksik sayaclar: 5 varsa 5. saniyenin dosyasi yok.
    gaps: tuple[int, ...] = ()
    #: Sayac geri gitmis mi. Bu bir sarma DEGIL, bir tutarsizliktir.
    decreasing: bool = False

    @property
    def present(self) -> bool:
        return bool(self.files)

    @property
    def first_counter(self) -> int | None:
        return self.files[0].counter if self.files else None

    @property
    def last_counter(self) -> int | None:
        return self.files[-1].counter if self.files else None

    @property
    def total_bytes(self) -> int:
        return sum(entry.size_bytes for entry in self.files)


@dataclass(frozen=True)
class RecordingFolder:
    """Keşfedilmiş bir kayıt klasörü."""

    path: Path
    streams: dict[Stream, StreamListing]
    manifest: dict[str, object] | None = None
    #: Klasor adindan cozulen baslangic damgasi; ad kalibi tutmuyorsa None.
    stamp: str | None = None
    warnings: tuple[str, ...] = ()

    @property
    def missing_streams(self) -> tuple[Stream, ...]:
        return tuple(s for s in Stream if not self.streams[s].present)

    @property
    def file_count(self) -> int:
        return sum(len(listing.files) for listing in self.streams.values())

    @property
    def total_bytes(self) -> int:
        return sum(listing.total_bytes for listing in self.streams.values())

    def listing(self, stream: Stream) -> StreamListing:
        return self.streams[stream]


def _scan_stream(folder: Path, stream: Stream) -> StreamListing:
    """Bir akımın dosyalarını sayaç sırasına göre toplar."""
    directory = folder / stream.value
    if not directory.is_dir():
        return StreamListing(stream=stream, files=())

    found: list[StreamFile] = []
    for entry in directory.iterdir():
        if not entry.is_file():
            continue
        match = FILE_PATTERN.match(entry.name)
        if match is None or match.group("stream") != stream.value:
            continue
        found.append(StreamFile(path=entry, stream=stream, counter=int(match.group("counter"))))

    # Siralama DOSYA ADINDAKI SAYACA gore; dosya sisteminin dondurdugu
    # siraya gore degil. Bes haneli sifir dolgu sayesinde sozluk sirasi da
    # ayni sonucu verirdi, ama sayiya gore siralamak dolguya bagimli olmaz.
    found.sort(key=lambda item: item.counter)

    counters = [item.counter for item in found]
    gaps = tuple(
        missing
        for previous, current in zip(counters, counters[1:])
        for missing in range(previous + 1, current)
    )
    return StreamListing(stream=stream, files=tuple(found), gaps=gaps)


def _read_manifest(folder: Path) -> tuple[dict[str, object] | None, list[str]]:
    """Manifesti okur; yoksa `None`. Bozuksa uyarı üretir, hata değil."""
    path = folder / MANIFEST_NAME
    if not path.is_file():
        return None, [f"{MANIFEST_NAME} bulunamadi; kayit bilgileri dosyalardan cikarilacak"]
    try:
        return load_path(path), []
    except Exception as error:
        return None, [f"{MANIFEST_NAME} okunamadi ({error}); dosyalar esas alinacak"]


def discover(path: Path) -> RecordingFolder:
    """Bir kayıt klasörünü keşfeder.

    `Tx/` ve `Rx/` **ikisi birden** yoksa bu bir Profil C kaydı değildir
    ve açık hata verilir. Biri yoksa kayıt açılmaya devam eder.
    """
    folder = Path(path)
    if not folder.is_dir():
        raise FolderError(f"kayit klasoru degil: {folder}")

    listings = {stream: _scan_stream(folder, stream) for stream in Stream}
    if not any(listing.present for listing in listings.values()):
        raise FolderError(
            f"{folder}: ne Tx/ ne Rx/ altinda TxDataNNNNN.bin bicimli dosya bulundu; "
            f"bu bir Profil C kayit klasoru degil"
        )

    manifest, warnings = _read_manifest(folder)

    match = FOLDER_PATTERN.match(folder.name)
    stamp = match.group("stamp") if match else None
    if stamp is None:
        warnings.append(
            f"klasor adi '{folder.name}' tarih kalibina uymuyor "
            f"(YYYY-MM-DDTHH-MM-SSZ); baslangic zamani dosyalardan okunacak"
        )

    for listing in listings.values():
        if not listing.present:
            continue
        if listing.gaps:
            warnings.append(
                f"{listing.stream.value}: {len(listing.gaps)} sayac bosluk "
                f"(ilk eksik: {listing.gaps[0]})"
            )

    return RecordingFolder(
        path=folder,
        streams=listings,
        manifest=manifest,
        stamp=stamp,
        warnings=tuple(warnings),
    )


def check_counter_sequence(listing: StreamListing) -> list[str]:
    """Sayaç sırasını denetler — `F7-029`.

    Sayaç azalarak devam ederse bu bir **sarma değil tutarsızlıktır**
    (`docs/format/profile-c.md` §2.4). Beş hane 100.000 saniyeyi kapsar;
    azami kayıt 10 dakika olduğundan sarma gerçekleşemez. Sessizce sarma
    varsaymak, karışmış iki kaydı tek kayıt gibi okuturdu.
    """
    issues: list[str] = []
    if not listing.present:
        return issues

    counters = [item.counter for item in listing.files]
    if len(set(counters)) != len(counters):
        duplicate = next(c for c in counters if counters.count(c) > 1)
        issues.append(f"{listing.stream.value}: {duplicate:05d} sayaci birden fazla dosyada")

    last = listing.last_counter
    if last is not None and last >= COUNTER_CAPACITY:
        issues.append(f"{listing.stream.value}: sayac {last} kapasiteyi ({COUNTER_CAPACITY}) asti")

    if listing.gaps:
        issues.append(
            f"{listing.stream.value}: eksik sayaclar {listing.gaps[:5]}"
            + (" ..." if len(listing.gaps) > 5 else "")
        )
    return issues


def aligned_counters(folder: RecordingFolder) -> tuple[int, ...]:
    """Tx ve Rx'in **ikisinde de** bulunan sayaçlar.

    `TxData00042.bin` ile `RxData00042.bin` aynı saniyeye aittir (§2.3).
    Yayın yapılmayan saniyede Tx dosyası üretilmez; bu yüzden kesişim
    Rx'ten küçük olabilir ve bu normaldir.
    """
    sets = [
        {item.counter for item in folder.listing(stream).files}
        for stream in Stream
        if folder.listing(stream).present
    ]
    if not sets:
        return ()
    common = sets[0]
    for other in sets[1:]:
        common &= other
    return tuple(sorted(common))
