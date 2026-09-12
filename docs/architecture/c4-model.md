# C4 Mimari Modeli

Bu belge uygulamayı C4 modelinin dört seviyesinde anlatır: **Bağlam**, **Konteyner**,
**Bileşen** ve **Kod**. Diyagramlar Mermaid ile çizilmiştir.

> **Sözdizimi notu:** Mermaid'in yerleşik `C4Context` / `C4Container` sözdizimi hâlâ deneysel
> ve yerleşimi denetlenemiyor; kutular büyük modellerde üst üste biniyor. Bu yüzden
> diyagramlar `flowchart` ile çizildi, **C4 öğe adlandırması korunarak**
> (`[Person]`, `[Software System]`, `[Container]`, `[Component]`). Her yerde aynı
> şekilde çizilir.

Kaynak: `src/sonar_analyzer/` ağacı, sürüm **4.5.0**. Bağımlılık okları belgeden değil,
modüllerdeki gerçek `import` satırlarından çıkarıldı.

---

## Seviye 1 — Sistem Bağlamı

Kimin kullandığı ve sistemin dışarıda neye dokunduğu.

```mermaid
flowchart TB
    operator["<b>Operatör</b><br/><i>[Person]</i><br/>Kaydı açar, olay ve BIT<br/>sonuçlarını gözden geçirir"]
    engineer["<b>Analiz Mühendisi</b><br/><i>[Person]</i><br/>Spektral analiz, DSP zinciri,<br/>dışa aktarma"]

    subgraph sinir["Sistem Sınırı"]
        app["<b>SONAR Veri Analiz Panosu</b><br/><i>[Software System]</i><br/>Kayıtları açar, çözer, doğrular,<br/>görselleştirir ve dışa aktarır<br/>Python 3.9 · PySide6 masaüstü"]
    end

    bin[("<b>Kayıt Dosyaları</b><br/><i>[External System]</i><br/>Profil A v1/v2 · Profil B<br/>ikili .bin")]
    device["<b>SONAR Cihazı</b><br/><i>[External System]</i><br/>TCP · UDP · Seri port<br/>canlı telemetri"]
    profile[("<b>Windows Kullanıcı Profili</b><br/><i>[External System]</i><br/>APPDATA · LOCALAPPDATA")]
    targets[("<b>Dışa Aktarma Hedefleri</b><br/><i>[External System]</i><br/>CSV · PNG · SVG · PDF · JSON")]

    operator -->|"kayıt açar, zamanda gezinir"| app
    engineer -->|"analiz eder, dışa aktarır"| app
    app -->|"okur ve çözer"| bin
    app -.->|"canlı akış alır<br/>gerçek cihazla doğrulanmadı"| device
    app -->|"ayar, günlük ve indeks yazar"| profile
    app -->|"kullanıcı isteğiyle üretir"| targets

    classDef person fill:#0b4884,stroke:#073763,color:#fff
    classDef system fill:#1168bd,stroke:#0b4884,color:#fff
    classDef ext fill:#6b6b6b,stroke:#4d4d4d,color:#fff
    class operator,engineer person
    class app system
    class bin,device,profile,targets ext
```

**Kesik ok neden kesik:** Canlı bağlantı katmanı yazıldı ve testleri var, ama elde gerçek
cihaz kaydı yok. Açık karar `E-01`/`E-02`; ayrıntı `docs/notes/open-decisions.md`.

---

## Seviye 2 — Konteynerler

Uygulama **tek işletim sistemi süreci**. Bu yüzden buradaki konteyner ayrımı
"ayrı çalışan servisler" değil, **süreç içindeki yürütme bağlamları ve kalıcı veri
depoları**dır.

