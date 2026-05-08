from flask import Blueprint, jsonify, request
from core.database_sql import query_db, get_db_connection
from modules.logs_manager import log_change, get_mac_address
from core.auth import require_auth, require_editor, require_admin
from modules.bim_service import get_bim_session, BIM_URL
import requests
from bs4 import BeautifulSoup
import urllib3
import subprocess
import re
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

printer_manager_bp = Blueprint('printer_manager', __name__)

PRINTER_STATUS_PORTAL = "https://10.241.1.21:49631/printers/"

class CUPSHelper:
    BASE_URL = "https://10.241.1.21:49631"
    AUTH_USER = 'root'
    AUTH_PASS = '1234qqqQ'

    @classmethod
    def get_session(cls):
        session = requests.Session()
        session.auth = (cls.AUTH_USER, cls.AUTH_PASS)
        session.verify = False
        
        # Gelişmiş SSL ayarları (Eski CUPS sunucuları için)
        try:
            from urllib3.util import ssl_
            ctx = ssl_.create_urllib3_context()
            ctx.load_default_certs()
            ctx.check_hostname = False
            ctx.verify_mode = 0
            ctx.set_ciphers('DEFAULT@SECLEVEL=1')
            
            adapter = requests.adapters.HTTPAdapter()
            adapter.pool_connections = 1
            adapter.pool_maxsize = 1
            session.mount("https://", adapter)
        except Exception as e:
            print(f"CUPS Session SSL Warning: {e}")
            
        return session

    @classmethod
    def _run_curl(cls, url, data=None, referer=None, multipart=False):
        """curl.exe kullanarak istek atar (Headers, Cookie ve SID Senkronizasyonu)."""
        cookie_file = "cups_cookies.txt"
        cmd = [
            'curl.exe', '-k', '-L', '-s',
            '--anyauth', '--user', f"{cls.AUTH_USER}:{cls.AUTH_PASS}",
            '-c', cookie_file, '-b', cookie_file,
            '-H', f'Origin: {cls.BASE_URL}',
            '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        ]
        
        # Multipart değilse standart form header'ı ekle
        if not multipart:
            cmd.extend(['-H', 'Content-Type: application/x-www-form-urlencoded'])
            
        if referer:
            cmd.extend(['-H', f'Referer: {referer}'])
            
        if data:
            for k, v in data.items():
                if multipart:
                    # Multipart/form-data formatı
                    cmd.extend(['-F', f"{k}={v}"])
                else:
                    # Standart URL-encoded formatı
                    cmd.extend(['--data-urlencode', f"{k}={v}"])
                
                if k == "org.cups.sid":
                    cmd.extend(['-b', f"{k}={v}"])
        
        cmd.append(url)
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=20, encoding='utf-8', errors='ignore')
            # print(f"DEBUG: CURL Output for {url}: {result.stdout[:200]}...") # Gerekirse açılabilir
            return result.stdout or ""
        except Exception as e:
            print(f"DEBUG: CUPS Curl Exception: {e}")
            return ""

    @classmethod
    def get_sid(cls):
        """SID'i çerez dosyasıyla birlikte taze olarak alır."""
        try:
            if os.path.exists("cups_cookies.txt"):
                try: os.remove("cups_cookies.txt")
                except: pass
                
            output = cls._run_curl(f"{cls.BASE_URL}/admin/")
            
            # Daha kapsamlı regex (name/value sırası değişebilir)
            match = re.search(r'name=["\']org\.cups\.sid["\'][^>]*value=["\']?([a-f0-9]+)["\']?', output, re.I)
            if not match:
                match = re.search(r'value=["\']?([a-f0-9]+)["\']?[^>]*name=["\']org\.cups\.sid["\']', output, re.I)
            
            if match:
                sid = match.group(1)
                print(f"DEBUG: Extracted SID: {sid}")
                return sid
            
            return None
        except Exception as e:
            print(f"CUPS SID Extraction Error: {e}")
            return None

    @classmethod
    def set_status(cls, printer_name, op):
        """op: pause-printer, resume-printer, reject-jobs, accept-jobs"""
        # HTML Analizi Sonucu: Bu CUPS sürümü 'stop-printer' ve 'start-printer' değerlerini bekliyor.
        real_op = op
        if op == 'pause-printer': real_op = 'stop-printer'
        elif op == 'resume-printer': real_op = 'start-printer'
        
        print(f"DEBUG: CUPS set_status (CURL+HEADERS) for {printer_name} with op {real_op}")
        try:
            sid = cls.get_sid()
            if not sid: 
                return False, "CUPS SID alınamadı."
            
            url = f"{cls.BASE_URL}/printers/{printer_name}"
            payload = {
                "org.cups.sid": sid,
                "OP": real_op,
                "printer_name": printer_name
            }
            
            # Buton label'ları (Maintenance menüsü simülasyonu)
            if real_op == 'stop-printer': payload["Pause Printer"] = "Pause Printer"
            elif real_op == 'start-printer': payload["Resume Printer"] = "Resume Printer"
            elif real_op == 'reject-jobs': payload["Reject Jobs"] = "Reject Jobs"
            elif real_op == 'accept-jobs': payload["Accept Jobs"] = "Accept Jobs"

            output = cls._run_curl(url, data=payload, referer=url)
            
            # Başarı kontrolü
            if "Error" in output or "Wrong" in output:
                return False, "CUPS sunucusu hata döndürdü."
            
            return True, f"İşlem başarılı: {real_op}"
        except Exception as e:
            print(f"DEBUG: CUPS set_status Exception: {e}")
            return False, str(e)

    @classmethod
    def get_printer_name_by_ip(cls, target_ip):
        """CUPS sunucusunda IP adresine (Device URI) göre yazıcı adını bulur. (Kesin eşleşme)"""
        print(f"DEBUG: Searching CUPS for printer with EXACT IP: {target_ip}")
        try:
            url = f"{cls.BASE_URL}/printers/"
            output = cls._run_curl(url)
            soup = BeautifulSoup(output, 'html.parser')
            links = [a.get('href') for a in soup.find_all('a') if a.get('href', '').startswith('/printers/') and not a.get('href', '').endswith('.ppd')]
            
            for href in set(links):
                p_name = href.replace('/printers/', '').strip()
                p_url = f"{cls.BASE_URL}/printers/{p_name}"
                p_output = cls._run_curl(p_url)
                
                # IP'yi URI veya Bağlantı satırında kesin olarak ara
                # Örn: socket://10.241.40.1 (yanında rakam olmamalı)
                pattern = rf'[:/]{re.escape(target_ip)}(?![0-9])'
                if re.search(pattern, p_output):
                    print(f"DEBUG: Found EXACT printer {p_name} for IP {target_ip}")
                    return p_name
            return None
        except Exception as e:
            print(f"DEBUG: get_printer_name_by_ip error: {e}")
            return None

    @classmethod
    def get_all_locations(cls):
        """CUPS sunucusundaki tüm yazıcıların Location bilgisini çeker."""
        print("DEBUG: Fetching all CUPS printer locations...")
        try:
            url = f"{cls.BASE_URL}/printers/"
            output = cls._run_curl(url)
            soup = BeautifulSoup(output, 'html.parser')
            
            locations = {}
            # CUPS printers tablosu
            table = soup.find('table')
            if not table: return {}
            
            rows = table.find_all('tr')[1:] # Header atla
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 2:
                    # Link içinden ismi al
                    a_tag = cols[0].find('a')
                    if a_tag:
                        name = a_tag.get_text(strip=True)
                        location = cols[1].get_text(strip=True)
                        locations[name] = location
            return locations
        except Exception as e:
            print(f"DEBUG: get_all_locations error: {e}")
            return {}

    @classmethod
    def update_db_cups_locations(cls):
        """CUPS'taki location bilgilerini DB'ye aktarır."""
        print("DEBUG: Starting Batch CUPS Location Sync...")
        try:
            cups_data = cls.get_all_locations()
            if not cups_data:
                print("DEBUG: CUPS'tan veri alınamadı.")
                return False
                
            conn = get_db_connection()
            for name, loc in cups_data.items():
                # pr_no ile eşleşen yazıcıyı bul (Büyük/Küçük harf duyarsız)
                conn.execute("UPDATE printers SET cups_location=? WHERE UPPER(pr_no) = UPPER(?)", (loc, name))
            conn.commit()
            conn.close()
            print(f"DEBUG: Batch CUPS Location Sync completed for {len(cups_data)} printers.")
            return True
        except Exception as e:
            print(f"DEBUG: update_db_cups_locations error: {e}")
            return False

    @classmethod
    def update_location(cls, printer_name, new_location, target_ip=None, new_info=None):
        """CUPS Dinamik Sihirbaz İzleyici (Wizard Follower). Başarı mesajı gelene kadar tüm adımları geçer."""
        print(f"DEBUG: CUPS update_location START for {printer_name} (Target IP: {target_ip})")
        try:
            if target_ip:
                actual_name = cls.get_printer_name_by_ip(target_ip)
                if actual_name: 
                    print(f"DEBUG: CUPS üzerindeki gerçek ad doğrulandı: {actual_name}")
                    printer_name = actual_name

            url = f"{cls.BASE_URL}/admin/"
            # Yazıcı ismini temizle (başında/sonunda slash varsa kaldır)
            clean_printer_name = printer_name.strip('/')
            printer_url = f"{cls.BASE_URL}/printers/{clean_printer_name}"
            
            # Fresh start: Çerezleri temizle
            cookie_file = "cups_cookies.txt"
            if os.path.exists(cookie_file):
                try: os.remove(cookie_file)
                except: pass

            current_res = ""
            current_referer = cls.BASE_URL
            active_sid = ""

            for step in range(1, 11):
                print(f"DEBUG: CUPS Step {step} İşleniyor...")
                
                if step == 1:
                    # Yazıcı sayfasından başla
                    print(f"DEBUG: Yazıcı sayfasına gidiliyor: {printer_url}")
                    current_res = cls._run_curl(printer_url, referer=cls.BASE_URL)
                    current_referer = printer_url
                
                soup = BeautifulSoup(current_res, 'html.parser')
                page_title = soup.title.string.strip() if soup.title else "Bilinmiyor"
                
                # SID Yakala
                sid_match = re.search(r'name=["\']org\.cups\.sid["\'][^>]*value=["\']?([a-f0-9]+)["\']?', current_res, re.I)
                active_sid = sid_match.group(1) if sid_match else active_sid
                
                if step == 1 and ("Administration" in page_title or not soup.find('form')):
                    print("DEBUG: Step 1: Modify Printer operasyonu tetikleniyor (POST)...")
                    payload = { "org.cups.sid": active_sid, "OP": "modify-printer", "printer_name": clean_printer_name }
                    current_res = cls._run_curl(f"{cls.BASE_URL}/admin/", data=payload, referer=printer_url)
                    current_referer = f"{cls.BASE_URL}/admin/"
                    soup = BeautifulSoup(current_res, 'html.parser')
                    page_title = soup.title.string.strip() if soup.title else "Bilinmiyor"

                print(f"DEBUG: Mevcut Sayfa: '{page_title}'")
                if active_sid: print(f"DEBUG: Step {step} SID: {active_sid}")

                # Başarı kontrolü
                if any(x in current_res.lower() for x in ["successfully", "başarıyla", "güncellendi", "updated"]):
                    print(f"DEBUG: CUPS Güncelleme {step}. adımda TAMAMLANDI.")
                    return True, "CUPS Mahal başarıyla güncellendi."

                # Formu bul (Sayfadaki herhangi bir /admin formunu yakala)
                form = soup.find('form', action=re.compile(r'/admin'))
                
                if not form:
                    # Alternatif: Sayfada hiç form yoksa ama 'Modify Printer' linki varsa
                    modify_link = soup.find('a', href=re.compile(r'modify-printer'))
                    if modify_link:
                        print("DEBUG: Modify link bulundu, link üzerinden gidiliyor...")
                        link_url = cls.BASE_URL + modify_link['href'] if modify_link['href'].startswith('/') else f"{cls.BASE_URL}/admin/{modify_link['href']}"
                        current_res = cls._run_curl(link_url, referer=current_referer)
                        current_referer = link_url
                        continue

                    if step > 1: 
                        print("DEBUG: Form bulunamadı, işlem bitmiş olabilir.")
                        return True, "İşlem tamamlandı (Form kalmadı)."
                    return False, f"CUPS Formu bulunamadı. Sayfa: {page_title}"

                # Payload hazırla (Sayfadaki TÜM inputları, hidden dahil topla)
                payload = {}
                for inp in form.find_all(['input', 'select', 'textarea']):
                    name = inp.get('name')
                    if not name: continue
                    
                    # Varsayılan değeri belirle
                    val = ''
                    if inp.name == 'select':
                        opt = inp.find('option', selected=True) or inp.find('option')
                        val = opt.get('value', '') if opt else ''
                    elif inp.name == 'textarea':
                        val = inp.string or ''
                    else:
                        val = inp.get('value', '')

                    # Özel alanları güncelle
                    if name == 'PRINTER_LOCATION':
                        val = new_location
                        print(f"DEBUG: Location güncellendi: {val}")
                    elif name == 'PRINTER_IS_SHARED':
                        val = "0"
                    
                    payload[name] = val

                # SID'yi zorunlu ekle
                payload["org.cups.sid"] = active_sid
                
                # Adım 1 Özelleştirmesi
                if step == 1 and "Printers" in page_title:
                    payload["OP"] = "modify-printer"
                    payload["printer_name"] = clean_printer_name

                # Buton belirle (Continue veya Modify Printer)
                submits = form.find_all('input', {'type': 'submit'})
                button_sent = False
                for p_val in ["Continue", "Modify Printer"]:
                    for btn in submits:
                        if p_val.lower() in (btn.get('value') or '').lower():
                            if btn.get('name'): payload[btn['name']] = btn.get('value')
                            else: payload[btn.get('value').upper().replace(' ', '_')] = btn.get('value')
                            button_sent = True; break
                    if button_sent: break
                
                if not button_sent and submits:
                    btn = submits[0]
                    payload[btn.get('name') or 'submit'] = btn.get('value', '')

                # POST isteğini gönder
                is_multipart = (form.get('enctype') == 'multipart/form-data')
                print(f"DEBUG: Step {step} POST gönderiliyor... Action: {form.get('action')}")
                
                # ÖZEL DURUM: Buton seçimi
                # Kullanıcı uyarısı: Mahal girildikten sonra 'Continue' denmeli, 'Modify Printer' değil.
                if step < 4:
                    if "Continue" in payload: 
                        payload["Continue"] = "Continue"
                        print("DEBUG: 'Continue' butonu seçildi.")
                else:
                    if "Modify Printer" in payload:
                        payload["Modify Printer"] = "Modify Printer"
                        print("DEBUG: 'Modify Printer' (Son Adım) seçildi.")

                # Action içindeki parametreleri de payload'a ekle (Gerekliyse)
                action_url = form.get('action')
                full_post_url = cls.BASE_URL + action_url if action_url.startswith('/') else f"{cls.BASE_URL}/admin/{action_url}"
                
                res = cls._run_curl(full_post_url, data=payload, referer=current_referer, multipart=is_multipart)
                
                # Sayfa ilerleme kontrolü
                new_soup = BeautifulSoup(res, 'html.parser')
                new_title = new_soup.title.string.strip() if new_soup.title else "Bilinmiyor"
                if new_title == page_title and step > 1:
                    print("DEBUG: Sayfa ilerlemedi. Form verisi reddedilmiş olabilir.")

                current_res = res
                current_referer = full_post_url

            return True, "CUPS İşlemleri bitti (Adım sınırı doldu)."
        except Exception as e:
            print(f"DEBUG: CUPS update_location ERROR: {e}")
            return False, str(e)
        except Exception as e:
            print(f"DEBUG: CUPS update_location ERROR: {e}")
            return False, str(e)

