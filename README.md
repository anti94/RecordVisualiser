# SONAR Data Analyzer

`.bin` kayıtlarındaki SONAR/sensör verilerini, BIT sonuçlarını, transmisyon bilgilerini ve olay
kayıtlarını tek masaüstü uygulamada açan, çözümleyen, görselleştiren ve dışa aktaran Python
uygulaması.

Ana ürün hedefi: [`SONAR Veri Analiz Panosu Mockup’ı.png`](<SONAR Veri Analiz Panosu Mockup’ı.png>)
görselindeki analiz panosu.

## Durum

Sürüm **4.5.0** (tek kaynak: [`VERSION`](VERSION)). Planın yedi milestone'u da kapandı:

| Milestone | Etiket | İçerik |
| --- | --- | --- |
| 1 | `ms/01-format-ready` | Format sözleşmesi ve kabul ölçütleri |
| 2 | `ms/02-app-shell` | Uygulama kabuğu ve üç sütunlu yerleşim |
| 3 | `ms/03-bin-reader` | `.bin` okuma, indeks, olay/BIT/TX çıkarımı |
| 4 | `ms/04-mvp` | Çizim, gezinme, dışa aktarma |
| 5 | `ms/05-analysis` | FFT/PSD, STFT, DSP zinciri, türetilmiş kanal |
| 6 | `ms/06-live-recording` | Canlı bağlantı ve diske kayıt |
| 7 | `ms/07-distribution` | Paketleme, NSIS kurulum, yayın kapıları |

Planın 354 numaralı işinin tamamı bitti. Kalan 19 kontrol maddesi
[`docs/notes/todo.md`](docs/notes/todo.md) içinde; bunların 14'ü paydaş sorusu,
2'si dış veri bağımlılığı, 1'i hiç tetiklenmemiş bir koşul, 2'si ertelenen
çoklu-panel işi. Hiçbiri kod yazılarak kapatılamaz durumda değil ama hiçbiri de
bu depoda tek başına kapatılamaz.

Testler: **5295** test, tamamı geçiyor. Tip denetimi pyright **strict**, sıfır hata.

> **Uyarı — gerçek donanım doğrulaması yok.** Elde gerçek cihaz kaydı yoktur. Format
> sözleşmesi taslaktır ve sentetik veriyle çalışılmaktadır; sentetik sonuçlar gerçek
> donanım doğrulaması sayılmaz. Açık kararlar `E-01`/`E-02`, ayrıntı
> [`docs/format/inventory.md`](docs/format/inventory.md).

> **Uyarı — Profil B arayüzden açılamaz.** `io/decoders/` altında tam bir Profil B
> çözücüsü ve testleri var, ama dosya açma yolu yalnız `FileRecordingRepository`
> üretiyor ve o da yalnız Profil A okuyor. Bir Profil B dosyası `Open .bin File` ile
> seçilirse `InvalidMagicError` alınır. Ayrıntı:
> [`docs/architecture/c4-model.md`](docs/architecture/c4-model.md).

## Videolu demo

`docs/demo/sonar-analyzer-demo.mp4` — 55 saniye, 14 sahne. Video çalışan uygulamanın
kendisidir: `tools/demo_video.py` ana pencereyi görünmez bir Qt platformunda açar,
senaryoyu uygulamanın genel API'siyle sürer ve her adımda pencereyi yakalar.

```powershell
.venv\Scripts\python.exe tools\demo_video.py --out docs\demo\sonar-analyzer-demo.mp4
```

Üçüncü sahneden sonrası **simülasyon verisidir** ve altyazıda böyle yazar. Ayrıntı:
[`docs/demo/README.md`](docs/demo/README.md).

## Kurulum (son kullanıcı)

Windows kurulum paketi kullanıcı başına kurulur, yönetici hakkı istemez:

```text
dist/sonar-analyzer-<sürüm>-setup.exe
```

Paketleme PyInstaller `onedir` + NSIS'tir; ayrıntı
[`docs/adr/ADR-012-packaging.md`](docs/adr/ADR-012-packaging.md). Yayın ve geri dönüş
prosedürü [`docs/release/release-and-rollback.md`](docs/release/release-and-rollback.md),
bilinen sorunlar [`docs/release/known-issues.md`](docs/release/known-issues.md).

## Belgeler

**Mimari ve plan**

| Konu | Belge |
| --- | --- |
| Geliştirme planı (ana belge) | [`plan.md`](plan.md) |
| C4 mimari modeli (bağlam → kod) | [`docs/architecture/c4-model.md`](docs/architecture/c4-model.md) |
| Videolu demo | [`docs/demo/README.md`](docs/demo/README.md) |
| Mimari karar kayıtları | [`docs/adr/README.md`](docs/adr/README.md) |
| Yapılacaklar listesi | [`docs/notes/todo.md`](docs/notes/todo.md) |
| İş günlüğü ve süreler | [`docs/notes/worklog.md`](docs/notes/worklog.md) |
| Açık kararlar / dış bağımlılıklar | [`docs/notes/open-decisions.md`](docs/notes/open-decisions.md) |

**Dosya biçimi**

| Konu | Belge |
| --- | --- |
| Çözücü kılavuzu (A v1 / A v2 / B ayrımı) | [`docs/format/decoder-guide.md`](docs/format/decoder-guide.md) |
| Profil A sözleşmesi | [`docs/format/profile-a.md`](docs/format/profile-a.md) |
| Profil B sözleşmesi | [`docs/format/profile-b.md`](docs/format/profile-b.md) |
| Örnek dosya envanteri | [`docs/format/inventory.md`](docs/format/inventory.md) |
| 125 ms periyot ve adlandırma | [`docs/format/timing-and-naming.md`](docs/format/timing-and-naming.md) |
| Kanal eşlemesi | [`docs/format/channel-map.md`](docs/format/channel-map.md) |
| Fixture beklentileri | [`docs/format/fixture-valid-8records.md`](docs/format/fixture-valid-8records.md) · [`docs/format/fixture-corrupt.md`](docs/format/fixture-corrupt.md) |