```mermaid
flowchart TB
    operator["<b>Operatör / Mühendis</b><br/><i>[Person]</i>"]

    subgraph proc["SONAR Veri Analiz Panosu — tek süreç"]
        gui["<b>GUI Katmanı</b><br/><i>[Container: PySide6 + PyQtGraph]</i><br/>Ana pencere, dock'lar, grafikler<br/>Qt ana iş parçacığı"]
        core["<b>Çekirdek Katman</b><br/><i>[Container: saf Python + NumPy]</i><br/>Çözümleme, indeks, sorgu, DSP<br/><b>Qt bilmez</b>"]
        workers["<b>Arka Plan İşçileri</b><br/><i>[Container: QThread]</i><br/>Dosya yükleme, DSP, dışa aktarma,<br/>canlı alım"]
    end

    settings[("<b>settings.json</b><br/><i>[Data Store]</i><br/>%APPDATA%/SonarAnalyzer/")]
    logs[("<b>sonar_analyzer.log</b><br/><i>[Data Store]</i><br/>%LOCALAPPDATA%/")]
    index[("<b>.bin.sidx indeks önbelleği</b><br/><i>[Data Store]</i><br/><b>kayıt dosyasının yanında</b>")]
    ws[("<b>Workspace .json</b><br/><i>[Data Store]</i><br/>kullanıcının seçtiği yol")]
    bin[("<b>Kayıt .bin</b><br/><i>[External]</i>")]

    operator -->|"kullanır"| gui
    gui -->|"sorgular"| core
    gui -->|"işi devreder"| workers
    workers -->|"çağırır"| core
    core -->|"okur"| bin
    core -->|"yazar ve geri okur"| index
    gui -->|"okur / yazar"| settings
    gui -->|"okur / yazar"| ws
    core -->|"yazar"| logs

    classDef person fill:#0b4884,stroke:#073763,color:#fff
    classDef cont fill:#438dd5,stroke:#2e6295,color:#fff
    classDef store fill:#7a5195,stroke:#5c3d70,color:#fff
    classDef ext fill:#6b6b6b,stroke:#4d4d4d,color:#fff
    class operator person
    class gui,core,workers cont
    class settings,logs,ws store
    class bin ext
```

### Kalıcı veri depoları

| Depo | Konum | Biçim | Amaç |
| --- | --- | --- | --- |
| Ayarlar | `%APPDATA%\SonarAnalyzer\settings.json` | JSON, şema sürümlü | Tema, son dosyalar, korelasyon toleransı |
| Günlük | `%LOCALAPPDATA%\...\sonar_analyzer.log` | metin | Tanılama |
| İndeks önbelleği | **kayıt dosyasının yanında**, `<ad>.bin.sidx` | JSON | Kayıt/olay/kanal indeksi; yeniden çözümlemeyi atlar |
| Workspace | kullanıcının seçtiği yol | JSON | Açık kanallar, düzen, görünüm durumu |

> İndeks önbelleğinin kurulum dizinine değil **kaydın yanına** yazılması bilinçli:
> salt okunur `Program Files` altına yazma denemesi olmaz. Karşılığında kayıt klasörü
> salt okunur bir paylaşımdaysa önbellek üretilemez.

---

## Seviye 3 — Bileşenler

Süreç içindeki Python alt paketleri. Oklar **gerçek `import` yönünü** gösterir.

```mermaid
flowchart TB
    subgraph ui_l["Sunum — Qt'yi yalnız bu katman bilir"]
        ui["<b>ui</b> · 48 modül<br/><i>[Component: PySide6]</i><br/>main_window · docks · plots<br/>cards · panels · shortcuts"]
        export["<b>export</b> · 6 modül<br/><i>[Component]</i><br/>csv · image · pdf · json"]
    end

    subgraph app_l["Uygulama"]
        application["<b>application</b> · 20 modül<br/><i>[Component]</i><br/>file_loader · playback_state<br/>view_history · export_controller"]
        settings["<b>settings</b> · 2 modül<br/><i>[Component]</i><br/>şema sürümlü ayar deposu"]
        workspace["<b>workspace</b> · 7 modül<br/><i>[Component]</i><br/>oturum kaydı ve geri yükleme"]
    end

    subgraph dom_l["Çekirdek — Qt bağımlılığı yok"]
        repository["<b>repository</b> · 10 modül<br/><i>[Component]</i><br/>RecordingRepository sözleşmesi<br/>file · mock · live · derived"]
        io["<b>io</b> · 64 modül<br/><i>[Component]</i><br/>decoders · index · live · readers<br/>profile_a / profile_b biçimleri"]
        processing["<b>processing</b> · 7 modül<br/><i>[Component]</i><br/>filtre zinciri · pencereleme<br/>yeniden örnekleme"]
        analysis["<b>analysis</b> · 12 modül<br/><i>[Component]</i><br/>spectrum · psd · stft<br/>istatistik · downsampling"]
        recording["<b>recording</b> · 7 modül<br/><i>[Component]</i><br/>canlı akışı diske yazma<br/>döndürme ve oturum"]
        domain["<b>domain</b> · 12 modül<br/><i>[Component]</i><br/>Channel · DataChunk · Event<br/>TimeRange · Quality"]
        logging_c["<b>logging</b> · 2 modül<br/><i>[Component]</i>"]
    end

    ui --> application
    ui --> repository
    ui --> export
    ui --> analysis
    ui --> processing
    ui --> settings
    ui --> workspace
    ui --> recording
    ui --> io
    ui --> domain

    application --> repository
    application --> processing
    application --> export
    application --> settings
    application --> domain

    repository --> io
    repository --> analysis
    repository --> processing
    repository --> domain

    io --> analysis
    io --> domain
    io --> logging_c
    processing --> domain
    analysis --> domain
    export --> domain
    recording --> io
    recording --> domain
    settings --> domain

    classDef pres fill:#438dd5,stroke:#2e6295,color:#fff
    classDef appc fill:#2f8f5b,stroke:#1f6b42,color:#fff
    classDef corec fill:#7a5195,stroke:#5c3d70,color:#fff
    class ui,export pres
    class application,settings,workspace appc
    class repository,io,processing,analysis,recording,domain,logging_c corec
```

