# Antigravity Proje Hafızası (HAFIZA.md)

Bu dosya, yapay zeka ajanlarının (Antigravity) geçmişte çözdüğü spesifik sorunları, karşılaştığı tuzakları ve uyguladığı özel çözümleri unutmaması için tasarlanmış **Kalıcı Ortak Hafıza** (Knowledge Base) dosyasıdır.

**KURAL:** Ajan, bir bug'a müdahale etmeden veya "bu sorunu ilk kez görüyorum" yanılgısına düşmeden önce mutlaka bu dosyadaki kayıtları taramalıdır.

## 📝 Kronik Sorunlar ve Çözüm Arşivi

### [01.06.2026] - Çevre Birim Seri Numarası "0" Değer Temizliği
* **Sorun:** Barkod yazıcı (`by_seri`), barkod okuyucu (`bo_seri`), tarayıcı (`tarayici_seri`), 1. ekran (`monitor_seri`) ve 2. ekran (`monitor2_seri`) alanlarında "0" yazıyorsa bu arayüzde gösteriliyordu. Kullanıcı bu "0" verisini "veri yok" anlamında girmişti.
* **Kök Neden:** Veritabanında bu alanlar boş (NULL) yerine "0" veya "0.0" olarak kaydedilmişti. Frontend ve backend bu değeri geçerli seri numarası gibi işliyordu.
* **Çözüm (Çok Katmanlı Temizlik):**
  1. **Backend `normalize_row` (core/utils.py):** Tüm API yanıtlarında seri numarası alanları kontrol edilip "0", "0.0", "0,0" değerleri boş string'e çevrildi.
  2. **Backend `map_db_row_to_frontend` (inventory_core.py):** PCs tablosu satır eşlemesinde aynı temizlik uygulandı.
  3. **Backend `update_inventory` ve `add_inventory` (inventory_core.py):** Gelen JSON payload'daki "0" seri değerleri `None` (DB NULL) olarak yazılacak şekilde sterilize edildi.
  4. **Backend `update_printer` (printers_printers.py):** Yazıcı güncellemesinde aynı sterilizasyon uygulandı.
  5. **Frontend `apiRequest` (UI_controller.js):** Her API yanıtı alındığında merkezi temizleme fonksiyonu eklendi.
  6. **Frontend `saveEdit` (UI_controller.js):** Form gönderilmeden önce payload içindeki seri numarası alanlarından "0" değerleri temizlendi.
  7. **Frontend `cleanZeroValues` (UI_controller.js):** Zaten loadInventory/renderPrinters'da çağrılan mevcut temizleyici korundu.
* **Dosya Değişiklikleri:** `core/utils.py`, `modules/inventory_core.py`, `modules/printers_printers.py`, `frontend/UI_controller.js`
* **Önemli Not:** Bu temizleme sadece seri numarası alanlarına uygulanır. `pc_no`, `ip`, `mac` gibi alanlar etkilenmez.

### [01.06.2026] - KeyOS Güncelle Sonrası Otomatik Yerel DB Kaydı
* **Sorun:** Kullanıcı envanter kartında "KeyOS Güncelle" butonuna bastığında KeyOS MGT başarıyla güncelleniyor ancak yerel veritabanı kaydı yapılmıyordu. Kullanıcının ayrıca "Güncelle" butonuna da basması gerekiyordu.
* **Kök Neden:** `executeKeyOSUpdateDirect` fonksiyonu sadece KeyOS API çağrısı yapıyordu, yerel DB kaydı tetiklenmiyordu.
* **Çözüm:** `executeKeyOSUpdateDirect` başarılı yanıt aldığında `await this.saveEdit()` çağrısı eklenerek yerel DB'nin de otomatik güncellenmesi sağlandı. Bu sayede kullanıcı tek butonla her iki sistemi de güncelleyebilir.
* **Dosya Değişiklikleri:** `frontend/UI_controller.js` (`executeKeyOSUpdateDirect` fonksiyonu)

