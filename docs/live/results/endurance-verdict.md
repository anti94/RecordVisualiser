# Dayanıklılık koşusu değerlendirmesi — `F5-039`

Koşu: **2.0 saat** (57600 pencere), seed `20260911`, duvar saati 15.181 s.
Makine: Windows-10-10.0.26200-SP0 / Python 3.9.13.

| Ölçüt | Durum | Ölçülen | Kural | Not |
| --- | --- | --- | --- | --- |
| bellek butcesi | **gecti** | oran 1.0034 | son ceyrek / ilk ceyrek <= 1.1 | — |
| beklenen kayip | **gecti** | 0.0107 (617/57600) | uretilen = kaydedilen + dusen VE gozlenen oran 0.01 degerinden en cok %25 sapar | — |
| kayit butunlugu | **gecti** | 56983 kayit | her kayit geri okunur, CRC tutar, sira artar, artik bayt yok | — |
