# Proje incelemesi — 2026-09-09

İncelenen başlangıç: `adf20e6`, uygulama `0.91.0`. Amaç, kalan işleri mevcut
mimariye göre sırayla tamamlayarak referans SONAR panosuna kayıtlı veri sağlamaktır.

## Mevcut durum

- `domain` kanal, zaman, olay, BIT ve transmisyon sözleşmelerini içeriyor.
- `io` altında Profil A v1/v2 okuyucuları, CRC, sıra/zaman teşhisleri ve indeks
  bileşenleri var. Bu bileşenler henüz dosya açma yaşam döngüsünde birleşmemiş.
- `RecordingRepository` GUI'nin veri erişim sınırı. Şu an yalnız
  `MockRecordingRepository` uygulaması var; `MainWindow` simülasyonu bu arayüzle çiziyor.
- `Open .bin File` eylemi görsel olarak mevcut; dosya repository'sine bağlı değil.
- `tools/run.ps1` mevcut sanal ortamdan uygulamayı başlatıyor; kurulum ayrı betikte.
- Ana yol haritasında 347 işin 91'i tamamlanmış. Todo'nun 492 toplamı ayrıca
  145 bölüm içi kontrol maddesini içeriyor; bunlar 492 bağımsız geliştirme işi değil.

## Bulgular ve etkileri

| Bulgu | Etki | Devam işi |
| --- | --- | --- |
| Atomik indeks yazıcısı ve testleri çalışma ağacında yarım kalmış | İndeks kalıcılığı henüz sürüme dahil değil | F2-031 |
| İndeks okuma/yeniden üretme akışı yok | İkinci açılışta mevcut indeks kullanılamıyor | F2-032 |
| Dosya repository'si yok | Metadata, kanal ve zaman/olay sorguları GUI'ye sunulamıyor | F2-033–035 |
| Çoklu dosya kimliği ve ham offset erişimi birleşik değil | Kaynaklar ve teşhisler karışabilir | F2-036–037 |
| Parser parçaları ayrı test ediliyor; uçtan uca yaşam döngüsü eksik | CRC, bozuk kayıt ve kapanış davranışı birlikte doğrulanmalı | F2-038–041 |
| `SourceFingerprint.from_path` tüm dosyayı RAM'e alıyor | Büyük dosyada gereksiz tepe bellek kullanımı | İndeks/dosya akışında kademeli okuma; büyük veri işleri Faz 4 |
| Header/kayıt v1 ve v2 modelleri ayrı; birçok yardımcı v1 tipini alıyor | Birleştirme sırasında v2 CRC alanları sessizce atlanmamalı | Repository entegrasyonunda iki sürümlü kabul kontrolleri |

## Başlangıç doğrulaması

`tools/check.ps1` çalıştırıldı: Ruff lint, biçim kontrolü, strict Pyright,
Qt dışı testler, GUI testleri ve todo eşleşmesi geçti. Atomik indeksin ek
kontrolleri de geçti: bozuk UTF-8, rename/flush hatasında eski indeksin korunması
ve geçici dosyanın temizlenmesi.

Doğrulama yerel Python 3.9 ortamında yapıldı. Bu incelemede uzak CI çalıştırılmadı.
Gerçek cihaz kaydı ve onaylı donanım sözlüğü bulunmadığından sentetik fixture
sonuçları donanım doğrulaması olarak değerlendirilmez.

## Çalışma sırası

F2-031 → F2-032 → metadata → zaman/olay sorguları → çoklu kayıt → ham erişim ve
kapanış → golden/bütünlük kontrolleri → parser milestone'u. Her tamamlanan iş
kendi sürüm commit'i ve açıklamalı etiketiyle izlenir. Başlatma betiği/README
değişiklikleri ile kaynak arşivi indeks işinin commit'ine dahil edilmez.
