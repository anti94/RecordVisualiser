# Release ve geri dönüş prosedürü — `F6-032`

Kabul: **Önceki paket ve kullanıcı ayarlarının geri yükleme adımları
uygulanabilirdir.**

Bu belge iki prosedür tanımlar: bir sürümü **yayınlamak** ve bir sürümden
**geri dönmek**. İkincisi denenmiş bir prosedürdür, bir temenni değil:
`tools/rollback_check.py` §4'teki adımları gerçek installer'larla
yürütür ve sonucu `docs/packaging/results/rollback-check.json`'a yazar.

Son yürütme: `3.33.0` → `3.8.0`, **12 adımın 12'si geçti**.

## 1. Neye dayanıyor

| | |
| --- | --- |
| Kurulum | Kullanıcı başına (HKCU + `%LOCALAPPDATA%`), yönetici gerekmez |
| Kurulum dizini | `%LOCALAPPDATA%\Programs\SonarAnalyzer` (öntanımlı) |
| Kullanıcı ayarları | `%APPDATA%\SonarAnalyzer\settings.json` |
| Workspace dosyaları | Kullanıcının seçtiği yerde (`.sonar-workspace.json`) |
| Kayıtlar | Kullanıcının seçtiği yerde (`.bin`) |
| Paketleme | PyInstaller onedir + NSIS (`ADR-012`) |

**Kullanıcı verisi kurulum dizininin dışındadır.** Geri dönüş
prosedürünün tamamı buna dayanır: program dosyalarını kaldırmak
ayarları, workspace'leri ve kayıtları silmez. Bu varsayılmaz,
`rollback_check.py` adım 5 ve 12'de **doğrulanır**.

## 2. Yayın öncesi kapılar

Sırayla ve hepsi geçmeden yayın yapılmaz:

| # | Kapı | Komut |
| --- | --- | --- |
| 1 | Lint · biçim · tip · testler | `python tools/local_gate.py` |
| 2 | Kapsam eşikleri | `python tools/coverage_gate.py` |
| 3 | Bağımlılık taraması | `python tools/dependency_scan.py` |
| 4 | Performans duman testi | `python tools/perf_smoke.py` |
| 5 | Paket üretimi | `python tools/build_package.py` |
| 6 | Kurulum dosyası | `python tools/build_installer.py` |
| 7 | Temiz ortam denetimi | `python tools/clean_env_check.py` |
| 8 | Kurulum/yükseltme/kaldırma | `python tools/installer_lifecycle_check.py` |
| 9 | Paketli kabul turu | `python tools/acceptance_run.py` |
| 10 | Mockup karşılaştırması | `python tools/mockup_compare.py` |
| 11 | Geri dönüş provası | `python tools/rollback_check.py` |
| 12 | Yayın bekçisi | `python tools/release_guard.py` |

Kapı 11 **yayından önce** çalıştırılır. Geri dönüşü ilk kez gerçek bir
olayda denemek, en kötü anda öğrenmek demektir.

## 3. Yayın adımları

1. `VERSION` dosyası yeni sürüme çıkarılır.
2. Bölüm 2'deki kapılar sırayla çalıştırılır.
3. `docs/release/release-notes-vX.Y.Z.md` yazılır; kapsam, bilinen
   sorunlar (`docs/release/known-issues.md`) ve artefakt listesi
   tutarlı olmalıdır.
4. Commit atılır, `vX.Y.Z` etiketi oluşturulur ve `main` ile birlikte
   itilir.
5. `tools/release_manifest.py` artefakt listesini ve SHA-256'larını
   üretir.
6. **Bir önceki sürümün kurulum dosyası saklanır.** Geri dönüş, elde
   önceki paket yoksa mümkün değildir; bu adım atlanırsa prosedürün
   geri kalanı işe yaramaz.

> Dağıtım **imzasızdır** (`K-16`, `D-17`). Kullanıcı SmartScreen
> uyarısını geçmek zorundadır; yayın duyurusunda bu açıkça yazılır.

## 4. Geri dönüş prosedürü

Yeni sürümde kullanıcıyı engelleyen bir sorun çıktığında uygulanır.
Aşağıdaki adımlar `tools/rollback_check.py` tarafından **bu sırayla**
yürütülür ve sonuçları kaydedilir.

### 4.1 Önce yedek

```text
copy "%APPDATA%\SonarAnalyzer\settings.json" "%USERPROFILE%\Desktop\settings-yedek.json"
```

Ayar dosyası kaldırma sırasında silinmez; yedek yine de alınır. Geri
dönüş sırasında **eski sürüm ayarları yeniden yazabilir** ve yeni
sürümün eklediği alanlar kaybolabilir (bkz. §4.5).

Workspace dosyaları ve `.bin` kayıtları kullanıcının kendi
klasörlerindedir; kurulum bunlara dokunmaz.

### 4.2 Yeni sürümü kaldır

Ayarlar → Uygulamalar → **SONAR Data Analyzer** → Kaldır. Ya da:

```text
"%LOCALAPPDATA%\Programs\SonarAnalyzer\uninstall.exe"
```