### [29.05.2026] - DevOps Engine Hayalet Import Hatası
* **Sorun:** Sistem başlatılırken (veya yetki kontrolünde) `No module named 'devops_engine'` hatası yaşanması.
* **Kök Neden:** `devops_engine` yapısının projeden silinmesine rağmen, `tools/main.py` içinde startup kontrolü ve `core/permissions.py` içinde safe_mode kontrolü için hala import edilmeye çalışılması.
* **Çözüm:** Kalan tüm import ve check (kontrol) satırları silinerek sistem temizlendi. Bu modül bir daha aranmamalıdır.

### [29.05.2026] - Toplu Yazıcı Ekleme/Kaldırma ve İkame Yazıcı Otomasyonu
* **İşleyiş Özeti:** Sistem, toplu yazıcı işlemlerini BIM'in API'si (`Handler.ashx`) üzerinden gerçekleştirir. Frontend (`UI_controller.js` içindeki `executeBatchPrinterAction` ve `handleAutomaticPrinterSwap`), seçilen PC'leri döngüyle **tek tek** işleyip her biri için backend'in `/printers/batch_action` rotasına istek atar. Backend (`printers_printers.py`), gelen PC ID'siyle veritabanından **anlık ve güncel IP adresini** çeker ve BIM API'ye `IpAddress` parametresi olarak iletir.
* **Kritik Payload Sözleşmesi:** Frontend'in yollayacağı JSON yapısı mutlaka backend'in beklentisiyle eşleşmelidir:
  `{ action: "add"|"remove", bim_function: "AddPrinter"|"RemovePrinter", command: "PR-001/01"|"PR-001", targets: [{type: "pc", value: <pc_id>}] }`