### Katman kuralı nasıl korunuyor

Kural şu: **çekirdek katman (domain, io, repository, processing) Qt'yi bilmez.**
Bu belgeyle değil testle korunuyor. `tests/unit/test_layering.py`, her çekirdek paketi
**temiz bir alt süreçte** içe aktarır ve `sys.modules` içinde `PySide6`, `PyQt5/6`,
`shiboken6`, `pyqtgraph` veya `matplotlib` belirip belirmediğine bakar. Aynı süreçte
koşsaydı, daha önce Qt yüklemiş başka bir test sonucu yanıltırdı.

### Bildirilen sıralamayı delen bağımlılıklar

Paket docstring'i katmanları `domain → io → repository → processing → application → ui`
sırasıyla anlatıyor. Gerçek `import` grafiği bu sırayı **beş yerde** ters yönde deliyor.
Hiçbiri Qt kuralını bozmuyor, bu yüzden hiçbiri testle yakalanmıyor:

| Delik | Dosya | Ne içe aktarıyor |
| --- | --- | --- |
| `domain → io` | `domain/correlation.py` | `profile_a_format.RECORD_PERIOD_NS` |
| `domain → processing` | `domain/derived_channel_definition.py` | `ProcessingChain`, `ProcessingStep` |
| `io → analysis` | `io/decoders/profile_b_indexed_query.py`, `io/live/ring_buffer.py` | `downsample_chunk`, `streaming_envelope` |
| `io → repository` | `io/decoders/profile_b_indexed_query.py`, `io/live/file_replay_source.py` | `MemoryBoundedCache`, `RecordingRepository` |
| `repository → application` | `repository/derived_repository.py` | `derived_sample_rate` |

Ayrıca `application/layout_report.py`, `ui`'yi içe aktarıyor; bu **kasıtlı** ve dar
kapsamlı: bir içe aktarma `TYPE_CHECKING` altında, diğeri fonksiyon içinde. Modül
seviyesinde bağımlılık oluşturmuyor, yalnız `--layout-report` tanılama yolu çalışırken
gerçekleşiyor.

**Bu bir arıza raporu değil, bir ölçüm.** Beş deliğin hiçbiri çalışma zamanında hata
üretmiyor. Ama katman sırası yalnız docstring'de yazdığı için, sıralamayı koruyan bir
test olmadığı sürece yenileri sessizce eklenebilir.

---

## Seviye 4 — Kod: bir kayıt açılıp çizilene kadar

C4'ün dördüncü seviyesi her sınıfı çizmez, **bir yolu** açar. En çok kullanılan yol bu:
kullanıcı bir `.bin` açar ve bir kanalı grafikte görür.

