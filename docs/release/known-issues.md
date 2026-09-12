# Bilinen sorunlar ve veri sınırlamaları — `F6-029`

Bu belge, bu sürümde **bilerek açık bırakılan** her maddeyi listeler.
Her madde üç şey söyler:

- **Etki** — kullanıcı bunu nasıl yaşar, neyi yanlış sanabilir,
- **İş kimliği** — hangi iş/karar kaydında izleniyor,
- **Hedef düzeltme** — kapanması için ne olması gerekiyor.

Bir sınırlamayı yazmamak onu ortadan kaldırmaz; yalnız kullanıcının onu
**hata sanmasına** yol açar. Buradaki maddeler kusur değil, bilinen ve
izlenen sınırlardır — kapanma koşulu belli olmayan hiçbiri listede
kalmamalıdır.

Son güncelleme: `v3.35.0` · Kapsam: Faz 0–6 · Toplam açık madde: **20**

## Özet

| # | Sorun | Şiddet |
| --- | --- | --- |
| `K-01` | Gerçek cihaz kaydı yok | **Yüksek** |
| `K-02` | Resmî format dokümanı yok | **Yüksek** |
| `K-03` | Kanal kataloğu doğrulanmadı | Orta |
| `K-04` | BIT kodu kataloğu doğrulanmadı | Orta |
| `K-05` | Zaman kaynağı bilinmiyor | Orta |
| `K-06` | Firmware sürüm listesi yok | Düşük |
| `K-07` | Profil A ile spektral analiz anlamlı değil | Orta |
| `K-08` | Analysis menüsü kalıcı olarak pasif | Orta |
| `K-09` | Tanılama paketi arayüzden üretilemiyor | Orta |
| `K-10` | Komut paleti yok | Düşük |
| `K-11` | Zoom kipi araç çubuğunda görünmüyor | Düşük |
| `K-12` | Cross Analysis · 3D View · Report sekmeleri boş | Düşük |
| `K-13` | Seri port isteğe bağlı ekstra gerektirir | Düşük |
| `K-14` | Arayüz yalnız İngilizce | Düşük |
| `K-15` | Çoklu kayıt zaman hizalı karşılaştırılamaz | Orta |
| `K-16` | Dağıtım imzasız | **Yüksek** |
| `K-17` | Offline paket tek platform/sürüme bağlı | Orta |
| `K-18` | Hedef ölçüm bilgisayarı bilinmiyor | Orta |
| `K-19` | Uygulama Python 3.9 üzerinde çalışıyor | Düşük |
| `K-20` | Geliştirme araçlarında 15 güvenlik bulgusu | Düşük |

---

## 1. Veri ve format sınırlamaları

### K-01 — Gerçek cihaz kaydı yok

**Etki:** Format sözleşmesinin tamamı **sentetik fixture** ile
doğrulandı. Gerçek bir `.bin` geldiğinde alan sırası, endian ya da
dolgu farklı çıkarsa decoder sessizce yanlış okuyabilir — bayt düzeni
doğruysa okuma hata vermez, yalnız değerler yanlış olur. Bu sürümdeki
hiçbir "format doğrulandı" ifadesi gerçek donanım kanıtı değildir.

**İş kimliği:** `E-01`, `D-01`, `F0-017`

**Hedef düzeltme:** En az bir tam gerçek kayıt (tercihen 1+ dakika)
alınır; `docs/format/profile-a.md` ve fixture'lar ona göre doğrulanır.
Uyuşmazlık çıkarsa etkilenen `F2-*` işleri `plan.md`'de yeniden açılır.

### K-02 — Resmî format dokümanı yok

**Etki:** `plan.md` Bölüm 8.2/8.3 taslağı sözleşme yerine geçiyor. CRC
algoritması, TLV blok türleri ve alan genişlikleri **bizim
seçimimizdir**, cihazın değil.

**İş kimliği:** `E-02`, `D-02`, `F0-004`, `F0-005`

**Hedef düzeltme:** Firmware ekibinden resmî sözleşme alınır; taslakla
farkları `docs/format/decoder-guide.md`'ye sürüm olarak eklenir.
Sürüm alanı zaten bunun için var — yeni sürüm, eski decoder'ı bozmadan
eklenebilir.

