# Çizim önbelleği — F4-059 / F4-060

Çizim sorguları, pencerenin değişmez kopyasını ve min/max özet seviyelerini LRU
önbelleğinde tutar. Tam çözünürlüklü analiz sorguları (`max_points=None`) doğrudan
kaynaktan okunur. Bütçe varsayılan olarak 64 MiB; boş sonuçların nesne sayısını da
sınırlamak için en fazla 256 pencere saklanır. Tek başına bütçeyi aşan pencere
sorgulanabilir fakat önbelleğe alınmaz.

`cache_stats()` tutulan NumPy dizilerinin baytlarını, isabet/ıska, çıkarma ve ret
sayılarını verir. Bu bütçe tüm süreç RAM'i değildir: Python nesneleri, kaynak
repository ve sorgu sırasında oluşan geçici diziler ayrıca bellek kullanır.

Ölçüm komutu (proje ortamında):

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
.venv/Scripts/python.exe tools/cache_benchmark.py docs/perf/results/cache-budget.json
```

[Kaydedilen yerel koşuda](results/cache-budget.json) 512 KiB bütçeyle 64 pencere
gezildi: 7 girdi / 476.504 bayt tutuldu, 57 girdi çıkarıldı. `tracemalloc` tutulan
belleği 525.468, tepeyi 693.683 bayt ölçtü. Bunlar sentetik yerel ölçümlerdir.

Önbellek anahtarı kanal, kaynak/işlem kimliği ve yarı açık zaman aralığından oluşur.
Kapsayan bir pencere ancak kimliğin tamamı aynıysa kullanılabilir. Kimlik şunları içerir:

- Dosyanın boyutu ve SHA-256 içerik özeti; simülasyonda üretici parametreleri.
- Kanal metadata'sı: kalibrasyon kimliği, gain/offset, örnekleme hızı ve zaman tabanı dahil.
- Parser, sayısal işlem ve özet algoritması sürümleri.
- İşlenmiş veri sağlayıcılarında `ProcessingChain.signature()` ile etkin adımların sırası
  ve parametreleri. Mevcut repository çizimleri fiziksel ham veriyi tutar; boş zincir kullanır.

Dosya özeti indeksin açılış kontrolünden tekrar kullanılır; her çizim sorgusunda
hesaplanmaz. Aynı dosya yolu ve boyut, içerik değiştiğinde aynı kaynak sayılmaz.
Açılış/kapanış ayrıca önbelleği temizler. Eski kimliğe ait girdiler yeni sonuçlar için
kullanılamaz; LRU bütçesine tabi kalır. Veri sağlayıcısı kullandığı kimliği sorgu boyunca
sabit tutmalı ve işleme/kaynak değişikliklerinde `identity_for` ile yeni kimlik vermelidir.
