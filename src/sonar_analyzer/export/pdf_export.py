"""Statik grafiği PDF olarak dışa aktarma — `F4-086`.

PNG bir ekran görüntüsüdür (`F3-062`), SVG vektöreldir ama tek bir
çizimdir (`F3-063`). Rapora giren çıktı bundan fazlasını ister: grafiğin
**hangi kayıttan**, **hangi işlemlerden sonra** çıktığı belgede yazmalı,
yoksa sayfa tek başına anlamsızdır.

Bu modül vektörel bir PDF üretir ve bilgiyi **iki yere** koyar:

* Sayfanın üstüne çizilen bir **başlık bloğu** — yazdırıldığında da
  görünür.
* PDF'in **XMP metadata**'sı — belge özelliklerinden okunur ve dosyanın
  içinde sıkıştırılmadan durur; böylece çıktı programla da denetlenebilir.

İkisi aynı `PlotDocumentInfo.lines()` listesinden üretilir; sayfada yazan
ile metadata'da yazan ayrışamaz.

Grafik `QPainter` üzerinden `QPdfWriter`'a çizilir: pyqtgraph'ın çizgi ve
metin komutları PDF'e **vektör** olarak gider, piksel olarak değil.

Başlık bloğunun kendisi saf veridir ve Qt olmadan doğrulanır; çizim
kısmı Qt gerektirir.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import QByteArray, QMarginsF, QPoint
from PySide6.QtGui import QFont, QPageLayout, QPageSize, QPainter, QPdfWriter
from PySide6.QtWidgets import QWidget

#: Belgenin üreticisi — PDF özelliklerinde görünür.
CREATOR = "SONAR Data Analyzer"
#: Başlık bloğu ile grafik arasındaki boşluk (nokta).
HEADER_GAP_PT = 18
#: Başlık satırı yüksekliği (nokta).
HEADER_LINE_PT = 16
#: Sayfa kenar boşluğu (mm).
PAGE_MARGIN_MM = 12.0
#: Çizim çözünürlüğü (dpi); vektör çıktıda koordinat hassasiyetini belirler.
RESOLUTION_DPI = 300
NS_PER_SECOND = 1_000_000_000


class PdfExportError(ValueError):
    """PDF üretilemiyor (boş grafik, yazılamayan hedef vb.)."""


@dataclass(frozen=True)
class PlotDocumentInfo:
    """Sayfanın üstüne ve metadata'ya yazılacak bilgi.

    `processing` boşsa "işlem uygulanmadı" yazılır — boş bırakmak,
    okuyucunun işlem olup olmadığını bilmemesine yol açardı.
    """

    title: str
    source: str
    processing: str = ""
    time_range: str = ""
    generated_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise PdfExportError("PDF başlığı boş olamaz")
        if not self.source.strip():
            raise PdfExportError("PDF kaynak bilgisi boş olamaz")

    @property
    def processing_text(self) -> str:
        return self.processing.strip() or "İşlem uygulanmadı"

    def lines(self) -> list[str]:
        """Sayfada ve metadata'da **aynı sırayla** görünecek satırlar."""
        moment = self.generated_at or datetime.now(tz=timezone.utc)
        lines = [
            self.title.strip(),
            f"Kaynak: {self.source.strip()}",
            f"İşlem: {self.processing_text}",
        ]
        if self.time_range.strip():
            lines.append(f"Aralık: {self.time_range.strip()}")
        lines.append(f"Üretildi: {moment.astimezone(timezone.utc).isoformat()}")
        return lines

    def xmp_metadata(self) -> bytes:
        """Satırları PDF'e gömülecek XMP belgesine çevirir."""
        rows = "".join(f"<rdf:li>{_escape(line)}</rdf:li>" for line in self.lines())
        return (
            '<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>'
            '<x:xmpmeta xmlns:x="adobe:ns:meta/">'
            '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
            '<rdf:Description xmlns:dc="http://purl.org/dc/elements/1.1/">'
            f"<dc:title>{_escape(self.title.strip())}</dc:title>"
            f"<dc:source>{_escape(self.source.strip())}</dc:source>"
            f"<dc:description><rdf:Alt>{rows}</rdf:Alt></dc:description>"
            "</rdf:Description></rdf:RDF></x:xmpmeta>"
            '<?xpacket end="w"?>'
        ).encode()


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