### K-03 — Kanal kataloğu doğrulanmadı

**Etki:** Kanal adları, birimleri ve kalibrasyon katsayıları
`docs/format/channel-map.md`'deki **öneri sözlükten** geliyor. Gösterilen
`bar`, `°C` gibi birimler ve ham → fiziksel dönüşüm, gerçek cihaz
kalibrasyonuyla eşleşmeyebilir; grafik yine makul görünür.

**İş kimliği:** `E-04`, `D-06`, `F0-007`, `F1-011`

**Hedef düzeltme:** Sistem mühendisliğinden kanal kataloğu (ad, birim,
sample rate, gain/offset) alınır ve `channel-map.md` gerçek değerlerle
değiştirilir.

### K-04 — BIT kodu kataloğu doğrulanmadı

**Etki:** `bit_status` bit → bileşen eşlemesi 12 bitlik bir **öneri
haritadır**; referans mockup ise **8 alt sistem** gösteriyor. BIT
panelindeki bileşen adları gerçek `test_id` anlamlarıyla
örtüşmeyebilir — arıza görünür ama yanlış bileşene atanabilir.

**İş kimliği:** `E-05`, `D-07`

**Hedef düzeltme:** Donanım ekibinden BIT test kataloğu alınır; harita
genişletilir ve `docs/format/channel-map.md` §4.1 güncellenir.

### K-05 — Zaman kaynağı bilinmiyor

**Etki:** Tick frekansı, GPS/PPS varlığı ve drift beklentisi bilinmediği
için Profil A'da **senkron kalitesi `bilinmiyor`** olarak gösterilir.
Mutlak zaman damgaları dosya başlığındaki `start_time_utc_ns`'e
dayanır; bu değerin gerçek UTC ile ne kadar tuttuğu doğrulanmadı.

**İş kimliği:** `E-07`, `D-09`, `F0-011`

**Hedef düzeltme:** Donanım ekibinden zaman kaynağı bilgisi alınır;
`docs/adr/ADR-003-time-base.md` drift düzeltmesiyle birlikte gözden
geçirilir.

### K-06 — Firmware sürüm listesi yok

**Etki:** Yalnız Profil A `version = 1` ve `2` destekleniyor. Cihaz
başka bir sürüm üretirse dosya **açılmaz** (`UnsupportedVersionError`).
Bu kasıtlıdır — bilinmeyen sürümü en yakın sürüm sanıp okumak sessizce
yanlış veri üretirdi — ama kullanıcı için bir engeldir.

**İş kimliği:** `E-08`, `D-10`

**Hedef düzeltme:** Firmware sürüm listesi alınır; her sürüm için
decoder çifti `version_dispatch.py`'ye eklenir.

### K-07 — Profil A ile spektral analiz anlamlı değil

**Etki:** Profil A'da bir kanal kayıt başına **tek değer** taşır →
efektif **8 Hz**, Nyquist **4 Hz**. FFT, PSD ve spektrogram hücreleri bu
veriyle gerçek bir sonuç üretemez. Uygulama bunu gizlemez: Profil A
verisiyle spektral panel **gerçek sonuç izlenimi veren sahte çıktı
göstermez**.

**İş kimliği:** `D-04`, `F4-009` (Profil B yolu)

**Hedef düzeltme:** Spektral analiz için Profil B akustik kanal
kullanılır (48 kHz). Kullanım örneği:
`docs/guide/filtre-ve-spektral-analiz.md`.

## 2. Uygulama sınırlamaları

### K-08 — Analysis menüsü kalıcı olarak pasif

**Etki:** **Analysis** menüsündeki `FFT`, `Spectrogram`, `Filter...` ve
`Statistics` eylemleri her zaman pasiftir ve hiçbir şeye bağlı değildir
(ipuçları `v2.0.0 ile kullanilabilir` der). Oysa bu işlevlerin
**tamamı çalışıyor** — sağ sütundaki *Analysis Tools* kartında ve merkez
sekmelerinde. Menüden arayan kullanıcı, var olan bir özelliği yok
sanar.

**İş kimliği:** `F1-023`, `D-25`

