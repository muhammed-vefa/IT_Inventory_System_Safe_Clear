# core/database_sql.py — Schema / Migration Risk İnceleme Raporu

Bu aşamada `core/database_sql.py` dosyasında **kod değişikliği yapılmadı**.

## Neden Patch Yapılmadı?

Bu dosya SQL bağlantısı, backup/restore, tablo oluşturma ve otomatik `ALTER TABLE` davranışlarını içeriyor. Mimari rehberde SQL schema/migration değişiklikleri açık onaya bağlı olduğu için burada doğrudan patch yapmak riskli olur.

## Eski Yedek ile Güncel Fark Özeti

Güncel dosyada eski yedeğe göre yeni/ek alanlar görünüyor:

| Yeni Unsur | Durum |
|---|---|
| `depot_transactions` | Güncel dosyada var, eski yedekte yok |
| `users.session_token` | Güncel dosyada var, eski yedekte yok |
| `users.trusted_ips` | Güncel dosyada var, eski yedekte yok |
| `user_sessions` | Güncel dosyada var, eski yedekte yok |
| `user_sessions.session_token/user_agent` type correction | Güncel dosyada var |

Bunlar auth/session ve depo hareket geçmişi alanına giriyor. Silinmemeli, eski yedekle geri alınmamalı.

## Yıkıcı / Hassas SQL İşaretleri

| Satır | Kod |
|---:|---|
| 70 | `query = f"BACKUP DATABASE [{DB_NAME}] TO DISK = '{backup_file}' WITH FORMAT, MEDIANAME = 'SQLServerBackups', NAME = 'Full Backup of {DB_NAME}'"` |
| 96 | `cursor.execute(f"ALTER DATABASE [{DB_NAME}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE")` |
| 99 | `query = f"RESTORE DATABASE [{DB_NAME}] FROM DISK = '{backup_file_path}' WITH REPLACE"` |
| 105 | `cursor.execute(f"ALTER DATABASE [{DB_NAME}] SET MULTI_USER")` |
| 115 | `cursor.execute(f"ALTER DATABASE [{DB_NAME}] SET MULTI_USER")` |
| 668 | `ALTER TABLE refresh_tokens ADD replaced_by_token NVARCHAR(MAX)` |
| 673 | `ALTER TABLE users ADD trusted_ips NVARCHAR(MAX)` |
| 678 | `ALTER TABLE users ADD session_token NVARCHAR(MAX)` |
| 702 | `cursor.execute(f"IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('{t}') AND name = 'archive_date') ALTER TABLE {t} ADD archive_date DATETIME")` |
| 703 | `cursor.execute(f"IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('{t}') AND name = 'deleted_at') ALTER TABLE {t} ADD deleted_at DATETIME")` |
| 785 | `cursor.execute(f"IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('{table}') AND name = '{col}') ALTER TABLE {table} ADD {col} {dtype}")` |
| 792 | `cursor.execute(f"IF EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('users') AND name = '{col}') ALTER TABLE users ALTER COLUMN [{col}] NVARCHAR(255)")` |
| 849 | `ALTER TABLE [{table}] ALTER COLUMN [{col}] {dtype}` |

## İzlenmesi Gereken Alan Adları

| Satır | Kelime | Kod |
|---:|---|---|
| 439 | `depo` | `"depot_items": """(` |
| 459 | `depo` | `"depot_transactions": """(` |
| 459 | `depot_transactions` | `"depot_transactions": """(` |
| 462 | `depo` | `item_type NVARCHAR(50) DEFAULT 'depot',` |
| 520 | `session_token` | `session_token NVARCHAR(MAX),` |
| 521 | `trusted_ips` | `trusted_ips NVARCHAR(MAX),` |
| 531 | `user_sessions` | `"user_sessions": """(` |
| 534 | `session_token` | `session_token NVARCHAR(MAX) NOT NULL,` |
| 671 | `trusted_ips` | `IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('users') AND name = 'trusted_ips')` |
| 673 | `trusted_ips` | `ALTER TABLE users ADD trusted_ips NVARCHAR(MAX)` |
| 676 | `session_token` | `IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('users') AND name = 'session_token')` |
| 678 | `session_token` | `ALTER TABLE users ADD session_token NVARCHAR(MAX)` |
| 751 | `depo` | `("depot_items", "is_deleted", "BIT DEFAULT 0"),` |
| 752 | `depo` | `("depot_items", "total_stock", "INT DEFAULT 0"),` |
| 753 | `depo` | `("depot_items", "current_stock", "INT DEFAULT 0"),` |
| 754 | `depo` | `("depot_items", "field_stock", "INT DEFAULT 0"),` |
| 755 | `depo` | `("depot_items", "faulty_stock", "INT DEFAULT 0"),` |
| 756 | `depo` | `("depot_items", "lost_stock", "INT DEFAULT 0"),` |
| 797 | `depo` | `for table in ["pcs", "printers", "tablets", "queing_machines", "barcode_printers", "barcode_readers", "scanners", "depot_items", "consumable_items"]:` |
| 834 | `session_token` | `("user_sessions", "session_token", "NVARCHAR(MAX)"),` |
| 834 | `user_sessions` | `("user_sessions", "session_token", "NVARCHAR(MAX)"),` |
| 835 | `user_sessions` | `("user_sessions", "user_agent", "NVARCHAR(MAX)")` |
| 863 | `depo` | `("depot_items", "saha_stock", "field_stock"),` |
| 863 | `saha_stock` | `("depot_items", "saha_stock", "field_stock"),` |
| 864 | `depo` | `("depot_items", "arizali_stock", "faulty_stock"),` |
| 864 | `arizali` | `("depot_items", "arizali_stock", "faulty_stock"),` |
| 864 | `arizali_stock` | `("depot_items", "arizali_stock", "faulty_stock"),` |
| 865 | `depo` | `("depot_items", "kayip_stock", "lost_stock"),` |
| 865 | `kayip_stock` | `("depot_items", "kayip_stock", "lost_stock"),` |
| 866 | `saha_stock` | `("consumable_items", "saha_stock", "field_stock")` |
| 896 | `mahal_kodu` | `# Anayasa Madde 9: Eski kolon adlari (pc_seri, mahal_kodu) yasaktir.` |

## Karar

`core/database_sql.py` için şu an **dosya üretmedim/değiştirmedim**. Çünkü buradaki her düzeltme canlı DB şeması ve auth/session davranışıyla ilişkili olabilir.

## Önerilen Sonraki İş

1. Önce canlı SQL’de gerçekten hangi tablolar/kolonlar var onu doğrula.
2. `mimari_rehber.md` içine şu alanlar eklenmeli mi karar ver:
   - `depot_transactions`
   - `user_sessions`
   - `users.session_token`
   - `users.trusted_ips`
3. Onaydan sonra `database_sql.py` için ayrı ve tek hedefli patch yapılmalı.

## Bu Aşamada Dokunulmayanlar

- SQL schema değiştirilmedi.
- `ALTER TABLE` kaldırılmadı.
- Backup/restore fonksiyonları değiştirilmedi.
- Auth/session alanları değiştirilmedi.
