# Videolu Demo

`sonar-analyzer-demo.mp4` — 55 saniye, 1520 × 1152, 15 fps, ~1,6 MB.

Video **çalışan uygulamanın kendisidir**. Bir animasyon, bir mockup ya da bir ekran
kaydı yazılımıyla alınmış bir çekim değil: `tools/demo_video.py`, `MainWindow`'u görünmez
bir Qt platformunda açar, senaryoyu uygulamanın genel API'siyle sürer ve her adımda
pencerenin kendisini yakalar. Görünen her piksel uygulamanın o an çizdiği şeydir.

## Yeniden üretme

```powershell
.venv\Scripts\python.exe tools\demo_video.py --out docs\demo\sonar-analyzer-demo.mp4 --fps 15
```

| Seçenek | Öntanım | Etki |
| --- | --- | --- |
| `--out` | `docs/demo/demo.mp4` | Çıktı yolu |
| `--fps` | 15 | Kare hızı (1–60) |
| `--scale` | 1.0 | Çıktı ölçeği (0 < s ≤ 1) |
| `--ffmpeg` | PATH'ten bulunur | `ffmpeg` çalıştırılabilirinin yolu |

`ffmpeg` gerekir. Kareler ara PNG dosyası yazılmadan **ham RGB olarak boruyla** verilir.

## Sahneler

| # | Sahne | Veri kaynağı |
| --- | --- | --- |
| 1 | Boş durum, üç sütunlu yerleşim | — |
| 2 | Gerçek `.bin` açılır | `tests/fixtures/valid_8records.bin` (Profil A) |
| 3 | Simülasyon kipine geçiş | Uygulamanın `Tools → Load Simulation Data` eylemi |
| 4 | Kanal çift tıklanır, zaman serisi | simülasyon |
| 5 | İkinci kanal, ikinci Y ekseni | simülasyon |
| 6–7 | Yakınlaştırma ve görünüm sıfırlama | simülasyon |
| 8 | Spectrum (FFT / PSD) | simülasyon |
| 9 | Spectrogram (STFT) | simülasyon |
| 10 | BIT / Status | simülasyon |
| 11 | Transmission | simülasyon |
| 12 | Olay tablosu ve kanal incelemesi | simülasyon |
| 13 | CSV dışa aktarma | simülasyon |
| 14 | Sürüm kapanışı | — |

## Veri kaynağı neden altyazıda yazıyor

Üçüncü sahneden sonrası **simülasyon verisidir** ve altyazı bunu açıkça söyler. Elde
gerçek cihaz kaydı yok (açık kararlar `E-01`, `E-02`); simülasyon çıktısını gerçek
telemetri gibi göstermek bu projede yapılabilecek en pahalı yanlış anlaşılma olurdu.
Sol üstteki Recording kartı da kaynağı `Simülasyon` olarak yazar, yani iddia ekranda
da doğrulanabilir.

## Simülasyon örnekleme hızı neden değiştirilmedi

Demo, uygulamanın kendi menü eylemini (`load_simulation()`) çağırır ve onun öntanımlı
8 Hz örnekleme hızını kullanır. İlk denemede daha "zengin" görünsün diye 256 Hz
denendi; sonuç ters çıktı. Simülasyonun akustik kanalı 1,5 Hz'lik bir ton taşıyor ve
Spectrum ekseni 0 Hz ile Nyquist arasını gösteriyor. 256 Hz'de Nyquist 128 Hz olur,
ton eksenin **sol kenarına yapışır** ve spektrum bomboş görünür. 8 Hz'de Nyquist 4 Hz'dir
ve ton eksenin ortasına, %37 konumuna düşer.

`tests/unit/test_demo_video.py` bunu bir kabul olarak tutuyor: tonun eksen üzerindeki
konumu %10 ile %90 arasında kalmazsa test düşer. Yani altyazının "tonu tepe olarak
görünür" iddiası bir daha sessizce yanlışlanamaz.

## Testler

`tests/unit/test_demo_video.py` (37 test) altyazıları **koddaki gerçeklerle**
karşılaştırır:

* sözü edilen her sekme sekme çubuğunda var ve **etkin** mi,
* sözü edilen kanallar simülasyon kaynağında var mı,
* "ikinci Y ekseni açılır" iddiasını doğrulayacak kadar birimler farklı mı,
* spektrumda görüneceği söylenen ton Nyquist'e göre görünür bir konumda mı,
* veri kaynağı değişimi altyazıda duyuruluyor mu,
* satır dolgusu karelerden atılıyor mu (atılmazsa video sessizce eğrilir).

## Bilinen sınır

Yakalama boyutu 1520 × 1151. İstenen 1520 × 840 idi ama pencerenin `minimumHeight`
değeri **1151 piksel**; pencere bundan kısa olamıyor. `docs/ui/layout-map.md` başlangıç
penceresini "~1520 × 840 mantıksal piksel" diye anlatıyor, yani belge ile davranış
ayrışıyor. 1080p bir ekranda pencere dikeyde sığmaz. Bu demo kapsamında düzeltilmedi;
düzeltmek merkez yerleşimi değiştirir ve `F6-031` mockup kabulünü yeniden ölçmeyi
gerektirir.