**Hedef düzeltme:** Menü eylemleri mevcut panellere bağlanır (ilgili
sekmeyi/kartı odaklayacak biçimde) ya da menüden kaldırılır. Pasif bir
menü girdisi, olmayan bir özellik kadar yanıltıcıdır.

### K-09 — Tanılama paketi arayüzden üretilemiyor

**Etki:** Tanılama paketi (`application/diagnostics.py`,
`diagnostics_export.py`) çalışıyor ve test edilmiş durumda, ancak
**Tools → Diagnostics** eylemi pasif ve hiçbir işleyiciye bağlı değil.
Kullanıcı destek için tanılama paketini uygulamadan üretemez; yalnız
geliştirici aracıyla üretilebilir.

**İş kimliği:** `F6-009`, `F6-010`

**Hedef düzeltme:** `action_diagnostics` etkinleştirilip
`diagnostics_export.export()`'a bağlanır; seçim ekranı
`DEFAULT_SELECTED` ile açılır (ham veri varsayılan olarak **dahil
değildir**).

### K-10 — Komut paleti yok

**Etki:** Plan Bölüm 16'daki `Ctrl+K` komut paleti bu sürümde
uygulanmadı; tuşa basmak hiçbir şey yapmaz.

**İş kimliği:** Bölüm 16, `F6-028`

**Hedef düzeltme:** v2 kapsamında değerlendirilir. O zamana kadar
`docs/guide/klavye-ve-mouse.md` §6'da fark olarak yazılı.

### K-11 — Zoom kipi araç çubuğunda görünmüyor

**Etki:** Etkin zoom kipi (X / Y / XY) **Log** panelinde bir satır olarak
bildirilir ve workspace'e kaydedilir, ama araç çubuğunda kalıcı bir
gösterge yoktur. Log'u kaydıran kullanıcı hangi kipte olduğunu
unutabilir ve tekerleğin "yanlış" eksende çalıştığını sanabilir.

**İş kimliği:** Bölüm 16, `F6-028`

**Hedef düzeltme:** Araç çubuğuna üç durumlu bir kip göstergesi eklenir;
kısayol ve gösterge tek kaynaktan beslenir.

### K-12 — Cross Analysis · 3D View · Report sekmeleri boş

**Etki:** Bu üç sekme görünür ama içerikleri
`v2.0.0 ile kullanılabilir` durumundadır.

**İş kimliği:** `D-25`

**Hedef düzeltme:** Kapsam kararı verilir (`D-25`); kapsam dışı kalırsa
sekmeler kaldırılır.

### K-13 — Seri port isteğe bağlı ekstra gerektirir

**Etki:** Seri port bağlantısı `live` ekstrası kurulu değilse
çalışmaz. Bağlantı **açık bir hata** verir, sessizce başarısız olmaz —
ama paketli uygulamada bu ekstra kurulu değilse seçenek kullanılamaz.

**İş kimliği:** `F5-009`, `F5-010`, `D-12`

**Hedef düzeltme:** `pip install -e ".[gui,live]"`; paket için ekstranın
varsayılan olarak dâhil edilip edilmeyeceğine karar verilir.

### K-14 — Arayüz yalnız İngilizce

**Etki:** Referans mockup'ın tüm arayüz metinleri İngilizce olduğu için
arayüz İngilizce, proje belgeleri Türkçe tutuldu. Türkçe arayüz
isteyen kullanıcı için karşılığı yok.

**İş kimliği:** `D-21`

**Hedef düzeltme:** Çift dil istenirse metinler `tr()` ile sarılır.
Sonradan eklemek pahalıdır; karar erken verilmelidir.

### K-15 — Çoklu kayıt zaman hizalı karşılaştırılamaz

**Etki:** Birden fazla kayıt aynı anda açık olabilir ve her biri Data
Tree'de ayrı görünür; birini kapatmak diğerlerini etkilemez. Ancak iki
kaydı **hizalayan bir karşılaştırma görünümü** ve **kayıt başına zaman
kaydırma denetimi yoktur**. İki ölçümü karşılaştırmak için kullanıcı
aralıkları elle eşitlemek zorundadır.

