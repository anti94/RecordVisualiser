# SONAR Veri Analiz Panosu — `v4.0.0` (Dağıtım)

Bu sürüm uygulamayı **kurulabilir bir Windows programına** dönüştürür.
Yeni analiz özelliği getirmez; getirdiği şey, var olanın bir geliştirme
ortamı olmadan, bir kurulum dosyasıyla çalışabilmesidir.

Major sürüm olmasının nedeni budur: dağıtım biçimi değişti.

| | |
| --- | --- |
| Milestone | `ms/07-distribution` |
| Kapsam | `F6-001`–`F6-034` (34 iş) |
| Önceki sürüm | `v3.0.0` (canlı veri ve kayıt) |
| Hedef | Windows 11 x64, kullanıcı başına kurulum |
| Kurulum | `sonar-analyzer-4.0.0-setup.exe`, yönetici hakkı **gerekmez** |

## Öne çıkanlar

### Kurulabilir paket

Uygulama artık PyInstaller **onedir** biçiminde paketleniyor ve NSIS ile
kurulum dosyasına dönüşüyor (`ADR-012`). Kurulum kullanıcı başınadır:
`%LOCALAPPDATA%` altına kurulur, `HKCU` altına kaydolur ve yönetici
hakkı istemez.

Hedef makinede **Python kurulu olması gerekmez**. Bu, temiz bir ortamda
doğrulandı: PATH'ten Python izleri kaldırılarak paket çalıştırıldı ve
açıldı (`F6-005`).

### Kendini denetleyen paket

Paket, dağıtımda en sık kaybolan şeyleri kendisi kontrol eder:

```text
sonar-analyzer.exe --self-check      # Qt platform eklentisi, tema, ana ekran, ikon
sonar-analyzer.exe --bin-check X.bin # kayıt açma, CSV ve PNG üretip geri okuma
sonar-analyzer.exe --layout-report J # dokuz bölge, sütunlar, tema, analiz
```

Üçü de sonucu **geri okuyarak** doğrular. Dosya yazıp "oldu" demek
yetmez: bozuk ya da boş bir dosya da yazılmış olur.

### Tanılama ve kurtarma

- **Tanılama paketi** (`F6-019`, `F6-020`): log, ayar, sürüm ve ortam
  bilgisi tek zip'te toplanır. Ham ölçüm verisi **varsayılan olarak
  dâhil değildir**; destek için gönderilen bir paketin içinde kullanıcı
  verisi olması, olmaması gerekendir.
- **Workspace kurtarma** (`F6-021`): beklenmedik kapanmadan sonra son
  geçerli workspace geri yüklenebilir. Checkpoint'ler yüklenerek
  doğrulanır; bozuk bir checkpoint "kurtarılabilir" olarak sunulmaz.

### Kullanım kılavuzları

Beş belge eklendi: ana ekran (`F6-024`), filtre ve spektral analiz
(`F6-025`), canlı bağlantı ve kayıt (`F6-026`), format ve decoder
(`F6-027`), klavye/mouse/ölçekleme (`F6-028`).

Kısayol tabloları elle yazılmadı: uygulamanın kendi eylem kayıtlarıyla
**çift yönlü** eşleştikleri test ediliyor. Belgede yazan her kısayol
uygulamada bağlıdır, uygulamada bağlı her kısayol belgede yazar.

## Doğrulama

Bu sürümde yapılan kontroller ve nerede kayıtlı oldukları:

| Kontrol | Araç | Kanıt |
| --- | --- | --- |
| Temiz ortamda açılış | `tools/clean_env_check.py` | `docs/packaging/results/clean-env-check.json` |
| Kurulum · yükseltme · kaldırma | `tools/installer_lifecycle_check.py` | `docs/packaging/results/installer-lifecycle.json` |
| Artefakt manifesti ve SHA-256 | `tools/release_manifest.py` | `docs/packaging/results/release-manifest.json` |
| Yeniden üretilebilirlik | `tools/compare_builds.py` | `docs/packaging/results/build-reproducibility.json` |
| Offline bağımlılık arşivi | `tools/offline_bundle.py` | `docs/packaging/results/offline-bundle.json` |
| İmzalama kararı | `tools/signing_check.py` | `docs/packaging/results/signing-check.json` |
| Bağımlılık taraması | `tools/dependency_scan.py` | `docs/packaging/results/dependency-scan.json` |
| Kapsam eşikleri | `tools/coverage_gate.py` | `docs/packaging/results/coverage-gate.json` |
| **Paketli kabul turu** | `tools/acceptance_run.py` | `docs/acceptance/packaged-acceptance.md` |
| **Mockup karşılaştırması** | `tools/mockup_compare.py` | `docs/ui/packaged-mockup-comparison.md` |
| **Geri dönüş provası** | `tools/rollback_check.py` | `docs/release/release-and-rollback.md` |

