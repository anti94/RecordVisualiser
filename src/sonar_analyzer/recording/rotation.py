"""Boyut ve isim sınırında yeni dosyaya geçiş — `F5-031`.

Kabul: **Yeni dosyanın başlangıç zamanı ve sıra başlangıcı kendi içinde
tutarlıdır.**

Uzun bir kayıt tek dosyada tutulamaz; iki sınır vardır:

* **Boyut** — dosya `RotationPolicy.max_bytes`'ı aşacaksa yeni dosyaya
  geçilir. Sınır *aşılmadan önce* kontrol edilir: sınırı aşan bir kayıt
  yazılıp sonra bölünseydi dosya sözü verilen boyutu tutmazdı.
* **İsim** — `docs/format/timing-and-naming.md` §2: ad sarmaz ve
  `char[12]` alanı en fazla `Data9999999` taşır. Sıra numarası bu sınıra
  dayandığında yeni dosya açılır.

Tutarlılık kuralı
-----------------

Yeni dosya, kendi ilk kaydının **pencere başlangıcına** çapalanır:

    yeni_baslangic = eski_baslangic + sira × RECORD_PERIOD_NS

Bu iki şeyi aynı anda sağlar:

1. *Kendi içinde tutarlılık*: yeni dosyanın ilk kaydı `Data00000` ve
   `elapsed_us = 0`'dır; `header.start_time_utc_ns + elapsed_us` o kaydın
   gerçek zamanını verir. Dosya tek başına, önceki dosyaya bakmadan
   doğru okunur.
2. *Izgara sürekliliği*: yeni çapa 125 ms ızgarasının bir noktasıdır,
   çünkü eski çapadan tam katı kadar uzaktır. Çapayı "ilk paketin geldiği
   an" yapmak ızgarayı dosya başına kaydırır ve iki dosyanın zamanları
   birbirini tutmazdı.

Sıra numarası her dosyada sıfırdan başlar; ad bir **etikettir** ve dosya
içinde benzersizdir (aynı belge §2). Dosyalar arası sıra devamlılığı
mutlak zamandan kurulur, addan değil.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from sonar_analyzer.domain.time_range import RECORD_PERIOD_NS
from sonar_analyzer.io.live.protocol import LivePacket
from sonar_analyzer.recording.accumulator import PendingRecord, RecordAccumulator
from sonar_analyzer.recording.header_writer import (
    DEFAULT_FORMAT_VERSION,
    build_file_header,
    header_size_for,
    record_size_for,
)
from sonar_analyzer.recording.session import RecordingOutcome, RecordingSession, RecordingState

#: `char[12]` ad alanının taşıyabildiği en büyük sıra numarası
#: (`Data9999999` = 11 karakter + sonlandırıcı sıfır).
MAX_SEQUENCE_NO = 9_999_999

#: Öntanımlı dosya boyutu sınırı. 1 GiB Profil A'da kabaca 15,8 milyon
#: kayda karşılık gelir; isim sınırından (10 milyon) sonra geldiği için
#: pratikte önce isim sınırı devreye girer — ikisi de kontrol edilir.
DEFAULT_MAX_BYTES = 1024 * 1024 * 1024


class ClosureReason(Enum):
    """Kaydın neden kapandığı — `F5-033`.

    Neden **kaydedilir**, çünkü dosyanın neden bittiği dosyaya bakarak
    anlaşılamaz: kullanıcının durdurduğu bir kayıt ile bağlantı koptuğu
    için biten bir kayıt diskte birbirinin aynıdır.
    """

    USER_STOP = "kullanici durdurdu"
    DISCONNECTED = "baglanti kesildi"
    SOURCE_ERROR = "kaynak hatasi"
    WRITE_ERROR = "disk yazma hatasi"


@dataclass(frozen=True)
class RecordingGap:
    """Kayıtta atlanan pencere aralığı — `F5-033`.

    `first_missing`/`last_missing` atlanan **kayıt sıralarıdır** (mutlak
    zaman ızgarasında), `missing_count` ise kaç pencerenin hiç gelmediği.
    """

    first_missing: int
    last_missing: int
    missing_count: int
    path: Path

    def __str__(self) -> str:
        return (
            f"{self.path.name}: {self.first_missing}..{self.last_missing} arasi "
            f"{self.missing_count} pencere gelmedi"
        )


@dataclass(frozen=True)
class RotationPolicy:
    """Yeni dosyaya ne zaman geçileceği."""

    max_bytes: int = DEFAULT_MAX_BYTES
    max_sequence_no: int = MAX_SEQUENCE_NO

    def __post_init__(self) -> None:
        if self.max_bytes < 1:
            raise ValueError(f"max_bytes pozitif olmali: {self.max_bytes}")
        if self.max_sequence_no < 0:
            raise ValueError(f"max_sequence_no negatif olamaz: {self.max_sequence_no}")
        if self.max_sequence_no > MAX_SEQUENCE_NO:
            # Daha buyugu `char[12]` ad alanina sigmaz; okunamayan dosya
            # uretmemek icin burada durdurulur.
            raise ValueError(
                f"max_sequence_no ad alanina sigmaz: {self.max_sequence_no} > {MAX_SEQUENCE_NO}"
            )


class RotatingRecorder:
    """Sınıra gelince yeni dosyaya geçen kayıt yazıcısı — `F5-031`."""

    def __init__(
        self,
        directory: Path,
        base_name: str,
        channel_ids: Sequence[str],
        *,
        policy: RotationPolicy | None = None,
        version: int = DEFAULT_FORMAT_VERSION,
        session_factory: Callable[[Path], RecordingSession] | None = None,
    ) -> None:
        if not base_name:
            raise ValueError("base_name bos olamaz")
        self._directory = directory
        self._base_name = base_name
        self._channel_ids = list(channel_ids)
        self._policy = policy if policy is not None else RotationPolicy()
        self._version = version
        self._header_size = header_size_for(version)
        self._record_size = record_size_for(version)

        def default_factory(path: Path) -> RecordingSession:
            return RecordingSession(path)

        self._session_factory: Callable[[Path], RecordingSession] = (
            session_factory if session_factory is not None else default_factory
        )

        self._session: RecordingSession | None = None
        self._accumulator: RecordAccumulator | None = None
        self._submitted = 0
        self._file_index = 0
        self._paths: list[Path] = []
        self._outcomes: list[RecordingOutcome] = []
        self._total_submitted = 0
        self._first_anchor_ns: int | None = None
        self._last_record_ns: int | None = None
        self._stopped = False
        self._gaps: list[RecordingGap] = []
        self._last_window: int | None = None
        self._closure_reason: ClosureReason | None = None

    # ----------------------------------------------------------------- #
    # gozlem
    # ----------------------------------------------------------------- #

    @property
    def policy(self) -> RotationPolicy:
        return self._policy

    @property
    def paths(self) -> list[Path]:
        """Şimdiye kadar açılan dosyalar, açılış sırasıyla."""
        return list(self._paths)

    @property
    def outcomes(self) -> list[RecordingOutcome]:
        """Kapanan dosyaların sonuçları."""
        return list(self._outcomes)

    @property
    def current_path(self) -> Path | None:
        return self._paths[-1] if self._session is not None else None

    @property
    def current_start_time_utc_ns(self) -> int | None:
        """Açık dosyanın başlangıç zamanı — başlığa yazılan değerle aynı."""
        accumulator = self._accumulator
        return None if accumulator is None else accumulator.start_time_utc_ns

    @property
    def current_record_count(self) -> int:
        """Açık dosyaya gönderilen kayıt sayısı."""
        return self._submitted

    @property
    def total_record_count(self) -> int:
        """Bütün dosyalara gönderilen toplam kayıt sayısı."""
        return self._total_submitted

    @property
    def gaps(self) -> list[RecordingGap]:
        """Kayıt boyunca hiç gelmeyen pencere aralıkları — `F5-033`."""
        return list(self._gaps)

    @property
    def missing_windows(self) -> int:
        """Toplam kaç 125 ms penceresinin hiç gelmediği."""
        return sum(gap.missing_count for gap in self._gaps)

    @property
    def closure_reason(self) -> ClosureReason | None:
        """Kaydın neden kapandığı; henüz kapanmadıysa `None`."""
        return self._closure_reason

    @property
    def total_dropped_records(self) -> int:
        """Bütün dosyalarda disk yetişemediği için düşen kayıt sayısı."""
        closed = sum(outcome.dropped_records for outcome in self._outcomes)
        session = self._session
        return closed + (0 if session is None else session.dropped_records)

    @property
    def recorded_span_ns(self) -> int:
        """Kaydın kapsadığı süre: ilk kaydın penceresinden sonuncusuna.

        Süre **veriden** türetilir, duvar saatinden değil: akış dursa bile
        "kayıt süresi" ilerlemeye devam etseydi, kullanıcı elinde olmayan
        saniyelerin kaydedildiğini sanırdı.
        """
        first, last = self._first_anchor_ns, self._last_record_ns
        if first is None or last is None:
            return 0
        return last - first

    @property
    def rotation_count(self) -> int:
        """Kaç kez yeni dosyaya geçildiği (ilk dosya sayılmaz)."""
        return max(0, len(self._paths) - 1)

    @property
    def state(self) -> RecordingState:
        """Kaydın durumu — henüz dosya açılmamış olsa bile doğru.

        Yazıcı ilk **veri taşıyan** pakete kadar dosya açmaz; o aralıkta
        durumu `IDLE` göstermek, kullanıcı Record'a bastığı hâlde "kayıt
        yok" demek olurdu. Durdurulduktan sonra ise dosyalardan biri hata
        aldıysa `FAILED` kalır (`F5-030`: başarılı denmez).
        """
        session = self._session
        if session is not None:
            return session.poll()
        if not self._stopped:
            return RecordingState.RECORDING
        if any(not outcome.succeeded for outcome in self._outcomes):
            return RecordingState.FAILED
        return RecordingState.STOPPED

    # ----------------------------------------------------------------- #
    # yazma
    # ----------------------------------------------------------------- #

    def accept(self, packet: LivePacket) -> PendingRecord | None:
        """Paketi uygun dosyaya yazar; gerekiyorsa önce yeni dosyaya geçer.

        Örnek taşımayan paket kayıt üretmez ve dosya açtırmaz — boş bir
        pakete dosya açmak, hiç veri gelmemiş bir kaydı başlatırdı.
        """
        if self._stopped:
            raise RuntimeError("Kayit durduruldu; yeni bir RotatingRecorder gerekli")
        first_ns = _first_sample_ns(packet)
        if first_ns is None:
            return None

        if self._accumulator is None:
            self._open_file(first_ns)

        accumulator = self._require_accumulator()
        sequence_no = accumulator.sequence_for(first_ns)
        if self._needs_rotation(sequence_no):
            self._rotate(accumulator.start_time_utc_ns + sequence_no * RECORD_PERIOD_NS)

        record = self._require_accumulator().accept(packet)
        if record is None:
            return None

        self._note_gap(first_ns)
        self._require_session().write(record.payload)
        self._submitted += 1
        self._total_submitted += 1
        self._last_record_ns = first_ns
        return record

    def stop(self, reason: ClosureReason = ClosureReason.USER_STOP) -> list[RecordingOutcome]:
        """Açık dosyayı kapatır ve **bütün** dosyaların sonuçlarını döndürür.

        `reason` kaydedilir (`closure_reason`): bağlantı koptuğu için biten
        bir kayıt ile kullanıcının durdurduğu kayıt diskte birbirinin
        aynıdır; nedeni saklamazsak sonradan ayırt edilemezdi.
        """
        self._close_current()
        self._stopped = True
        if self._closure_reason is None:
            self._closure_reason = reason
        return list(self._outcomes)

    def _note_gap(self, first_ns: int) -> None:
        """Bu kaydın öncekiyle arasında atlanan pencere varsa kaydeder.

        Ölçü **mutlak zaman ızgarasındaki** pencere indeksidir, dosya içi
        sıra numarası değil: dosya değişince sıra sıfırlanır ve iki dosya
        arasındaki boşluk görünmez olurdu.
        """
        anchor = self._first_anchor_ns
        if anchor is None:  # pragma: no cover - _open_file her zaman kurar
            return
        window = (first_ns - anchor) // RECORD_PERIOD_NS
        previous = self._last_window
        if previous is not None and window > previous + 1:
            self._gaps.append(
                RecordingGap(
                    first_missing=previous + 1,
                    last_missing=window - 1,
                    missing_count=window - previous - 1,
                    path=self._paths[-1],
                )
            )
        self._last_window = window

    # ----------------------------------------------------------------- #
    # ic isleyis
    # ----------------------------------------------------------------- #

    def _needs_rotation(self, sequence_no: int) -> bool:
        """Bu kayıt yazılmadan **önce** yeni dosyaya geçilmeli mi?"""
        if sequence_no > self._policy.max_sequence_no:
            return True
        next_size = self._header_size + (self._submitted + 1) * self._record_size
        return next_size > self._policy.max_bytes

    def _rotate(self, anchor_ns: int) -> None:
        self._close_current()
        self._open_file(anchor_ns)

    def _open_file(self, anchor_ns: int) -> None:
        """Yeni dosyayı, başlığı ve sayacı **aynı** çapaya göre kurar."""
        self._file_index += 1
        path = self._directory / f"{self._base_name}_{self._file_index:03d}.bin"
        session = self._session_factory(path)
        session.start(build_file_header(start_time_utc_ns=anchor_ns, version=self._version))
        # Basliga yazilan zaman ile accumulator'un capasi TEK bir degerdir;
        # ikisini ayri hesaplamak dosyayi kendi icinde tutarsiz kilardi.
        self._accumulator = RecordAccumulator(anchor_ns, self._channel_ids, version=self._version)
        self._session = session
        self._submitted = 0
        self._paths.append(path)
        if self._first_anchor_ns is None:
            self._first_anchor_ns = anchor_ns

    def _close_current(self) -> None:
        session = self._session
        if session is None:
            return
        self._outcomes.append(session.stop())
        self._session = None
        self._accumulator = None

    def _require_session(self) -> RecordingSession:
        session = self._session
        if session is None:  # pragma: no cover - accept() her zaman acar
            raise RuntimeError("Acik kayit dosyasi yok")
        return session

    def _require_accumulator(self) -> RecordAccumulator:
        accumulator = self._accumulator
        if accumulator is None:  # pragma: no cover - accept() her zaman acar
            raise RuntimeError("Acik kayit dosyasi yok")
        return accumulator


def _first_sample_ns(packet: LivePacket) -> int | None:
    """Pakedin ilk örnek zamanı; örnek yoksa `None`."""
    starts = [int(chunk.timestamps_ns[0]) for chunk in packet.chunks if len(chunk)]
    return min(starts) if starts else None
