# Antigravity Proje Hafızası (HAFIZA.md)

Bu dosya, yapay zeka ajanlarının (Antigravity) geçmişte çözdüğü spesifik sorunları, karşılaştığı tuzakları ve uyguladığı özel çözümleri unutmaması için tasarlanmış **Kalıcı Ortak Hafıza** (Knowledge Base) dosyasıdır.

**KURAL:** Ajan, bir bug'a müdahale etmeden veya "bu sorunu ilk kez görüyorum" yanılgısına düşmeden önce mutlaka bu dosyadaki kayıtları taramalıdır.

## 📝 Kronik Sorunlar ve Çözüm Arşivi

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

---

## 🖥️ Önemli Kodlar ve Entegrasyon API Protokolleri

### 1. BİM Entegrasyonu (Yazıcı Ekleme / Kaldırma) API İstekleri
Sistem, yazıcı ekleme ve kaldırma işlemleri için Kocaeli Sağlık Hizmetleri BİM sunucusundaki `Handler.ashx` endpoint'i ile haberleşir.

#### A. Giriş (Login) Aşaması
BİM API üzerinde işlem yapabilmek için önce bir oturum (session ID) alınması gerekir:
* **URL**: `http://bim.kocaelish.com/Handler.ashx`
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
* **URL**: `http://bim.kocaelish.com/Handler.ashx`
* **Yöntem**: POST
* **İstek Başlıkları (Headers)**:
  * `IPASession`: `<Login aşamasında alınan session_id>`
  * `User-Agent`: `Mozilla/5.0 (Windows NT 10.0; Win64; x64)...`
  * `Referer`: `http://bim.kocaelish.com/`
  * `Origin`: `http://bim.kocaelish.com`
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
* **URL**: `http://bim.kocaelish.com/Handler.ashx`
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
