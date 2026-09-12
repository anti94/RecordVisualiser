# Paketli uygulamada kullanıcı kabul turu — `F6-030`

Kabul: **Operatör ve mühendis akışları kanıtla işaretlenir;
başarısızlıklar ayrı işe dönüşür.**

Bu tur **paketlenmiş `.exe` üzerinde** yürütüldü. Kaynak ağacından
çalıştırmak bir şey kanıtlamaz; paketlemede kaybolan şeyler (eksik veri
dosyası, gelmeyen Qt eklentisi, yanlış sürüm) yalnız pakette görünür.

Koşucu: `tools/acceptance_run.py` ·
Ham kanıt: `docs/acceptance/results/packaged-acceptance.json`

## 1. Tur künyesi

| | |
| --- | --- |
| Çalıştırılan | `dist/sonar-analyzer-3.35.0/sonar-analyzer.exe` |
| Sürüm | `3.35.0` |
| Platform | Windows 11 (10.0.26200), x64 |
| Adım sayısı | **9** (4 operatör + 5 mühendis) |
| Geçen | **9** |
| Başarısız | **0** |

## 2. Yöntem

Her adım **çalıştırılmadan önce** ne beklendiğini bildirir: çıkış kodu,
çıktıda bulunması (ya da bulunmaması) gereken ifadeler ve üretilmesi
gereken dosyalar. Sonuç, sonradan uydurulmuş bir beklentiyle değil,
önceden yazılmış bir sözleşmeyle karşılaştırılır.

Üretilen her dosya için **boyut ve SHA-256** kaydedilir. "Yazıldı"
demek yetmez; boş ya da bozuk bir dosya da yazılmış olur.

Bazı adımlar **başarısızlık bekler**. Desteklenmeyen sürümlü ya da kesik
bir dosyanın açılmaması bu turda hata değil, **geçme koşuludur**.

## 3. Operatör akışı

Operatör uygulamayı açar, bir kaydı görüntüler, çıktı alır. Onun için
"çalışıyor", ekranın açılması ve dosyanın okunmasıdır.

| Adım | Ne denendi | Sonuç | Kanıt |
| --- | --- | --- | --- |
| `O-01` | Doğru sürüm kuruldu mu | **TAMAM** | `sonar-analyzer 3.35.0` |
| `O-02` | Ekransız temiz başlangıç ve kapanış | **TAMAM** | çıkış kodu 0; oturum log'u yazıldı |
| `O-03` | Ana ekran, tema ve ikon | **TAMAM** | `platform plugin: windows`, `tema: 3216 karakterlik stil sayfasi`, `ana ekran: 1520x1201`, `ikon: sonar-analyzer.ico` |
| `O-04` | Kayıt açma, CSV ve PNG çıktısı | **TAMAM** | 8 kanal / 8 kayıt; `export.csv` 8 satır geri okundu; `export.png` 1406 bayt, imza doğru |

`O-03` dört şeyi birden kanıtlar ve dördü de pencere **gerçekten
gösterilerek** denetlenir: Qt platform eklentisi yüklendi, tema
uygulandı, ana ekran açıldı, ikon paketten çözüldü.

`O-04`'te çıktılar yazıldıktan sonra **geri okundu**: CSV'nin veri satır
sayısı sorgudaki örnek sayısıyla karşılaştırıldı, PNG'nin dosya imzası
denetlendi.

## 4. Mühendis akışı

Mühendis verinin doğruluğunu sorgular. Onun için "çalışıyor", **bozuk
verinin reddedilmesi** ve sağlam verinin eksiksiz okunmasıdır.

| Adım | Ne denendi | Beklenen | Sonuç | Kanıt |
| --- | --- | --- | --- | --- |
| `M-01` | CRC'siz eski sürüm (v1) kayıt | açılmalı | **TAMAM** | 544 baytlık v1 dosya okundu, 8 satır CSV |
| `M-02` | Sıra boşluklu kayıt | açılmalı | **TAMAM** | boşluk kaydı bozulma sayılmadı, 8 örnek okundu |
| `M-03` | Desteklenmeyen format sürümü | **reddedilmeli** | **TAMAM** | `desteklenmeyen surum: 99 (desteklenen: 1, 2) (offset 8)`, çıkış kodu 1 |
| `M-04` | Kesik başlıklı dosya | **reddedilmeli** | **TAMAM** | `kesik header: 32 bayt gerekli, 20 bayt bulundu (offset 0)`, çıkış kodu 1 |
| `M-05` | Bozuk CRC'li kayıt | açılmalı **ve işaret görünmeli** | **TAMAM** | `kalite: 1/8 ornek isaretli (CRC_ERROR=1)`; CSV'de `quality` sütunu |

