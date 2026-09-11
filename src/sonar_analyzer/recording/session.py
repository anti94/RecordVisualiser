"""Kayıt oturumu ve disk hatası durumu — `F5-030`.

Kabul: **Kayıt hata durumuna geçer; başarılı kayıt mesajı verilmez.**

`RecordingWriter` (`F5-028`/`F5-029`) bir yazma hatasını *görünür* kılar
ama ondan bir sonuç çıkarmaz. Bu modül o hatayı bir **duruma** çevirir ve
oturumun sonunda verilecek mesajı belirler. Buradaki tek kural şudur:

    Bir yazma hatası olduysa oturum `FAILED` durumundadır ve
    `RecordingOutcome.succeeded` **False**'tur — dosyada kaç kayıt olursa
    olsun "kayıt başarıyla tamamlandı" denmez.

Mesaj metni koddan değil durumdan üretilir; "başarılı" cümlesi yalnız
`STOPPED` dalında kurulur, böylece yeni bir hata yolu eklendiğinde
yanlışlıkla başarı mesajına düşmek mümkün olmaz.

Disk dolması iki yerde yakalanır:

* **Başlamadan önce** — `shutil.disk_usage` ile boş alan bakılır; alan
  eşiğin altındaysa oturum hiç başlamaz. Başlayıp birkaç saniye sonra
  ölecek bir kayıt, kullanıcının kaydı var sanması demek olurdu.
* **Yazarken** — `ENOSPC` (`errno` 28) ayrı bir mesajla bildirilir;
  "diskte yer kalmadı", genel bir G/Ç hatasından farklı bir eylem
  gerektirir.

Hata sonrası dosya **silinmez**: `F5-029`'un kestiği yarım blok sayesinde
dosyadaki tam kayıtlar okunabilir durumdadır ve elde olan veri, olmayan
veriden iyidir. Sonuç nesnesi kaç kaydın kurtulduğunu söyler.
"""

from __future__ import annotations

import errno
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from sonar_analyzer.recording.disk_writer import DEFAULT_QUEUE_BLOCKS, RecordingWriter

#: Kayda başlamak için gereken en az boş alan (bayt). 125 ms'lik Profil A
#: kaydı 68 bayttır; 64 MiB kabaca 2.5 saatlik tek kanal kaydına yeter ve
#: "az sonra dolacak" bir diskte kayda hiç başlamamayı sağlar.
MIN_FREE_BYTES = 64 * 1024 * 1024


class RecordingState(Enum):
    """Kayıt oturumunun durumu."""

    IDLE = "idle"
    RECORDING = "recording"
    STOPPED = "stopped"
    FAILED = "failed"


class RecordingStartError(OSError):
    """Kayıt hiç başlatılamadı (yer yok, dizin açılamadı vb.)."""


@dataclass(frozen=True)
class RecordingOutcome:
    """Bir kayıt oturumunun sonucu — mesaj dâhil."""

    state: RecordingState
    path: Path
    record_count: int
    dropped_records: int
    truncated_bytes: int
    message: str
    error: str | None = None

    @property
    def succeeded(self) -> bool:
        """Yalnız `STOPPED` başarıdır; hata olan oturum başarılı sayılmaz."""
        return self.state is RecordingState.STOPPED


def _free_bytes(path: Path) -> int:
    """Hedef dosyanın bulunacağı birimdeki boş alan."""
    probe = path.parent
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    return shutil.disk_usage(probe).free


