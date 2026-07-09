# 📋 SPESİFİK KODLAR / ÖZEL KODLAR (Akıllı Servis Otomasyonu)

> **Son Güncelleme:** 03.06.2026
> **Açıklama:** Yazıcı servis süreci için baştan aşağıya kurgulanan ve uygulanan tam otomasyon algoritması. İhtiyaç halinde bu belge referans kod niteliğindedir. Sistemin en stabil ve zeki halidir.

---

## 🚀 1. İŞ AKIŞI (Workflow)

Sistemde iki farklı senaryo çalışmaktadır:

### Senaryo 1: İkamesiz Servis Kaydı Açılması
Kullanıcı bir yazıcıyı servise gönderirken yerine "İkame Yazıcı" işaretlemezse:
1. İlgili yazıcının SQL veritabanındaki lokasyonu (`location_code`) **`SERVİSTE-[Eski_Lokasyon]`** (Örn: `SERVİSTE-a.b1.t4.333`) olarak güncellenir.
2. Cihaz CUPS üzerinden uzaktan bağlanılarak **Pause (Durdur)** ve **Reject (İşleri Reddet)** moduna alınır.
3. CUPS `PRINTER_LOCATION` bilgisi `SERVİSTE-[Eski_Lokasyon]` olarak güncellenir.

