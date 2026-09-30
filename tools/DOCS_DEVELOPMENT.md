# IT Envanter Sistemi - Teknik Geliştirme Rehberi

Bu belge, sistemin kritik mantıksal kurallarını ve algoritmalarını belgelemektedir. Gelecekteki güncellemelerde bu kuralların bozulmaması KRİTİKTİR.

## 1. Gelişmiş Arama Algoritması (Search Logic)

Sistemdeki arama motoru (`filterInventory` ve `applyPrinterFilters`), kullanıcıların hem çok spesifik hem de toplu aramalar yapabilmesini sağlayan hibrit bir yapıdadır.

### Kurallar:
1.  **Boşluk (Space) = VE (AND)**: Boşlukla ayrılan her kelime bir "Grup" olarak kabul edilir. Sonuçların TÜM gruplarla eşleşmesi zorunludur.
    *   Örnek: `A.01 HP` -> Mahal kodu A.01 olan VE HP markalı olanları getirir.
2.  **Tire (-) = VEYA (OR / Toplu Arama)**: Bir grup (kelime) içinde tire varsa, bu o grubun kendi içinde "VEYA" mantığıyla çalışacağı anlamına gelir.
    *   Örnek: `28-29-30` -> PC no 28 VEYA 29 VEYA 30 olanları getirir.
    *   Örnek: `A.01 28-29` -> A.01 mahali içindeki 28 veya 29 nolu PC'leri getirir.
3.  **PR- Ön Eki Koruması**: `PR-` ile başlayan terimler (Yazıcı Kodları) tire içermesine rağmen parçalanmaz. Bütün olarak `bagli_yazicilar` veya `pr_no` alanlarında aranır.
4.  **Eşleşme Önceliği (Sıralama)**:
    *   Sayısal terimler önce `pc_no` veya `id` ile **Tam Eşleşme** (Exact Match) kontrol edilir.
    *   Ardından IP adresi ve Seri No substring kontrolü yapılır.
    *   Harf içeren terimler Mahal Kodu, Mahal Adı ve Genel İçerik (Hostname, Açıklama vb.) içinde aranır.

---

## 2. CUPS Yazıcı Yönetim Mantığı

Yazıcıların `Pause`, `Resume` ve `Mahal Güncelleme` işlemleri CUPS 2.2 API (Web GUI) üzerinden simüle edilerek yapılır.

### Operasyon Eşleşmeleri:
*   **Pause**: `stop-printer` (Sadece `pause-printer` göndermek bazı sürümlerde çalışmaz).
*   **Resume**: `start-printer`.
*   **Reject Jobs**: `reject-jobs`.
*   **Accept Jobs**: `accept-jobs`.

### Mahal (Location) Güncelleme (Wizard Simulation):
CUPS'ta mahal güncellemek çok adımlı bir işlemdir. Başarılı bir güncelleme için şu payload yapısı korunmalıdır:
*   **URL**: `/admin/`
*   **Referer**: `/admin/?op=modify-printer&printer_name=[PR_NO]`
*   **Payload Anahtarları (Büyük Harf)**: `PRINTER_LOCATION`, `PRINTER_INFO`, `OP`, `PRINTER_NAME`, `CONTINUE`.
*   **Adımlar**: Önce sayfayı "GET" yaparak session primelenmeli, ardından "Continue" butonu ile POST edilmelidir.

---

## 3. UI/UX Standartları

1.  **Hızlı Temizleme (X)**: Tüm arama `input` alanları bir `.search-wrapper` içinde olmalı ve `app.clearSearch('id')` fonksiyonunu tetikleyen bir `.clear-btn` içermelidir.
2.  **Durum Renkleri**:
    *   Sahada / Kurulu: `--status-online` (#00ff88)
    *   Arızalı / Serviste: `--status-fault` (#ff4b2b)
    *   Depoda / Kayıp: `--status-warning` (#ffb400)

---

**Not**: Bu belgedeki kurallar kullanıcı deneyimi için hayati önem taşımaktadır. Kod refactoring işlemlerinde bu mantığın korunduğundan emin olun.