class RecordingSession:
    """Yazıcıyı bir duruma bağlar; hatayı yutmadan sonuca çevirir — `F5-030`."""

    def __init__(
        self,
        path: Path,
        *,
        queue_maxsize: int = DEFAULT_QUEUE_BLOCKS,
        min_free_bytes: int = MIN_FREE_BYTES,
        writer_factory: Callable[[Path], RecordingWriter] | None = None,
        free_space: Callable[[Path], int] | None = None,
    ) -> None:
        self._path = path
        self._min_free_bytes = min_free_bytes
        self._free_space = free_space if free_space is not None else _free_bytes

        def default_factory(target: Path) -> RecordingWriter:
            return RecordingWriter(target, queue_maxsize=queue_maxsize)

        self._writer_factory: Callable[[Path], RecordingWriter] = (
            writer_factory if writer_factory is not None else default_factory
        )
        self._writer: RecordingWriter | None = None
        self._state = RecordingState.IDLE
        self._error: str | None = None
        self._error_code: int | None = None

    @property
    def path(self) -> Path:
        return self._path

    @property
    def state(self) -> RecordingState:
        return self._state

    @property
    def is_recording(self) -> bool:
        return self._state is RecordingState.RECORDING

    @property
    def error(self) -> str | None:
        return self._error

    @property
    def record_count(self) -> int:
        writer = self._writer
        return 0 if writer is None else writer.written_records

    @property
    def dropped_records(self) -> int:
        writer = self._writer
        return 0 if writer is None else writer.dropped_records

    def start(self, header: bytes) -> None:
        """Kaydı başlatır; yer yoksa **başlamaz** ve `RecordingStartError` yükselir."""
        if self._state is RecordingState.RECORDING:
            raise RuntimeError("Kayit zaten suruyor")

        free = self._free_space(self._path)
        if free < self._min_free_bytes:
            message = (
                f"Diskte yeterli yer yok: {free} bayt bos, "
                f"en az {self._min_free_bytes} bayt gerekli."
            )
            self._fail(message, errno.ENOSPC)
            raise RecordingStartError(errno.ENOSPC, message)

        writer = self._writer_factory(self._path)
        try:
            writer.open(header)
        except OSError as exc:
            message = f"Kayit dosyasi acilamadi: {exc}"
            self._fail(message, exc.errno)
            raise RecordingStartError(exc.errno or 0, message) from exc

        self._writer = writer
        self._error = None
        self._error_code = None
        self._state = RecordingState.RECORDING

    def write(self, block: bytes) -> bool:
        """Bir kaydı yazmaya gönderir; hata çıkmışsa oturumu `FAILED` yapar.

        Dönüş değeri yalnız bloğun **kuyruğa alındığını** söyler; disk
        hatası yazma anında değil worker'da görülür, bu yüzden her
        gönderimden sonra yazıcının hatası yoklanır.
        """
        if self._state is not RecordingState.RECORDING or self._writer is None:
            raise RuntimeError(f"Kayit suruyor degil: {self._state.value}")

        accepted = self._writer.submit(block)
        self._check_writer_error()
        return accepted

    def poll(self) -> RecordingState:
        """Yazıcıyı yoklar; hata varsa duruma yansıtır ve durumu döndürür.

        Kayıt sürerken hiç yeni blok gelmese bile (bağlantı sessizleşti)
        çağrılabilmelidir — hata yalnız `write()` ile fark edilseydi sessiz
        bir kayıt sırasında disk dolması hiç görülmezdi.
        """
        self._check_writer_error()
        return self._state

    def stop(self) -> RecordingOutcome:
        """Kaydı durdurur ve **durumdan türeyen** sonucu döndürür."""
        writer = self._writer
        if writer is None:
            return RecordingOutcome(
                state=self._state,
                path=self._path,
                record_count=0,
                dropped_records=0,
                truncated_bytes=0,
                message=self._error or "Kayit hic baslamadi.",
                error=self._error,
            )

        writer.close()
        self._check_writer_error()
        if self._state is RecordingState.RECORDING:
            self._state = RecordingState.STOPPED

        return RecordingOutcome(
            state=self._state,
            path=self._path,
            record_count=writer.written_records,
            dropped_records=writer.dropped_records,
            truncated_bytes=writer.truncated_bytes,
            message=self._message_for(writer),
            error=self._error,
        )

    # ----------------------------------------------------------------- #
    # ic yardimcilar
    # ----------------------------------------------------------------- #

    def _check_writer_error(self) -> None:
        writer = self._writer
        if writer is None or writer.error is None:
            return
        self._fail(self._describe(writer.error, writer.error_code), writer.error_code)

    def _fail(self, message: str, code: int | None) -> None:
        """Oturumu hata durumuna alır; ilk hata korunur (sonrakiler onun sonucudur)."""
        self._state = RecordingState.FAILED
        if self._error is None:
            self._error = message
            self._error_code = code

    def _describe(self, raw: str, code: int | None) -> str:
        """Ham `OSError` metnini kullanıcıya anlamlı bir cümleye çevirir."""
        if code == errno.ENOSPC:
            return f"Diskte yer kalmadi; kayit durduruldu. ({raw})"
        if code in (errno.EACCES, errno.EPERM):
            return f"Kayit dosyasina yazma izni yok; kayit durduruldu. ({raw})"
        return f"Diske yazilamadi; kayit durduruldu. ({raw})"

    def _message_for(self, writer: RecordingWriter) -> str:
        """Sonuç mesajı — "başarılı" cümlesi **yalnız** hata yokken kurulur."""
        if self._state is not RecordingState.STOPPED:
            saved = writer.written_records
            detail = self._error or "Bilinmeyen kayit hatasi."
            return f"{detail} Dosyada {saved} tam kayit okunabilir durumda: {self._path}"

        parts = [f"Kayit tamamlandi: {writer.written_records} kayit, {self._path}"]
        if writer.dropped_records:
            # Tamamlandi ama eksik: bunu sessizce gecmek dosyayi tam
            # sanmaya yol acardi.
            parts.append(f"Disk yetisemedigi icin {writer.dropped_records} kayit dustu.")
        return " ".join(parts)
