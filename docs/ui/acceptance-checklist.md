# Mockup etkileşimleri ve görsel kabul listesi

> `F0-013` çıktısıdır. `docs/ui/layout-map.md` yerleşimi tanımlar; bu belge **davranışı** tanımlar:
> hangi etkileşim hangi gözlenebilir sonucu üretmeli ve kabulde ne kontrol edilir.
>
> Her madde tek başına kontrol edilebilir. "Düzgün çalışır" gibi ölçülemeyen ifade kullanılmaz.
> Kutular kabul oturumunda işaretlenir; kanıt olarak ekran görüntüsü veya kısa kayıt eklenir.

Kabul aşamaları: **M** = MVP (`v1.0.0`) · **A** = Analiz panosu (`v2.0.0`) · **L** = Canlı (`v3.0.0`)

## 1. Yerleşim kabulü (dokuz bölge)

| # | Kontrol | Aşama | Durum |
| --- | --- | --- | --- |
| 1.1 | Uygulama açıldığında dokuz bölgenin tamamı görünür ve `layout-map.md` §2'deki alanlardadır | M | [ ] |
| 1.2 | Sol sütun 200 px, sağ sütun 300 px, merkez kalan alan | M | [ ] |
| 1.3 | Sekme çubuğunda sekiz sekme, mockup sırasıyla; `Time Series` seçili açılır | M | [ ] |
| 1.4 | Merkez üç satır; alt satır solda FFT, sağda istatistik kartı | M | [ ] |
| 1.5 | Playback grafiklerin altında, Log playback'in altında | M | [ ] |
| 1.6 | Durum çubuğunda solda işlem durumu, sağda bellek göstergesi | M | [ ] |
| 1.7 | Koyu tema; eksen, birim, etiket ve pasif öğeler okunabilir | M | [ ] |
| 1.8 | Pencere 1280 px genişliğe indirildiğinde hiçbir eylem erişilemez hâle gelmez | M | [ ] |
| 1.9 | Windows %150 DPI ölçeğinde metin kırpılmaz | M | [ ] |
| 1.10 | `View → Reset Layout` mockup düzenine döner | M | [ ] |
| 1.11 | Panel taşınıp boyutlandırıldığında düzen workspace ile kaydedilir ve yeniden açılışta korunur | M | [ ] |

## 2. Dosya ve veri yönetimi (bölge 1)

| # | Etkileşim | Beklenen gözlenebilir sonuç | Aşama | Durum |
| --- | --- | --- | --- | --- |
| 2.1 | `Open .bin File` tıklanır | Dosya seçici açılır; yalnız desteklenen uzantılar öne çıkar | M | [ ] |
| 2.2 | Geçerli dosya seçilir | File / Size / Start / Duration / Platform alanları **açılan kayıttan** dolar; sabit örnek değer gösterilmez | M | [ ] |
| 2.3 | Dosya yüklenirken | Durum çubuğu `Parsing…`, ardından `Indexing…`; arayüz donmaz, iptal edilebilir | M | [ ] |
| 2.4 | Yükleme biter | Log'a zaman damgalı satırlar düşer (yüklendi, ayrıştırıldı, kanal sayısı) | M | [ ] |
| 2.5 | `Channels` / `Data Tree` sekmesi değiştirilir | İki sekme **aynı kanal modelini** gösterir; seçim korunur | M | [ ] |
| 2.6 | Arama kutusuna metin yazılır | Ağaç ada, ID'ye, birime ve kaynağa göre süzülür; eşleşme yoksa boş durum metni görünür | M | [ ] |
| 2.7 | Kanal çift tıklanır | Kanal aktif grafiğe eklenir ve çizilir | M | [ ] |
| 2.8 | Kanal grafiğe sürüklenir | Bırakılan kart kanalı ekler; geçersiz hedefte bırakma göstergesi olumsuzdur | M | [ ] |
| 2.9 | Kaynakta olmayan kanal | Seçilemez ve nedeni görünür; sahte veriyle çizilmez | M | [ ] |
| 2.10 | Çoklu seçim + `Aynı grafikte aç` | Seçili kanallar tek kartta, ayrı renklerle | M | [ ] |
| 2.11 | Sağ tık | Plot, Inspect, Add to Existing Plot, Export, Copy Path görünür | M | [ ] |

## 3. Görselleştirme ve hızlı araçlar (bölge 2, 3)

