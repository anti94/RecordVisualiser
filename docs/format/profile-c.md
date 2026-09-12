# Profil C — klasör tabanlı Tx/Rx kayıt sözleşmesi

Profil A ve Profil B **tek dosyalık** kayıtlardır. Profil C değildir: bir kayıt, içinde
saniyelik dosyalar bulunan bir **klasör ağacıdır**.

Kayıt dosyalarını **C++ tarafı üretir**. Bu belge bizim tanımladığımız bir yapıyı değil,
dışarıdan gelen bir yapının **tarifini** yazar. Bunun bir sonucu var ve baştan söylenmeli:
tarif ile gerçek dosya ayrışırsa veri **hatasız ama yanlış** okunur. Sözleşmenin en
kritik maddesi bu ayrışmayı yakalamaktır (§7).

İlgili belgeler: [`decoder-guide.md`](decoder-guide.md) (üç profilin ayrımı),
[`profile-a.md`](profile-a.md), [`profile-b.md`](profile-b.md).

## 1. Sinyal parametreleri

| Büyüklük | Değer | Kaynak |
| --- | --- | --- |
| Örnekleme frekansı | 8192 Hz | Sistem tanımı |
| Frame boyutu | 820 complex örnek | Sistem tanımı |
| Sensör sayısı | 32 | Sistem tanımı |
| Örnek tipi | `complex64` (float32 I/Q, 8 bayt) | Karar `D-28` |
| Nominal kayıt periyodu | 100 ms | Sistem tanımı |
| Saniyedeki frame sayısı | 10 | Türetilir |
| Azami kayıt süresi | 10 dakika | Karar `D-26` |

**Frame süresi tam olarak 100 ms değildir.** 820 / 8192 = 100,0977 ms. Bu fark bilinçlidir
ve kabul edilmiştir (`D-27`); ayrıntı ve birikim hesabı §6'dadır.

## 2. Klasör ağacı

```text
<kayıt kökü>/
└── 2026-09-12T14-30-00Z/        ← kayıt klasörü, UTC başlangıç anı
    ├── manifest.toml            ← kaydın kimliği ve özeti
    ├── Tx/
    │   ├── TxData00000.bin      ← 1 saniyelik dilim
    │   ├── TxData00001.bin
    │   └── …
    └── Rx/
        ├── RxData00000.bin
        ├── RxData00001.bin
        └── …
```

### 2.1 Kayıt klasörü adı

Biçim: `YYYY-MM-DDTHH-MM-SSZ` — ISO 8601'in dosya sistemi için uyarlanmış hâli.

Saat ve dakika ayıracı `:` yerine `-` kullanılır; Windows dosya adlarında iki nokta
üst üste yasaktır. Sondaki `Z` zamanın **UTC** olduğunu söyler. Yerel saat kullanılsaydı
iki kayıt aynı ada sahip olabilirdi: yaz saati geri alındığında aynı yerel saat iki kez
yaşanır.

Ad kaydın **başlangıç anını** taşır. Aynı saniyede iki kayıt başlarsa çakışma olur;
bu durumda ada `_2`, `_3` soneki eklenir. Üzerine yazmak bir kaydı sessizce yok ederdi.

### 2.2 Tx ve Rx ayrımı

| Klasör | İçerik |
| --- | --- |
| `Tx/` | Her PRI'da **yalnız yayın yapılan süredeki** örnekler |
| `Rx/` | PRI'nın **yayın dışında kalan** süresindeki örnekler |

İkisi **tamamlayıcıdır**, kopya değil: bir PRI'nın her örneği ya Tx'e ya Rx'e gider,
ikisine birden değil. Bu yüzden Tx ve Rx dosya boyutları PRI içindeki yayın oranına
göre değişir ve toplamları tam PRI'yı verir.

Bir kayıtta iki klasörden biri bulunmayabilir: yayın yapılmadan sadece dinlenen bir
oturumda `Tx/` boş ya da yok olur. Eksik klasör hata değildir; hangi akımın bulunmadığı
kullanıcıya bildirilir.

### 2.3 Dosya adları

Biçim: `TxData` ya da `RxData` + **beş haneli sıfır dolgulu sayaç** + `.bin`.