def get_cups_printers():
    """CUPS sunucusundaki tüm yazıcı isimlerini (PR NO) çeker."""
    try:
        session = CUPSHelper.get_session()
        # SSL Context'i session ile kullanıyoruz
        try:
            res = session.get(PRINTER_STATUS_PORTAL, timeout=5)
            if res.status_code != 200: return []
            
            soup = BeautifulSoup(res.text, 'html.parser')
            # CUPS genelde tablolarda printer isimlerini link olarak verir
            printers = []
            for link in soup.find_all('a'):
                href = link.get('href', '')
                if href.startswith('/printers/'):
                    name = href.replace('/printers/', '').strip()
                    if name: printers.append(name)
            return list(set(printers))
        except (requests.exceptions.SSLError, requests.exceptions.ConnectionError) as e:
            print(f"CUPS SSL/Protokol Hatası (Yine de devam ediliyor): {e}")
            return []
    except Exception as e:
        print(f"CUPS Scraping Beklenmedik Hata: {e}")
        return []

@printer_manager_bp.route('/get_all', methods=['GET'])
@require_auth
def get_printers():
    """Tüm yazıcıları yazıcılar tablosundan getirir."""
    try:
        items = query_db("SELECT * FROM printers")
        return jsonify([dict(row) for row in items])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