| # | Etkileşim | Beklenen gözlenebilir sonuç | Aşama | Durum |
| --- | --- | --- | --- | --- |
| 3.1 | Fare tekerleği | İmlecin bulunduğu eksende yakınlaşma; odak noktası kayar değil | M | [ ] |
| 3.2 | Sürükleme (pan aracı) | Görünüm kayar; veri yeniden yüklenirken grafik boş kalmaz | M | [ ] |
| 3.3 | Kutu ile yakınlaştırma | Seçilen dikdörtgen tam ekrana oturur | M | [ ] |
| 3.4 | `Sığdır` düğmesi | Tüm kayıt aralığı görünür | M | [ ] |
| 3.5 | Cursor aracı | İmleç konumundaki zaman ve değer, birimiyle okunur | M | [ ] |
| 3.6 | İki imleçli ölçüm | Δt ve Δdeğer gösterilir | M | [ ] |
| 3.7 | `Sync` işaretli | Zaman eksenli tüm kartlar aynı aralığı gösterir | M | [ ] |
| 3.8 | `Sync` kaldırılır | Kartlar bağımsız yakınlaşır; durum görsel olarak bellidir | M | [ ] |
| 3.9 | Zaman penceresi `1 s` değiştirilir | FFT ve istatistik yeni pencereyle yeniden hesaplanır; başlıkta pencere uzunluğu görünür | A | [ ] |
| 3.10 | Kanal seçici değiştirilir | İlgili kart yeni kanalı çizer; başlık ve birim güncellenir | M | [ ] |
| 3.11 | Zaman serisi çizimi | X/Y/Z sırasıyla mavi/turuncu/yeşil; legend sağ üstte | M | [ ] |
| 3.12 | Boşluklu bölge | Grafikte kesinti görünür; iki uç birleştirilmez, sıfırla doldurulmaz | M | [ ] |
| 3.13 | Spektrogram | Renk skalası sağda, `PSD [dB]` etiketli; renk haritası algısal olarak düzgün | A | [ ] |
| 3.14 | FFT kartı | Seçili zaman penceresinin spektrumu; eksen `Frequency [kHz]`, log büyüklük | A | [ ] |
| 3.15 | İstatistik kartı | Mean, Std, RMS, Min, Max, Peak-Peak; her biri birimiyle | A | [ ] |
| 3.16 | MVP'de hesaplanmayan analiz | Alan pasif ve `v2.0.0 ile kullanılabilir` açıklamalı; sahte sonuç gösterilmez | M | [ ] |

## 4. BIT ve analiz araçları (bölge 4, 5)

| # | Etkileşim | Beklenen gözlenebilir sonuç | Aşama | Durum |
| --- | --- | --- | --- | --- |
| 4.1 | Kayıt açılır | Alt sistem tablosu kayıttaki BIT sonuçlarıyla dolar; `Last Update` gerçek zamanı gösterir | M | [ ] |
| 4.2 | Bir alt sistem `Warning`/`FAIL` | Genel durum rozeti bunu yansıtır; `All Systems Nominal` yazamaz | M | [ ] |
| 4.3 | `Run BIT Analysis` | Kayıtlı BIT verisi yeniden özetlenir; **donanıma komut gönderilmez** | M | [ ] |
| 4.4 | BIT satırı seçilir | İlgili zamana gidilir ve grafiklerde marker seçili görünür (senaryo S-01) | M | [ ] |
| 4.5 | Filtre parametreleri girilir | Geçersiz değer (negatif kesim frekansı, sıfır derece) kabul edilmez ve neden görünür | A | [ ] |
| 4.6 | `Apply Filter` | Filtrelenmiş seri **ayrı** gösterilir; ham veri değişmez | A | [ ] |
| 4.7 | `Show filtered data` kapatılır | Ham seriye dönülür; hesaplanan sonuç silinmez | A | [ ] |
| 4.8 | Filtre uygulanmış kartta dışa aktarma | Çıktı, uygulanan işlem zincirini metadata olarak taşır | A | [ ] |

## 5. Zaman kontrolü ve log (bölge 7, 8)

| # | Etkileşim | Beklenen gözlenebilir sonuç | Aşama | Durum |
| --- | --- | --- | --- | --- |
| 5.1 | `Oynat` | İmleç ilerler; grafikler takip eder; geçen süre sayacı artar | M | [ ] |
| 5.2 | `Duraklat` | İmleç ve görünüm o anda durur | M | [ ] |
| 5.3 | Hız değiştirilir | Oynatma hızı değişir; seçili hız görünür | M | [ ] |
| 5.4 | Slider sürüklenir | İmleç anında taşınır; büyük dosyada arayüz donmaz | M | [ ] |
| 5.5 | `Start`/`End` girilip `Go` | Görünüm o aralığa gider; ters aralık (`End < Start`) reddedilir ve nedeni görünür | M | [ ] |
| 5.6 | Kayıt sonuna gelinir | Oynatma durur; sona geldiği belirtilir | M | [ ] |
| 5.7 | `Döngü` etkin | Aralık başa sararak tekrar oynatılır | M | [ ] |
| 5.8 | Herhangi bir işlem | Log'a zaman damgalı satır düşer; hata satırı görsel olarak ayrışır | M | [ ] |
| 5.9 | Log dolar | Otomatik kaydırma vardır ve kullanıcı yukarı kaydırınca durur | M | [ ] |
| 5.10 | Olay ayrıntısı aranır | Log değil, `Events` sekmesindeki tablo kullanılır; ikisi karıştırılmaz | M | [ ] |

