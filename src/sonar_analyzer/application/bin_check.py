"""Paketlenmiş uygulamada BIN açma ve dışa aktarma denetimi — `F6-006`.

Kabul: **Örnek kayıt açılır; CSV/PNG çıktısı yeniden okunabilir.**

`F6-005` paketin *açıldığını* gösterdi; bu modül **iş yaptığını** gösterir.
Paketlemede en sık kaybolan şeyler tam da burada ortaya çıkar: dosya
okuyucu çalışıyor mu, NumPy geldi mi, Qt görüntü yazıcıları (PNG) pakete
girdi mi.

Denetim üç adımdır ve her biri **sonucu geri okunarak** doğrulanır:

1. örnek `.bin` üretim deposuyla açılır ve bir kanal sorgulanır,
2. CSV yazılır, sonra **geri okunup** satır sayısı ve başlık denetlenir,
3. PNG yazılır, sonra **geri okunup** gerçekten PNG olduğu (imza) ve
   boyutunun sıfırdan büyük olduğu denetlenir.

Yazıp "oldu" demek yetmez: bozuk ya da boş bir dosya da yazılmış olur.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:  # pragma: no cover - yalniz tip denetimi
    from sonar_analyzer.domain.data_chunk import DataChunk

#: PNG dosya imzasi (`\x89PNG\r\n\x1a\n`).
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


@dataclass
class BinCheckReport:
    """Denetimin sonucu; her satır kullanıcıya gösterilir."""

    lines: list[str] = field(default_factory=lambda: [])
    failures: list[str] = field(default_factory=lambda: [])
    csv_path: str = ""
    png_path: str = ""

    @property
    def ok(self) -> bool:
        return not self.failures


def run_bin_check(source: Path, output_dir: Path) -> BinCheckReport:
    """Örnek kaydı açar, CSV/PNG üretir ve ikisini de geri okur."""
    from sonar_analyzer.export.csv_export import write_channel_csv
    from sonar_analyzer.repository.file_repository import FileRecordingRepository

    lines: list[str] = []
    failures: list[str] = []
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1) Kayit acilir.
    repository = FileRecordingRepository()
    try:
        repository.open(source, cache_path=output_dir / "index.sidx")
    except Exception as exc:
        return BinCheckReport(
            lines=[f"kayit: ACILAMADI ({exc})", "sonuc: EKSIK -> kayit"],
            failures=["kayit"],
        )

    metadata = repository.metadata()
    channels = list(repository.channels())
    lines.append(f"kayit: {len(channels)} kanal, {metadata.record_count} kayit")
    if not channels:
        failures.append("kanal")
        lines.append("kanal: YOK")
        return BinCheckReport(lines=[*lines, "sonuc: EKSIK -> kanal"], failures=failures)

    channel = channels[0]
    chunk = repository.query(channel.id, metadata.time_range)
    lines.append(f"sorgu: {channel.id} -> {len(chunk)} ornek")
    if not len(chunk):
        failures.append("sorgu")

    # F6-035: bayrakli ornekler burada gorunmeli. Bilinen bozuk bir
    # dosyada "sonuc: TAMAM" demek, denetimin en cok ise yarayacagi yerde
    # sessiz kalmasi olurdu.
    lines.append(_quality_line(chunk))

    # 2) CSV yazilir ve GERI OKUNUR.
    csv_path = output_dir / "export.csv"
    try:
        write_channel_csv(chunk, channel, csv_path, recording=metadata)
        rows = _csv_data_rows(csv_path)
    except Exception as exc:
        failures.append("csv")
        lines.append(f"csv: YAZILAMADI ({exc})")
    else:
        if rows == len(chunk):
            lines.append(f"csv: {rows} satir geri okundu ({csv_path.name})")
        else:
            failures.append("csv")
            lines.append(f"csv: SATIR SAYISI TUTMUYOR ({rows} != {len(chunk)})")

    # 3) PNG yazilir ve GERI OKUNUR.
    png_path = output_dir / "export.png"
    try:
        _write_png(png_path)
        signature_ok = png_path.read_bytes()[:8] == PNG_SIGNATURE
        size = png_path.stat().st_size
    except Exception as exc:
        failures.append("png")
        lines.append(f"png: YAZILAMADI ({exc})")
    else:
        if signature_ok and size > 0:
            lines.append(f"png: {size} bayt, imza dogru ({png_path.name})")
        else:
            failures.append("png")
            lines.append(f"png: GECERSIZ (imza={signature_ok}, bayt={size})")

    lines.append("sonuc: " + ("TAMAM" if not failures else "EKSIK -> " + ", ".join(failures)))
    return BinCheckReport(
        lines=lines,
        failures=failures,
        csv_path=str(csv_path),
        png_path=str(png_path),
    )


def _quality_line(chunk: DataChunk) -> str:
    """Sorgudan dönen parçanın kalite özeti — `F6-035`.

    Kalite bilgisi yoksa "hepsi sağlam" denmez; bilgi olmadığı yazılır.
    Bayrak varsa hangi bayraktan kaç örnek olduğu tek satırda görünür.
    """
    from sonar_analyzer.export.csv_export import QUALITY_SEPARATOR, describe_quality

    quality = chunk.quality
    if quality is None:
        return "kalite: bilgi yok (kaynak bayrak vermedi)"

    counts: dict[str, int] = {}
    flagged = 0
    for raw in quality.tolist():
        mask = int(raw)
        if mask == 0:
            continue
        flagged += 1
        for name in describe_quality(mask).split(QUALITY_SEPARATOR):
            counts[name] = counts.get(name, 0) + 1
    total = len(quality)
    if not flagged:
        return f"kalite: {total} ornegin hicbirinde bayrak yok"
    detail = ", ".join(f"{name}={count}" for name, count in sorted(counts.items()))
    return f"kalite: {flagged}/{total} ornek isaretli ({detail})"


def _csv_data_rows(path: Path) -> int:
    """CSV'deki **veri** satırlarını sayar (metadata ve başlık hariç)."""
    data_rows = 0
    header_seen = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if not header_seen:
            header_seen = True  # ilk veri satiri sutun basligidir
            continue
        data_rows += 1
    return data_rows


def _write_png(path: Path) -> None:
    """Basit bir görüntü yazar; amaç Qt PNG yazıcısının pakette olduğunu görmek.

    Qt uygulaması yoksa **açık bir hata** verilir. `QPainter` bir
    `QGuiApplication` olmadan kullanıldığında PySide6 istisna yükseltmez;
    süreci düşürür (Windows'ta 0xC0000409). Süreci çökerten bir yardımcı,
    hata veren bir yardımcıdan her zaman kötüdür: çağıran taraf ne
    olduğunu göremez.
    """
    from PySide6.QtGui import QGuiApplication, QImage, QPainter

    if QGuiApplication.instance() is None:
        raise RuntimeError("PNG yazmak icin bir Qt uygulamasi gerekli (QGuiApplication bulunamadi)")

    image = QImage(320, 200, QImage.Format.Format_ARGB32)
    image.fill(0xFF101418)
    painter = QPainter(image)
    painter.drawText(12, 24, "sonar-analyzer")
    painter.end()
    # PySide6 TASLAGI bicim adini `bytes` sanıyor, calisma zamani `str`
    # istiyor; taslak yanlis oldugu icin cagri tiplenmis bir sarmalayiciyla
    # yapilir (tools/make_app_icon.py ile ayni durum).
    saver = cast("Callable[[str, str], bool]", image.save)
    if not saver(str(path), "PNG"):
        raise RuntimeError("Qt PNG yazici kullanilamadi")
