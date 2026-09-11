# F4-094 — Özet piramidi blok işlemleri

İlk seviyedeki her 32 örnek için ayrı Python çağrısı yerine NumPy satır işlemleri kullanılır. Üst seviyeler aynı kaynak indekslerini dört alt bloktan birleştirir. Geçici matrisler 131.072 aday örneklik parçalara ayrılır; kaynak dizinin tamamı kopyalanmaz. Min için ilk, max için son, geçersiz örnek için ilk konum korunur. int64/uint64 değerleri float dönüşümüne uğramaz.

`vectorized-summary-probe.json`: aynı 1 GB dosyada indeks ölçümden önce kuruldu; 2.000 nokta bütçesiyle ilk on ayrı 1 saniyelik pencere sorgulandı. Her sorgudan önce DisplayQuery cache temizlendi; tracemalloc ölçüm boyunca açıktı. Sorgular 7,62–9,49 ms sürdü (en yavaş sorgu 105,4 FPS hazırlık eşdeğeri). Önceki F4-093 koşusunun 1 saniyelik sorgusu 76,21 ms idi. Qt paint ölçüme dahil değildir; kapsamlı üç dosyalı tekrar F4-096’dadır.

65 ilgili test ve strict Pyright geçti; Ruff temiz. Testler bütün piramit seviyelerini ham extrema referansıyla karşılaştırır; tamsayı hassasiyeti, eşit değerler, NaN/Inf, kısmi bloklar ve parça sınırları kapsanır.

Tam kayıt sorgusunun ham veri biriktirmesi ayrı F4-095 işidir; bu değişiklik tek başına toplam bellek hedefini kapatmaz.
