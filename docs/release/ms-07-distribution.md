# Milestone kabul tutanağı — `ms/07-distribution`

Bu tutanak Faz 6'nın (`F6-001`–`F6-034`) kabul ölçütünü, ne yapıldığını
ve **neyin doğrulanmadığını** kaydeder. Amaç, sonradan "bu sürümde ne
kanıtlanmıştı?" sorusuna tek yerden cevap verebilmektir.

| | |
| --- | --- |
| Milestone | `ms/07-distribution` |
| Sürüm | `v4.0.0` |
| İş sayısı | 34 (`F6-001`–`F6-034`) + `F6-035` (kabul turundan doğdu, kapatıldı) |
| Önceki milestone | `ms/06-live-recording` (`v3.0.0`) |

## 1. Faz kabul ölçütü

> Kurulum, mockup kabulü, kalite kapıları ve yayın belgeleri tamdır.

Dördü de aşağıda ayrı ayrı ele alınıyor.

## 2. İşler ve çıktılar

| Grup | İşler | Çıktı |
| --- | --- | --- |
| Paketleme | `F6-001`–`F6-012` | `ADR-012`, `packaging/sonar-analyzer.spec`, `packaging/installer.nsi`, ikon, sürüm çözümü, offline arşiv, imzalama kararı |
| Kalite kapıları | `F6-013`–`F6-018` | Coverage, bağımlılık taraması, performans smoke, paket smoke, sürüm artefaktı iş akışı, `docs/ci/quality-gates.md` |
| Dayanıklılık ve tanılama | `F6-019`–`F6-023` | Tanılama paketi, workspace kurtarma, aç/kapat dayanıklılık koşusu |
| Kullanım belgeleri | `F6-024`–`F6-029` | Beş kılavuz + bilinen sorunlar listesi |
| Kabul ve yayın | `F6-030`–`F6-034` | Paketli kabul turu, mockup karşılaştırması, geri dönüş prosedürü, sürüm notları, milestone kapanışı |

## 3. Kurulum — geçti