`M-03` ve `M-04`'te ret mesajları **nedenini ve bayt konumunu** veriyor.
"Dosya açılamadı" demek yerine hangi alanın hangi offsette
uyuşmadığını söylemek, sorunu firmware tarafında aranabilir kılar.

## 5. İlk turda düşen adım: `M-05` — düzeltildi

Bu bölüm, turun **ne işe yaradığının** kaydıdır: ilk koşuda `M-05`
düştü, bulgu ayrı bir işe dönüştürüldü, iş yapıldı ve tur tekrarlandı.

### 5.1 Ne bekleniyordu

`ADR-011` §2.4: kayıt CRC hatası **fatal değildir** — dosya açılır,
bozuk kayıt `CRC_ERROR` olarak işaretlenir ve verisi çizilmez. Dosyanın
tamamını reddetmek sağlam kayıtları da kaybettirirdi.

İşaretlenmiş olması tek başına yetmez: mühendis bunu **görebilmelidir**.

### 5.2 İlk koşuda ne oldu

`crc_error.bin` (bilinen bozuk CRC'li tek kayıt içerir) paketli
uygulamayla açıldı ve şu çıktı alındı:

```text
kayit: 8 kanal, 8 kayit
sorgu: ch0 -> 8 ornek
csv: 8 satir geri okundu (export.csv)
png: 1406 bayt, imza dogru (export.png)
sonuc: TAMAM
```

Üretilen CSV'nin sütunları yalnız `timestamp_ns, timestamp_utc, value`
idi. Bozuk kaydın değeri **diğer yedisinden ayırt edilemeden** yazıldı.

### 5.3 Kök neden

Hata okuma katmanında **değildi**. `FileRecordingRepository`, sürüm 2
dosyalarda her kaydın CRC'sini doğruluyor ve uyuşmayan kaydı
`Quality.CRC_ERROR` ile işaretliyordu — bu doğru çalışıyordu.

Kayıp, bilgiyi kullanıcıya taşıyan yoldaydı:

1. **CSV dışa aktarma** kalite bayraklarını hiç yazmıyordu; `DataChunk`
   içindeki bayrak bilgisi dosyaya çıkarken düşüyordu.
2. **`--bin-check`** sorgudan dönen bayrakları özetlemiyordu; bu yüzden
   bilinen bozuk bir dosyada bile `sonuc: TAMAM` diyordu.

Bozuk bir kayıttan alınan CSV'yi inceleyen biri, o sekiz sayıdan
birinin bütünlük denetiminden geçemediğini **anlayamazdı**. Bozuk bir
değeri ortalamaya katmak, onu hiç görmemekten daha zararlıdır.

### 5.4 Ayrı işe dönüştürüldü ve kapatıldı

`F6-035` — *Kalite bayraklarını dışa aktarmaya ve paket denetimine
taşı*. Bulgu ayrıca `K-21` olarak bilinen sorunlara yazıldı.

Kabul turu içinde **düzeltilmedi**: turun işi kusuru bulmak ve
kaydetmektir; bulduğu kusuru aynı iş içinde kapatmak, turun
başarısızlık yolunu da denetimsiz bırakırdı.

`F6-035` tamamlandıktan sonra paket yeniden üretildi ve tur
tekrarlandı:

```text
kayit: 8 kanal, 8 kayit
sorgu: ch0 -> 8 ornek
kalite: 1/8 ornek isaretli (CRC_ERROR=1)
csv: 8 satir geri okundu (export.csv)
png: 1406 bayt, imza dogru (export.png)
sonuc: TAMAM
```

CSV artık bir `quality` sütunu taşıyor ve bozuk örnek `CRC_ERROR`
olarak işaretli. `K-21` kapandığı için bilinen sorunlar listesinden
çıkarıldı.

## 6. Turun kendisi hakkında

- Atlanan adım **başarısızlık sayılır**. Fixture bulunamazsa adım
  "geçti" olmaz; eksik fixture problem olarak yazılır.
- Tur kendi sürümüne bağlıdır: öntanımlı olarak `VERSION`'daki sürümün
  paketi aranır. Başka bir sürümün paketiyle tur yürütmek, neyin kabul
  edildiğini belirsiz kılardı.
- Tur, başarısız adım varken **sıfırdan farklı** çıkış kodu döndürür;
  yayın akışına bağlanabilir.

## 7. İlgili belgeler

- Ham kanıt: `docs/acceptance/results/packaged-acceptance.json`
- MVP senaryoları: `docs/acceptance/mvp-scenarios.md`
- Bilinen sorunlar: `docs/release/known-issues.md`
- CRC kararı: `docs/adr/ADR-011-crc.md`
- Paketleme kararı: `docs/adr/ADR-012-packaging.md`