**Kullanım**

| Konu | Belge |
| --- | --- |
| Ana ekran | [`docs/guide/ana-ekran.md`](docs/guide/ana-ekran.md) |
| Klavye ve mouse | [`docs/guide/klavye-ve-mouse.md`](docs/guide/klavye-ve-mouse.md) |
| Filtre ve spektral analiz | [`docs/guide/filtre-ve-spektral-analiz.md`](docs/guide/filtre-ve-spektral-analiz.md) |
| Canlı bağlantı | [`docs/guide/canli-baglanti.md`](docs/guide/canli-baglanti.md) |
| Kullanıcı senaryoları | [`docs/scenarios.md`](docs/scenarios.md) |

**Arayüz, başarım, yayın**

| Konu | Belge |
| --- | --- |
| Arayüz yerleşimi ve kabul listesi | [`docs/ui/layout-map.md`](docs/ui/layout-map.md) · [`docs/ui/acceptance-checklist.md`](docs/ui/acceptance-checklist.md) |
| Mockup karşılaştırması (paketli) | [`docs/ui/packaged-mockup-comparison.md`](docs/ui/packaged-mockup-comparison.md) |
| Paketli kabul turu | [`docs/acceptance/packaged-acceptance.md`](docs/acceptance/packaged-acceptance.md) |
| Performans bütçesi | [`docs/perf/budget.md`](docs/perf/budget.md) |
| Büyük dosya ölçümleri | [`docs/perf/large-file-verdict.md`](docs/perf/large-file-verdict.md) |
| Kalite kapıları (CI) | [`docs/ci/quality-gates.md`](docs/ci/quality-gates.md) |
| Sürüm notları v4.0.0 | [`docs/release/release-notes-v4.0.0.md`](docs/release/release-notes-v4.0.0.md) |

## Geliştirme kurulumu

Tek komut (Windows, PowerShell):

```powershell
powershell -ExecutionPolicy Bypass -File tools/setup-dev.ps1
```

Betik sanal ortamı oluşturur, paketi `[dev]` ekstrasıyla kurar ve beş doğrulama yapar
(paket import, ruff lint, ruff format, pyright, pytest).
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

### Uygulamayı çalıştırma

Proje kökünde PowerShell ile:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/run.ps1
```

Betik projenin `.venv` ortamını kullanır; ortamı etkinleştirmek gerekmez. Başka bir
klasörden çağırırken `run.ps1` için tam yol verilebilir. Pencere kapandığında uygulamanın
çıkış kodunu döndürür.

İlk kurulumda GUI bağımlılıklarını da yükleyin:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/setup-dev.ps1 -WithGui -Locked
```

| Seçenek | Komut |
| --- | --- |
| Sürümü göster | `powershell -NoProfile -ExecutionPolicy Bypass -File tools/run.ps1 -Version` |
| Pencere göstermeden başlangıcı doğrula | `powershell -NoProfile -ExecutionPolicy Bypass -File tools/run.ps1 -NoWindow` |

Doğrudan giriş noktası: `.venv\Scripts\python.exe -m sonar_analyzer`.

**Open .bin File** (`Ctrl+O`) ile gerçek bir kayıt açabilirsiniz; birden fazla
dosya seçilebilir. Yükleme arka planda çalışır, alt şeritte ilerleme ve iptal
görünür. Denemek için depodaki `tests/fixtures/valid_8records.bin` kullanılabilir.
**Tools → Load Simulation Data** (`Ctrl+Shift+S`) ise dosyasız sahte veri yükler.
Her iki durumda da bir kanala çift tıklayarak grafiği açabilirsiniz.

### Testler

| Seçim | Komut |
| --- | --- |
| Tümü | `python -m pytest` |
| Qt gerektirmeyenler | `python -m pytest -m "not gui"` |
| Yalnız GUI | `python -m pytest -m gui` |

Uygulamanın ekran görüntüsünü almak için (görünür pencere açmaz):

```powershell
.venv\Scripts\python.exe tools/screenshot.py docs/ui/app.png
```

> **Not:** Qt'nin `offscreen` platformu sistem yazı tiplerini kendiliğinden bulmaz.
> `QT_QPA_FONTDIR` ayarlanmazsa tüm metinler kutu olarak çizilir; betik ve test
> yapılandırması bunu kendiliğinden ayarlar.

CI ile birebir aynı kontrolleri yerelde koşmak için:

```powershell
powershell -ExecutionPolicy Bypass -File tools/check.ps1        # kontrol et
powershell -ExecutionPolicy Bypass -File tools/check.ps1 -Fix   # düzeltip kontrol et
```

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
src/sonar_analyzer/     uygulama paketi (katmanlar için bkz. docs/architecture/c4-model.md)
tests/                  unit · integration · gui · performance · fixtures
tools/                  yardımcı betikler (fixture üretici, ölçüm, paketleme, yayın kapıları)
packaging/              PyInstaller spec, NSIS betiği, uygulama ikonu
docs/                   mimari, format, arayüz, kullanım, performans, ADR, yayın
dist/                   üretilen paketler ve kurulum dosyaları (sürüm denetimi dışı)
```