```text
TxData00000.bin   sayaç 0     kaydın 0. saniyesi
TxData00001.bin   sayaç 1     kaydın 1. saniyesi
RxData00599.bin   sayaç 599   kaydın 599. saniyesi (10 dakikanın sonu)
```

Sayaç **kayıt başına sıfırdan başlar**, dosya başına bir artar ve **bir saniyeye** karşılık
gelir. Her dosya 10 frame taşır.

Tx ve Rx sayaçları **bağımsızdır ama aynı saniyeyi gösterir**: `TxData00042.bin` ile
`RxData00042.bin` aynı saniyeye aittir. Yayın yapılmayan bir saniyede Tx dosyası
üretilmez; bu durumda Tx sayacında **boşluk** oluşur ve boşluk bir hata değil, bilgidir.

### 2.4 Sayaç sarması

Beş hane 00000–99999 aralığını, yani 100.000 saniyeyi (27,8 saat) kapsar. Azami kayıt
süresi 10 dakika (600 dosya) olduğundan **sarma bu profilde gerçekleşmez**.

Yine de okuyucu sarmayı varsaymaz: sayaç azalarak devam ederse bu bir sarma değil, bir
**tutarsızlık** olarak raporlanır. Sessizce sarma varsaymak, karışmış iki kaydın tek
kayıt gibi okunmasına yol açardı.

## 3. Dosya sayısı ve boyut

| Süre | Saniye | Tx dosyası | Rx dosyası | Toplam dosya |
| --- | --- | --- | --- | --- |
| 1 dakika | 60 | ≤ 60 | 60 | ≤ 120 |
| **10 dakika (tavan)** | **600** | **≤ 600** | **600** | **≤ 1.200** |

Tx dosya sayısı "≤" ile yazılıdır: yayın yapılmayan saniyelerde dosya üretilmez.

Bir saniyelik dosyanın yükü (header hariç):

```text
820 örnek × 32 sensör × 8 bayt × 10 frame = 2.099.200 bayt = 2,002 MiB
```

10 dakikalık bir kaydın Tx ve Rx toplamı **1,173 GiB**'dır. Ayrıntılı bütçe `F7-003`
ile bu belgeye eklenecektir.

## 4. Kayıt klasörünün kökü

`manifest.toml` kaydın kimliğini taşır ve klasörü tek tek dosya açmadan tanımayı sağlar:

| Alan | Anlamı |
| --- | --- |
| `schema_id` | Dosyaları üreten C++ struct tanımının kimliği |
| `schema_version` | O tanımın sürümü |
| `start_time_utc_ns` | Kaydın başlangıcı, `int64` UTC epoch ns |
| `sample_rate_hz` | 8192 |
| `frame_samples` | 820 |
| `sensor_count` | 32 |
| `sample_dtype` | `complex64` |
| `duration_s` | Kaydın süresi |
| `tx_file_count` / `rx_file_count` | Üretilen dosya sayıları |

Manifest **bulunmayabilir**; C++ tarafı üretmiyorsa okuyucu bu bilgileri dosyalardan
çıkarır ve manifesti kendi üretir. Manifest varsa ve dosyalarla çelişiyorsa **dosyalar
esas alınır**, çelişki kullanıcıya bildirilir.

İndeks önbelleği `manifest.toml` ile aynı dizine değil, ayrı bir `.sonar-index/`
alt klasörüne yazılır; kayıt klasörü salt okunursa indeks bellekte kurulur ve kayıt
yine açılır.

## 5. Okuma sırası

1. Kayıt klasörü seçilir.
2. `Tx/` ve `Rx/` aranır; ikisi de yoksa bu bir Profil C kaydı değildir.
3. `manifest.toml` varsa okunur.
4. Dosya adları sayaca göre sıralanır, boşluklar not edilir.
5. Her akımın ilk dosyasının header'ı okunur ve manifestle karşılaştırılır.
6. Klasör indeksi kurulur ya da önbellekten yüklenir.

Sıralama **dosya adındaki sayaca** göredir, dosya sisteminin döndürdüğü sıraya göre
değil. Sözlük sıralaması beş haneli sıfır dolgu sayesinde sayısal sıralamayla aynıdır;
dolgu olmasaydı `TxData10.bin`, `TxData9.bin`'den önce gelirdi.