@dataclass(frozen=True)
class PdfExportResult:
    """Yazma sonucu — çağıran ve testler için özet."""

    path: Path
    header_lines: tuple[str, ...]


def export_widget_pdf(
    widget: QWidget,
    path: str | Path,
    info: PlotDocumentInfo,
    *,
    page_size: QPageSize.PageSizeId = QPageSize.PageSizeId.A4,
    landscape: bool = True,
) -> PdfExportResult:
    """`widget`'ı başlık bloğuyla birlikte vektörel PDF'e yazar.

    * `PdfExportError` — widget'ın boyutu sıfır (henüz gösterilmemiş) ya
      da Qt çizim aygıtını açamadı.
    """
    width, height = widget.width(), widget.height()
    if width <= 0 or height <= 0:
        raise PdfExportError("Grafik boyutu sıfır; dışa aktarmadan önce pencere gösterilmeli")

    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    lines = info.lines()

    writer = QPdfWriter(str(dest))
    writer.setResolution(RESOLUTION_DPI)
    writer.setTitle(info.title.strip())
    writer.setCreator(CREATOR)
    writer.setDocumentXmpMetadata(QByteArray(info.xmp_metadata()))
    layout = QPageLayout(
        QPageSize(page_size),
        QPageLayout.Orientation.Landscape if landscape else QPageLayout.Orientation.Portrait,
        QMarginsF(PAGE_MARGIN_MM, PAGE_MARGIN_MM, PAGE_MARGIN_MM, PAGE_MARGIN_MM),
        QPageLayout.Unit.Millimeter,
    )
    writer.setPageLayout(layout)

    painter = QPainter()
    if not painter.begin(writer):
        raise PdfExportError(f"PDF açılamadı: {dest}")
    try:
        header_height = _draw_header(painter, writer, lines)
        _draw_widget(painter, writer, widget, top=header_height)
    finally:
        painter.end()

    return PdfExportResult(path=dest, header_lines=tuple(lines))


def _points_to_device(painter: QPainter, points: float) -> int:
    """Nokta (1/72 inç) cinsinden ölçüyü aygıt piksellerine çevirir."""
    device = painter.device()
    dpi = device.logicalDpiY() if device is not None else RESOLUTION_DPI
    return round(points * dpi / 72.0)


def _draw_header(painter: QPainter, writer: QPdfWriter, lines: list[str]) -> int:
    """Başlık bloğunu çizer ve kapladığı yüksekliği döndürür."""
    line_height = _points_to_device(painter, HEADER_LINE_PT)
    title_font = QFont(painter.font())
    title_font.setPointSize(12)
    title_font.setBold(True)
    body_font = QFont(painter.font())
    body_font.setPointSize(9)

    y = line_height
    for index, line in enumerate(lines):
        painter.setFont(title_font if index == 0 else body_font)
        painter.drawText(0, y, line)
        y += line_height
    return y + _points_to_device(painter, HEADER_GAP_PT)


def _draw_widget(painter: QPainter, writer: QPdfWriter, widget: QWidget, *, top: int) -> None:
    """Grafiği başlığın altına, sayfaya sığacak şekilde ölçekleyerek çizer."""
    page = writer.pageLayout().paintRectPixels(writer.resolution())
    available_width = max(1, page.width())
    available_height = max(1, page.height() - top)
    scale = min(available_width / widget.width(), available_height / widget.height())

    painter.save()
    painter.translate(0, top)
    painter.scale(scale, scale)
    widget.render(painter, QPoint(0, 0))
    painter.restore()
