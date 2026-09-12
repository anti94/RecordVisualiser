"""Uygulamanın videolu demosunu üretir — gerçek pencere, gerçek veri.

Bu betik bir animasyon ya da mockup çizmez. **Çalışan `MainWindow`'u**
görünmez (offscreen) bir Qt platformunda açar, senaryoyu gerçek genel
API üzerinden sürer (`open_channel`, `view_tabs`, `export_channel_csv`
...) ve her adımda pencerenin kendisini yakalar. Videoda görünen her
piksel uygulamanın o an çizdiği şeydir.

Kareler `ffmpeg`'e **ham RGB olarak borudan** verilir; ara PNG dosyası
yazılmaz. Binlerce geçici dosya hem yavaş hem de iş yarıda kalırsa
temizlenmemiş çöp bırakır.

Altyazılar kareye gömülür. Altyazısız bir demo videosu, izleyenden neye
baktığını tahmin etmesini ister.

Veri kaynağı altyazıda **açıkça yazar**: gerçek `.bin` fixture'ı mı,
uygulamanın kendi simülasyon kipi mi. Hangi verinin gerçek olduğunu
gizleyen bir demo yanıltır.

Kullanım::

    python tools/demo_video.py --out docs/demo/sonar-analyzer-demo.mp4
    python tools/demo_video.py --out demo.mp4 --fps 12 --scale 0.75
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Callable

ROOT = Path(__file__).resolve().parent.parent
for location in (ROOT, ROOT / "src"):
    if str(location) not in sys.path:
        sys.path.insert(0, str(location))

if TYPE_CHECKING:  # pragma: no cover - yalniz tip denetimi
    from PySide6.QtGui import QImage

    from sonar_analyzer.ui.main_window import MainWindow

WINDOWS_FONT_DIR = "C:/Windows/Fonts"

#: Gercek Profil A kaydi (depodaki fixture).
FIXTURE = ROOT / "tests" / "fixtures" / "valid_8records.bin"

#: Demoda spektral gorunumlerin bagli oldugu kanal. Simulasyon
#: kaynagindaki tek akustik kanal ve tek belirgin tonu tasiyan kanal bu.
ANALYSIS_CHANNEL = "ch5"

#: Grafige ikinci seri olarak eklenen kanal — farkli birim, ikinci Y ekseni.
SECOND_CHANNEL = "ch0"

CAPTION_BAND_PX = 96
TITLE_PT = 20
DETAIL_PT = 13


def prepare_environment() -> None:
    """Görünür pencere açmadan ve yazı tipsiz kalmadan çizim için ortam."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    if "QT_QPA_FONTDIR" not in os.environ and Path(WINDOWS_FONT_DIR).is_dir():
        os.environ["QT_QPA_FONTDIR"] = WINDOWS_FONT_DIR


def even_dimension(value: int) -> int:
    """H.264 tek sayı boyut kabul etmez."""
    return value if value % 2 == 0 else value + 1


def image_bytes(image: QImage) -> bytes:
    """QImage'ı satır dolgusundan arındırılmış ham RGB bayta çevirir.

    `bytesPerLine` genişlik×3'ten büyük olabilir (4 bayta hizalama).
    Dolguyu atmadan ffmpeg'e vermek görüntüyü her satırda kaydırır.
    """
    width, height = image.width(), image.height()
    stride = image.bytesPerLine()
    raw = bytes(image.constBits())
    row = width * 3
    if stride == row:
        return raw[: row * height]
    return b"".join(raw[y * stride : y * stride + row] for y in range(height))