## 6. Dışa aktarma ve ayarlar (bölge 9)

| # | Etkileşim | Beklenen gözlenebilir sonuç | Aşama | Durum |
| --- | --- | --- | --- | --- |
| 6.1 | `Export Format` seçilir | Seçilen biçim dışa aktarmada kullanılır | M | [ ] |
| 6.2 | `Export selected time range` işaretli | Yalnız seçili aralık yazılır; ilk/son satır aralık sınırlarıyla eşleşir (senaryo S-04) | M | [ ] |
| 6.3 | `Include metadata` işaretli | Kayıt kimliği, kanal, birim, zaman aralığı ve uygulanan işlemler çıktıya girer | M | [ ] |
| 6.4 | `Export Data` | Hedef yol sorulur; iş bitince Log'a satır düşer ve dosya oluşur | M | [ ] |
| 6.5 | Uzun dışa aktarma | İlerleme görünür ve iptal edilebilir; iptal edilen çıktı yarım dosya bırakmaz | M | [ ] |
| 6.6 | Ayarlar dişlisi | Tema, zaman gösterimi (UTC / yerel / geçen süre) ve birim tercihleri açılır | M | [ ] |
| 6.7 | Zaman gösterimi değiştirilir | Tüm eksen ve tablolar aynı anda değişir; hangi zamanın gösterildiği etiketlidir | M | [ ] |

## 7. Hata ve sınır durumları

| # | Durum | Beklenen davranış | Aşama | Durum |
| --- | --- | --- | --- | --- |
| 7.1 | Kesik header (`K-01`) | Dosya açılmaz; hata nedeni ve sayısal ayrıntı görünür; önceki oturum bozulmaz | M | [ ] |
| 7.2 | Desteklenmeyen sürüm (`K-05`) | Sürüm numarası gösterilir; genel "bozuk dosya" mesajı verilmez | M | [ ] |
| 7.3 | Kesik son kayıt (`K-02`) | Dosya açılır, sağlam kayıtlar okunur, uyarı görünür | M | [ ] |
| 7.4 | Sıra boşluğu (`K-03`) | Boşluk sayısı ve süresi raporlanır; grafikte kesinti | M | [ ] |
| 7.5 | CRC hatası (`K-04`) | Yalnız bozuk kayıt işaretlenir; diğerleri çizilir | M | [ ] |
| 7.6 | Ad/sıra uyuşmazlığı (`K-06`) | Uyarı verilir; sayısal alan esas alınır | M | [ ] |
| 7.7 | Boş kayıt / hiç kanal yok | Boş durum metni; grafik alanı hata vermez | M | [ ] |
| 7.8 | İşlenmemiş istisna | Kullanıcıya sızmaz; log'a ayrıntı, kullanıcıya anlaşılır ileti | M | [ ] |

## 8. Görsel kabul yöntemi

1. Referans PNG ile **aynı mantıksal pencere boyutunda** (1520 × 840) uygulama görüntüsü alınır.
2. Dokuz bölgenin konumu, sütun oranları, sekme sırası, kart başlıkları, eksen ve birim etiketleri
   karşılaştırılır.
3. Sinyal örneklerinin piksel piksel aynı olması **beklenmez**; veri doğruluğu ayrı kanıtlanır
   (fixture testleri).
4. Fark bulunursa bölge numarasıyla kaydedilir ve ilgili iş kimliğine bağlanır.
5. Kabul, `docs/scenarios.md`'deki beş senaryonun tamamı çalıştırılmadan kapanmaz.

## 9. Kapsam dışı (bu kabulde kontrol edilmez)

- `Cross Analysis`, `3D View` ve otomatik `Report` işlevleri — opsiyonel backlog.
- Canlı veri göstergeleri — Faz 5 (`L`).
- Gerçek donanım kaydıyla doğrulama — gerçek `.bin` gelene kadar yapılamaz (envanter E-01).