| Kontrol | Sonuç |
| --- | --- |
| Paket üretimi tek komutla | **TAMAM** (`tools/build_package.py`) |
| Kurulum dosyası üretimi | **TAMAM** (`tools/build_installer.py`, NSIS) |
| Temiz ortamda açılış (Python'suz) | **TAMAM** (`F6-005`) |
| Kurulum · yükseltme · kaldırma | **TAMAM** (`F6-008`) |
| Kaldırma kullanıcı verisine dokunmuyor | **TAMAM** (`F6-008`, `F6-032`) |
| Artefakt manifesti ve SHA-256 | **TAMAM** (`F6-009`) |
| Yeniden üretilebilirlik | **KISMİ** — 291 dosyanın 289'u birebir aynı; ikisi gömülü zaman damgası taşıyor (`F6-010`) |
| Offline bağımlılık arşivi | **TAMAM** — 17 wheel; tek platform/sürüme bağlı (`K-17`) |
| İmzalama | **YAPILMADI** — imzasız dağıtım kararı kayıtlı (`K-16`, `D-17`) |

## 4. Mockup kabulü — geçti

`tools/mockup_compare.py`, **paketli uygulamayı** `--layout-report` ile
çalıştırıp ana ekranı ölçtü. Yedi maddenin tamamı geçti:

| Madde | Ölçüm |
| --- | --- |
| Dokuz bölge doğru alanda | 9/9 |
| Hiyerarşi | 1 sol · 3 merkez · 3 sağ · 2 alt |
| Sütun genişlikleri | sol 200 px, sağ 319 px |
| Sekme çubuğu | 8 sekme, `Time Series` seçili |
| Pasif görünümler | 3 sekme v2 ipucuyla pasif |
| Koyu tema | 3216 karakter stil, arka plan `#0b1118` |
| Çalışan ana analiz | spektrum paneli gerçek kayıttan eğri üretti |

Ölçüm bir listeden kopyalanmadı: bölgelerin alanı pencerenin kendi
yerleşiminden okundu.

**Kapsam dışı:** piksel düzeyinde görsel karşılaştırma yapılmadı ve
%150 DPI ölçeklemesi bu turda ölçülmedi (kaynak ağacındaki DPI
testlerinde kapsanıyor).

## 5. Kullanıcı kabul turu — 9/9

`tools/acceptance_run.py`, iki rolü paketli `.exe` üzerinde yürüttü.

| Rol | Adım | Sonuç |
| --- | --- | --- |
| Operatör | Sürüm · ekransız başlangıç · ana ekran · kayıt açma ve CSV/PNG | **4/4** |
| Mühendis | v1 kayıt · sıra boşluğu · desteklenmeyen sürüm reddi · kesik başlık reddi · bozuk CRC | **5/5** |

**İlk koşuda `M-05` düştü.** Bozuk CRC'li bir kayıt açılıyor ve sekiz
örneği okunuyordu, ancak CSV çıktısı bozuk örneği hiçbir işaret olmadan
yazıyordu. Okuma katmanı doğruydu (`Quality.CRC_ERROR` atanıyordu);
kayıp, bilgiyi kullanıcıya taşıyan yoldaydı.

Bulgu **ayrı işe dönüştürüldü** (`F6-035`) ve kullanıcıya dönük
sınırlama olarak kaydedildi (`K-21`). Kabul turu içinde düzeltilmedi;
turun işi kusuru bulup kaydetmektir.

`F6-035` tamamlandıktan sonra paket yeniden üretildi ve tur
tekrarlandı: **9/9**. `M-05` artık aradığı kanıtı buluyor —
`kalite: 1/8 ornek isaretli (CRC_ERROR=1)`. `K-21` kapandığı için
bilinen sorunlar listesinden çıkarıldı (20 madde kaldı).

Bu, turun **ne işe yaradığının** kaydıdır: kaynak ağacındaki 5000'den
fazla test bu kusuru yakalamamıştı, çünkü hiçbiri "bozuk bir kayıttan
alınan CSV'yi bir mühendis okusa ne görür?" sorusunu sormuyordu.

## 6. Kalite kapıları — geçti

| Kapı | Eşik / ölçüt | Sonuç |
| --- | --- | --- |
| Lint · biçim · tip | `ruff` + `pyright` strict, sıfır hata | **TAMAM** |
| Testler | Tam takım | **TAMAM** |
| Kapsam | Genel ≥ %70 + kritik paketlerde daha yüksek | **TAMAM** — genel **%96,4**; `domain` %99,4 (≥90), `io` %97,3 (≥85), `recording` %98,2 (≥85), `repository` %98,3 (≥80) |
| Bağımlılık taraması | **Sevk edilen** pakette bulgu yok | **TAMAM** — 15 bulgu, hepsi geliştirme araçlarında (`K-20`) |
| Performans smoke | Cömert bütçeler; gerileme yakalama amaçlı | **TAMAM** (`F6-015`) |
| Paket smoke | CI'da paket üretilip çalıştırılıyor | **TAMAM** (`F6-016`) |

Bağımlılık kapısının ölçütü bilerek "bulgunun şiddeti" değil, "paket
kullanıcıya gidiyor mu" olarak seçildi: şiddeti bilinmeyeni engelleyici
saymak kapıyı sürekli çalar ve kapı kapatılır.

## 7. Yayın belgeleri — tam

| Belge | Durum |
| --- | --- |
| `docs/release/release-notes-v4.0.0.md` | **var** |
| `docs/release/known-issues.md` | **var** — 20 açık madde, her biri etki/iş/hedef düzeltme ile |
| `docs/release/release-and-rollback.md` | **var** — geri dönüş provası 12/12 |
| `docs/acceptance/packaged-acceptance.md` | **var** — 9/9; ilk koşudaki düşen adım ve kapanışı kayıtlı |
| `docs/ui/packaged-mockup-comparison.md` | **var** — 7/7 |
| `docs/ci/quality-gates.md` | **var** |
| Beş kullanım kılavuzu | **var** (`F6-024`–`F6-028`) |

## 8. Gerçek veri ve donanımla doğrulanmayan maddeler

Bu bölüm bilerek uzundur. Bir milestone'un en tehlikeli yanı,
doğrulanmamış olanı doğrulanmış sanmaktır.

| # | Ne doğrulanmadı | Neden | İzleniyor |
| --- | --- | --- | --- |
| 1 | Gerçek cihaz kaydıyla format | Elimizde gerçek `.bin` yok | `K-01`, `D-01` |
| 2 | Resmî format dokümanına uygunluk | Doküman gelmedi; taslak sözleşme sayıldı | `K-02`, `D-02` |
| 3 | Kanal katalogu ve kalibrasyon | Katalog gelmedi | `K-03`, `D-06` |
| 4 | BIT kodlarının gerçek anlamı | Katalog gelmedi | `K-04`, `D-07` |
| 5 | Zaman kaynağı ve drift | Bilgi gelmedi | `K-05`, `D-09` |
| 6 | Hedef makinede performans | Hedef makine bilinmiyor | `K-18`, `D-15` |
| 7 | Gerçek canlı cihazla akış | Protokol tanımı gelmedi; replay ve simülasyon kullanıldı | `D-12` |
| 8 | İmzalı dağıtım | Sertifika kararı verilmedi | `K-16`, `D-17` |
| 9 | Kurumsal dağıtım kanalı | Karar verilmedi; elle kurulum varsayıldı | `D-19` |
| 10 | %150 DPI'da paketli ekran | Bu turda ölçülmedi | kabul listesi 1.9 |

**Sentetik veri gerçek donanım doğrulaması sayılmaz** (plan Bölüm 22.1).
Bu sürümdeki hiçbir "format doğrulandı" ifadesi E-01/E-02 yerine
geçmez.

## 9. Kabul

Faz kabul ölçütünün dört başlığı da karşılandı:

- **Kurulum** — üretiliyor, kuruluyor, yükseltiliyor, kaldırılıyor ve
  temiz ortamda açılıyor.
- **Mockup kabulü** — paketli ana ekranda 7/7.
- **Kalite kapıları** — hepsi tanımlı, çalışır ve CI'a bağlı.
- **Yayın belgeleri** — sürüm notları, bilinen sorunlar, geri dönüş
  prosedürü ve kabul kanıtları tam.

Kabul turunun düşen adımı **kapatıldı** (`F6-035`) ve turun bulgusu
belgelerde izlenebilir kaldı. Bir kabul turunun değeri, geçmesi değil,
geçmediğinde ne olduğudur.
