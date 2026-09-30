# SAFE TO REMOVE - Temizlik Raporu

Bu rapor, sistemde teknik borç yaratan, yedekleme amacı güden veya artık kullanılmayan dosyaların listesini içerir. **Bu dosyalar doğrudan silinmemiştir, güvenle silinebileceği tespit edilmiştir.**

## 1. Geçici / Yedek (Backup) Dosyaları
*   **`main.py.bak`**
    *   **Neden Gereksiz:** Projenin bir önceki stabil sürümünün yedeğidir. Git gibi versiyon kontrol sistemleri kullanıldığından bu tarz `*.bak` dosyalarına üretim ortamında ihtiyaç yoktur.
    *   **Referans:** Hiçbir yerde referans edilmiyor.
    *   **Risk:** Yok.
*   **`backup_manager.py`** & **`manual_sql_backup.py`**
    *   **Neden Gereksiz:** `main.py` içerisindeki `check_saturday_backup()` fonksiyonu artık doğrudan `core.database_sql.backup_sql_db` metodunu kullanıyor. Bu ayrı betikler eski cron mantığından kalmış ve yedek amaçlıdır.
    *   **Referans:** Cron haricinde referans edilmiyor.
    *   **Risk:** Düşük.
*   **`tools/run_backup.py`**
    *   **Neden Gereksiz:** Aynı şekilde eski yedekleme görevlisidir. Core modül içindeki yedekleme mantığı ile çakışmaktadır.

## 2. Kullanılmayan Test / Araç Scriptleri
*   **`tools/nuclear_reset.py`** & **`tools/reset_db.py`**
    *   **Neden Gereksiz:** Tüm veritabanını sıfırlayan tehlikeli geçici test betikleridir. Canlı ortamda kazara tetiklenmesi felakete yol açabilir.
    *   **Referans:** Hiçbir modül çağırmıyor.
    *   **Risk:** Yok (Silinmesi güvenliği artırır).
*   **`tools/test_db.py`** & **`scratch/test_flask.py`**
    *   **Neden Gereksiz:** Geliştirme sürecinde oluşturulmuş tek seferlik doğrulama betikleridir.
    *   **Referans:** Yok.
    *   **Risk:** Yok.
*   **`tools/sync_trigger.txt`**, **`tools/sync_now.py`**, **`tools/upload_to_server.py`**
    *   **Neden Gereksiz:** CI/CD veya zamanlanmış görevlerin denemeleri için oluşturulmuş kalıntılar. Sistem artık doğrudan XAMPP ve Windows görev zamanlayıcısı ile entegredir.
    *   **Risk:** Yok.

## 3. Kod İçi Kalıntılar (Dosya bazlı değil, kod içi temizlik adayları)
*   `verileri_yukle.py` ve `tools/dashboard_debugger.py` içindeki eski "arizali" sayım mantıkları, yeni `is_faulty` yapısına tam geçiş sağlandıktan sonra (henüz devam ediyor) tamamen silinmelidir.
