# Filtre ve spektral analiz kullanım örneği — `F6-025`

Bu belge tek bir somut örneği baştan sona yürütür. Amaç özellikleri
saymak değil; **birim, örnekleme hızı, ilgi alanı (ROI) ve işlem
geçmişinin** her adımda nerede durduğunu göstermek. Bu dördü
karıştırıldığında sonuç sessizce yanlış olur ve grafik yine de makul
görünür.

## 1. Örnek: 50 Hz şebeke girişimini ayırmak

**Soru:** Basınç kanalında 50 Hz'lik bir girişim var mı, varsa asıl
sinyali bozuyor mu?

### 1.1 Başlangıç durumu

| | |
| --- | --- |
| Kayıt | `Data00000.bin`, Profil A sürüm 2 |
| Kanal | `ch0` — *Pressure*, birim **bar** |
| Örnekleme hızı | **8 Hz** (125 ms kayıt periyodu) |
| Kayıt süresi | 600 s |

**Örnekleme hızı burada belirleyicidir.** 8 Hz örneklenen bir kanalda
Nyquist sınırı **4 Hz**'dir; 50 Hz'lik bir girişim bu kanalda *doğrudan
görünemez*. Görünse bile o, 50 Hz'in kendisi değil **katlanmış**
(aliased) bir yankısıdır.

> Bu yüzden ilk iş filtre kurmak değil, **örnekleme hızını okumaktır**.
> Kanal ağacında kanala tıklayınca Inspector sekmesi hızı gösterir.
> 50 Hz'i gerçekten görmek için Profil B akustik kanal gerekir
> (48 kHz, `docs/format/profile-b.md`).

### 1.2 ROI (ilgi alanı) seçmek

Bütün kaydı analiz etmek gerekmiyor; şüphelenilen olay 120–180 s
arasında.

1. **Bölge 2**'den pencere genişliğini `60 s` yapın.
2. Grafikte 120 s'e kaydırın; durum çubuğu imleç zamanını hem göreli hem
   UTC olarak gösterir.
3. İsterseniz aralığı bir **işaret** (annotation) ile adlandırın; işaret
   workspace'e kaydedilir ve sonra aynı aralığa dönmek kolaylaşır.

**ROI analizi neyi değiştirir:** FFT ve istatistik **yalnız görünen
aralıktan** hesaplanır. Aralığı değiştirdiğinizde spektrum da değişir —
bu bir kusur değil, tanımın kendisidir. Karşılaştırma yaparken iki
ölçümün aynı ROI'de olduğundan emin olun.

### 1.3 İşlem zinciri kurmak

**Bölge 5 → Analysis Tools**. Adımlar **sırayla** uygulanır ve sıra
sonucu değiştirir:

| # | Adım | Parametre | Neden bu sırada |
| --- | --- | --- | --- |
| 1 | `detrend` | `mode=linear` | Eğilim (drift) spektrumda 0 Hz'e büyük bir tepe koyar ve ölçeği ezer |
| 2 | `bandpass` | `lo=0.5 Hz`, `hi=3.5 Hz`, `order=4` | Nyquist (4 Hz) altında kalır; üstü zaten güvenilir değil |
| 3 | `rms` | `window=2 s` | Zarf enerjisi; filtreden **sonra** anlamlı |

Sıra ters olsaydı: RMS'i filtreden önce almak, filtrenin ayırmaya
çalıştığı bileşenleri zaten birbirine karıştırırdı.

**Kesim frekansı seçerken kural:** `hi` değeri örnekleme hızının yarısını
(Nyquist) **aşamaz**. Aştığınızda uygulama adımı reddeder ve nedenini
yazar; sessizce sınıra kırpmaz, çünkü kırpılmış bir filtre sizin
tasarladığınız filtre değildir.

### 1.4 Spektrumu okumak

**Bölge 6 → Spectrum** sekmesi tek taraflı FFT genlik spektrumunu verir.

- **X ekseni** Hz; sağ sınır Nyquist'tir (burada 4 Hz).
- **Y ekseni** kanalın birimindedir (**bar**), dB değil. Birim
  değiştirmek için ölçek seçicisini kullanın; eksen etiketi seçiminizle
  birlikte değişir.
- **Pencere fonksiyonu** (rectangular / Hann / Hamming) seçilebilir. Hann
  sızıntıyı azaltır ama tepe genliğini düşürür; genlik okumak
  istiyorsanız bunu hesaba katın.

Spektrogram sekmesi aynı veriyi zaman–frekans düzleminde gösterir;
girişimin **sürekli mi yoksa olaya bağlı mı** olduğunu ancak orada
görürsünüz.

### 1.5 Sonucu yorumlamak

Bu örnekte 50 Hz doğrudan görünmez (Nyquist 4 Hz). Spektrumda 1,2 Hz'de
belirgin bir tepe çıkarsa bu ya gerçek bir fiziksel olaydır ya da daha
yüksek frekanslı bir bileşenin katlanmasıdır. Ayırt etmek için:

- örnekleme hızı daha yüksek bir kanala (Profil B) bakın,
- ya da olayın zamanla nasıl değiştiğine spektrogramda bakın.

Kılavuz burada bir cevap **uydurmaz**: 8 Hz'lik bir kanaldan 50 Hz
hakkında kesin bir şey söylenemez.

## 2. İşlem geçmişi

Kurduğunuz zincir **kaydedilir ve geri alınabilir**:

- **Geri/İleri al** (`Ctrl+Z` / `Ctrl+Y`) zincir ve işaret
  değişikliklerini adım adım geri alır.
- Zincir, türetilmiş kanallar ve işaretler **workspace dosyasına** yazılır
  (`.sonar-workspace.json`).
- Aynı workspace yeniden açıldığında **aynı sonuç** üretilir: FFT, PSD,
  STFT ve istatistik bit düzeyinde aynıdır (`F4-088` bunu doğrular).

Bu, bir ölçümü sonradan savunabilmenin yoludur: hangi adımların hangi
parametrelerle uygulandığı dosyada durur.

### 2.1 Dışa aktarırken geçmişi de yazın

**Bölge 9 → Export**, JSON biçimini seçerseniz çıktı işlem zincirini de
içerir. CSV çıktısı ise başındaki metadata satırlarında kanal, birim,
kaynak dosya ve aralığı taşır.

`raw` seçeneği kalibrasyonu **geri alır** ve ham cihaz değerlerini yazar;
`variant=raw` olarak işaretlenir. İşlenmiş ve ham değerleri aynı dosyada
karıştırmaz.

## 3. Sık yapılan dört hata

1. **Nyquist'i unutmak.** Örnekleme hızının yarısının üstünde bir şey
   aramak. Önce hızı okuyun.
2. **ROI'yi değiştirip spektrumları karşılaştırmak.** Farklı aralıkların
   spektrumları karşılaştırılamaz.
3. **Detrend'i atlamak.** Drift, 0 Hz'e koyduğu tepeyle bütün ölçeği
   ezer ve asıl tepeleri görünmez kılar.
4. **Pencere fonksiyonunu göz ardı etmek.** Hann ile okunan tepe genliği,
   rectangular ile okunandan sistematik olarak düşüktür.

## 4. İlgili belgeler

- Ana ekran ve bölgeler: `docs/guide/ana-ekran.md`
- Format ve örnekleme hızları: `docs/format/profile-a.md`, `docs/format/profile-b.md`
- Canlı veriyle aynı analiz: `docs/guide/canli-baglanti.md`
