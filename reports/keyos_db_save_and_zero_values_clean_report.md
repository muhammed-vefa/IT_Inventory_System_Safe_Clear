# Kök Sebep Analizi ve Patch Önerisi Raporu

## 1. İncelenen Dosyalar
- [UI_controller.js](file:///c:/Users/MUHAMMED-VEFA-IS/.gemini/antigravity/scratch/IT_Inventory/frontend/UI_controller.js)
- [inventory_core.py](file:///c:/Users/MUHAMMED-VEFA-IS/.gemini/antigravity/scratch/IT_Inventory/modules/inventory_core.py)
- [printers_printers.py](file:///c:/Users/MUHAMMED-VEFA-IS/.gemini/antigravity/scratch/IT_Inventory/modules/printers_printers.py)
- [utils.py](file:///c:/Users/MUHAMMED-VEFA-IS/.gemini/antigravity/scratch/IT_Inventory/core/utils.py)

## 2. Kök Sebep Analizi
1. **KeyOS Güncelleme Sonrası Kayıt:** `executeKeyOSUpdateDirect` fonksiyonu `await this.saveEdit()` çağrısı içermesine rağmen, form gönderilirken ve doğrulanırken bazı senaryolarda (örn. mükerrer IP/Hostname uyarılarında veya yeni çevre birimi onay pencerelerinde) işlem yarım kalmakta veya kullanıcıya çift işlem hissi uyandırmaktadır. Ayrıca, form verilerinde veya gönderilen payload'larda sterilizasyon eksikliği bulunmaktadır.
2. **"0" Değerlerinin Gösterilmesi:** Çevre birimlerin (barkod yazıcı, barkod okuyucu, tarayıcı, 1. ve 2. ekran) seri numaraları veritabanında `"0"` veya `"0.0"` olarak saklandığında, bu değerler arayüz listelerinde, datalistlerde, formlarda ve detay popuplarında doğrudan `"0"` olarak render edilmektedir. `cleanZeroValues` sadece belirli metotlarda çağrıldığı için datalistler ve bazı ekranlar bu temizlikten mahrum kalmaktadır.

## 3. Etkilenen Route & Endpointler
- POST `/keyos/update` (KeyOS MGT güncelleme tetikleyicisi)
- POST `/inventory/update` (Yerel PC/Monitör/Scanner/Barcode updates)
- POST `/printers/printers/update` (Yerel Printer updates)
- GET `/inventory/pcs`, `/inventory/monitors`, `/printers/.../get_all` (Veri çekme API'leri)

## 4. Domino Etkisi - Bozulabilecek 3 Alan
1. **Cihaz Detay Kayıt Akışı:** Form kaydederken seri numaralarının `None`/`NULL` yapılması, formda kayıtlı çevre birimlerinin otomatik eklenme/tanınma (auto-register) mantığını bozabilir.
2. **Arama ve Datalist Filtreleme:** Seri numarası `"0"` olan alanlar boş stringe dönüştüğünde, arama indekslerinde `"0"` araması yapan filtreler etkilenebilir.
3. **KeyOS Senkronizasyonu:** KeyOS MGT'deki boşluklar ile yerel DB'deki `NULL` değerleri arasında uyumsuzluk çıkabilir (ancak string normalizasyonu bunu önleyecektir).

## 5. Patch Önerisi (Minimal Patch)
1. **Frontend:**
   - `apiRequest` içinde gelen tüm JSON yanıtlarındaki seri no alanları (`monitor_seri`, `monitor2_seri`, `by_seri`, `bo_seri`, `tarayici_seri`, `pc_serial`, `serial_no`, `seri`) otomatik temizlenecek.
   - `saveEdit` ve `saveNewDevice` içinde `"0"` değerleri kaydedilmeden önce temizlenecek.
2. **Backend:**
   - `inventory_core.py` ve `printers_printers.py` update endpoint'lerinde `"0"` ve `""` seri no değerleri DB'ye `NULL` yazılması için `None` yapılacak.
   - `map_db_row_to_frontend` (inventory) ve `normalize_row` (printers) mappers içinde `"0"` değerleri `""` olarak normalize edilerek API çıkışında temizlenecek.

## 6. Rollback Planı

| Dosya | Değişiklik | Risk | Test/Kanıt | Rollback |
|---|---|---|---|---|
| `UI_controller.js` | `apiRequest`, `saveEdit`, `saveNewDevice` güncellemeleri | Düşük | Tarayıcı konsolu ve arayüz doğrulaması | `git checkout frontend/UI_controller.js` |
| `inventory_core.py` | `map_db_row_to_frontend`, `update_inventory`, `add_inventory` güncellemeleri | Orta | Python derleme ve API testi | `git checkout modules/inventory_core.py` |
| `printers_printers.py` | `update_printer` güncellemeleri | Orta | Python derleme ve API testi | `git checkout modules/printers_printers.py` |
| `utils.py` | `normalize_row` güncellemesi | Düşük | Python derleme testi | `git checkout core/utils.py` |