## 6. Zaman ekseni

Bir frame 820 örnek taşır ve 8192 Hz'de bu **100,0977 ms** eder, 100 ms değil.

| Süre | Birikmiş kayma |
| --- | --- |
| 1 saniye | 0,977 ms |
| 1 dakika | 58,6 ms |
| **10 dakika (tavan)** | **0,586 s** |

Bu kayma kabul edilmiştir (`D-27`). Ama bir kural doğurur: zaman ekseni **frame
sayacından mı yoksa frame başlığındaki timestamp'ten mi** türetilecek? İkisi 10 dakikanın
sonunda tam da bu 0,586 saniye kadar ayrışır.

Seçim kodda **tek bir yerde** tanımlanmalıdır. İki panel iki farklı kaynaktan türetirse
aynı kayıt için iki farklı zaman gösterirler ve hangisinin doğru olduğu anlaşılmaz.
Bu seçim `F7-005` ile sözleşmeye bağlanacaktır.

## 7. Şema ile kaydın ayrışması

C++ tarafı bir struct alanını değiştirir ve TOML şeması güncellenmezse, okuyucu dosyayı
**hatasız okur ve yanlış değerler üretir**. Bayt sayısı tutar, CRC tutar, hiçbir istisna
oluşmaz; yalnız her alan kaymış olur.

Bu yüzden sözleşme üç bağımsız kapı gerektirir:

1. **Sihirli sayı** — dosyanın Profil C olduğunu doğrular.
2. **Şema kimliği ve sürümü** — dosya header'ında taşınır ve TOML'daki değerle
   karşılaştırılır. Tutmazsa kayıt açılmaz.
3. **Akıl sağlığı denetimi** — sensör sayısı, frame boyutu ve dosya uzunluğu birbirini
   tutmalıdır. `dosya_boyutu = header + frame_sayısı × (frame_header + 32 × 820 × 8)`
   denklemi sağlanmıyorsa şema yanlıştır.

Üçü de geçtiğinde okuma başlar. Biri düşerse kayıt açılmaz ve **hangi kapının neden
düştüğü** söylenir. Sessizce açmak, yanlış veriyle çalışılan bir analiz oturumu demektir.

## 8. Profil A ve B ile ilişki

Profil C üçüncü bir profildir; öncekiler emekliye ayrılmaz. Profil A kayıtları açılmaya
devam eder ve fixture'ları korunur.

| | Profil A | Profil B | Profil C |
| --- | --- | --- | --- |
| Yerleşim | Tek dosya | Tek dosya | **Klasör ağacı** |
| Örnek tipi | `float32` / ölçekli `int` | `int16` | **`complex64`** |
| Kanal kavramı | 8 sabit kanal | Kanal tablosu | **32 sensör × Tx/Rx** |
| Layout tanımı | Kodda `struct.Struct` | Kodda `struct.Struct` | **TOML şeması** |
| Üreten taraf | Bu uygulama | Bu uygulama | **C++ sistemi** |
| Yazma desteği | Var | Yalnız fixture | **Yok — okuma tarafı** |

Son satır bu profilin en belirgin farkıdır: uygulama Profil C **yazmaz**. Sentetik üreteç
yalnız test içindir ve bir ürün özelliği değildir.

## 9. Açık kararlar

| Kimlik | Soru | Durum |
| --- | --- | --- |
| `D-26` | Azami kayıt süresi | **Kapalı** — 10 dakika |
| `D-27` | 8192 Hz ile 820 örnek/100 ms tutarsızlığı | **Kapalı** — kayma kabul edildi |
| `D-28` | Complex örnek tipi | **Kapalı** — `complex64` (float complex) |
| `D-29` | Kayıt dosyalarını kim yazıyor | **Kapalı** — C++ tarafı |
| `D-30` | CIT alanı tam olarak nedir | **Açık** |
| `D-31` | PRI değeri ve Tx süresi | **Açık** |
| `D-32` | Bir frame'in 820 örneği tam PRI'yı mı kapsıyor | **Açık** |
| `D-33` | Zaman ekseni frame sayacından mı timestamp'ten mi | `F7-005` ile karara bağlanacak |
