# SONAR Data Analyzer

`.bin` kayıtlarındaki SONAR/sensör verilerini, BIT sonuçlarını, transmisyon bilgilerini ve olay
kayıtlarını tek masaüstü uygulamada açan, çözümleyen, görselleştiren ve dışa aktaran Python
uygulaması.

Ana ürün hedefi: [`SONAR Veri Analiz Panosu Mockup’ı.png`](<SONAR Veri Analiz Panosu Mockup’ı.png>)
görselindeki analiz panosu.

## Durum

Geliştirme sürümü. Güncel sürüm [`VERSION`](VERSION) dosyasındadır.
İlerleme: [`docs/notes/todo.md`](docs/notes/todo.md) · Tamamlanan fazlar:
`ms/01-format-ready` (format sözleşmesi ve kabul ölçütleri).

> **Uyarı:** Elde gerçek cihaz kaydı yoktur. Format sözleşmesi taslaktır ve sentetik veriyle
> çalışılmaktadır; sentetik sonuçlar gerçek donanım doğrulaması sayılmaz.
> Ayrıntı: [`docs/format/inventory.md`](docs/format/inventory.md).

## Belgeler

| Konu | Belge |
| --- | --- |
| Geliştirme planı (ana belge) | [`plan.md`](plan.md) |
| Yapılacaklar listesi | [`docs/notes/todo.md`](docs/notes/todo.md) |
| İş günlüğü ve süreler | [`docs/notes/worklog.md`](docs/notes/worklog.md) |
| Açık kararlar / dış bağımlılıklar | [`docs/notes/open-decisions.md`](docs/notes/open-decisions.md) |
| Örnek dosya envanteri | [`docs/format/inventory.md`](docs/format/inventory.md) |
| Profil A format sözleşmesi | [`docs/format/profile-a.md`](docs/format/profile-a.md) |
| 125 ms periyot ve adlandırma | [`docs/format/timing-and-naming.md`](docs/format/timing-and-naming.md) |
| Kanal eşlemesi | [`docs/format/channel-map.md`](docs/format/channel-map.md) |
| Fixture beklentileri | [`docs/format/fixture-valid-8records.md`](docs/format/fixture-valid-8records.md) · [`docs/format/fixture-corrupt.md`](docs/format/fixture-corrupt.md) |
| Kullanıcı senaryoları | [`docs/scenarios.md`](docs/scenarios.md) |
| Arayüz yerleşimi ve kabul listesi | [`docs/ui/layout-map.md`](docs/ui/layout-map.md) · [`docs/ui/acceptance-checklist.md`](docs/ui/acceptance-checklist.md) |
| Performans bütçesi | [`docs/perf/budget.md`](docs/perf/budget.md) |
| Mimari karar kayıtları | [`docs/adr/README.md`](docs/adr/README.md) |

## Geliştirme kurulumu

Tek komut (Windows, PowerShell):

```powershell
powershell -ExecutionPolicy Bypass -File tools/setup-dev.ps1
```

Betik sanal ortamı oluşturur, paketi `[dev]` ekstrasıyla kurar ve üç doğrulama yapar
beş doğrulama yapar (paket import, ruff lint, ruff format, pyright, pytest).
Yeniden çalıştırılabilir; mevcut `.venv` varsa kullanır.

| Seçenek | Etki |
| --- | --- |
| `-Recreate` | Mevcut `.venv` silinip sıfırdan kurulur |
| `-WithGui` | PySide6 + PyQtGraph ekstrası da kurulur |
| `-Locked` | Bağımlılıklar `requirements-dev.lock` (ve `-WithGui` ile `requirements-gui.lock`)
içindeki sabit sürümlerden kurulur |

Elle kurulum (diğer platformlar veya betiği kullanmak istemeyenler için):

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e ".[dev]"     # Windows
# source .venv/bin/activate && pip install -e ".[dev]"  # Linux/macOS
```

Arayüz ve DSP katmanları ayrı kurulur:

```bash
pip install -e ".[gui]"   # PySide6 + PyQtGraph
pip install -e ".[dsp]"   # SciPy
```

### Testler

| Seçim | Komut |
| --- | --- |
| Tümü | `python -m pytest` |
| Qt gerektirmeyenler | `python -m pytest -m "not gui"` |
| Yalnız GUI | `python -m pytest -m gui` |

GUI testleri `QT_QPA_PLATFORM=offscreen` ile görünür pencere açmadan koşar; PySide6 kurulu
değilse otomatik atlanır. `tests/unit/test_layering.py`, çekirdek katmanların Qt yüklemediğini
ayrı bir alt süreçte doğrular — katman kuralı belgeyle değil testle korunur.

Çekirdek katman (domain, io, repository, processing) **Qt'ye bağımlı değildir**; bu ayrım
`pyproject.toml` içinde bağımlılık seviyesinde zorlanır.

### Kontroller

```bash
.venv/Scripts/python.exe -m pytest               # testler
.venv/Scripts/python.exe -m ruff check .         # lint (salt kontrol)
.venv/Scripts/python.exe -m ruff format --check . # bicim (salt kontrol)
.venv/Scripts/python.exe -m ruff format .        # bicimlendir
.venv/Scripts/python.exe -m pyright              # tip kontrolu
```

Ruff yapılandırması `pyproject.toml` içindedir: satır uzunluğu 100, kural setleri
`E, F, W, I, UP, B, SIM, RUF`. Markdown dosyaları kapsam dışıdır — belgelerdeki Python
örnekleri bilerek elle yazılmıştır.

Pyright **strict** modda çalışır (`[tool.pyright]`). Pyright ilk çalıştırmada kendi Node
çalışma zamanını indirir; ağ erişimi olmayan ortamda bu adım atlanmalıdır.

> **Python sürümü:** plan Python **3.12** hedefliyor; bu makinede yalnız **3.9.13** kurulu olduğu
> için `requires-python` geçici olarak `>=3.9`'dur. Bkz. açık karar **D-20**.

## Depo düzeni

```text
plan.md                 ana geliştirme planı
VERSION                 uygulama sürümünün tek kaynağı
pyproject.toml          paket tanımı ve araç yapılandırması
src/sonar_analyzer/     uygulama paketi (katmanlar için bkz. paket docstring'i)
tests/                  unit · integration · gui · performance · fixtures
tools/                  yardımcı betikler (todo eşitleme, fixture üretici)
docs/                   format, arayüz, performans, ADR ve notlar
```