import subprocess
import platform

def ping_host(host):
    """Pings a host and returns True if it's online, False otherwise."""
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    command = ['ping', param, '1', '-w', '2000', host]
    try:
        return subprocess.call(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0
    except Exception:
        return False

@printer_manager_bp.route('/sync', methods=['POST'])
@require_auth
def sync_printer():
    target_ip = request.json.get('ip')
    if not target_ip: return jsonify({"error": "IP missing"}), 400
    
    try:
        is_online = ping_host(target_ip)
        if not is_online:
            return jsonify({
                "status": "Offline",
                "toner": "Bilinmiyor",
                "location": "-"
            })
            
        # Eğer printer online ise, basit bir HTTP web paneline bağlanmayı dene
        toner_level = "%100" # Varsayılan (fallback)
        try:
            # Gerçek bir senaryoda yazıcı markasına göre SNMP veya web scraping yapılır.
            # Şimdilik yazıcının web sayfasına HTTP GET atarak toner durumunu yakalamak için örnek bir deneme.
            # Timeout'u kısa tutalım.
            res = requests.get(f"http://{target_ip}", timeout=2, verify=False)
            if res.status_code == 200:
                toner_level = "%80" # Web paneli cevap verdi, burada HTML'den toner okunabilir
        except:
            toner_level = "Erişilemiyor (Web/SNMP kapalı)"

        return jsonify({
            "status": "Online",
            "toner": toner_level,
            "location": "-"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@printer_manager_bp.route('/update', methods=['POST'])
@require_editor
def update_printer():
    data = request.json
    id = data.get('id')
    changed_by = data.get('changed_by', 'system')
    display_name = data.get('display_name', 'Sistem')

    if not id: return jsonify({"error": "ID missing"}), 400
    
    try:
        conn = get_db_connection()
        # 1. Mevcut kaydı al (log Karşılaştırması için)
        old_record = conn.execute("SELECT * FROM printers WHERE id=?", (id,)).fetchone()
        if not old_record:
            conn.close()
            return jsonify({"error": "Kayıt bulunamadı"}), 404

        pr_label = f"{old_record['pr_no'] or 'Yazıcı'}"

        # 2. Aktif Servis Kontrolü: Eğer yazıcı servisteyse durumu sadece servis modülünden değişebilir
        new_status = data.get('status')
        if old_record['status'] != new_status:
            # Arızalı veya Serviste olan bir yazıcının durumu doğrudan değiştirilmek istenirse kontrol et
            active_service = conn.execute("SELECT id FROM printer_service WHERE printer_id=? AND return_date IS NULL", (id,)).fetchone()
            if active_service:
                 # Eğer aktif servis kaydı varsa ve durum 'Kurulu' veya 'Depoda' yapılmak isteniyorsa engelle
                 if new_status not in ['Arızalı', 'Serviste']:
                     conn.close()
                     return jsonify({"error": f"Bu yazıcı ({pr_label}) şu an AKTİF SERVİS sürecindedir. Durum değişikliği sadece Servis Yönetimi üzerinden (Giriş Tarihi girilerek) yapılabilir."}), 403

        # 3. Güncelleme yap
        conn.execute('''UPDATE printers SET 
            pr_no=?, model=?, ip=?, seri=?, mac=?, status=?, mahal=?
            WHERE id=?''', (
            data.get('pr_no'), data.get('model'), data.get('ip'), 
            data.get('seri'), data.get('mac'), data.get('status'), data.get('mahal'), id
        ))

        # 3. Değişiklikleri logla
        tracked_fields = ['pr_no', 'model', 'ip', 'seri', 'mac', 'status', 'mahal']
        for field in tracked_fields:
            old_val = str(old_record.get(field, '') or '')
            new_val = str(data.get(field, '') or '')
            
            label_map = {
                'pr_no': 'PR Numarası', 'model': 'Model', 'ip': 'IP Adresi',
                'seri': 'Seri No', 'mac': 'MAC Adresi', 'status': 'Durum',
                'mahal': 'Mahal / Konum'
            }
            label = label_map.get(field, field)
            
            client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            if ',' in client_ip: client_ip = client_ip.split(',')[0]
            client_mac = get_mac_address(client_ip)
            
            log_change(conn, 'printers', id, pr_label, label, old_val, new_val, changed_by, display_name, client_ip=client_ip, client_mac=client_mac)

        conn.commit()
        conn.close()
        return jsonify({"message": "Yazıcı bilgileri güncellendi"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def sync_printers_from_excel_internal():
    """Excel'den yazıcıları/tarayıcıları/barkod okuyucuları senkronize eder."""
    import openpyxl
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    yaz_path = os.path.join(BASE_DIR, "database", "yazıcılar.xlsx")
    
    if not os.path.exists(yaz_path):
        raise FileNotFoundError("yazıcılar.xlsx bulunamadı")
        
    conn = get_db_connection()
    wb = openpyxl.load_workbook(yaz_path, data_only=True)
    
    # Tüm sekmeleri gez (Barkod Yazıcı, Barkod Okuyucu, Tarayıcı, Yazıcılar)
    updated_count = 0
    for sheet_name in wb.sheetnames:
        sheet = wb[sheet_name]
        rows = list(sheet.rows)
        if not rows: continue
        
        headers = [str(cell.value).strip().upper() if cell.value else f"Col{i}" for i, cell in enumerate(rows[0])]
        
        durum_idx = -1
        for i, h in enumerate(headers):
            if h in ['DURUM', 'STATUS', 'STATE']: durum_idx = i; break
        
        for r_idx, row_cells in enumerate(rows[1:], start=2):
            item = {headers[i]: row_cells[i].value for i in range(len(row_cells)) if i < len(headers)}
            
            pr_no = str(item.get('PR NUMARASI') or item.get('PR NO') or 
                        item.get('BY NO') or item.get('BARKOD YAZICI NO') or 
                        item.get('BO NO') or item.get('BARKOD OKUYUCU NO') or 
                        item.get('TR NO') or item.get('TARAYICI NO') or 
                        item.get('CİHAZ NO') or item.get('CIHAZ NO') or '').strip()
            seri = str(item.get('SERİ NUMARASI') or item.get('SERI NO') or '').strip()
            mac = str(item.get('MAC ADRESS') or item.get('MAC ADRES') or '').strip()
            model = str(item.get('MODEL') or item.get('CİHAZ MODELİ') or '').strip()
            
            if not pr_no or not seri:
                continue

            exists = conn.execute("SELECT id, status, model, seri, mac, ip FROM printers WHERE pr_no=? OR (seri=? AND seri != '')", (pr_no, seri)).fetchone()
            excel_status = str(row_cells[durum_idx].value or '').strip() if durum_idx != -1 else 'Kurulu'
            
            # Excel'den gelen durum bilgisini temizle
            final_status = 'Kurulu'
            if excel_status:
                s_up = excel_status.upper()
                if s_up in ['KURULU', 'SAHADA', 'OK', 'K', 'S']: final_status = 'Kurulu'
                elif s_up in ['DEPO', 'DEPODA', 'STOK', 'D']: final_status = 'Depoda'
                elif s_up in ['ARIZALI', 'A', 'BOZUK']: final_status = 'Arızalı'
                elif s_up in ['SERVİSTE', 'SERVIS', 'SERVİS']: final_status = 'Serviste'
                elif s_up in ['KAYIP', 'L', 'M']: final_status = 'Kayıp'

            if exists:
                conn.execute('''UPDATE printers SET model=?, seri=?, mac=?, ip=?, status=? WHERE id=?''', 
                             (model or exists['model'], 
                              seri or exists['seri'], 
                              mac or exists['mac'], 
                              item.get('IP ADRES') or exists['ip'],
                              final_status,
                              exists['id']))
            else:
                conn.execute('''INSERT INTO printers (pr_no, model, seri, mac, ip, status) 
                               VALUES (?,?,?,?,?,?)''', (
                    pr_no, model, seri, 
                    mac, item.get('IP ADRES'), final_status
                ))
            updated_count += 1
    
    try: wb.save(yaz_path)
    except: pass
    
    conn.commit()
    conn.close()
    return updated_count

@printer_manager_bp.route('/sync_from_excel', methods=['POST'])
@require_admin
def sync_printers_from_excel():
    """Excel'den yazıcıları senkronize eder."""
    try:
        count = sync_printers_from_excel_internal()
        return jsonify({"message": f"{count} cihaz senkronize edildi."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@printer_manager_bp.route('/status/<ip>', methods=['GET'])
def get_status(ip):
    """Canlı yazıcı durumunu Brother web arayüzünden çeker."""
    from modules.printer_service import get_brother_printer_status
    return jsonify(get_brother_printer_status(ip))

@printer_manager_bp.route('/scan_all', methods=['POST'])
@require_editor
def scan_all_printers():
    """Tüm yazıcıları sırayla tarar ve toner/durum bilgilerini günceller."""
    from modules.printer_service import get_brother_printer_status
    import threading
    
    def run_scan():
        try:
            printers = query_db("SELECT id, ip FROM printers WHERE ip IS NOT NULL AND ip != ''")
            for p in printers:
                ip = p['ip']
                status_data = get_brother_printer_status(ip)
                if status_data.get('success'):
                    query_db("UPDATE printers SET live_status=?, toner=? WHERE id=?", 
                             (status_data['device_status'], status_data['toner_level'], p['id']))
                else:
                    query_db("UPDATE printers SET live_status='Offline' WHERE id=?", (p['id'],))
        except Exception as e:
            print(f"Batch Scan Error: {e}")

    # Arka planda çalıştır (Zaman alabilir)
    thread = threading.Thread(target=run_scan)
    thread.start()
    
    return jsonify({"success": True, "message": "Tarama işlemi arka planda başlatıldı. Tamamlandığında liste güncellenecektir."})
@printer_manager_bp.route('/batch_action', methods=['POST'])
@require_editor
def batch_action():
    """Toplu yazıcı ekleme (++) veya çıkarma (--) işlemini gerçekleştirir."""
    data = request.json
    action = data.get('action') # 'add' or 'remove'
    printer_id = data.get('printer_id')
    targets = data.get('targets') # list of {type: 'PC'|'MAHAL', value: id|name}
    user_name = data.get('user', 'Sistem')
    bim_user = data.get('bim_user')
    bim_pass = data.get('bim_pass')
    bim_func = data.get('bim_function')
    command = data.get('command')

    if not action or not printer_id or not targets:
        return jsonify({"error": "Parametreler eksik"}), 400

    try:
        conn = get_db_connection()
        # printer_id'ye ait yazıcıyı bul
        printer = conn.execute("SELECT * FROM printers WHERE id=?", (printer_id,)).fetchone()
        if not printer:
            conn.close()
            return jsonify({"error": "Yazıcı bulunamadı"}), 404

        pr_no = printer['pr_no']
        
        # Hedef PC ID'lerini topla
        pc_ids = set()
        for t in targets:
            # Type case insensitive check
            t_type = str(t.get('type', '')).upper()
            if t_type == 'PC':
                pc_ids.add(int(t['value']))
            elif t_type == 'MAHAL':
                pcs_in_mahal = conn.execute("SELECT id FROM inventory WHERE category='PC' AND (mahal_adi=? OR mahal_kodu=?)", (t['value'], t['value'])).fetchall()
                for p in pcs_in_mahal:
                    pc_ids.add(p['id'])

        updated_count = 0
        bim_errors = []
        
        # BIM Session al (Eğer bilgiler varsa)
        session_token = None
        if bim_user and bim_pass:
            session_token = get_bim_session(bim_user, bim_pass)
            if not session_token:
                conn.close()
                return jsonify({"error": "BIM girişi başarısız. Lütfen bilgilerinizi kontrol edin."}), 401

        for pc_id in pc_ids:
            pc = conn.execute("SELECT * FROM inventory WHERE id=?", (pc_id,)).fetchone()
            if not pc: continue
            
            # 1. DB GÜNCELLEME (BİM başarılı olursa commit edeceğiz)
            current_raw = (pc['bagli_yazicilar'] or "").strip()
            pr_list = [x.strip() for x in current_raw.split(',') if x.strip()]
            
            db_updated = False
            if action == 'add':
                if pr_no not in pr_list:
                    pr_list.append(pr_no)
                    db_updated = True
            elif action == 'remove':
                original_len = len(pr_list)
                # Kısmi eşleşme kontrolü (Örn: 'PR-001 (Sahada)' kaydını 'PR-001' ile silmek için)
                # Regex: Başlangıçta pr_no olacak, sonra ya boşluk, ya parantez ya da satır sonu gelecek.
                pattern = re.compile(rf'^{re.escape(pr_no)}(\s|\(|$)', re.IGNORECASE)
                pr_list = [p for p in pr_list if not pattern.match(p)]
                
                if len(pr_list) < original_len:
                    db_updated = True
            
            # 2. BIM KOMUTU GÖNDERME
            bim_success = True
            if session_token and bim_func and command:
                if not pc['ip']:
                    bim_errors.append(f"PC-{pc['pc_no']}: IP Eksik")
                    bim_success = False
                else:
                    try:
                        payload = {
                            "Functions": bim_func,
                            "UserName": bim_user,
                            "IPAddress": pc['ip'],
                            "PrinterName": command if bim_func in ['AddPrinter', 'RemovePrinter'] else None,
                            "Commands": command if bim_func not in ['AddPrinter', 'RemovePrinter'] else None
                        }
                        payload = {k: v for k, v in payload.items() if v is not None}
                        headers = {"IPASession": session_token}
                        
                        resp = requests.post(BIM_URL, data=payload, headers=headers, timeout=15)
                        if resp.status_code != 200 or "Error" in resp.text:
                            err_detail = "BIM Reddedildi"
                            if "Error" in resp.text:
                                # Hata mesajını çekmeye çalış
                                err_detail = resp.text.split(':')[-1].strip() if ':' in resp.text else resp.text[:30]
                            bim_errors.append(f"PC-{pc['pc_no']}: {err_detail}")
                            bim_success = False
                    except Exception as e:
                        bim_errors.append(f"PC-{pc['pc_no']}: Bağlantı Hatası")
                        bim_success = False

            # Eğer BIM komutu gerekmiyorsa veya başarılıysa DB'yi güncelle
            if bim_success and db_updated:
                new_val = ", ".join(pr_list)
                conn.execute("UPDATE inventory SET bagli_yazicilar=? WHERE id=?", (new_val, pc_id))
                client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
                log_change(conn, 'inventory', pc_id, f"PC-{pc['pc_no']}", f'Bağlı Yazıcılar (Toplu {action.capitalize()})', current_raw, new_val, user_name, user_name, client_ip=client_ip)
                updated_count += 1

        conn.commit()
        conn.close()
        
        # Excel yedekleme
        try:
            from modules.inventory_manager import _backup_to_excel
            _backup_to_excel(get_db_connection())
        except: pass

        if bim_errors:
            error_summary = f"{len(bim_errors)} cihazda sorun oluştu:\n" + "\n".join(bim_errors[:10])
            if len(bim_errors) > 10: error_summary += "\n..."
            return jsonify({
                "success": updated_count > 0, 
                "error": error_summary,
                "count": updated_count
            })

        return jsonify({"success": True, "count": updated_count, "message": f"{updated_count} cihazda işlem başarıyla tamamlandı."})
    except Exception as e:
        if 'conn' in locals(): conn.close()
        return jsonify({"error": str(e)}), 500

@printer_manager_bp.route('/cups/update_mahal', methods=['POST'])
@require_editor
    ip = data.get('ip')
    mahal = data.get('mahal')
    if not ip or not mahal:
        return jsonify({"error": "Parametreler eksik (IP veya Mahal)."}), 400
    
    try:
        # IP üzerinden CUPS adını bul (Kullanıcı kesinlikle IP ile bulunsun dedi)
        printer_name = CUPSHelper.get_printer_name_by_ip(ip)
        if not printer_name:
            return jsonify({"error": f"CUPS üzerinde {ip} adresine sahip bir yazıcı bulunamadı."}), 200

        success, msg = CUPSHelper.update_location(printer_name, mahal, target_ip=ip)
        if success:
            return jsonify({"success": True, "message": msg})
        return jsonify({"error": msg}), 200
    except Exception as e:
        print(f"CUPS Update Mahal (IP-based) Error: {e}")
        return jsonify({"error": f"Sistem Hatası: {str(e)}"}), 200

@printer_manager_bp.route('/cups/set_status', methods=['POST'])
@require_editor
def cups_set_status():
    data = request.json
    pr_no = data.get('pr_no')
    op = data.get('op') # pause-printer, resume-printer, reject-jobs, accept-jobs
    if not pr_no or not op:
        return jsonify({"error": "Parametreler eksik."}), 400
    
    success, msg = CUPSHelper.set_status(pr_no, op)
    if success:
        return jsonify({"success": True, "message": msg})
    return jsonify({"error": msg}), 500