class FrameSink:
    """ffmpeg'e ham kare yazan boru."""

    def __init__(
        self,
        output: Path,
        size: tuple[int, int],
        fps: int,
        scale: float,
        ffmpeg: str | None = None,
    ) -> None:
        exe = ffmpeg or shutil.which("ffmpeg")
        if exe is None:
            raise RuntimeError("ffmpeg bulunamadi. PATH'e ekleyin ya da --ffmpeg ile verin.")

        self._size = size
        width, height = size
        output.parent.mkdir(parents=True, exist_ok=True)

        out_w = even_dimension(round(width * scale))
        out_h = even_dimension(round(height * scale))
        command = [
            exe,
            "-y",
            "-loglevel",
            "error",
            "-f",
            "rawvideo",
            "-pixel_format",
            "rgb24",
            "-video_size",
            f"{width}x{height}",
            "-framerate",
            str(fps),
            "-i",
            "-",
            "-vf",
            f"scale={out_w}:{out_h}:flags=lanczos",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output),
        ]
        self._process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        self.frames = 0

    def write(self, frame: bytes) -> None:
        expected = self._size[0] * self._size[1] * 3
        if len(frame) != expected:
            raise RuntimeError(f"kare {len(frame)} bayt, beklenen {expected}")
        stdin = self._process.stdin
        if stdin is None:  # pragma: no cover
            raise RuntimeError("ffmpeg stdin kapali")
        stdin.write(frame)
        self.frames += 1

    def close(self) -> None:
        stdin = self._process.stdin
        if stdin is not None:
            stdin.close()
        _, stderr = self._process.communicate()
        if self._process.returncode != 0:
            raise RuntimeError(
                f"ffmpeg {self._process.returncode} ile cikti:\n{stderr.decode('utf-8', 'replace')}"
            )


class Stage:
    """Pencereyi süren ve kareleri boruya yazan sahne."""

    def __init__(self, window: MainWindow, sink: FrameSink, fps: int) -> None:
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:  # pragma: no cover - main() once olusturur
            raise RuntimeError("QApplication yok")

        self.window = window
        self.app = app
        self._sink = sink
        self._fps = fps
        self._title = ""
        self._detail = ""
        self._progress = 0.0

    def settle(self, rounds: int = 8) -> None:
        """Bekleyen Qt olaylarını işler; yarı çizilmiş kare yakalanmasın."""
        for _ in range(rounds):
            self.app.processEvents()

    def caption(self, title: str, detail: str) -> None:
        self._title = title
        self._detail = detail

    def progress(self, value: float) -> None:
        self._progress = min(1.0, max(0.0, value))

    def hold(self, seconds: float) -> None:
        """Aynı görüntüyü `seconds` boyunca kareye yazar."""
        self.settle()
        frame = self._compose()
        for _ in range(max(1, round(seconds * self._fps))):
            self._sink.write(frame)

    def animate(self, seconds: float, step: Callable[[float], None]) -> None:
        """Her karede `step(t)` çağırıp yeniden yakalar — 0 <= t <= 1."""
        count = max(2, round(seconds * self._fps))
        for index in range(count):
            step(index / (count - 1))
            self.settle(3)
            self._sink.write(self._compose())

    def _compose(self) -> bytes:
        """Pencereyi yakalar, altyazıyı gömer, ham bayta çevirir."""
        from PySide6.QtCore import QRect, Qt
        from PySide6.QtGui import QColor, QFont, QImage, QPainter

        pixmap = self.window.grab()
        image = pixmap.toImage().convertToFormat(QImage.Format.Format_RGB888)
        width, height = image.width(), image.height()

        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        top = height - CAPTION_BAND_PX
        painter.fillRect(QRect(0, top, width, CAPTION_BAND_PX), QColor(11, 15, 22))
        painter.fillRect(QRect(0, top, width, 2), QColor(64, 158, 255))

        font = QFont()
        font.setPointSize(TITLE_PT)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(240, 244, 250))
        painter.drawText(
            QRect(36, top + 12, width - 72, 34),
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            self._title,
        )

        font.setPointSize(DETAIL_PT)
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(QColor(168, 182, 200))
        painter.drawText(
            QRect(36, top + 48, width - 72, 32),
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            self._detail,
        )

        painter.fillRect(QRect(0, height - 4, int(width * self._progress), 4), QColor(64, 158, 255))
        painter.end()
        return image_bytes(image)