Kaldırma bittiğinde kurulum dizini **tamamen** silinir ve HKCU altındaki
kaldırma kaydı kalkar. `rollback_check.py` adım 11 bunu doğrular: normal
kaldırmadan sonra dizinde hiçbir dosya kalmaz.

> Otomatik denetimlerde kaldırıcı `_?=` ile **yerinde** çalıştırılır;
> bu kipte kaldırıcı kendini silemez ve `uninstall.exe` geride kalır.
> Bu, çağrının sonucudur, ürünün değil — bu yüzden araç iki kipi ayrı
> ayrı sınar.

### 4.3 Önceki sürümü kur

Saklanan `sonar-analyzer-<onceki>-setup.exe` çalıştırılır. Kurulum
kullanıcı başınadır; yönetici hakkı gerekmez.

### 4.4 Doğrula

```text
"%LOCALAPPDATA%\Programs\SonarAnalyzer\sonar-analyzer.exe" --version
"%LOCALAPPDATA%\Programs\SonarAnalyzer\sonar-analyzer.exe" --self-check
```

Birincisi **beklenen eski sürümü** yazmalı, ikincisi `sonuc: TAMAM`
demelidir.

### 4.5 Ayarları kontrol et

Geri dönüşün asıl riski buradadır: eski sürüm, **yeni sürümün yazdığı**
bir ayar dosyasıyla karşılaşır.

Uygulama bunu tolere eder. Ayar dosyası `schema_version` taşır; dosya
daha yeni bir şemadan geliyorsa uygulama bir uyarı yazar, tanımadığı
alanları yok sayar ve **açılır**. Tanınmayan alanlar, dosya yeniden
kaydedildiğinde kaybolur — bu yüzden §4.1'deki yedek önemlidir.

`rollback_check.py` adım 8 bunu gerçek paketlerle sınar: `3.8.0`,
`schema_version: 99` ve tanımadığı alanlar içeren bir ayar dosyasıyla
sorunsuz açıldı.

Ayarlar bozulduysa yedekten geri yüklenir:

```text
copy "%USERPROFILE%\Desktop\settings-yedek.json" "%APPDATA%\SonarAnalyzer\settings.json"
```

Yedek de yoksa dosya **silinir**; uygulama varsayılan ayarlarla açılır.
Silmek veri kaybıdır ama açılamayan bir uygulamadan iyidir.

### 4.6 Kaydet

Geri dönüşün nedeni `docs/release/known-issues.md`'ye yazılır ve
düzeltme için ayrı bir iş açılır. Geri dönülen sürüm, nedeni
kapanmadan yeniden yayınlanmaz.

## 5. Son provanın sonucu

`tools/rollback_check.py`, `3.33.0` → `3.8.0` geri dönüşünü yürüttü:

| # | Adım | Sonuç |
| --- | --- | --- |
| 1 | Yeni sürüm kurulur | **TAMAM** |
| 2 | Yeni sürüm çalışıyor (`sonar-analyzer 3.33.0`) | **TAMAM** |
| 3 | Ayarlar yazılır ve yedeklenir | **TAMAM** |
| 4 | Yeni sürümün uygulama dosyaları kaldırılır | **TAMAM** |
| 5 | Ayarlar kaldırmadan sağ çıktı | **TAMAM** |
| 6 | Önceki sürüm kurulur (geri dönüş) | **TAMAM** |
| 7 | Geri dönülen sürüm doğru (`sonar-analyzer 3.8.0`) | **TAMAM** |
| 8 | Önceki sürüm, yeni sürümün ayar dosyasıyla açılıyor | **TAMAM** |
| 9 | Yedekten geri yükleme çalışıyor | **TAMAM** |
| 10 | Geri yüklenen ayarlarla açılıyor | **TAMAM** |
| 11 | Normal kaldırmada iz bırakmıyor | **TAMAM** |
| 12 | Ayarlar kaldırmadan sonra hâlâ duruyor | **TAMAM** |

Ham kanıt: `docs/packaging/results/rollback-check.json`.

## 6. Bu prosedürün kapsamadıkları

- **Otomatik güncelleme kanalı yoktur** (`D-19`); kurulum ve geri dönüş
  elle yapılır.
- **Eski sürüme dönüş, veri biçimini geri almaz.** Yeni sürümle
  yazılmış `.bin` kayıtları, eski sürümün desteklediği format
  sürümündeyse okunur; değilse eski sürüm dosyayı **reddeder**
  (`UnsupportedVersionError`). Bu kasıtlıdır — bilinmeyen sürümü tahmin
  ederek okumak sessizce yanlış veri üretirdi.
- **Çoklu kullanıcı kurulumu ele alınmaz**; kurulum kullanıcı başınadır.

## 7. İlgili belgeler

- Paketleme kararı: `docs/adr/ADR-012-packaging.md`
- Kalite kapıları: `docs/ci/quality-gates.md`
- Bilinen sorunlar: `docs/release/known-issues.md`
- Paketli kabul turu: `docs/acceptance/packaged-acceptance.md`
- Mockup karşılaştırması: `docs/ui/packaged-mockup-comparison.md`