**İş kimliği:** `D-22`, `F2-036`, `F3-007`

**Hedef düzeltme:** Kapsam kararı verilir; girerse kayıt başına zaman
offset'i ve hizalama denetimi eklenir.

## 3. Dağıtım ve ortam

### K-16 — Dağıtım imzasız

**Etki:** Kurulum dosyası ve `.exe` **imzasızdır**. Windows SmartScreen
bilinmeyen yayıncı uyarısı gösterir; kullanıcı
*Daha fazla bilgi → Yine de çalıştır* demek zorundadır. Kurumsal
ortamda politika bunu tamamen engelleyebilir.

**İş kimliği:** `D-17`, `F6-012`, `ADR-012`

**Hedef düzeltme:** Code signing sertifikası tedarik edilir ve
`tools/signing_check.py` yapılandırılır. **Sertifika tedariki uzun
sürer**; bu madde erken cevap gerektirir.

### K-17 — Offline paket tek platform/sürüme bağlı

**Etki:** `tools/offline_bundle.py` 17 wheel'lik (~294 MiB) bir arşiv
üretir, ancak wheel'ler **üretildiği Python ve platform için**
seçilir (bu arşiv: Python 3.9.13, Windows x64). Başka bir sürüm ya da
mimaride kurulum yapılamaz.

**İş kimliği:** `D-16`, `F6-011`

**Hedef düzeltme:** Hedef ortam netleşince (`D-15`, `D-20`) arşiv o
ortam için yeniden üretilir; gerekirse çok platformlu üretim eklenir.

### K-18 — Hedef ölçüm bilgisayarı bilinmiyor

**Etki:** Bütün performans ölçümleri **geliştirme makinesinde** yapıldı.
`docs/perf/budget.md` bütçeleri bu yüzden geçici referanstır; hedef
makine daha zayıfsa açılış süresi, çizim akıcılığı ve bellek
davranışı farklı çıkar.

**İş kimliği:** `E-10`, `D-15`, `F0-014`

**Hedef düzeltme:** Hedef makine özellikleri alınır, ölçümler orada
tekrarlanır ve `F4` performans kabulü o sonuçlarla kapatılır.

### K-19 — Uygulama Python 3.9 üzerinde çalışıyor

**Etki:** `D-20` hedef olarak Python 3.12 varsayıyordu; depo hâlâ
**3.9.13** üzerinde çalışıyor ve `requires-python = ">=3.9"`. Bu, tip
söz dizimi ve standart kütüphane kısıtlarını sürdürür. Kullanıcıya
doğrudan etkisi yoktur (paket kendi yorumlayıcısını taşır).

**İş kimliği:** `D-20`, `F1-001`

**Hedef düzeltme:** Hedef makinede kurulabilecek sürüm doğrulanır;
yükseltme kararı verilirse `requires-python` ve tip söz dizimi
güncellenir.

### K-20 — Geliştirme araçlarında 15 güvenlik bulgusu

**Etki:** `tools/dependency_scan.py` 57 pakette **15 bulgu** raporluyor.
Hepsi yalnız geliştirme/test araçlarındadır (`pip`, `setuptools`,
`pytest`, `requests`, `urllib3`, `filelock`, `msgpack`); **kullanıcıya
sevk edilen pakette 0 bulgu** vardır. Bu yüzden kapı engellemez —
engelleme ölçütü "paket kullanıcıya gidiyor mu"dur, bulgunun
şiddeti değil.

**İş kimliği:** `F6-014`

**Hedef düzeltme:** Geliştirme bağımlılıkları düzeltme sürümlerine
yükseltilir. Rapor: `docs/packaging/results/dependency-scan.json`.

---

## Güncelleme kuralı

- Bir madde kapandığında satır listeden **çıkarılır** ve kapanış
  gerekçesi `docs/notes/worklog.md`'ye yazılır.
- Yeni bir sınırlama bulunduğunda buraya **üç alanıyla birlikte**
  eklenir; hedef düzeltmesi yazılamayan bir madde, henüz anlaşılmamış
  demektir.
- Açık kararların tam kütüğü: `docs/notes/open-decisions.md`.
  Eksik dış girdiler: `docs/format/inventory.md` §2.