@dataclass(frozen=True)
class Scene:
    """Bir sahne: başlık, açıklama, süre ve yapılacak iş."""

    title: str
    detail: str
    seconds: float
    action: Callable[[Stage], None] | None = None


# --------------------------------------------------------------------------- #
# SENARYO
# --------------------------------------------------------------------------- #


def _version() -> str:
    """Sürümü `VERSION` dosyasından okur.

    Altyazıya elle yazılan bir sürüm numarası, bir sonraki sürüm
    artışında sessizce yanlışa döner: video 4.4.0 der, uygulama 4.5.0
    çizer. Tek kaynak `VERSION` dosyasıdır.
    """
    from sonar_analyzer import __version__

    return __version__


def _tab(stage: Stage, title: str) -> None:
    """Merkez sekmesini başlığıyla seçer; yoksa yüksek sesle düşer."""
    titles = stage.window.view_tabs.tab_titles()
    if title not in titles:
        raise RuntimeError(f"sekme yok: {title} (var olanlar: {titles})")
    index = titles.index(title)
    if not stage.window.view_tabs.isTabEnabled(index):
        raise RuntimeError(f"sekme pasif: {title}")
    stage.window.view_tabs.setCurrentIndex(index)


def _open_fixture(stage: Stage) -> None:
    from sonar_analyzer.repository.file_repository import FileRecordingRepository

    if not FIXTURE.is_file():
        raise RuntimeError(f"fixture yok: {FIXTURE}")
    repository = FileRecordingRepository()
    repository.open(FIXTURE)
    stage.window.set_repository(repository)


def _load_simulation(stage: Stage) -> None:
    """Uygulamanın kendi menü eylemi — Tools -> Load Simulation Data.

    Elle kurulmuş bir repository yerine bu çağrılıyor: kullanıcı o menüyü
    seçtiğinde ne görüyorsa demo da onu göstersin. Öntanımlı 8 Hz
    örnekleme, spektrum ekseninin Nyquist'i 4 Hz demek; simülasyonun
    1,5 Hz'lik akustik tonu eksenin ortasına düşer ve **görünür**. Daha
    yüksek bir örnekleme hızı tonu eksenin sol kenarına sıkıştırır ve
    spektrum bomboş görünür.
    """
    stage.window.load_simulation()


def _plot_hydrophone(stage: Stage) -> None:
    stage.window.open_channel(ANALYSIS_CHANNEL)


def _add_pressure(stage: Stage) -> None:
    stage.window.left_dock.channels_add_requested.emit([SECOND_CHANNEL])


def _recording_seconds(stage: Stage) -> float:
    """Kaydın gerçek uzunluğu — sabite gömmek yerine kaynağa sorulur."""
    repository = stage.window.repository
    if repository is None:
        raise RuntimeError("acik kayit yok")
    span = repository.metadata().time_range
    return (span.end_ns - span.start_ns) / 1_000_000_000


def _zoom_in(stage: Stage) -> None:
    panel = stage.window.plot_panel
    full = _recording_seconds(stage)

    def step(value: float) -> None:
        panel.set_x_range((0.30 * full) * value, full - (0.55 * full) * value)

    stage.animate(3.2, step)


def _zoom_out(stage: Stage) -> None:
    stage.window.reset_plot_view()


def _select_analysis_channel(stage: Stage) -> None:
    """Spektral sahneler öncesi analiz yüzeylerini akustik kanala bağlar.

    Çoklu seri sahnesinde ikinci kanal eklendiği için analiz yüzeyleri
    basınç kanalına bağlı kalıyordu. Basınç sinyali neredeyse saf DC;
    spektrumu sol kenarda tek bir çubuk, gerisi düz çizgi. Altyazı
    "seçili kanalın spektrumu" derken ekranda başka kanal olmamalı.
    """
    stage.window.open_channel(ANALYSIS_CHANNEL)