* **Geçmiş Tuzaklar ve Notlar:**
  1. **Hayalet Başarı (Sessiz Hata):** Geçmişte Frontend `targets` yerine `ips` ve `action` göndermediği için, backend listeyi boş sanıp işlem yapmadan `success: true` dönüyordu. Bu payload uyumsuzluğu çözüldü.
  2. **İşletim Sistemi:** Hastane uç birimleri (PC'ler) **KeyOS (Pardus/Linux) tabanlıdır**. Dolayısıyla PowerShell veya CMD komutları ile (`ExecuteCommand`) Windows'a özgü arka kapı kodları çalışmaz. Kaldırma (Remove) işlemleri için BIM'in standart `RemovePrinter` parametreleri kullanılmaya devam edilmelidir.

### [29.05.2026] - Haftalık Mahal Değişikliği Envanter Raporu (PDF)
* **İşleyiş Özeti:** Sistem, son 7 gün içinde mahali (`location_code` veya `keyos_location`) değiştirilen tüm IT cihazlarının (Bilgisayar, Tablet, Sıramatik, Yazıcı vb.) bir listesini raporlar. 
* **Backend Endpoint:** `/api/inventory/weekly_location_report` (GET, `@require_auth` yetkisi gerektirir). `audit_logs` tablosunu `field_name IN ('location_code', 'keyos_location')` ve `timestamp >= DATEADD(day, -7, GETDATE())` kriterleriyle sorgular, ardından `mahal_list` tablosunu kullanarak eski ve yeni mahal kodlarını anlaşılır mahal adlarına dönüştürür.
* **Frontend Entegrasyonu:** Kullanıcı profil dropdown menüsüne "Envanter Haftalık Rapor" butonu (`#menu-weekly-report`) eklenmiştir. Tıklandığında, `jsPDF` ve `jsPDF-AutoTable` kütüphanelerini kullanarak detaylı yatay (landscape) PDF raporu oluşturup indirir.
* **Dosya Değişiklikleri:**
  - [inventory_core.py](file:///c:/Users/MUHAMMED-VEFA-IS/IT_Inventory/modules/inventory_core.py) (Yeni endpoint)
  - [index.html](file:///c:/Users/MUHAMMED-VEFA-IS/IT_Inventory/index.html) (Buton eklemesi)
  - [UI_controller.js](file:///c:/Users/MUHAMMED-VEFA-IS/IT_Inventory/frontend/UI_controller.js) (Frontend api çağrısı ve PDF oluşturma fonksiyonu)

### [02.06.2026] - Yazıcı Servis Durumları ve Excel/PDF Form İhracat İyileştirmesi
* **Sorun:** Yazıcılar servis listesindeyken, Excel/PDF form çıktıları kısmen boş geliyor, bazı servis kayıtlarında seri no/MAC alanları eksik çıkıyor ve sisteme sadece "Arızalı" veya "Serviste" olarak eklenip henüz servis manager'a kaydı açılmamış yazıcılar çıktıda listelenmiyordu.
* **Kök Neden:**
  1. `/export_form` ve `/export_pdf` sorgularındaki `AND (s.acquisition_date IS NOT NULL OR s.sent_date IS NOT NULL)` koşulu, yeni açılan ve henüz tarihi girilmemiş tüm aktif servis kayıtlarını dışarıda bırakıyordu.
  2. Bazı servis kayıtları içe aktarılan Excel'deki eksiklikler nedeniyle boş serial_no, mac veya model alanlarına sahipti.
  3. Yazıcı statüsü envanter arayüzünde sadece `printers` tablosunun `is_faulty` ve `in_service` alanlarına bakılarak belirleniyordu; `printer_service` tablosundaki aktif kapanmamış servis kayıtları dinamik kontrol edilmiyordu.
* **Çözüm:**
  1. Excel ve PDF dışa aktarma (export) sorgularından tarih filtresi kaldırıldı. Kapanmamış (`return_date IS NULL`) tüm servis kayıtlarının ihracat dosyalarında yer alması sağlandı.
  2. İhracat aşamasında, `printers` tablosundan taze veriler çekilerek, servis kayıtlarındaki boş/eksik `serial_no`, `mac`, `model` ve `location_code` alanları veritabanındaki asıl yazıcı kartından dinamik olarak tamamlandı (Fallback enrichment).
  3. Sistemde `is_faulty = 1` veya `in_service = 1` durumunda olup, henüz `printer_service` kaydı oluşturulmamış cihazlar için dinamik olarak "Sanal Servis Kaydı" üretilip listeye dahil edildi.
  4. Yazıcı `/get_all` ve `/device/<id>` API rotalarında, her yazıcı için `printer_service` tablosunda aktif bir kayıt (`return_date IS NULL` ve `is_deleted = 0`) olup olmadığı sayısal `pr_no` bazında sorgulandı ve dinamik olarak statüsü güncellendi.
* **Dosya Değişiklikleri:** [service_manager.py](file:///c:/Users/MUHAMMED-VEFA-IS/.gemini/antigravity/scratch/IT_Inventory/modules/service_manager.py), [printers_printers.py](file:///c:/Users/MUHAMMED-VEFA-IS/.gemini/antigravity/scratch/IT_Inventory/modules/printers_printers.py)

### [03.06.2026] - Hostname Sıralama Otomasyonu (Sequence Gap Manager)
* **İşleyiş Özeti:** Belirli bir mahal koduna (Örn: `AB1T5143`) bağlı ve `AB1T5143x01` formatında isimlendirilmiş aktif makinelerin arasındaki sıra kopukluklarını (Örn: `x03` taşındığı için `x01`, `x02`, `x04` kalması durumunu) algılayarak, sıralamayı 1'den başlayıp ardışık olacak şekilde otomatik olarak yeniden düzenler.
* **Yürütme Scripti:** [seq_hostname_manager.py](file:///c:/Users/MUHAMMED-VEFA-IS/.gemini/antigravity/scratch/IT_Inventory/tools/seq_hostname_manager.py)
* **Desteklenen Modlar:**
  * **Dry-Run (Varsayılan):** `python tools/seq_hostname_manager.py --location AB1T5143` komutuyla çalıştırıldığında herhangi bir değişiklik yapmadan, sadece hangi makinelerin etkileneceğini tablo halinde simüle eder.
  * **Execute (Canlı Uygulama):** `python tools/seq_hostname_manager.py --location AB1T5143 --execute` komutuyla çalıştırıldığında veritabanını günceller ve KeyOS MGT API'sine bulk güncelleme isteği atarak isimleri sunucu üzerinde senkronize eder.
* **Kimlik Doğrulama:** Script, KeyOS MGT yetkilendirmesi için öncelikle `tools/.env` dosyasındaki `KEYOS_USER`/`KEYOS_PASS` alanlarını okur veya çalıştırılırken geçilen `--keyos-user`/`--keyos-pass` argümanlarını kullanır. Bilgiler eksikse çalışmayı güvenli şekilde durdurur (yetki aşımı veya diğer kullanıcıların şifrelerini kullanma riski tamamen önlenmiştir).

---

## 🖥️ Önemli Kodlar ve Entegrasyon API Protokolleri

### 1. BİM Entegrasyonu (Yazıcı Ekleme / Kaldırma) API İstekleri
Sistem, yazıcı ekleme ve kaldırma işlemleri için ornek Sağlık Hizmetleri BİM sunucusundaki `Handler.ashx` endpoint'i ile haberleşir.

#### A. Giriş (Login) Aşaması
BİM API üzerinde işlem yapabilmek için önce bir oturum (session ID) alınması gerekir:
* **URL**: `http://bim.ornek-kurum.com/Handler.ashx`
* **Yöntem**: POST
* **İstek Gövdesi (Form Data / URL Encoded)**:
  ```json
  {
    "Functions": "Login",
    "UserName": "<bim_user>",
    "Password": "<bim_pass>"
  }
  ```
* **Yanıt**: Başarılı durumda doğrudan session token string (örn. `ipa_session_id`) döndürülür. Hata durumunda ise `"Error"` string döner.

#### B. Yazıcı Ekleme (AddPrinter)
Bilgisayara yeni bir ağ yazıcısı tanımlamak için gönderilen istek:
* **URL**: `http://bim.ornek-kurum.com/Handler.ashx`
* **Yöntem**: POST
* **İstek Başlıkları (Headers)**:
  * `IPASession`: `<Login aşamasında alınan session_id>`
  * `User-Agent`: `Mozilla/5.0 (Windows NT 10.0; Win64; x64)...`
  * `Referer`: `http://bim.ornek-kurum.com/`
  * `Origin`: `http://bim.ornek-kurum.com`
* **İstek Gövdesi (Form Data / URL Encoded)**:
  ```json
  {
    "Functions": "AddPrinter",
    "UserName": "<bim_user>",
    "IPAddress": "<hedef_cihaz_ip>",
    "PrinterName": "PR-001/01"  // Tanımlanacak yazıcı kodu ve kuyruğu (Örn: PR-001/01)
  }
  ```

#### C. Yazıcı Kaldırma (RemovePrinter)
Bilgisayardan tanımlı bir ağ yazıcısını silmek için gönderilen istek:
* **URL**: `http://bim.ornek-kurum.com/Handler.ashx`
* **Yöntem**: POST
* **İstek Başlıkları**: Aynı (`IPASession`, `User-Agent`, `Referer`, `Origin`)
* **İstek Gövdesi (Form Data / URL Encoded)**:
  ```json
  {
    "Functions": "RemovePrinter",
    "UserName": "<bim_user>",
    "IPAddress": "<hedef_cihaz_ip>",
    "PrinterName": "PR-001"  // Kaldırılacak yazıcı adı (Örn: PR-001)
  }
  ```

---

### 2. Backend Toplu İşlem Rotası (Batch Action)
Uygulama sunucusunun kendi API'si üzerinden toplu eylemleri tetiklemek için kullanılan rota ve payload yapısı.

* **Rota**: `/printers/printers/batch_action` (veya `/printers/batch_action`)
* **Yöntem**: POST
* **Yetkilendirme**: `@require_editor`
* **Gönderilen JSON Verisi**:
  ```json
  {
    "action": "add" | "remove",
    "bim_function": "AddPrinter" | "RemovePrinter",
    "command": "PR-001/01" | "PR-001",
    "printer_id": <yazici_id_veya_null>,
    "targets": [
      { "type": "pc", "value": <hedef_pc_veritabani_id> }
    ],
    "user": "<aktif_kullanici_adi>",
    "bim_user": "<bim_kullanici_adi>",
    "bim_pass": "<bim_sifresi>"
  }
  ```

---

### 3. İkame Yazıcı Değişim Otomasyonu (Automatic Printer Swap)
Bir yazıcı arızalandığında veya bakıma alındığında, o yazıcıya bağlı olan tüm bilgisayarları yeni (ikame) yazıcıya geçirmek için tetiklenen frontend akışı (`frontend/UI_controller.js -> handleAutomaticPrinterSwap`):

1. **Hedef Tespiti**:
   Veritabanında `bagli_yazicilar` kolonunda eski yazıcı kodu (örn: `PR-001`) geçen bilgisayarlar filtrelenir.
2. **Kaldırma İsteği (Remove Old)**:
   Eski yazıcıyı kaldırmak için `/printers/printers/batch_action` endpoint'ine şu payload gönderilir:
   ```json
   {
       "action": "remove",
       "bim_function": "RemovePrinter",
       "command": "<eski_yazici_kodu>", // Örn: PR-001
       "printer_id": null,
       "targets": [{"type": "pc", "value": <pc_id>}],
       "user": "<aktif_kullanici>",
       "bim_user": "<bim_user>",
       "bim_pass": "<bim_pass>"
   }
   ```
3. **Ekleme İsteği (Add Substitute)**:
   Yeni ikame yazıcıyı kurmak için aynı endpoint'ye `/01` ekiyle ekleme payload'ı gönderilir:
   ```json
   {
       "action": "add",
       "bim_function": "AddPrinter",
       "command": "<yeni_yazici_kodu>/01", // Örn: PR-002/01
       "printer_id": null,
       "targets": [{"type": "pc", "value": <pc_id>}],
       "user": "<aktif_kullanici>",
       "bim_user": "<bim_user>",
       "bim_pass": "<bim_pass>"
   }
   ```

### [02.06.2026] - Manuel Müdahale ve Hata Çözümü İletişim Kuralı (Kritik Anayasa Kuralı)
* **Kural:** Kullanıcı bir hatanın çözüldüğünü (kodda yapılmış göründüğünü) ancak fiilen düzelmediğini (CUPS veya sunucu) rapor ettiğinde; "Cihazı yeniden başlatın", "Önbelleği (cache) temizleyin", "Sunucu güncellenmemiş olabilir" gibi **bahaneler ASLA sunulmayacaktır.**
* **Kullanıcının İş Akışı:** Kullanıcı, kod değişikliğini onayladıktan sonra değişiklikleri sunucuya *manuel olarak kopyalar*, sunucuyu (veya siteyi) *kendi eliyle yeniden başlatır* ve *CTRL+F5* ile arayüzü sıfırlar. Bu nedenle, hata devam ediyorsa sorun **kesinlikle yazılan kodun mantığında veya API çağrısındadır** (örn: eksik parametre, hatalı JSON parse, SQL kısıtlaması, sessizce yutulan try-catch bloku vb.).
* **Ajanın Sorumluluğu:** Kullanıcı "Değişen bir şey olmadı" dediğinde, kodun uçtan uca (Frontend JSON -> Backend Route -> DB SQL -> CUPS POST) akışı tekrar, daha derinlemesine (değişken isimleri, HTTP Payload tipleri, SQL syntax vs. açısından) denetlenmelidir. Cache veya restart bahanesi üretilmeyecektir.