Kabul turu ve mockup karşılaştırması **paketli `.exe` üzerinde**
yürütülür. Kaynak ağacından çalıştırmak paketi kanıtlamaz.

### Kabul turunun sonucu dürüsttür

Paketli kabul turu **9 adımdan 8'ini geçti**. Düşen adım (`M-05`)
gizlenmedi: bozuk CRC'li bir kayıttan alınan CSV, bozuk örneği hiçbir
işaret olmadan yazıyor. Bulgu `F6-035` işine ve `K-21` bilinen sorununa
dönüştürüldü.

Okuma katmanı doğru çalışıyor — kayıt `CRC_ERROR` olarak işaretleniyor;
kayıp, bilgiyi kullanıcıya taşıyan yolda.

## Geri dönüş

Geri dönüş prosedürü yazılmakla kalmadı, **provası yapıldı**:
`3.32.0` → `3.8.0` geri dönüşü gerçek installer'larla yürütüldü ve 12
adımın tamamı geçti (`docs/release/release-and-rollback.md`).

Kullanıcı ayarları kurulum dizininin dışında yaşadığı için kaldırma
onları silmez. Geri dönülen eski sürüm, yeni sürümün yazdığı ayar
dosyasını (ileri şema, tanımadığı alanlar) sorunsuz açar.

## Bilinen sınırlar

Tam liste: `docs/release/known-issues.md` (**21 açık madde**). Bu
sürümde kullanıcıyı en çok ilgilendirenler:

- **`K-16` Dağıtım imzasız.** Windows SmartScreen bilinmeyen yayıncı
  uyarısı gösterir; kullanıcı *Daha fazla bilgi → Yine de çalıştır*
  demek zorundadır. Sertifika kararı (`D-17`) hâlâ açık.
- **`K-21` CSV çıktısı kalite bayraklarını taşımıyor.** Bozuk CRC'li ya
  da boşluklu bir kayıttan alınan CSV, bu durumu göstermez (`F6-035`).
- **`K-08` Analysis menüsü kalıcı olarak pasif.** Analiz işlevleri
  çalışıyor ama sağ sütundan ve sekmelerden kullanılıyor; menüden
  arayan kullanıcı yok sanabilir.
- **`K-09` Tanılama paketi arayüzden üretilemiyor.** Kod çalışıyor,
  menü eylemi bağlanmadı.
- **`K-01`, `K-02` Gerçek cihaz kaydı ve resmî format dokümanı yok.**
  Format doğrulamasının tamamı sentetik veriyle yapıldı; hiçbir "format
  doğrulandı" ifadesi gerçek donanım kanıtı değildir.
- **`K-18` Hedef ölçüm bilgisayarı bilinmiyor.** Performans bütçeleri
  geliştirme makinesinde ölçüldü.

## Yükseltme

Önceki sürümü kaldırmaya gerek yok; kurulum dosyası üzerine kurar ve
kullanıcı verisine dokunmaz (`F6-008` doğruladı). Yine de yükseltmeden
önce ayar dosyasının bir kopyasını almak, geri dönüş gerekirse işi
kolaylaştırır:

```text
copy "%APPDATA%\SonarAnalyzer\settings.json" "%USERPROFILE%\Desktop\settings-yedek.json"
```

`v3.x` ile yazılmış `.bin` kayıtları ve workspace dosyaları bu sürümde
olduğu gibi açılır; format sürümü değişmedi (Profil A sürüm 2).

## Kaldırma

Ayarlar → Uygulamalar → **SONAR Data Analyzer** → Kaldır. Kaldırma
kurulum dizinini tamamen siler ve `HKCU` kaydını kaldırır; kullanıcı
ayarları, workspace'ler ve kayıtlar **silinmez**.