def _spectrum(stage: Stage) -> None:
    _select_analysis_channel(stage)
    _tab(stage, "Spectrum")


def _spectrogram(stage: Stage) -> None:
    _tab(stage, "Spectrogram")


def _run_bit(stage: Stage) -> None:
    _tab(stage, "BIT / Status")
    stage.window.refresh_bit_analysis()


def _show_events(stage: Stage) -> None:
    """Olay tablosunu **gerçekten** öne getirir.

    Alt şerit öntanımlı olarak Log sekmesinde açılıyordu; altyazı olay
    tablosundan söz ederken ekranda günlük satırları duruyordu.
    """
    from sonar_analyzer.ui.docks.bottom_panel import EVENTS_TAB_TITLE

    _tab(stage, "Time Series")
    stage.window.show_channel_in_inspector(ANALYSIS_CHANNEL)

    tabs = stage.window.bottom_dock.tabs
    titles = [tabs.tabText(index) for index in range(tabs.count())]
    if EVENTS_TAB_TITLE not in titles:
        raise RuntimeError(f"olay sekmesi yok: {titles}")
    tabs.setCurrentIndex(titles.index(EVENTS_TAB_TITLE))


def _export_csv(stage: Stage) -> None:
    import tempfile

    target = Path(tempfile.gettempdir()) / "sonar-demo" / "ch5.csv"
    result = stage.window.export_channel_csv(target, channel_id="ch5")
    stage.window.bottom_dock.append_log(f"CSV yazildi: {result.path}")


SCENES: tuple[Scene, ...] = (
    Scene(
        "SONAR Veri Analiz Panosu",
        "Kayit acilmadan once bos durum: uc sutunlu yerlesim ve sekiz analiz sekmesi.",
        3.0,
    ),
    Scene(
        "Gercek bir .bin acilir",
        "tests/fixtures/valid_8records.bin - Profil A, 8 kanal, 1 saniye. "
        "Kanal agaci dogrudan dosyadan cozulur.",
        4.0,
        _open_fixture,
    ),
    Scene(
        "Daha uzun kayit: simulasyon kipi",
        "Tools -> Load Simulation Data. Bundan sonraki her sahnede veri kaynagi "
        "SIMULASYONDUR - sol ustteki Recording karti da bunu yazar.",
        3.5,
        _load_simulation,
    ),
    Scene(
        "Kanal cift tiklanir",
        "ch5 Hydrophone 1 zaman serisi olarak cizilir. "
        "Nokta butcesi grafigin piksel genisliginden turer.",
        4.0,
        _plot_hydrophone,
    ),
    Scene(
        "Ikinci kanal ayni grafige eklenir",
        "ch0 Pressure farkli birimde - ikinci Y ekseni acilir, zaman ekseni ortaktir.",
        4.0,
        _add_pressure,
    ),
    Scene(
        "Zaman ekseninde yakinlastirma",
        "X araligi daraltilir; bagli paneller ayni araligi izler.",
        0.6,
        _zoom_in,
    ),
    Scene(
        "Gorunum sifirlanir",
        "Reset View kaydin tamamina doner.",
        2.5,
        _zoom_out,
    ),
    Scene(
        "Spectrum sekmesi",
        "Akustik kanalin FFT / PSD gorunumu. Eksen 0 Hz - Nyquist; "
        "simulasyonun tonu tepe olarak gorunur.",
        4.5,
        _spectrum,
    ),
    Scene(
        "Spectrogram sekmesi",
        "Ayni kanalin STFT selale gorunumu - zaman ekseninde frekans icerigi.",
        4.5,
        _spectrogram,
    ),
    Scene(
        "BIT / Status",
        "Yerlesik test sonuclari kategori kategori. Run BIT Analysis kayitli veriyi "
        "yeniden sorgular, cihaza komut gondermez.",
        4.5,
        _run_bit,
    ),
    Scene(
        "Transmission",
        "TX aralik tablosu: baslangic, bitis ve sure.",
        4.0,
        lambda stage: _tab(stage, "Transmission"),
    ),
    Scene(
        "Olaylar ve inceleme",
        "Alt seritte olay tablosu (kaynak ve onem derecesine gore suzulur), "
        "sag sutunda secili kanalin incelemesi.",
        5.0,
        _show_events,
    ),
    Scene(
        "CSV disa aktarma",
        "Secili kanal CSV olarak yazilir; kalite bayraklari ayri sutunda tasinir.",
        4.0,
        _export_csv,
    ),
    Scene(
        f"Surum {_version()}",
        "Kaynak: VERSION dosyasi. Paketleme PyInstaller onedir + NSIS kullanici basina kurulum.",
        3.5,
    ),
)


