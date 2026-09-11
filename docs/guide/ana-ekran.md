# Ana ekran kullanım kılavuzu — `F6-024`

> Bu kılavuz `docs/ui/layout-map.md`'deki dokuz bölgeye ve uygulamanın
> gerçek davranışına dayanır. Ekran görüntüsündeki sayılar bölge
> numaralarıdır; uygulamada görünmezler.

Uygulama açıldığında pencere üç sütun ve bir alt şeritten oluşur. Yerleşim
referans mockup'la birebir eşleşir ve dosya açıldığında da, canlı akış
sürerken de değişmez.

## 1. Dokuz bölge

| # | Bölge | Nerede | Ne işe yarar |
| --- | --- | --- | --- |
| 1 | **Dosya ve Veri Yönetimi** | sol sütun | `.bin` açma, dosya özeti, kanal ağacı, arama |
| 2 | **Hızlı Araçlar** | merkez üst | Pencere genişliği, kanal seçimi, X-senkron, marker/TX anahtarları |
| 3 | **Görselleştirme Alanı** | merkez | Zaman serisi, spektrogram, FFT ve istatistik |
| 4 | **Donanım / BIT Durumu** | sağ sütun | Alt sistemlerin en kötü durumu ve rozet |
| 5 | **Hesaplamalar ve Analiz** | sağ sütun | İşlem zinciri: filtre, FFT, istatistik, özel adımlar |
| 6 | **Çoklu Görünüm** | merkez üst | Time Series · Spectrum · Spectrogram · … sekmeleri |
| 7 | **Zaman Kontrolü** | alt şerit | Oynat/duraklat, hız, konum, zaman etiketi |
| 8 | **Log / Mesajlar** | alt şerit | Olaylar, uyarılar, kayıt ve bağlantı mesajları |
| 9 | **Ayarlar ve Dışa Aktarma** | sağ sütun | CSV/JSON/PNG/PDF çıktı, biçim ve aralık seçimi |

Sol sütun 200 px, sağ sütun 300 px civarında sabit-esnektir; merkez kalan
alanı alır ve pencere büyüdükçe **merkez büyür**. Bu, en çok yer isteyen
şeyin grafik olmasındandır.

## 2. Dosyadan analize ana akış

### 2.1 Kayıt açma

**Bölge 1 → Open .bin** ya da `Ctrl+O`.

Açılır açılmaz dosya özeti görünür: kayıt süresi, kanal sayısı, başlangıç
zamanı ve format sürümü. Sürüm bilgisi önemlidir — Profil A sürüm 1 ile
sürüm 2 aynı görünür ama ikincisi CRC taşır (`docs/format/profile-a.md`).

Dosya bozuksa uygulama **açmayı reddeder ve nedenini yazar**; yarım bir
kayıtla açılıp sessizce yanlış veri göstermez. Bozuk kayıtların nasıl
raporlandığı `docs/format/` altındadır.

### 2.2 Kanal seçme

Kanal ağacı (bölge 1) kayıttaki kanalları gösterir. Bir kanala **çift
tıklamak** onu zaman serisine çizer. Arama kutusu uzun listelerde ada göre
süzer.

Birden çok kanal çizildiğinde hepsi **aynı zaman eksenini** paylaşır. Farklı
birimdeki kanallar (basınç ve sıcaklık gibi) ikinci bir Y ekseni alır;
değerler birbirine karışmaz.

### 2.3 Zaman aralığı seçme

- **Bölge 2**'deki pencere genişliği listesi hazır aralıkları verir (1 s, 10 s …).
- Grafikte **sürükleyerek** yakınlaşabilir, tekerlekle ölçek değiştirebilirsiniz.
- **Bölge 7**'deki oynatma denetimi zamanı ilerletir; imleç konumu durum
  çubuğunda hem göreli hem UTC olarak görünür.

`Sync` işaretliyken bir grafikte yaptığınız yakınlaştırma diğerlerine de
uygulanır. Bu, aynı olayı farklı kanallarda karşılaştırmanın yoludur.

### 2.4 Analiz çalıştırma

**Bölge 5 → Analysis Tools** işlem zincirini kurar. Adımlar sırayla
uygulanır ve sıra önemlidir: önce detrend, sonra filtre, sonra FFT gibi.

Zincir çalışırken arayüz kilitlenmez; uzun işlemler iptal edilebilir.
Sonuçlar bölge 3'teki FFT ve istatistik hücrelerinde görünür.

Analiz sonucu her zaman **kaynak veriden** türetilir; grafikte gördüğünüz
işlenmiş eğri ham veriyi değiştirmez. Ham ve işlenmiş seriyi birlikte
görebilirsiniz.

### 2.5 Dışa aktarma

**Bölge 9 → Data Export**. Biçim seçilir (CSV, JSON, PNG, PDF), aralık
seçilir (görünen pencere ya da tüm kayıt) ve yazılır.

CSV çıktısı başında metadata satırları taşır: kanal kimliği, birim, kaynak
dosya ve dışa aktarılan aralık. Böylece dosya tek başına da anlamlıdır.
`raw` seçeneği kalibrasyonu geri alır ve ham cihaz değerlerini yazar.

## 3. Neyin nerede olduğunu hatırlamanın kolay yolu

- **Sol** = veri nereden geliyor,
- **Merkez** = veri nasıl görünüyor,
- **Sağ** = veriye ne yapılıyor ve nereye gidiyor,
- **Alt** = zaman ve ne olduğu.

## 4. Durum çubuğu

Pencerenin altında soldan sağa: genel durum, açık dosya, **bağlantı
durumu**, **kayıt durumu** ve imleç zamanı; en sağda bellek kullanımı.

Bağlantı ve kayıt alanları canlı veriyle ilgilidir ve
`docs/guide/canli-baglanti.md`'de anlatılır. Dosyayla çalışırken boş
görünürler (`—`).

## 5. Sonraki adımlar

- Filtre ve spektral analiz örneği: `docs/guide/filtre-ve-spektral-analiz.md`
- Canlı bağlantı ve kayıt: `docs/guide/canli-baglanti.md`
- Klavye ve fare kısayolları: `docs/guide/klavye-ve-olcekleme.md`
- Bilinen sorunlar: `docs/guide/bilinen-sorunlar.md`