```mermaid
sequenceDiagram
    autonumber
    actor U as Operatör
    participant W as MainWindow<br/>[ui]
    participant S as FileLoadService<br/>[application]
    participant T as QThread işçisi
    participant R as FileRecordingRepository<br/>[repository]
    participant D as decoders + index<br/>[io]
    participant P as PlotPanel<br/>[ui.plots]

    U->>W: Ctrl+O — Open .bin File
    W->>W: request_open_files() → QFileDialog
    W->>S: submit(paths)
    S->>T: iş kuyruğa alınır
    Note over W: Arayüz donmaz —<br/>alt şeritte ilerleme ve iptal görünür

    T->>R: default_loader(path) → open(path)
    R->>R: MappedSource — dosya kopyalanmaz,<br/>salt okunur eşleme
    R->>D: read_validated_header(data)
    D-->>R: magic, sürüm, header_size, record_size
    Note over R: v1 ise CRC yok —<br/>bütünlük doğrulanmadı uyarısı biriktirilir

    R->>D: load_or_build_record_index(data, header, .sidx)
    alt Önbellek geçerli
        D-->>R: kayıtlar yeniden kullanıldı
    else Önbellek yok veya parmak izi tutmuyor
        D->>D: kayıt indeksi baştan kurulur
        D-->>R: kayıtlar + yeni .sidx yazıldı
    end
    Note over D: .sidx yazılamazsa (salt okunur klasör)<br/>indeks bellekte kurulur, açma sürer

    T-->>S: FileLoadResult (kuyruklu sinyal)
    S-->>W: yükleme bitti + uyarılar
    W->>W: set_repository(repository)
    W->>R: channels()
    R-->>W: 8 kanal (ad, birim, örnekleme hızı)
    W->>W: Data Explorer ağacı dolar

    U->>W: kanala çift tık
    W->>R: query(channel_id, span, max_points=nokta bütçesi)
    R->>D: indeksten kayıtları oku, ölçekle, seyrelt
    D-->>R: DataChunk (değerler + kalite bayrakları)
    R-->>W: DataChunk
    W->>P: set_channel(channel, chunk, time_origin_ns)
    W->>W: refresh_analysis_views(channel, değerler)
    Note over W: Spectrum ve Spectrogram sekmeleri<br/>gizliyken hesaplamaz —<br/>açılınca aynı snapshot'ı alır
```

### Bu yolda dikkat çeken üç karar

**Nokta bütçesi.** `query` çağrısı `max_points` alır ve bu değer grafiğin piksel
genişliğinden türer. Ekranda 1200 piksel varsa 10 milyon örneği çizmenin bir anlamı yok;
seyreltme okuma katmanında yapılır, çizim katmanında değil.

**İndeks önbelleği zorunlu değil.** `.sidx` yazılamıyorsa açma başarısız olmaz, yalnız
yavaşlar. Salt okunur bir paylaşımdaki kaydı incelemek engellenmemeli.

**Uyarılar sessizce yutulmaz.** Profil A v1'in CRC'si yoktur; dosya açılır ama
"bütünlük doğrulanmadı" uyarısı kullanıcıya taşınır. Kesik son kayıt da aynı şekilde:
tam kayıtlar kullanılır, kaç baytın atıldığı söylenir.

---

## Model ile kodun ayrıştığı yer

Diyagramlar kodu olduğu gibi gösteriyor. Bunun bir sonucu var ve yazılı olması gerekir:

**Profil B arayüzden açılamıyor.** `io/decoders/` altında tam bir Profil B çözücü var —
`profile_b.py`, `profile_b_timing.py`, `profile_b_validation.py`, `profile_b_sequence.py`,
`profile_b_indexed_query.py` ve `io/index/profile_b_index.py`. Hepsinin testi var ve
`tests/fixtures/acoustic_8records.bin` ile doğrulanıyor. Ama `application/file_loader.py`
yalnızca `FileRecordingRepository` üretiyor, o da yalnız Profil A okuyor. Profil B
çözücüsünü çağıran tek yer testler ve `tools/` altındaki karşılaştırma betikleri.

Doğrulaması tek komut:

```bash
grep -rn "profile_b" src/sonar_analyzer/repository src/sonar_analyzer/ui src/sonar_analyzer/application
# çıktı yok
```

Yani bir Profil B dosyası `Open .bin File` ile seçilirse `InvalidMagicError` alınır.
Eksik olan çözücü değil, **çözücüyü repository sözleşmesine bağlayan sınıf**.

## Kaynaklar

| Konu | Belge |
| --- | --- |
| Mimari karar kayıtları | `docs/adr/README.md` |
| Format sözleşmeleri | `docs/format/profile-a.md` · `docs/format/decoder-guide.md` |
| Arayüz yerleşimi | `docs/ui/layout-map.md` |
| Açık kararlar | `docs/notes/open-decisions.md` |
| Paketleme | `docs/adr/ADR-012-packaging.md` |