# --------------------------------------------------------------------------- #
# CALISTIRMA
# --------------------------------------------------------------------------- #


def record(output: Path, fps: int, scale: float, ffmpeg: str | None) -> dict[str, object]:
    """Senaryoyu koşturur ve videoyu yazar."""
    from PySide6.QtGui import QFontDatabase
    from PySide6.QtWidgets import QApplication

    from sonar_analyzer import __version__
    from sonar_analyzer.ui.main_window import DEFAULT_WINDOW_SIZE, MainWindow

    app = QApplication.instance() or QApplication([])
    if not QFontDatabase.families():
        raise RuntimeError(
            "Hic yazi tipi bulunamadi; butun metinler kutu cizilirdi. QT_QPA_FONTDIR ayarlayin."
        )

    width, height = DEFAULT_WINDOW_SIZE
    window = MainWindow()
    window.resize(width, height)
    window.show()
    for _ in range(5):
        app.processEvents()
    window.apply_default_layout()
    for _ in range(5):
        app.processEvents()

    grabbed = window.grab()
    size = (grabbed.width(), grabbed.height())

    sink = FrameSink(output, size, fps, scale, ffmpeg)
    stage = Stage(window, sink, fps)
    total = len(SCENES)
    try:
        for index, scene in enumerate(SCENES):
            stage.caption(scene.title, scene.detail)
            stage.progress((index + 1) / total)
            print(f"  [{index + 1}/{total}] {scene.title}", flush=True)
            if scene.action is not None:
                scene.action(stage)
            stage.hold(scene.seconds)
    finally:
        sink.close()
        window.close()

    return {
        "path": str(output),
        "version": __version__,
        "frames": sink.frames,
        "fps": fps,
        "seconds": round(sink.frames / fps, 2),
        "capture_size": f"{size[0]}x{size[1]}",
        "bytes": output.stat().st_size if output.exists() else 0,
        "scenes": total,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Uygulamanin videolu demosunu uretir")
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "demo" / "demo.mp4")
    parser.add_argument("--fps", type=int, default=15)
    parser.add_argument("--scale", type=float, default=1.0, help="cikti olcegi (0 < s <= 1)")
    parser.add_argument("--ffmpeg", default=None, help="ffmpeg yolu")
    args = parser.parse_args(argv)

    if args.fps < 1 or args.fps > 60:
        print(f"fps 1..60 araliginda olmali: {args.fps}", file=sys.stderr)
        return 2
    if not 0.0 < args.scale <= 1.0:
        print(f"olcek (0, 1] araliginda olmali: {args.scale}", file=sys.stderr)
        return 2

    prepare_environment()
    try:
        summary = record(args.out, args.fps, args.scale, args.ffmpeg)
    except RuntimeError as exc:
        print(f"HATA: {exc}", file=sys.stderr)
        return 1

    print()
    for key, value in summary.items():
        print(f"  {key:14} {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