### Senaryo 2: İkameli Servis Kaydı Açılması (Tam Otomasyon)
Kullanıcı servise giden (Örn: PR-362) yazıcının yerine geçici bir ikame yazıcı (Örn: PR-214) verirse:
1. Eski yazıcı (PR-362) artık o mahale geri dönmeyeceği için veritabanı lokasyonu ve CUPS PRINTER_LOCATION bilgisi sadece **`SERVİSTE`** olarak güncellenir ve **Pause/Reject** edilir.
2. İkame yazıcının (PR-214) konumu, eski yazıcının asıl konumu (Örn: `a.b1.t4.333`) ile değiştirilir (SQL ve CUPS üzerinde).
3. Depoda durdurulmuş (Pause) olma ihtimaline karşı ikame yazıcı (PR-214) CUPS üzerinden **Resume (Başlat)** ve **Accept (İş Kabul Et)** komutlarıyla uyandırılır.
4. Sistemin hafızasından eski yazıcının (PR-362) bağlı olduğu tüm bilgisayarlar (IP'leri) tespit edilir.
5. Tespit edilen bu PC'lere BİM API üzerinden uzaktan bağlanılarak; önce eski yazıcı (PR-362) **kaldırılır (RemovePrinter)**, ardından aynı saniye içerisinde ikame yazıcı (PR-214/01) **kurulur (AddPrinter)**.

### Senaryo 3: Servis Kaydı Tamamlanması (Dönüş Tarihi Girildiğinde)
Servis kaydı güncellenerek dönüş tarihi eklendiğinde:
1. Tamirden dönen yazıcının (PR-362) konumu doğrudan **`Depo`** olarak güncellenir (SQL ve CUPS üzerinde).
2. CUPS üzerinden bu yazıcı (PR-362) **Pause (Durdur)** ve **Reject (İşleri Reddet)** moduna alınır.
3. **ÖNEMLİ:** Sahadaki ikame yazıcıya (PR-214) veya PC'lerdeki yazıcı bağlantılarına **hiçbir şekilde dokunulmaz**. İkame yazıcı artık o mahalin kalıcı yazıcısı olmuştur ve çalışmaya devam eder. Dönüş yapan yazıcı ise depoda yeni görevini bekler.

---

## 🏗️ 2. MİMARİ: TÜM OTOMASYON BACKEND'DE

> **ÖNEMLİ:** Otomasyon kodu tamamen **backend** tarafında (`service_manager.py`) çalışır.
> Frontend (`UI_controller.js`) sadece API çağrısı yapar ve sonucu bekler.
> Bu sayede güncelleme (update) sırasında otomasyon tekrar çalışmaz, sadece ilk kayıt ve servis tamamlama anında tetiklenir.

### Backend Dosyaları:
- **`modules/service_manager.py`** → `add_service()` ve `update_service()` rotaları
  - `run_service_automations_async()` → Arka plan thread'inde CUPS + BİM otomasyonu çalıştırır
- **`modules/printers_printers.py`** → `update_cups_printer_location_wizard()` fonksiyonu
  - CUPS 2.2.6 wizard tabanlı lokasyon değişimi (4 adımlı form navigasyonu)

### Frontend Dosyaları:
- **`frontend/UI_controller.js`** → `saveServiceRecord()` fonksiyonu
  - Sadece API'ye POST atar, otomasyon mantığı YOKTUR
  - Mükerrer kayıt kontrolü (açık servis kaydı varsa yenisi açılamaz)

---

## 🔧 3. CUPS WIZARD YAKLAŞIMI (REGEX İLE WIZARD GEZİNTİSİ)

CUPS 2.2.6'da `modify-printer` işlemi doğrudan bir POST ile yapılamaz. Wizard (sihirbaz) tabanlı çok adımlı form gerektirir. 
Harici paket (BeautifulSoup vb.) kurulumuna gerek kalmaması için sadece standart `re` (regex) kütüphanesi kullanılmıştır.

```python
def update_cups_printer_location_wizard(pr_no, new_location):
    """CUPS Wizard ile yazıcı lokasyonunu değiştirir (Regex Tabanlı).
    Step 1: Connection (DEVICE_URI)
    Step 2: Connection Details (BAUDRATE, PRINTER_LOCATION görünür)
    Step 3: Name/Location/Make (PRINTER_LOCATION override edilir)
    Step 4: Tamamlandı
    """
    import requests, re, base64

    clean_digits = "".join(filter(str.isdigit, str(pr_no)))
    if clean_digits: pr_no = f"PR-{clean_digits.zfill(3)}"

    CUPS_URL = "http://192.168.X.X:49631"
    CUPS_USER = "root"
    CUPS_PASS = "1234qqqQ"
    TIMEOUT = 30

    def parse_form(html):
        """CUPS wizard HTML'ini regex ile parse eder (bs4 gerektirmez)."""
        form_match = re.search(r'<FORM\s[^>]*METHOD="POST"[^>]*>(.*?)</FORM>', html, re.DOTALL | re.IGNORECASE)
        if not form_match: return None, {}
        
        form_html = form_match.group(0)
        form_body = form_match.group(1)
        action_m = re.search(r'ACTION="([^"]+)"', form_html, re.IGNORECASE)
        action = action_m.group(1) if action_m else '/admin'
        
        data = {}
        for m in re.finditer(r'<INPUT\s+[^>]*TYPE="HIDDEN"[^>]*NAME="([^"]+)"[^>]*VALUE="([^"]*)"', form_body, re.IGNORECASE):
            data[m.group(1)] = m.group(2)
        for m in re.finditer(r'<INPUT\s+[^>]*NAME="([^"]+)"[^>]*TYPE="HIDDEN"[^>]*VALUE="([^"]*)"', form_body, re.IGNORECASE):
            data[m.group(1)] = m.group(2)
        for m in re.finditer(r'<INPUT\s+[^>]*TYPE="TEXT"[^>]*NAME="([^"]+)"[^>]*VALUE="([^"]*)"', form_body, re.IGNORECASE):
            data[m.group(1)] = m.group(2)
        for m in re.finditer(r'<INPUT\s+[^>]*NAME="([^"]+)"[^>]*TYPE="TEXT"[^>]*VALUE="([^"]*)"', form_body, re.IGNORECASE):
            if m.group(1) not in data: data[m.group(1)] = m.group(2)
        for m in re.finditer(r'<INPUT\s+[^>]*TYPE="RADIO"[^>]*NAME="([^"]+)"[^>]*VALUE="([^"]*)"[^>]*CHECKED', form_body, re.IGNORECASE):
            data[m.group(1)] = m.group(2)
        
        for sel_m in re.finditer(r'<SELECT\s+[^>]*NAME="([^"]+)"[^>]*>(.*?)</SELECT>', form_body, re.DOTALL | re.IGNORECASE):
            name, options_html = sel_m.group(1), sel_m.group(2)
            selected = re.search(r'<OPTION\s+[^>]*VALUE="([^"]+)"[^>]*SELECTED', options_html, re.IGNORECASE)
            if selected:
                data[name] = selected.group(1)
            else:
                first = re.search(r'<OPTION\s+[^>]*VALUE="([^"]+)"', options_html, re.IGNORECASE)
                if first: data[name] = first.group(1)
        
        return action, data

    try:
        session = requests.Session()
        b64_auth = base64.b64encode(f"{CUPS_USER}:{CUPS_PASS}".encode()).decode()
        session.headers.update({'Authorization': f'Basic {b64_auth}'})

        r = session.get(f"{CUPS_URL}/printers/{pr_no}", verify=False, timeout=TIMEOUT)
        sid_m = re.search(r'org\.cups\.sid.*?VALUE="([^"]+)"', r.text, re.I)
        if not sid_m: return False, "SID bulunamadı"
        
        html = session.post(f"{CUPS_URL}/admin/", data={
            'org.cups.sid': sid_m.group(1), 'OP': 'modify-printer', 'printer_name': pr_no
        }, verify=False, timeout=TIMEOUT).text

        for step in range(6):
            action, data = parse_form(html)
            if not action or not data:
                return True, f"{pr_no} CUPS lokasyonu güncellendi."
            if 'PRINTER_LOCATION' in data:
                data['PRINTER_LOCATION'] = new_location
            html = session.post(f"{CUPS_URL}{action}", data=data, verify=False, timeout=TIMEOUT).text

        return True, "CUPS wizard tamamlandı."
    except Exception as e:
        return False, f"CUPS Wizard Hatası: {str(e)}"
```python
# ÖRNEK: CUPS Pause ve Reject İşlemi (Backend)
import requests
cups_admin_url = 'http://192.168.X.X:49631/admin/'

# Pause (Durdur)
requests.post(cups_admin_url, data={
    'OP': 'pause-printer',
    'printer_name': 'PR-362',
    'confirm': 'Yes'
}, timeout=10, verify=False)

# Reject (İş Kabulünü Kapat)
requests.post(cups_admin_url, data={
    'OP': 'reject-jobs',
    'printer_name': 'PR-362',
    'confirm': 'Yes'
}, timeout=10, verify=False)
```

---

## 🛡️ 4. GÜVENLİK KURALLARI

1. **Mükerrer Kayıt Engeli:** Aynı yazıcı için açık (dönüş tarihi olmayan) servis kaydı varken yeni kayıt açılamaz.
2. **Sadece İlk Kayıtta Otomasyon:** Servis kaydı güncellenirken CUPS/BİM otomasyonu tekrar çalışmaz.
3. **Silinen Kayıt Sonrası:** Servis kaydı silindikten sonra `loadServiceRecords()` await ile çağrılır, eski cache temizlenir.
4. **Stale Cache Koruması:** Durum değişikliği öncesi `await this.loadServiceRecords()` ile güncel veri çekilir.

---

## 🚨 5. BİM API ENTEGRASYONU VE KOMUT ŞİFRELEME (KRİTİK UYARI)

> **DİKKAT: BUNU YAPARSANIZ SİSTEM SESSİZCE PATLAR VE SORUNU BULMANIZ GÜNLER SÜRER!**
> BİM (RMM) ajanlarına arka uç üzerinden komut gönderirken (Ortak Alan tanımlama, Script çalıştırma vb.) uyulması KESİN ZORUNLU iki kural vardır:

### 1. `RunCommand` Parametresi Asla `Command` Değildir!
BİM API'sinde `RunCommand` (Komut Çalıştır) fonksiyonu tetiklenirken, gönderilecek script dizisi **`Command`** parametresiyle değil, SONUNDA "S" HARFİ OLAN **`Commands`** parametresiyle gönderilmelidir. 
Eğer yanlışlıkla `Command` yazarsanız:
- BİM sunucusu size **"Başarılı" (HTTP 200)** yanıtı döner.
- Ancak hedef ajana "BOŞ" bir komut kaydeder.
- Ajan sessizce hiçbir şey yapmaz (Silent Failure) ve saatlerce sorunun nerede olduğunu ararsınız.

**Doğru Kullanım:**
```python
post_data["Functions"] = "RunCommand"
post_data["Commands"] = command  # <--- SONUNDAKİ 'S' HARFİNE DİKKAT!
```

### 2. URL Encoding'de Boşluklar `+` Değil, `%20` Olmalıdır!
Linux hedeflerine Base64 komut zinciri (Örn: `echo IyE... | base64 -d | bash`) gönderirken Python'ın varsayılan `urllib.parse.urlencode` fonksiyonu boşlukları `+` işaretine çevirir (`echo+IyE...+%7C...`).
BİM'in arka uç işleyicisi (Handler.ashx) `+` işaretini geri boşluğa dönüştürme (URL Decode) konusunda hatalı (legacy) davranır ve `+` işaretini 그대로 (olduğu gibi) veritabanına yazar. Ajan bu komutu `echo+IyE...` şeklinde bitişik ve hatalı olarak alır.

**Doğru Kullanım (Python `requests` için):**
Bu durumu aşmak ve BİM'in Javascript arayüzünü (encodeURIComponent) taklit etmek için Python'da boşlukları zorla `%20` yapmalısınız:
```python
import urllib.parse
# quote_via=urllib.parse.quote argümanı boşlukları + yerine %20 yapar!
encoded_data = urllib.parse.urlencode(post_data, quote_via=urllib.parse.quote)

cmd_resp = requests.post(base_url, data=encoded_data, headers={"Content-Type": "application/x-www-form-urlencoded"}, ...)
```

---

## 📡 6. CUPS SENKRONIZASYON VE `cups_queue_name` OTOMASYONU

> **Son Güncelleme:** 09.06.2026
> **Amaç:** Tabletten/mobilden çıktı alırken yazıcı listesinin anında açılması için CUPS kuyruk isimlerini veritabanına önbellekleme (cache).

### Sorun
Mobilden çıktı alınırken her seferinde CUPS sunucusuna (`http://192.168.X.X:49631`) sorgu atılarak yazıcı isimleri çekiliyordu. Bu işlem 1-2 saniye gecikmeye neden oluyordu.

### Çözüm: `cups_queue_name` Sütunu
`printers` tablosuna `cups_queue_name NVARCHAR(255)` sütunu eklendi. CUPS senkronizasyonu yapıldığında bu sütun otomatik dolar. Mobil yazdırma sırasında CUPS'a tekrar sorgu atılmaz, veritabanındaki değer direkt kullanılır.

### Veritabanı Migrasyonu (database_sql.py → init_db)
```python
# --- YAZICILAR CUPS QUEUE NAME MIGRATION ---
try:
    cursor.execute("SELECT cups_queue_name FROM printers WHERE 1=0")
except Exception:
    print("[*] 'printers' tablosuna 'cups_queue_name' sutunu ekleniyor...")
    cursor.execute("ALTER TABLE printers ADD cups_queue_name NVARCHAR(255)")
```

### Senkronizasyon Kodu (printers_printers.py → /query_cups)
```python
@printers_printers_bp.route('/query_cups', methods=['POST'])
@require_editor
def query_cups():
    """
    CUPS sunucusundaki TÜM yazıcıları sayfa sayfa tarar.
    Her yazıcıyı DB'deki karşılığıyla eşleştirir ve:
      1. cups_queue_name sütununa CUPS kuyruk adını yazar
      2. location_code farklıysa günceller
    
    Eşleştirme Önceliği:
      1. IP adresi (Connection URI'den çıkarılır)
      2. Yazıcı numarası (PR-038 → 38)
      3. Alt-string eşleşmesi (fallback)
    """
    import requests
    from bs4 import BeautifulSoup
    import re

    conn = get_db_connection()
    cursor = conn.cursor()

    # DB'deki tüm aktif yazıcıları çek
    cursor.execute("SELECT id, pr_no, location_code, ip FROM printers WHERE is_deleted = 0")
    db_printers = cursor.fetchall()

    # Hızlı lookup haritaları oluştur
    db_printers_ip_map = {}
    db_printers_num_map = {}
    for db_id, pr_no, db_loc, db_ip in db_printers:
        clean_ip = str(db_ip).strip() if db_ip else None
        if clean_ip:
            db_printers_ip_map[clean_ip] = (db_id, pr_no, db_loc, db_ip)
        num = extract_printer_number(pr_no)
        if num is not None:
            db_printers_num_map[num] = (db_id, pr_no, db_loc, db_ip)

    updated_count = 0
    first = 0
    last_page_first_printer = None
    cups_config = get_integration_config('CUPS') or {}
    cups_base_url = cups_config.get('base_url', 'http://192.168.X.X:49631').rstrip('/')

    # TÜM sayfaları tara (100'er yazıcı/sayfa)
    while True:
        cups_url = f"{cups_base_url}/printers/?FIRST={first}"
        response = requests.get(cups_url, timeout=10, verify=False)

        if response.status_code != 200:
            if first == 0:
                return jsonify({"error": f"CUPS Hatasi: {response.status_code}"}), 500
            break

        soup = BeautifulSoup(response.text, 'html.parser')
        rows = soup.find_all('tr')
        parsed_on_this_page = 0
        current_page_first_printer = None

        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 3:
                cups_name = cols[0].get_text(strip=True)  # Örn: "PR-038"
                hedef_mahal = cols[2].get_text(strip=True).replace("-", ".")

                if not cups_name: continue
                if current_page_first_printer is None:
                    current_page_first_printer = cups_name
                parsed_on_this_page += 1

                # Detay sayfasından IP çıkar
                printer_ip = None
                detail_resp = requests.get(f"{cups_base_url}/printers/{cups_name}", timeout=5, verify=False)
                if detail_resp.status_code == 200:
                    uri_match = re.search(r"(?:socket|ipp|lpd|http)://([^:/'\"\\s]+)", detail_resp.text)
                    if uri_match:
                        potential_ip = uri_match.group(1)
                        if re.match(r'^(?:[0-9]{1,3}\\.){3}[0-9]{1,3}$', potential_ip):
                            printer_ip = potential_ip

                # Eşleştirme: IP → Numara → Substring
                matched_printer = None
                if printer_ip and printer_ip in db_printers_ip_map:
                    matched_printer = db_printers_ip_map[printer_ip]
                if not matched_printer:
                    cups_num = extract_printer_number(cups_name)
                    if cups_num is not None and cups_num in db_printers_num_map:
                        matched_printer = db_printers_num_map[cups_num]

                if matched_printer:
                    db_id = matched_printer[0]
                    # ★ KRİTİK SATIR: cups_queue_name'i kaydet
                    cursor.execute("UPDATE printers SET cups_queue_name = ? WHERE id = ?", (cups_name, db_id))
                    updated_count += 1

        # Sayfa sonu kontrolü
        if parsed_on_this_page == 0 or current_page_first_printer == last_page_first_printer:
            break
        last_page_first_printer = current_page_first_printer
        first += 100  # Sonraki sayfa

    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": f"Toplam {updated_count} yazici guncellendi."})
```

### CUPS Kuyruk Adı Örnekleri
| Yazıcı No | IP | CUPS Kuyruk Adı (`cups_queue_name`) |
|---|---|---|
| PR-001 | 192.168.40.1 | `PR-001` |
| PR-038 | 192.168.40.38 | `PR-038` |

### Kullanım
1. Arayüzden **Yazıcılar → CUPS Senkronize Et** butonuna basılır
2. Sistem tüm CUPS sayfalarını tarar ve eşleştirmeleri yapar
3. Her yazıcının `cups_queue_name` sütunu güncellenir
4. Mobilden çıktı alırken bu sütun okunur, CUPS'a tekrar sorgu atılmaz

---

## 📂 7. GEREKLİ İNDİRMELER / BAT UYGULAMALARI (Klasör Yolu Değişikliği)

> **Son Güncelleme:** 10.06.2026
> **Amaç:** Frontend'de "Gerekli İndirmeler" ve "Bat Uygulamaları" olarak sunulan sabit dosyaların (KMS lisans, Kamu Admin vb.) kod dizinindeki yerinin standartlaştırılması.

### Sorun
Sistemin eski halinde dosyalar projenin kök dizinindeki `bat_uygulama` veya `tools/bat_uygulama` içerisinde dağınık olarak bulunuyordu.

### Çözüm
1. Tüm indirilebilir ve sabit dosyalar (`.bat`, `.rar`, `.deb` vb.) `static/bat_uygulama` klasörü altında toplandı. Bu sayede Flask'in statik dosya yönetimi mimarisine uygun hale getirildi.
2. API uçlarındaki dizin yolları bu klasörü işaret edecek şekilde güncellendi.

### Kod Değişikliği (document_service.py & bat_manager.py)
```python
BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

# Önceden:
# DL_DIR = os.path.join(BASE_DIR, "bat_uygulama")

# Yeni Standart Yol:
DL_DIR = os.path.join(BASE_DIR, "static", "bat_uygulama")
BAT_DIR = os.path.join(BASE_DIR, "static", "bat_uygulama")
```

### Kullanım
* Sisteme yeni bir uygulama ekleneceğinde dosya `static/bat_uygulama` klasörüne atılır.
* Arayüz (/downloads/list API'si) dosyaları buradan okuyup otomatik listeler.

---

## 🖨️ 8. YAZICI SAYAÇ RAPORLAMA VE PDF AKTARIM ALTYAPISI

> **Son Güncelleme:** 11.06.2026
> **Amaç:** Ağdaki tüm yazıcıların MIB `prtMarkerLifeCount` sayacını SNMP üzerinden çekerek periyodik rapor sunma, fark hesaplama, farka göre sıralama ve PDF olarak indirme.

### Backend Sayaç Ayrıştırma ve Tarih Formatı Güvenliği (printer_pages_service.py)
1. Yazıcıların çevrimdışı olması gibi durumlarda veritabanında `page_count` alanının `NULL` dönmesi durumunda `int(None)` hatası ile servis çökmesini önlemek için korumalı dönüşüm uygulandı:
```python
try:
    s_count = int(first_record.get('page_count') or 0)
except (ValueError, TypeError):
    s_count = 0
```
2. Rapor çıktısındaki başlangıç ve bitiş tarihleri (`start_date` ve `end_date`), saat/dakika bilgisi olmadan sadece gün bazında temiz ve Türkçe uyumlu tarih formatı (`DD.MM.YYYY`) olarak çıktı verecek şekilde backend tarafında otomatik temizlenip formatlanmaktadır:
```python
# Sadece tarih formatı (DD.MM.YYYY) döndürülür
t1_fmt = format_date_only(t1) 
```

### Rapor Sıralama ve Ön Yüz Zarf Yönetimi (UI_controller.js)
1. `apiRequest` yapısının yanıt zarfını (`success: true, data: [...]`) otomatik ayrıştırma özelliğine uyum sağlandı.
2. Çıktı sayacına göre farkların **küçükten büyüğe (ascending)** sıralanması sağlandı:
```javascript
reportData.sort((a, b) => {
    const diffA = a.difference !== undefined ? Number(a.difference) : 0;
    const diffB = b.difference !== undefined ? Number(b.difference) : 0;
    return diffA - diffB;
});
```

### PDF İndirme Altyapısı (UI_controller.js)
İstemci tarafında `jsPDF` ve `jspdf-autotable` kütüphanelerini kullanarak Türkçe karakter uyumlu dikey A4 PDF rapor çıktısı alma:
```javascript
const { jsPDF } = window.jspdf;
const doc = new jsPDF('p', 'mm', 'a4');
// ... Logo ve Başlık ...
doc.autoTable({
    startY: 32,
    head: [[ 'Yazici No', 'Seri No', 'Mahal', 'Baslangic Tarihi', 'Baslangic Sayac', 'Bitis Tarihi', 'Bitis Sayac', 'Fark (Cikti)' ]],
    body: rows,
    theme: 'striped',
    headStyles: { fillColor: [239, 68, 110] },
    // ...
});
doc.save(`Yazici_Sayac_Raporu_${start}_${end}.pdf`);
```

---

## 🔌 9. BİM ENTEGRASYONU API PROTOKOLLERİ (Login, Add, Remove)

Sistem, yazıcı ekleme ve kaldırma işlemleri için Ornek Sağlık Hizmetleri BİM sunucusundaki `Handler.ashx` endpoint'i ile haberleşir.

### A. Giriş (Login) Aşaması
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
* **Yanıt**: Başarılı durumda doğrudan session token string (örn. `ipa_session_id`) döndürülür.

### B. Yazıcı Ekleme (AddPrinter)
Bilgisayara yeni bir ağ yazıcısı tanımlamak için gönderilen istek:
* **URL**: `http://bim.ornek-kurum.com/Handler.ashx`
* **Yöntem**: POST
* **İstek Başlıkları (Headers)**:
  * `IPASession`: `<Login aşamasında alınan session_id>`
* **İstek Gövdesi (Form Data / URL Encoded)**:
  ```json
  {
    "Functions": "AddPrinter",
    "UserName": "<bim_user>",
    "IPAddress": "<hedef_cihaz_ip>",
    "PrinterName": "PR-001/01"  // Tanımlanacak yazıcı kodu ve kuyruğu (Örn: PR-001/01)
  }
  ```

### C. Yazıcı Kaldırma (RemovePrinter)
Bilgisayardan tanımlı bir ağ yazıcısını silmek için gönderilen istek:
* **URL**: `http://bim.ornek-kurum.com/Handler.ashx`
* **Yöntem**: POST
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

## 🤖 10. BACKEND TOPLU İŞLEM (BATCH ACTION) VE İKAME YAZICI ROTASI

Uygulama sunucusunun kendi API'si üzerinden toplu eylemleri tetiklemek için kullanılan rota ve payload yapısı.

* **Rota**: `/printers/printers/batch_action` (veya `/printers/batch_action`)
* **Yöntem**: POST
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

### İkame Yazıcı Değişim Otomasyonu (Automatic Printer Swap) Frontend Akışı
Bir yazıcı arızalandığında o yazıcıya bağlı olan tüm bilgisayarları yeni (ikame) yazıcıya geçirmek için tetiklenen akış (`frontend/UI_controller.js -> handleAutomaticPrinterSwap`):

1. **Hedef Tespiti**: Veritabanında `bagli_yazicilar` kolonunda eski yazıcı kodu geçen bilgisayarlar filtrelenir.
2. **Kaldırma İsteği (Remove Old)**: Eski yazıcıyı kaldırmak için yukarıdaki batch rotasına `action: "remove"` ve `bim_function: "RemovePrinter"` olarak payload atılır.
3. **Ekleme İsteği (Add Substitute)**: Yeni ikame yazıcıyı kurmak için aynı rotaya `/01` ekiyle (Örn: `PR-002/01`) `action: "add"` payload'ı gönderilir.

---

## 📄 11. TUTANAK TASARIMLARI VE PDF/EXCEL DÖNÜŞTÜRÜCÜSÜ (document_service.py)

> **Açıklama:** Sistemin Zimmet, VPN, Hasar Tespit ve İzin İstek tutanaklarını ürettiği merkez. Zimmet ve VPN tamamen `fpdf` kütüphanesi ile doğrudan kodlanarak çizilirken, Hasar Tespit ve İzin İstek formları ise Excel (`.xlsx`) şablonlarından okunup veri yazıldıktan sonra PDF'e dönüştürülmektedir.

### A. FPDF ile Dinamik Kod Çizimi (Zimmet ve VPN)
Bu yöntemde tasarım tamamen kodla piksel piksel işlenir.

```python
class TutanakPDF(FPDF):
    def __init__(self, t_type, **kwargs):
        super().__init__(**kwargs)
        self.t_type = t_type
        # Font Yükleme (Türkçe Karakter Desteği İçin Arial)
        font_dir = os.path.join(os.path.dirname(__file__), "..", "static", "fonts")
        self.add_font("ArialTR", "", os.path.join(font_dir, "arial.ttf"), uni=True)
        self.add_font("ArialTR", "B", os.path.join(font_dir, "arialbd.ttf"), uni=True)

    def header(self):
        if self.t_type == "VPN": return
        LOGO_DIR = os.path.join(os.path.dirname(__file__), "..", "static", "logo")
        t_logo = "ht_left.png" if self.t_type == "HT" else "zimmet_left.png"
        self.image(os.path.join(LOGO_DIR, t_logo), 0, 0, 210)
        self.ln(30)

    def footer(self):
        # ... Alt logo ...
        pass

# VPN Tutanağı Çizimi (Dinamik Koordinatlarla Tablo/Kutu Tasarımı)
# Tablo hücreleri ve check-box'lar tamamen rect(), line(), ve cell() kullanılarak oluşturulur.
pdf = TutanakPDF("VPN")
pdf.add_page()
pdf.set_line_width(0.5)
pdf.rect(10, 10, 190, 30) # Ana Çerçeve
pdf.line(55, 10, 55, 40)  # Sütun Çizgisi
# VPN Checkbox'ları:
os_choice = items.get("os", "")
pdf.cell(47.5, 8, f" Windows   {'[X]' if os_choice == 'Windows' else '[  ]'}", border=1)
pdf.cell(47.5, 8, f" Linux        {'[X]' if os_choice == 'Linux' else '[  ]'}", border=1)
```

### B. Excel Şablonu Üzerinden PDF Üretimi (Hasar Tespit & İzin)
Bu yöntem mevcut form tasarımlarını (Excel) bozmamak için kullanılır. Excel açılır, hücrelere veri girilir, varsa olay yeri fotoğrafı eklenir ve PDF'e export edilir.

```python
def generate_ht_from_excel(items, photo_path=None):
    template_path = os.path.join(os.path.dirname(__file__), "..", "database", "sablonlar", "hasar_tespit.xlsx")
    shutil.copy2(template_path, temp_excel)
    
    wb = openpyxl.load_workbook(temp_excel)
    ws = wb.active
    
    # 1. Metin ve Seri No alanlarının doldurulması
    ws["D32"] = str(items.get("seri", "-"))
    ws["B27"] = str(items.get("desc", items.get("hasar_aciklama", "-")))
    
    # 2. Checkbox'ların işaretlenmesi (X)
    equipment_cells = {
        "Bilgisayar": "A12", "Klavye": "F12", "Monitör": "A14", 
        "Yazıcı": "A16", "Barkod Okuyucu": "A20", "Switch": "F22"
    }
    for eq in items.get("equipment", []):
        if eq in equipment_cells:
            ws[equipment_cells[eq]] = "X"
            
    # 3. Fotoğrafın Excel'e dinamik gömülmesi (Eğer varsa)
    if photo_path and os.path.exists(photo_path):
        from openpyxl.drawing.image import Image as OpenpyxlImage
        img = OpenpyxlImage(photo_path)
        img.width = 400
        img.height = 250
        ws.add_image(img, "B36")

    wb.save(temp_excel)
    
    # 4. win32com Kullanarak Excel'in PDF Olarak Kaydedilmesi (Gizli İşlem)
    excel = win32com.client.Dispatch("Excel.Application")
    excel.Visible = False
    wb_com = excel.Workbooks.Open(os.path.abspath(temp_excel))
    wb_com.ExportAsFixedFormat(0, os.path.abspath(temp_pdf))
    wb_com.Close(False)
    excel.Quit()
    
    return temp_pdf
```

---

## ?? 7. YAZICI ARAY�Z�NDEN DURUM VE TONER �EKME (WEB SCRAPING)

Yaz�c�lar�n web aray�z�ne (genellikle 80 veya 443 portu) do�rudan istek at�larak (BeautifulSoup ile) anl�k durum (Status) ve Toner bilgisinin �ekilmesi i�lemi.

`python
import requests
from bs4 import BeautifulSoup
import re

def get_printer_live_status(ip_address):
    status_info = {
        "status": "�evrimd���",
        "toner_level": "Bilinmiyor"
    }
    try:
        url = f"http://{ip_address}/general/status.html"
        r = requests.get(url, timeout=5)
        r.encoding = r.apparent_encoding
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # 1. Toner Seviyesi (Regex ve Class Bazl� Yakalama)
        # �rn: <img class="tonerremain" height="50" width="56" />
        toner_img = soup.find('img', class_=re.compile(r"tonerremain", re.I))
        if toner_img:
            w = toner_img.get('width')
            if w and w.isdigit():
                val = int(w)
                if val <= 100: status_info["toner_level"] = f"%{val}"
                elif val <= 160: status_info["toner_level"] = f"%{int((val/160)*100)}"
                elif val <= 56: status_info["toner_level"] = f"%{int((val/56)*100)}"
                
        # 2. Alternatif Toner Yakalama (Text Bazl�)
        if status_info["toner_level"] == "Bilinmiyor":
            toner_text = soup.find(text=re.compile(r"Toner.*?(\d+%)", re.I))
            if toner_text:
                match = re.search(r"(\d+%)", toner_text)
                if match: status_info["toner_level"] = match.group(1)
                
        status_info["status"] = "�evrimi�i"
        return status_info
    except Exception:
        return status_info
`

---

## ?? 8. G�VENL� IP S�STEM� (TRUSTED IPS)

Kullan�c�lar�n kendi bilgisayarlar�ndan / cihazlar�ndan yapt�klar� giri�lerin otomatik olarak sonland�r�lmas�n� engelleyen, oturum s�resini **1 y�l** (8760 saat) olarak ayarlayan sistem.

1. **Kullan�c� Modeli**: users tablosuna 	rusted_ips (NVARCHAR) alan� eklendi.
2. **Giri� (Login) Kontrol�**: Kullan�c� giri� yapt���nda equest.remote_addr al�n�r. E�er kullan�c�n�n 	rusted_ips listesinde bu IP varsa, olu�turulan JWT token ve Refresh Token s�resi 8760 saat olarak ayarlan�r.
3. **Frontend Entegrasyonu**: Profil ayarlar� (Profile Settings) �zerinden kullan�c� kendi IP'sini virg�lle ay�rarak (�rn: 192.168.1.50, 10.0.0.15) kaydedebilir.
4. **Aktif Oturumlar Y�netimi**: Kullan�c�, /api/users/sessions rotas� �zerinden kendi hesaplar�na ba�l� a��k oturumlar� (Refresh tokenlar�) listeleyebilir ve dilerse evoked = 1 yaparak di�er cihazlardan ��k�� yapabilir.

---

## ?? 9. HASAR TESP�T TUTANA�I (FPDF ENTEGRASYONU)

Daha �nce Excel �ablonlar� �zerinden olu�turulan Hasar Tespit tutanaklar�n�n FPDF k�t�phanesi ile tamamen kod tabanl� olarak �izdirilmesi i�lemidir.
Bu sayede Excel'in getirdi�i stil kaymalar� ve PDF'e d�n���m hatalar� ortadan kald�r�lm��t�r.

- Resim/Foto�raf ekleme pdf.image() ile dinamik konumland�r�l�r.
- Checkbox'lar (Hasar G�ren Cihaz T�r� vb.) pdf.rect() ve pdf.text() kullan�larak manuel olarak �izilir.
- Oturum a�an kullan�c�n�n ad� (Birim Sorumlusu vb.) otomatik olarak frontend'den (app.state.activeUser.display_name) g�nderilip items.get("birim_sorumlusu") ile PDF'e bas�l�r.


## --- EKLENEN ÖZEL KODLAR (TUTANAK TASARIMLARI VE GÜVENLİ IP) ---

### TUTANAK PDF ÜRETİM KODLARI (document_service.py)
```python
from flask import Blueprint, jsonify, send_from_directory, request, send_file, after_this_request
import os
import datetime
import shutil
import json
import openpyxl
import win32com.client
from fpdf import FPDF

document_service_bp = Blueprint('document_service', __name__)

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
DL_DIR = os.path.join(BASE_DIR, "tools", "bat_uygulama")
TEMP_DIR = os.path.join(BASE_DIR, "uploads", "temp")

@document_service_bp.route('/list', methods=['GET'])
def list_files():
    try:
        if not os.path.exists(DL_DIR):
            os.makedirs(DL_DIR, exist_ok=True)
            
        files = []
        for f in os.listdir(DL_DIR):
            f_path = os.path.join(DL_DIR, f)
            if os.path.isfile(f_path):
                stats = os.stat(f_path)
                files.append({
                    "name": f,
                    "size": f"{round(stats.st_size / 1024, 2)} KB",
                    "date": datetime.datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M")
                })
        return jsonify({"success": True, "files": files})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@document_service_bp.route('/get/<filename>', methods=['GET'])
def get_file(filename):
    try:
        safe_filename = os.path.basename(filename)
        return send_from_directory(DL_DIR, safe_filename, as_attachment=True)
    except Exception as e:
        return jsonify({"success": False, "error": "Dosya bulunamadi"}), 404


# --- PDF GENERATION LOGIC ---

class TutanakPDF(FPDF):
    def __init__(self, t_type, **kwargs):
        super().__init__(**kwargs)
        self.t_type = t_type
        font_dir = os.path.join(os.path.dirname(__file__), "..", "static", "fonts")
        
        if os.path.exists(os.path.join(font_dir, "arial.ttf")):
            self.add_font("ArialTR", "", os.path.join(font_dir, "arial.ttf"), uni=True)
            self.add_font("ArialTR", "B", os.path.join(font_dir, "arialbd.ttf"), uni=True)
        else:
            self.add_font("ArialTR", "", "c:/windows/fonts/arial.ttf", uni=True)
            self.add_font("ArialTR", "B", "c:/windows/fonts/arialbd.ttf", uni=True)
        
    def header(self):
        if self.t_type == "VPN":
            return
        LOGO_DIR = os.path.join(os.path.dirname(__file__), "..", "static", "logo")
        t_logo = "ht_left.png" if self.t_type == "HT" else "zimmet_left.png"
        t_path = os.path.join(LOGO_DIR, t_logo)
        if os.path.exists(t_path):
            self.image(t_path, 0, 0, 210)
        self.set_font("ArialTR", "B", 16)
        self.ln(25)
        self.ln(5)

    def footer(self):
        if self.t_type == "VPN":
            return
        LOGO_DIR = os.path.join(os.path.dirname(__file__), "..", "static", "logo")
        b_logo = "ht_right.png" if self.t_type == "HT" else "zimmet_right.png"
        b_path = os.path.join(LOGO_DIR, b_logo)
        if os.path.exists(b_path):
            self.image(b_path, 0, 265, 210)

def generate_pdf_direct(t_type, items, photo_path=None):
    pdf = TutanakPDF(t_type)
    pdf.add_page()
    now_str = datetime.datetime.now().strftime("%d.%m.%Y")
    
    if t_type == "ZIMMET":
        pdf.set_y(35)
        pdf.set_font("ArialTR", "", 10)
        pdf.cell(0, 10, f"TARİH: {now_str}", ln=True, align="R")
        pdf.set_font("ArialTR", "B", 14)
        pdf.cell(0, 15, "ZİMMET TUTANAĞI", ln=True, align="C")
        pdf.ln(5)
        
        pdf.set_font("ArialTR", "", 10)
        staff = items.get("staff", "......")
        text = f"Aşağıda marka, model ve seri numaraları belirtilmiş cihazlar KEYDATA firmasından {staff} isimli personele / firmaya elden teslim edilmiştir."
        pdf.multi_cell(0, 6, text, align="C")
        pdf.ln(10)
        
        pdf.set_fill_color(245, 245, 245)
        pdf.set_font("ArialTR", "B", 10)
        pdf.set_x(10)
        pdf.cell(15, 8, "ADET", border=1, fill=True, align="C")
        pdf.cell(35, 8, "ÜRÜN TİPİ", border=1, fill=True, align="C")
        pdf.cell(40, 8, "MARKA", border=1, fill=True, align="C")
        pdf.cell(50, 8, "MODEL", border=1, fill=True, align="C")
        pdf.cell(50, 8, "SERİ NUMARASI", border=1, fill=True, align="C", ln=True)
        
        pdf.set_font("ArialTR", "", 10)
        for d in items.get("devices", []):
            pdf.set_x(10)
            pdf.cell(15, 8, str(d.get("adet", "1")), border=1, align="C")
            pdf.cell(35, 8, str(d.get("tip", "-")), border=1, align="C")
            pdf.cell(40, 8, str(d.get("marka", "-")), border=1, align="C")
            pdf.cell(50, 8, str(d.get("model", "-")), border=1, align="C")
            pdf.cell(50, 8, str(d.get("seri", "-")), border=1, align="C", ln=True)
            
        pdf.ln(10)
        pdf.set_x(10)
        pdf.cell(0, 6, "Durumu belirtilen iş bu tutanak tebellüğ yerine geçmesi hasebiyle imza altına alınmıştır.", ln=True)
        
        if pdf.get_y() > 240:
            pdf.add_page()
            
        pdf.ln(30)
        pdf.cell(95, 6, "Teslim Eden", align="C")
        pdf.cell(95, 6, "Teslim Alan", align="C", ln=True)
        pdf.cell(95, 6, "Ad-Soyad/Unvan", align="C")
        pdf.cell(95, 6, "Ad-Soyad/Unvan", align="C", ln=True)
        pdf.cell(95, 6, "İmza", align="C")
        pdf.cell(95, 6, "İmza", align="C", ln=True)
        pdf.ln(15)
        pdf.set_font("ArialTR", "B", 10)
        pdf.cell(95, 6, str(items.get("veren", "-")), align="C")
        pdf.cell(95, 6, str(items.get("alan", "-")), align="C", ln=True)
        pdf.set_font("ArialTR", "", 9)
        veren_unvan = items.get("veren_unvan", "Bilgi İşlem ve HBYS Uzm. Yrd.")
        alan_unvan = items.get("alan_unvan", "")
        pdf.cell(95, 6, veren_unvan, align="C")
        pdf.cell(95, 6, alan_unvan, align="C", ln=True)

    elif t_type == "SLA":
        pdf.set_auto_page_break(False)
        pdf.set_y(35)
        pdf.set_font("ArialTR", "B", 14)
        pdf.cell(0, 15, "TUTANAKTIR", ln=True, align="C")
        pdf.ln(10)
        
        pdf.set_font("ArialTR", "", 11)
        ticket = items.get("ticket", ".......")
        text1 = f"{ticket} no'lu SLA talebi sehven kapatılmıştır, açıklaması şu şekildedir;"
        pdf.multi_cell(0, 8, text1, align="L")
        pdf.ln(5)
        
        pdf.set_font("ArialTR", "B", 11)
        aciklama = items.get("aciklama", "Proje kapsamında yeteri sayıda bilgisayar ve ekipmanları bulunduğundan yeni bilgisayar, ekipman kurulumu yapılamayacaktır.")
        pdf.multi_cell(0, 8, aciklama, align="L")
        pdf.ln(5)
        
        pdf.set_font("ArialTR", "", 11)
        text3 = "İş bu tutanak bu açıklamalara istinaden tarafımızca imza altına toplanmıştır, gerekli işlemlerin yapılması konusunda destekleriniz rica olunur."
        pdf.multi_cell(0, 8, text3, align="L")
        
        pdf.ln(30)
        pdf.set_font("ArialTR", "B", 10)
        kisi1_ad = items.get("kisi1_ad", "Murat COŞKUN")
        kisi2_ad = items.get("kisi2_ad", "Halil DUMAN")
        kisi3_ad = items.get("kisi3_ad", "Muhammed Vefa ARABACI")
        pdf.cell(65, 6, kisi1_ad, align="L")
        pdf.cell(65, 6, kisi2_ad, align="C")
        pdf.cell(65, 6, kisi3_ad, align="R", ln=True)
        
        pdf.set_font("ArialTR", "", 9)
        kisi1_unvan = items.get("kisi1_unvan", "HBYS Yöneticisi")
        kisi2_unvan = items.get("kisi2_unvan", "HBYS Ve İYM Birim Sorumlusu")
        kisi3_unvan = items.get("kisi3_unvan", "Bilgi İşlem ve HBYS Uzm. Yrd.")
        pdf.cell(65, 6, kisi1_unvan, align="L")
        pdf.cell(65, 6, kisi2_unvan, align="C")
        pdf.cell(65, 6, kisi3_unvan, align="R", ln=True)

    elif t_type == "VPN":
        pdf.set_auto_page_break(False)
        # 1. HEADER
        pdf.set_line_width(0.5)
        pdf.rect(10, 10, 190, 30)
        pdf.line(55, 10, 55, 40)
        pdf.line(10, 35, 200, 35)
        pdf.line(55, 35, 55, 40)
        pdf.line(100, 35, 100, 40)
        pdf.line(140, 35, 140, 40)
        pdf.line(175, 35, 175, 40)
        
        logo_path = os.path.join(os.path.dirname(__file__), "..", "static", "logo", "ht_right.png")
        if os.path.exists(logo_path):
            pdf.image(logo_path, 25, 11, 14)
            
        pdf.set_font("ArialTR", "B", 7)
        pdf.set_xy(10, 26)
        pdf.cell(45, 3, "T.C. SAĞLIK BAKANLIĞI", align="C")
        pdf.set_xy(10, 29)
        pdf.set_font("ArialTR", "", 6)
        pdf.cell(45, 3, "KOCAELİ İL SAĞLIK MÜDÜRLÜĞÜ", align="C")
        pdf.set_xy(10, 32)
        pdf.cell(45, 3, "KOCAELİ ŞEHİR HASTANESİ", align="C")
        
        pdf.set_xy(55, 15)
        pdf.set_font("ArialTR", "B", 12)
        pdf.cell(145, 10, "KOCAELİ ŞEHİR HASTANESİ", align="C")
        pdf.set_xy(55, 22)
        pdf.cell(145, 10, "VPN BAĞLANTI TALEP FORMU", align="C")
        
        pdf.set_font("ArialTR", "B", 7)
        pdf.set_xy(10, 35)
        pdf.cell(45, 5, "DOKÜMAN KODU:BY.FR.12", align="C")
        pdf.set_xy(55, 35)
        pdf.cell(45, 5, "YAY.TAR.:01.11.2022", align="C")
        pdf.set_xy(100, 35)
        pdf.cell(40, 5, "REVİZYON TARİHİ: -", align="C")
        pdf.set_xy(140, 35)
        pdf.cell(35, 5, "REVİZYON NO: 00", align="C")
        pdf.set_xy(175, 35)
        pdf.cell(25, 5, "SAYFA 1 / 1", align="C")
        
        pdf.set_line_width(0.2)
        pdf.ln(10)
        
        # 2. Text Paragraph
        pdf.set_font("ArialTR", "", 11)
        text = (
            "Kampüs dışından kampüs ağına erişim için VPN (özel sanal ağ) hesabının açılmasını talep ediyorum. "
            "Açılacak VPN hesabı ile aşağıda belirtilen LAN (yerel ağ) bölgesindeki bilgisayara belirttiğim "
            "portlardan erişmek istiyorum. VPN hesabı ile erişim sağladığımda doğabilecek tüm sorumluluğun "
            "bende olduğunu, bağlantı istediğim sistemler dışında bir yere bağlanmayacağıma, kampüs ağ "
            "güvenliğine zarar vermeyeceğimi taahhüt ediyorum. Belirttiğim şartları sağlamadığım takdirde "
            "KEYDATA Bilişim Teknolojileri yetkililerinin bu hizmeti durdurabileceğini, inceleme ve yönetme "
            "konusunda yetkili olduğunu kabul ediyorum."
        )
        pdf.set_xy(10, 45)
        pdf.multi_cell(190, 5, text, align="J")
        pdf.ln(3)
        
        # 3. Kullanıcı Bilgileri
        pdf.set_fill_color(200, 200, 200)
        pdf.set_font("ArialTR", "B", 11)
        pdf.set_x(10)
        pdf.cell(190, 7, " Kullanıcı Bilgileri", border=1, fill=True, ln=True)
        
        pdf.set_font("ArialTR", "", 10)
        fields = [
            ("Adı ve Soyadı", items.get("adsoyad", "")),
            ("Firma Adı", items.get("firma", "")),
            ("Resmi Yazı Bilgisi", items.get("resmiyazi", "")),
            ("Görevi", items.get("gorevi", "")),
            ("HBYS Kul. Adı", items.get("hbys", "")),
            ("Cep Telefonu", items.get("telefon", "")),
            ("E-Posta", items.get("eposta", ""))
        ]
        
        for label, val in fields:
            pdf.set_x(10)
            pdf.cell(50, 7, f" {label}", border=1)
            pdf.cell(140, 7, f" {val}", border=1, ln=True)
            
        pdf.ln(3)
        
        # 4. OS Selection
        pdf.set_font("ArialTR", "B", 10)
        pdf.set_x(10)
        pdf.cell(190, 7, " VPN bağlantısını hangi işletim sisteminden yapmak istiyorsunuz?", border=1, fill=True, ln=True)
        
        pdf.set_font("ArialTR", "", 10)
        pdf.set_x(10)
        os_choice = items.get("os", "")
        pdf.cell(47.5, 7, f" Windows   {'[X]' if os_choice == 'Windows' else '[  ]'}", border=1)
        pdf.cell(47.5, 7, f" Linux        {'[X]' if os_choice == 'Linux' else '[  ]'}", border=1)
        pdf.cell(47.5, 7, f" Android     {'[X]' if os_choice == 'Android' else '[  ]'}", border=1)
        pdf.cell(47.5, 7, f" Mac IOS    {'[X]' if os_choice == 'Mac IOS' else '[  ]'}", border=1, ln=True)
        
        pdf.ln(3)
        
        # 5. VPN End Date
        pdf.set_x(10)
        pdf.set_font("ArialTR", "", 10)
        pdf.cell(190, 7, f"Vpn hesabının kapatılacağı tarih (sınırlı bir süre için ise) : .....{items.get('bitis', '')}.....", ln=True)
        pdf.ln(2)
        
        # 6. LAN Bilgileri
        pdf.set_x(10)
        pdf.set_font("ArialTR", "B", 10)
        pdf.cell(190, 6, "ERİŞİLMEK İSTENEN LAN (Yerel Ağ) BİLGİLERİ :", ln=True)
        
        pdf.set_font("ArialTR", "", 10)
        pdf.set_x(20)
        pdf.cell(180, 6, f"Network / Subnet (Var ise) : {items.get('network', '')}", ln=True)
        pdf.set_x(20)
        pdf.cell(180, 6, f"IP Adresi : {items.get('ip', '')}", ln=True)
        pdf.set_x(20)
        pdf.cell(180, 6, f"MAC (Ethernet) Adresi : {items.get('mac', '')}", ln=True)
        
        pdf.ln(5)
        
        # 7. Signatures
        pdf.set_x(10)
        pdf.cell(95, 6, "Yetkiyi İsteyen Adı Soyadı İmza (Kaşe)", align="C")
        pdf.cell(95, 6, "Hizmet Sağlayıcı Bilişim Teknolojileri", align="C", ln=True)
        pdf.set_x(10)
        pdf.cell(95, 6, "", align="C")
        pdf.cell(95, 6, "(Kaşe) İmza", align="C", ln=True)
        pdf.ln(8)
        pdf.set_x(10)
        pdf.cell(95, 6, "Tarih : ..../..../.......", align="C")
        pdf.cell(95, 6, "Tarih : ..../..../.......", align="C", ln=True)
        
        # 8. Footer table AT THE VERY BOTTOM OF THE PAGE
        pdf.set_y(-40)  # Pin to bottom
        pdf.set_font("ArialTR", "B", 10)
        pdf.set_line_width(0.5)
        
        pdf.set_x(20)
        pdf.cell(56.6, 8, "HAZIRLAYAN", border=1, align="C")
        pdf.cell(56.6, 8, "KONTROL EDEN", border=1, align="C")
        pdf.cell(56.6, 8, "ONAYLAYAN", border=1, align="C", ln=True)
        
        pdf.set_x(20)
        pdf.cell(56.6, 12, "", border=1, align="C")
        pdf.cell(56.6, 12, "KALİTE DİREKTÖRÜ", border=1, align="C")
        pdf.cell(56.6, 12, "BAŞHEKİM", border=1, align="C", ln=True)

    elif t_type == "HT":
        pdf.set_y(35)
        pdf.set_font("ArialTR", "B", 12)
        pdf.cell(0, 6, "KOCAELİ ŞEHİR HASTANESİ", ln=True, align="C")
        pdf.cell(0, 6, "BİLGİ İŞLEM HASAR TESPİT TUTANAĞI", ln=True, align="C")
        
        pdf.set_font("ArialTR", "", 10)
        pdf.set_y(50)
        now_str = datetime.datetime.now().strftime("%d.%m.%Y")
        pdf.cell(0, 6, f"Tarih : {now_str}", ln=True, align="R")
        sla = items.get("sla", "")
        if sla:
            pdf.cell(0, 6, f"SLA Numarası : {sla}", ln=True, align="R")
        
        pdf.ln(5)
        
        # 1. CİHAZ BİLGİLERİ
        pdf.set_font("ArialTR", "B", 10)
        pdf.cell(0, 6, "1. CİHAZ BİLGİLERİ", ln=True)
        pdf.set_font("ArialTR", "", 10)
        pdf.rect(10, pdf.get_y(), 190, 10)
        pdf.set_xy(12, pdf.get_y() + 2)
        model_str = items.get("model", "")
        seri_str = items.get("serial", "")
        pdf.cell(95, 6, f"Ürün Modeli: {model_str}")
        pdf.cell(90, 6, f"Seri Numarası: {seri_str}", ln=True)
        pdf.ln(4)
        
        # 2. HASAR GÖREN CİHAZ TÜRÜ
        pdf.set_font("ArialTR", "B", 10)
        pdf.cell(0, 6, "2. HASAR GÖREN CİHAZ TÜRÜ", ln=True)
        y_start = pdf.get_y()
        pdf.rect(10, y_start, 190, 25)
        
        equipment = items.get("equipment", [])
        if isinstance(equipment, str):
            equipment = [equipment]
            
        def draw_checkbox(x, y, label, is_checked):
            pdf.rect(x, y, 4, 4)
            if is_checked:
                pdf.set_font("ArialTR", "B", 10)
                pdf.text(x+0.5, y+3.5, "X")
            pdf.set_font("ArialTR", "", 10)
            pdf.text(x+6, y+3.5, label)
            
        pdf.set_y(y_start + 4)
        # Row 1
        draw_checkbox(15, pdf.get_y(), "Bilgisayar", "Bilgisayar" in equipment)
        draw_checkbox(65, pdf.get_y(), "Monitör", "Monitör" in equipment)
        draw_checkbox(115, pdf.get_y(), "Yazıcı", "Yazıcı" in equipment)
        draw_checkbox(160, pdf.get_y(), "Barkod Yazıcı", "Barkod Yazıcı" in equipment)
        pdf.ln(7)
        # Row 2
        draw_checkbox(15, pdf.get_y(), "Barkod Okuyucu", "Barkod Okuyucu" in equipment)
        draw_checkbox(65, pdf.get_y(), "Switch", "Switch" in equipment)
        draw_checkbox(115, pdf.get_y(), "Klavye", "Klavye" in equipment)
        draw_checkbox(160, pdf.get_y(), "Mouse", "Mouse" in equipment)
        pdf.ln(7)
        # Row 3
        draw_checkbox(15, pdf.get_y(), "43\" Ekran", "43\" Ekran" in equipment)
        draw_checkbox(65, pdf.get_y(), "24\" Ekran", "24\" Ekran" in equipment)
        draw_checkbox(115, pdf.get_y(), "Kiosk", "Kiosk" in equipment)
        
        other_val = items.get("other_equipment", "")
        draw_checkbox(160, pdf.get_y(), f"Diğer: {other_val}", "Diğer" in equipment or other_val != "")
        pdf.ln(10)
        
        # 3. HASAR TESPİT AÇIKLAMASI
        pdf.set_font("ArialTR", "B", 10)
        pdf.cell(0, 6, "3. HASAR TESPİT AÇIKLAMASI", ln=True)
        pdf.set_font("ArialTR", "", 8)
        pdf.cell(0, 4, "Hasar nasıl tespit edildi? Hasarın durumu ve kapsamı hakkında ayrıntılı bilgi veriniz.", ln=True)
        pdf.set_font("ArialTR", "", 10)
        
        desc = items.get("desc", "")
        pdf.set_xy(10, pdf.get_y() + 2)
        pdf.multi_cell(190, 6, desc, border=1)
        pdf.ln(5)
        
        # 4. HASAR TESPİT FOTOĞRAFI
        pdf.set_font("ArialTR", "B", 10)
        pdf.cell(0, 6, "4. HASAR TESPİT FOTOĞRAFI", ln=True)
        photo_y = pdf.get_y()
        pdf.rect(10, photo_y, 190, 80)
        if photo_path and os.path.exists(photo_path):
            try:
                pdf.image(photo_path, 12, photo_y + 2, 186, 76)
            except Exception as e:
                pdf.set_xy(12, photo_y + 35)
                pdf.cell(186, 10, "Fotoğraf yüklenemedi", align="C")
        else:
            pdf.set_xy(12, photo_y + 35)
            pdf.set_font("ArialTR", "", 10)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(186, 10, "(Lütfen hasarın net görüldüğü fotoğrafı buraya ekleyiniz veya zımbalayınız)", align="C")
            pdf.set_text_color(0, 0, 0)
            
        pdf.set_y(photo_y + 85)
        
        # FOOTER INFO & SIGNATURES
        pdf.set_font("ArialTR", "", 9)
        pdf.cell(0, 6, "İş bu tutanak, durumu belgelemek ve tebellüğ yerine geçmek üzere düzenlenmiş ve imza altına alınmıştır.", ln=True)
        pdf.ln(5)
        
        kullanici = items.get("kullanici", "")
        tespit_eden = items.get("tespit_eden", "")
        birim_sorumlusu = items.get("birim_sorumlusu", "MURAT COŞKUN")
        
        pdf.set_font("ArialTR", "B", 9)
        pdf.cell(63, 6, "Kullanıcı / Sorumlu", align="L")
        pdf.cell(63, 6, "Tespit Eden", align="C")
        pdf.cell(64, 6, "Birim Sorumlusu", align="R", ln=True)
        
        pdf.set_font("ArialTR", "", 9)
        pdf.cell(63, 6, "Ad-Soyad/Unvan/İmza", align="L")
        pdf.cell(63, 6, "Ad-Soyad/Unvan/İmza", align="C")
        pdf.cell(64, 6, "Ad-Soyad/Unvan/İmza", align="R", ln=True)
        
        pdf.ln(10)
        pdf.set_font("ArialTR", "B", 9)
        pdf.cell(63, 6, kullanici, align="L")
        pdf.cell(63, 6, tespit_eden, align="C")
        pdf.cell(64, 6, birim_sorumlusu, align="R", ln=True)

    temp_dir = TEMP_DIR
    os.makedirs(temp_dir, exist_ok=True)
    temp_pdf_path = os.path.join(temp_dir, f"temp_direct_{datetime.datetime.now().timestamp()}.pdf")
    pdf.output(temp_pdf_path)
    return temp_pdf_path

def generate_ht_from_excel(items, photo_path=None):
    temp_dir = TEMP_DIR
    os.makedirs(temp_dir, exist_ok=True)
    
    timestamp = datetime.datetime.now().timestamp()
    temp_excel = os.path.join(temp_dir, f"temp_ht_{timestamp}.xlsx")
    temp_pdf = os.path.join(temp_dir, f"temp_ht_{timestamp}.pdf")
    
    template_path = os.path.join(os.path.dirname(__file__), "..", "database", "sablonlar", "hasar_tespit.xlsx")
    shutil.copy2(template_path, temp_excel)
    
    wb = openpyxl.load_workbook(temp_excel)
    ws = wb.active
    
    # Text Fields
    ws["D10"] = str(items.get("sla", "-"))
    ws["D32"] = str(items.get("seri", "-"))
    ws["D33"] = str(items.get("model", "-"))
    ws["B27"] = str(items.get("desc", items.get("hasar_aciklama", "-")))
    ws["B50"] = str(items.get("teslimEden", "-"))
    ws["E50"] = str(items.get("tespitEden", "-"))
    ws["I50"] = str(items.get("birimSorumlusu", "-"))
    
    # Checkboxes
    equipment_cells = {
        "Bilgisayar": "E12", "Klavye": "I12", "Monitör": "E14", "Mouse": "I14",
        "Yazıcı": "E16", "43\" Ekran": "I16", "Barkod Yazıcı": "E18", "24\" Ekran": "I18",
        "Barkod Okuyucu": "E20", "Kiosk": "I20", "Switch": "I22"
    }
    
    selected_eqs = items.get("equipment", [])
    if isinstance(selected_eqs, str):
        selected_eqs = [selected_eqs]
        
    other_items = []
    for eq in selected_eqs:
        if eq in equipment_cells:
            ws[equipment_cells[eq]] = "X"
        else:
            other_items.append(eq)
            
    if other_items:
        ws["E22"] = "X"
        ws["D22"] = ", ".join(other_items)
        
    # Photo insertion
    if photo_path and os.path.exists(photo_path):
        try:
            from openpyxl.drawing.image import Image as OpenpyxlImage
            img = OpenpyxlImage(photo_path)
            # Resize image to fit nicely
            img.width = 320
            img.height = 160
            ws.add_image(img, "G35")
        except Exception as e:
            print("Could not add image to Excel:", e)

    wb.save(temp_excel)
    
    # Convert to PDF
    try:
        excel = win32com.client.Dispatch("Excel.Application")
        excel.Visible = False
        wb_com = excel.Workbooks.Open(os.path.abspath(temp_excel))
        ws_com = wb_com.ActiveSheet
        ws_com.PageSetup.Zoom = False
        ws_com.PageSetup.FitToPagesWide = 1
        ws_com.PageSetup.FitToPagesTall = False
        ws_com.PageSetup.LeftMargin = 5
        ws_com.PageSetup.RightMargin = 5
        ws_com.PageSetup.TopMargin = 5
        ws_com.PageSetup.BottomMargin = 5
        
        wb_com.ExportAsFixedFormat(0, os.path.abspath(temp_pdf))
        wb_com.Close(False)
        excel.Quit()
    except Exception as e:
        print("Excel to PDF conversion failed:", e)
        # Fallback to excel if PDF fails
        return temp_excel, [temp_excel]
        
    return temp_pdf, [temp_excel, temp_pdf]

def generate_izin_from_excel(items):
    temp_dir = TEMP_DIR
    os.makedirs(temp_dir, exist_ok=True)
    
    timestamp = datetime.datetime.now().timestamp()
    temp_excel = os.path.join(temp_dir, f"temp_izin_{timestamp}.xlsx")
    temp_pdf = os.path.join(temp_dir, f"temp_izin_{timestamp}.pdf")
    
    template_path = os.path.join(os.path.dirname(__file__), "..", "database", "sablonlar", "İzin İstek Formu.xlsx")
    shutil.copy2(template_path, temp_excel)
    
    def format_date(d_str):
        if not d_str or d_str == "-":
            return "-"
        try:
            parts = d_str.split("-")
            if len(parts) == 3 and len(parts[0]) == 4:
                return f"{parts[2]}.{parts[1]}.{parts[0]}"
        except:
            pass
        return d_str

    wb = openpyxl.load_workbook(temp_excel)
    ws = wb.active
    
    # Fill values
    ws["B6"] = datetime.datetime.now().strftime("%d.%m.%Y")
    ws["B7"] = str(items.get("ad_soyad", "-"))
    ws["F7"] = str(items.get("bolum", "-"))
    ws["B8"] = str(items.get("sicil", "-"))
    ws["F8"] = str(items.get("gorev", "-"))
    ws["B9"] = str(items.get("sebep", "-"))
    ws["B10"] = format_date(items.get("baslangic", "-"))
    ws["D10"] = str(items.get("bas_saat", "-"))
    ws["B11"] = format_date(items.get("bitis", "-"))
    ws["D11"] = str(items.get("bit_saat", "-"))
    ws["B12"] = format_date(items.get("isbasi", "-"))
    ws["D12"] = str(items.get("isbasi_saat", "-"))
    
    # Format duration
    ws["E10"] = f"{items.get('sure_gun', '0')} Gün / {items.get('sure_saat', '0')} Saat"
    
    # Paid/Unpaid selection in A13
    tur = items.get("tur", "")
    if "Ücretsiz" in tur:
        ws["A13"] = "Yukarıda Adı Soyadı Yazılı çalışanımıza mazeretine binaen aşağıda belirtilen tarih / tarihleri arasında ÜCRETSİZ izin verilmesi uygun görülmüştür."
    else:
        ws["A13"] = "Yukarıda Adı Soyadı Yazılı çalışanımıza mazeretine binaen aşağıda belirtilen tarih / tarihleri arasında ÜCRETLİ izin verilmesi uygun görülmüştür."
        
    # Signatures
    ws["A16"] = str(items.get("talep_eden_ad", "-"))
    ws["B16"] = str(items.get("takim_lideri_ad", "-"))
    ws["C16"] = str(items.get("bolum_muduru_ad", "-"))
    ws["F16"] = str(items.get("ik_ad", "-"))
    
    wb.save(temp_excel)
    
    # Convert to PDF
    try:
        excel = win32com.client.Dispatch("Excel.Application")
        excel.Visible = False
        wb_com = excel.Workbooks.Open(os.path.abspath(temp_excel))
        ws_com = wb_com.ActiveSheet
        ws_com.PageSetup.Zoom = False
        ws_com.PageSetup.FitToPagesWide = 1
        ws_com.PageSetup.FitToPagesTall = False
        ws_com.PageSetup.LeftMargin = 5
        ws_com.PageSetup.RightMargin = 5
        ws_com.PageSetup.TopMargin = 5
        ws_com.PageSetup.BottomMargin = 5
        
        wb_com.ExportAsFixedFormat(0, os.path.abspath(temp_pdf))
        wb_com.Close(False)
        excel.Quit()
    except Exception as e:
        print("Excel to PDF conversion failed for Izin:", e)
        # Fallback to excel if PDF fails
        return temp_excel, [temp_excel]
        
    return temp_pdf, [temp_excel, temp_pdf]

@document_service_bp.route('/generate_tutanak', methods=['POST'])
def generate_tutanak():
    files_to_delete = []
    try:
        temp_dir = TEMP_DIR
        os.makedirs(temp_dir, exist_ok=True)
        
        photo_path = None
        if request.is_json:
            data = request.json
            items = data.get('data', data.get('items', {}))
            t_type = data.get('type')
        else:
            data = request.form
            items = json.loads(data.get('data', '{}'))
            t_type = data.get('type')
            photo_file = request.files.get('photo')
            if photo_file:
                photo_path = os.path.join(temp_dir, f"photo_{datetime.datetime.now().timestamp()}.jpg")
                photo_file.save(photo_path)
                files_to_delete.append(photo_path)
        if not t_type:
            return jsonify({"success": False, "error": "type is required"}), 400
            
        if t_type == "IZIN":
            out_path, created_files = generate_izin_from_excel(items)
            files_to_delete.extend(created_files)
            response = send_file(out_path, as_attachment=True, download_name=f"{t_type}_Tutanak.{out_path.split('.')[-1]}")
        else:
            pdf_path = generate_pdf_direct(t_type, items, photo_path)
            files_to_delete.append(pdf_path)
            response = send_file(pdf_path, as_attachment=True, download_name=f"{t_type}_Tutanak.pdf")

        @response.call_on_close
        def remove_temporary_files():
            import time
            time.sleep(0.5)  # Buffer for Win32 Excel/Flask file handles to close
            for path in files_to_delete:
                last_err = None
                for _ in range(3):
                    try:
                        if path and os.path.exists(path):
                            os.remove(path)
                        break
                    except Exception as e:
                        last_err = e
                        time.sleep(0.2)
                else:
                    print(f"Error removing temporary file {path}: {last_err}")

        return response
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

```

### GÜVENLİ IP MANTIĞI (user_manager.py)
```python
        cursor.execute("SELECT id, username, role, session_timeout, password_hash, display_name, keyos_user, keyos_pass, bim_user, bim_pass, permissions, trusted_ips FROM users")
            u_id, u_name, u_role, u_timeout, db_hash, disp_name, keyos_u, keyos_p_enc, bim_u, bim_p_enc, u_perms, trusted_ips = user_row
                if trusted_ips:
                    trusted_list = [ip.strip() for ip in trusted_ips.split(',') if ip.strip()]
                    "session_timeout": int(u_timeout) if u_timeout is not None and str(u_timeout).strip() != "" else 5,
                    "trusted_ips": str(trusted_ips or ""),
            SELECT id, username, role, display_name, session_timeout, permissions 
            "session_timeout": int(u_timeout or 30)
                    "session_timeout": r.get("session_timeout", 30),
        session_timeout = data.get('session_timeout', 60)
                SET keyos_user=?, keyos_pass=?, bim_user=?, bim_pass=?, session_timeout=? 
            """, (keyos_user, enc_keyos, bim_user, enc_bim, session_timeout, user_id))
                SET keyos_user=?, keyos_pass=?, bim_user=?, session_timeout=? 
            """, (keyos_user, enc_keyos, bim_user, session_timeout, user_id))
                SET keyos_user=?, bim_user=?, bim_pass=?, session_timeout=? 
            """, (keyos_user, bim_user, enc_bim, session_timeout, user_id))
                SET keyos_user=?, bim_user=?, session_timeout=? 
            """, (keyos_user, bim_user, session_timeout, user_id))
        if 'trusted_ips' in data:
            trusted_ips = data.get('trusted_ips')
            cursor.execute("UPDATE users SET trusted_ips=? WHERE id=?", (trusted_ips, user_id))

```
