from core.integrations import get_integration_config
from flask import Blueprint, jsonify, request
import requests
from bs4 import BeautifulSoup
from core.database_sql import query_db, get_db_connection
from core.auth import require_auth, require_admin
from core.encryption import decrypt_password
import os
import json
BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
from dotenv import load_dotenv
import urllib3
import socket

# DNS Rate-Limit Koruması: Sürekli istek atıldığında Windows/DNS sunucusu 
# 'getaddrinfo failed' hatası vermesin diye IP'yi manuel çözümlüyoruz.
_orig_getaddrinfo = socket.getaddrinfo

# .env'den ayarları çek (veya varsayılan Kocaeli ayarlarını kullan)
from core.integrations import get_integration_config
from urllib.parse import urlparse

def get_keyos_domain():
    keyos_cfg = get_integration_config('KEYOS')
    if keyos_cfg is None:
        return 'keyosmgt.kocaelish.com'
    return urlparse(keyos_cfg.get('base_url', 'http://keyosmgt.kocaelish.com')).hostname or 'keyosmgt.kocaelish.com'

KEYOS_PATCH_IP = os.getenv("KEYOS_PATCH_IP", "10.241.1.45")

def get_keyos_login_url():
    return os.getenv("get_keyos_login_url()", f"https://{get_keyos_domain()}/login")

def get_keyos_computers_url():
    return os.getenv("get_keyos_computers_url()", f"https://{get_keyos_domain()}/computers")

def _patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    # Evaluate domain at runtime to avoid DB queries during module load
    current_domain = get_keyos_domain()
    if KEYOS_PATCH_IP and host == current_domain:
        host = KEYOS_PATCH_IP
    return _orig_getaddrinfo(host, port, family, type, proto, flags)
socket.getaddrinfo = _patched_getaddrinfo

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

keyos_service_bp = Blueprint('keyos_service', __name__)

def _first_value(row, keys, default='-'):
    for key in keys:
        val = row.get(key)
        if val is not None and str(val).strip() not in ('', '-', 'None', 'null'):
            return str(val).strip()
    return default

def _normalize_os_flags(os_text, version_text=''):
    val = str(os_text or '').upper() + ' ' + str(version_text or '').upper()
    val = val.strip()
    if not val:
        return None, None
        
    if 'WINDOWS' in val or 'WIN' in val:
        return 1, 0
    if 'KEYOS' in val or 'KEY OS' in val or 'LINUX' in val or 'PARDUS' in val:
        return 0, 1
        
    # Eğer belli değilse mevcut durumu bozmamak için None döner
    return None, None

def _table_columns(table_name):
    try:
        rows = query_db("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = ?
        """, (table_name,))
        return {str(r.get('column_name')).lower() for r in rows} if rows else set()
    except Exception as e:
        print(f"[KeyOS] column scan error: {e}")
        return set()

def _safe_update_pc_from_keyos(pc_id, details, db_last_active=None):
    """Schema değiştirmeden sadece mevcut kolonları günceller."""
    cols = _table_columns('pcs')
    updates = []
    values = []

    def add(col, val):
        if col.lower() in cols:
            updates.append(f"{col} = ?")
            values.append(val)

    add('ip', details.get('ip'))
    add('mac', details.get('mac'))
    add('connected_printers', details.get('printers'))

    new_last_active = details.get('last_active')
    
    # KeyOS her zaman last_active sütununa yazar
    if new_last_active:
        add('last_active', new_last_active)
        add('operating_system', details.get('os'))
        add('os_name', details.get('os'))
        add('keyos_version', details.get('keyos_version'))
        
        win_flag, keyos_flag = _normalize_os_flags(details.get('os'), details.get('keyos_version'))
        if win_flag is not None and keyos_flag is not None:
            add('windows', win_flag)
            add('keyos', keyos_flag)

    if not updates:
        return

    values.append(pc_id)
    query_db(f"UPDATE pcs SET {', '.join(updates)} WHERE id = ?", tuple(values))


class KeyOSClient:
    def __init__(self, username, password):
        self.session = requests.Session()
        self.username = username
        self.password = password
        self.is_logged_in = False

    def login(self):
        try:
            # Get CSRF if any
            r = self.session.get(get_keyos_login_url(), timeout=10, verify=False)
            
            # The login API is /login/login and accepts JSON
            login_api = get_keyos_login_url() + "/login"
            payload = {
                "userName": self.username,
                "password": self.password
            }
            
            resp = self.session.post(login_api, json=payload, timeout=10, verify=False)
            if resp.status_code == 200 and "success" in resp.text:
                self.is_logged_in = True
                return True
        except Exception as e:
            print(f"[KeyOS] Login Error: {e}")
        return False

    def get_live_dashboard_stats(self):
        try:
            if not self.is_logged_in:
                if not self.login(): return None
            
            dash_url = get_keyos_login_url().replace("/login", "/dashboard")
            dash = self.session.get(dash_url, timeout=10, verify=False)
            
            # Extract numbers from text
            # Format: "5 dk açık 909 pc \n 5-10 gün kapalı 91 pc \n 11-29 gün kapalı 115 pc \n 30+ gün kapalı 227 pc"
            import re
            text = dash.text
            
            stats = {
                "k5": 0,
                "k5_10": 0,
                "k11_29": 0,
                "k30p": 0
            }
            
            m1 = re.search(r'5 dk a.*?(\d+)\s*pc', text, re.IGNORECASE)
            m2 = re.search(r'5-10 g.*?(\d+)\s*pc', text, re.IGNORECASE)
            m3 = re.search(r'11-29 g.*?(\d+)\s*pc', text, re.IGNORECASE)
            m4 = re.search(r'30\+\s*g.*?(\d+)\s*pc', text, re.IGNORECASE)
            
            if m1: stats["k5"] = int(m1.group(1))
            if m2: stats["k5_10"] = int(m2.group(1))
            if m3: stats["k11_29"] = int(m3.group(1))
            if m4: stats["k30p"] = int(m4.group(1))
            
            return stats
        except Exception as e:
            print(f"[KeyOS] Live Stats Error: {e}")
            return None

    def query_serial(self, serial):
        import time
        if not self.is_logged_in:
            return None
        for attempt in range(3):
            try:
                # Yeni sistemde DataTables AJAX (POST) endpointi kullanılıyor.
                api_url = get_keyos_login_url().replace("/login", "/computers/getDataTable")
                payload = {
                    'draw': 1,
                    'start': 0,
                    'length': 10,
                    'search[value]': serial,
                    'search[regex]': 'false'
                }
                
                resp = self.session.post(api_url, data=payload, timeout=15, verify=False)
                if resp.status_code != 200:
                    return None
                    
                json_data = resp.json()
                
                # 'data' listesi boşsa sonuç yok demektir.
                if not json_data.get('data') or len(json_data['data']) == 0:
                    return None
                    
                # Eşleşen ilk kaydı alalım. (Bazen search substring olarak çalışabilir, 
                # bu yüzden tam seri no eşleşmesini teyit etmek daha sağlıklıdır.)
                record = None
                for row in json_data['data']:
                    if str(row.get('serialNumber', '')).strip().upper() == str(serial).strip().upper():
                        record = row
                        break
                
                if not record:
                    record = json_data['data'][0] # Fallback: tam eşleşme bulamazsa ilki
                
                data = {
                    "hostname": record.get('hostName', '-').strip(),
                    "mac": record.get('ethernetMACAddress', '-').strip(),
                    "printers": record.get('printers', '-').strip(),
                    "last_update": record.get('lastUpdatedDateTime', '-').strip(),
                    "last_active": _first_value(record, ['lastActiveDateTime', 'lastSeenDateTime', 'lastUpdatedDateTime', 'updatedAt']),
                    "ip": _first_value(record, ['ethernetIPAddress', 'wifiIPAddress', 'ipAddress', 'ip', 'IPv4']),
                    "os": _first_value(record, ['operatingSystem', 'operatingSystemName', 'osName', 'os', 'keyOSVersion']),
                    "keyos_version": _first_value(record, ['keyOSVersion', 'version'])
                }
                        
                return data
            except Exception as e:
                print(f"[KeyOS] Query Error ({serial}) Attempt {attempt+1}: {e}")
                if attempt < 2:
                    time.sleep(2.0)
                    if "Connection aborted" in str(e) or "Disconnected" in str(e) or "Remote end closed" in str(e):
                        print(f"[KeyOS] Re-logging in due to connection failure...")
                        self.login()
        return None

def format_device_no(no_str):
    if not no_str: return '-'
    s = str(no_str).strip()
    if s.upper().startswith('PC-') or s.upper().startswith('PR-'):
        return s.upper()
    if s.isdigit():
        return f"PC-{int(s):03d}"
    return s.upper()

@keyos_service_bp.route('/manual_sync', methods=['POST'])
@require_auth
def sync_all():
    """Kullanıcı arayüzünden manuel tetiklenen eşitleme (Önce KeyOS, sonra DC)."""
    keyos_res = perform_keyos_sync(auto_update=True)
    
    try:
        from modules.desktop_central_service import perform_dc_sync
        dc_res = perform_dc_sync()
        dc_msg = dc_res.get('message', 'DC tamamlandı.')
    except Exception as e:
        dc_msg = f"DC hatası: {e}"
        
    try:
        if isinstance(keyos_res, dict):
            return {"success": True, "message": f"[KeyOS] {keyos_res.get('message', 'OK')} | [DC] {dc_msg}"}
        else:
            data = keyos_res.get_json()
            if data and "message" in data:
                data["message"] = f"[KeyOS] {data['message']} | [DC] {dc_msg}"
            return jsonify(data)
    except:
        return keyos_res

def perform_keyos_sync(auto_update=True):
    """Tüm envanteri KeyOS ile senkronize eder. auto_update=False ise sadece uyumsuzlukları tespit eder."""
    try:
        username = os.getenv("KEYOS_USER", "dashboard")
        password = os.getenv("KEYOS_PASS", "DashBoard2025*!")
        
        client = KeyOSClient(username, password)
        if not client.login():
            return jsonify({"success": False, "error": "KeyOS Giriş Başarısız! (Hedef sunucuya bağlanılamadı veya şifre yanlış)"})
            
        # Toplu veri çekme işlemi (Excel mantığına benzer, ancak daha hızlı JSON API)
        api_url = get_keyos_login_url().replace("/login", "/computers/getDataTable")
        payload = {
            'draw': 1,
            'start': 0,
            'length': 10000, # Bütün cihazları alabilmek için büyük bir değer
            'search[value]': '',
            'search[regex]': 'false'
        }
        
        resp = client.session.post(api_url, data=payload, timeout=30, verify=False)
        if resp.status_code != 200:
            return jsonify({"success": False, "error": "KeyOS'tan cihaz listesi çekilemedi!"})
            
        keyos_data = resp.json().get('data', [])
        
        # --- Ekstra: Manuel senkronizasyonda son aktiflik durumlarını da güncelle ---
        try:
            import datetime, json
            parsed_data = []
            for row in keyos_data:
                serial_save = str(row.get('serialNumber', '')).strip().upper()
                if serial_save and len(serial_save) > 2:
                    parsed_data.append({
                        "Seri_No": serial_save,
                        "Hostname": str(row.get('hostName', '-')).strip(),
                        "IP_Adresi": _first_value(row, ['ethernetIPAddress', 'wifiIPAddress', 'ipAddress', 'ip', 'IPv4']),
                        "MAC_Adresi": str(row.get('ethernetMACAddress', '-')).strip(),
                        "Bagli_Yazicilar": str(row.get('printers', '-')).strip(),
                        "KeyOS_Versiyon": str(row.get('keyOSVersion', '-')).strip(),
                        "Isletim_Sistemi": _first_value(row, ['operatingSystem', 'operatingSystemName', 'osName', 'os', 'keyOSVersion']),
                        "Son_Guncelleme": _first_value(row, ['lastActiveDateTime', 'lastSeenDateTime', 'lastUpdatedDateTime', 'updatedAt']),
                        "Aktif": "Evet" if str(row.get('active', '0')) == "1" else "Hayır"
                    })
            
            WEEKLY_STATUS_FILE = os.path.join(BASE_DIR, "database", "data", "keyos_weekly_status.json")
            os.makedirs(os.path.dirname(WEEKLY_STATUS_FILE), exist_ok=True)
            with open(WEEKLY_STATUS_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "last_fetch": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "total_devices": len(parsed_data),
                    "devices": parsed_data
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Manual Sync] Active status JSON save error: {e}")
        # -------------------------------------------------------------------------
        
        # KeyOS verilerini Seri No'ya göre bir sözlüğe (dictionary) aktaralım, arama anında O(1) olsun.
        keyos_dict = {}
        for row in keyos_data:
            serial = str(row.get('serialNumber', '')).strip().upper()
            if serial and len(serial) > 2:
                keyos_dict[serial] = {
                    "hostname": str(row.get('hostName', '-')).strip(),
                    "mac": str(row.get('ethernetMACAddress', '-')).strip(),
                    "printers": str(row.get('printers', '-')).strip(),
                    "ip": _first_value(row, ['ethernetIPAddress', 'wifiIPAddress', 'ipAddress', 'ip', 'IPv4']),
                    "last_active": _first_value(row, ['lastActiveDateTime', 'lastSeenDateTime', 'lastUpdatedDateTime', 'updatedAt']),
                    "os": _first_value(row, ['operatingSystem', 'operatingSystemName', 'osName', 'os', 'keyOSVersion']),
                    "keyos_version": _first_value(row, ['keyOSVersion', 'version'])
                }

        # Ensure last_active exists silently
        try:
            from modules.inventory_core import check_column_exists, _SCHEMA_CACHE
            if not check_column_exists('pcs', 'last_active'):
                try:
                    query_db("ALTER TABLE pcs ADD last_active VARCHAR(50)")
                except Exception:
                    pass
                if 'pcs' in _SCHEMA_CACHE:
                    del _SCHEMA_CACHE['pcs']
        except Exception:
            pass
        inventory = query_db("SELECT id, pc_no, pc_serial, hostname, windows, keyos, last_active FROM pcs WHERE pc_serial IS NOT NULL AND pc_serial != '-' AND TRIM(pc_serial) != ''")
        if not inventory:
            return jsonify({"message": "Sorgulanacak cihaz bulunamadı."})
            
        updated_count = 0
        mismatches = []
        successful_list = []
        failed_list = []
        
        import time
        for pc in inventory:
            seri = str(pc['pc_serial']).strip().upper()
            details = keyos_dict.get(seri)
            
            if details:
                # Update DB sadece auto_update True ise yapilir
                if auto_update:
                    _safe_update_pc_from_keyos(pc['id'], details, pc.get('last_active'))
                    updated_count += 1
                
                # Os String tespit et (rapor icin)
                win_flag, keyos_flag = _normalize_os_flags(details.get('os'), details.get('keyos_version'))
                os_str = "Bilinmiyor"
                if win_flag:
                    os_str = "Windows"
                elif keyos_flag:
                    os_str = "KeyOS/Pardus"
                    
                os_changed = False
                if win_flag is not None and keyos_flag is not None:
                    if win_flag != pc.get('windows', 0) or keyos_flag != pc.get('keyos', 0):
                        os_changed = True

                # Check Hostname mismatch
                if details['hostname'].upper() != (pc['hostname'] or '').upper():
                    mismatches.append({
                        "pc_no": format_device_no(pc['pc_no']),
                        "serial": pc['pc_serial'],
                        "ip": details['ip'],
                        "local_hostname": pc['hostname'],
                        "keyos_hostname": details['hostname']
                    })
                
                successful_list.append({
                    "pc_no": format_device_no(pc['pc_no']),
                    "serial": pc['pc_serial'],
                    "ip": details['ip'],
                    "mac": details['mac'],
                    "printers": details['printers'],
                    "os": os_str,
                    "os_changed": os_changed
                })
                updated_count += 1
            else:
                failed_list.append({
                    "pc_no": format_device_no(pc['pc_no']),
                    "serial": pc['pc_serial']
                })
                
        # Raporu diske kaydet (Son 2 raporu tut)
        report_data = {
            "id": time.time(),
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "updated_count": updated_count,
            "failed_count": len(failed_list),
            "mismatch_count": len(mismatches),
            "successful": successful_list,
            "failed": failed_list,
            "mismatches": mismatches
        }
        
        os.makedirs(os.path.join(BASE_DIR, "database", "data"), exist_ok=True)
        reports_file = os.path.join(BASE_DIR, "database", "data", "keyos_reports.json")
        
        existing_reports = []
        if os.path.exists(reports_file):
            try:
                with open(reports_file, "r", encoding="utf-8") as f:
                    existing_reports = json.load(f)
            except:
                pass
                
        existing_reports.insert(0, report_data)
        existing_reports = existing_reports[:2] # Sadece son 2 raporu tut
        
        try:
            with open(reports_file, "w", encoding="utf-8") as f:
                json.dump(existing_reports, f, ensure_ascii=False, indent=2)
        except Exception as file_e:
            print(f"Rapor kaydetme hatasi: {file_e}")

        return jsonify({
            "success": True,
            "updated": updated_count,
            "mismatches": mismatches,
            "message": f"{updated_count} cihaz güncellendi. {len(failed_list)} cihaz KeyOS'ta bulunamadı."
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@keyos_service_bp.route('/last_report', methods=['GET'])
def last_report():
    """Son çalıştırılan KeyOS senkronizasyonlarının raporlarını döner."""
    try:
        report_path = os.path.join(BASE_DIR, "database", "data", "keyos_reports.json")
        if not os.path.exists(report_path):
            # Geriye dönük uyumluluk için eski dosyayı da kontrol edelim
            old_report_path = os.path.join(BASE_DIR, "database", "data", "last_keyos_report.json")
            if os.path.exists(old_report_path):
                with open(old_report_path, "r", encoding="utf-8") as f:
                    data = [json.load(f)]
                return jsonify({"success": True, "reports": data})
                
            return jsonify({"success": False, "message": "Henüz oluşturulmuş bir rapor bulunmuyor."})
            
        with open(report_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        return jsonify({"success": True, "reports": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@keyos_service_bp.route('/check_all_mismatches', methods=['GET'])
def check_all_mismatches():
    # Return empty list for now, as mismatches are computed during sync
    return jsonify({"success": True, "mismatches": []})

@keyos_service_bp.route('/check/<serial>', methods=['GET'])
@require_auth
def check_keyos_single(serial):
    """Tekil bir seri numarasını KeyOS MGT üzerinden canlı sorgular."""
    try:
        user_id = request.current_user.get('user_id')
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT keyos_user, keyos_pass FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()

        if not row or not row[0] or not row[1]:
            return jsonify({"success": False, "error": "Lütfen profil ayarlarınızdan KeyOS MGT yetkili bilgilerinizi kaydedin."}), 400
            
        keyos_u = row[0]
        enc_pass = row[1]
        keyos_p = decrypt_password(enc_pass)

        client = KeyOSClient(keyos_u, keyos_p)
        if not client.login():
            return jsonify({"success": False, "error": "KeyOS Girişi Başarısız! Lütfen bilgilerinizi kontrol edin."}), 401
            
        data = client.query_serial(serial)
        if not data:
            return jsonify({"success": False, "error": f"'{serial}' KeyOS üzerinde bulunamadı."}), 404
            
        return jsonify({"success": True, **data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@keyos_service_bp.route('/update', methods=['POST'])
@require_auth
def update_keyos():
    """Kullanıcının kendi yetkili hesabı ile KeyOS'ta mahal ve hostname günceller."""
    try:
        data = request.json
        serial = data.get('serial')
        hostname = data.get('hostname')
        place_id_name = data.get('placeId') # Mahal ismi, örn. B-02-C1-229
        user_id = request.current_user.get('user_id')
        
        if not serial or not hostname or not place_id_name:
            return jsonify({"success": False, "error": "Seri no, hostname ve mahal bilgileri zorunludur."}), 400
            
        # 1. DB'den aktif kullanıcının KeyOS yetkilendirme bilgilerini çek
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT keyos_user, keyos_pass FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row or not row[0] or not row[1]:
            return jsonify({"success": False, "error": "Profil ayarlarınızdan KeyOS MGT kullanıcı adı ve şifrenizi kaydetmelisiniz."}), 400
            
        keyos_u = row[0]
        enc_pass = row[1]
        
        # Şifreyi çöz
        keyos_p = decrypt_password(enc_pass)
        
        # 2. KeyOS MGT Client'ı oluştur ve giriş yap
        client = KeyOSClient(keyos_u, keyos_p)
        if not client.login():
            return jsonify({"success": False, "error": "KeyOS Girişi Başarısız! Lütfen KeyOS kullanıcı bilgilerinizi kontrol edin."}), 401
            
        # 3. Tüm bilgisayar listesini çek ve seri numarasıyla yerelde eşleştir
        #    (KeyOS'un search özelliği seri numarasında çalışmıyor, bu yüzden manual_sync ile aynı yöntemi kullanıyoruz)
        api_url = get_keyos_login_url().replace("/login", "/computers/getDataTable")
        ajax_payload = {
            'draw': 1,
            'start': 0,
            'length': 10000,
            'search[value]': '',
            'search[regex]': 'false'
        }
        
        resp_ajax = client.session.post(api_url, data=ajax_payload, timeout=30, verify=False)
        if resp_ajax.status_code != 200:
            return jsonify({"success": False, "error": "KeyOS bilgisayar tablosu sorgulanamadı."}), 500
            
        res_json = resp_ajax.json()
        data_list = res_json.get('data', [])
        
        computer_id = None
        target_serial = serial.strip().upper()
        for row_c in data_list:
            row_serial = str(row_c.get('serialNumber', '')).strip().upper()
            if row_serial == target_serial:
                computer_id = row_c.get('id')
                break
        
        if not computer_id:
            return jsonify({"success": False, "error": f"'{serial}' seri numaralı cihaz KeyOS'ta bulunamadı."}), 400

        # 4. Mahal bilgisini KeyOS edit sayfasında ara (3 kez deneme)
        edit_page_url = get_keyos_login_url().replace("/login", f"/updateComputer?{computer_id}")
        place_id_val = None
        
        import time
        for attempt in range(1, 4):
            r_edit = client.session.get(edit_page_url, timeout=30, verify=False)
            if r_edit.status_code == 200:
                soup = BeautifulSoup(r_edit.text, 'html.parser')
                place_select = soup.find('select', attrs={'name': 'placeId'})
                if place_select:
                    for opt in place_select.find_all('option'):
                        val = opt.get('value')
                        text = opt.get_text(strip=True)
                        if text.strip().upper() == place_id_name.strip().upper():
                            place_id_val = val
                            break
            if place_id_val:
                break
            else:
                if attempt < 3:
                    time.sleep(2.0)
                    
        # 5. Mahal bulunamadıysa ekleme yap
        if not place_id_val:
            add_place_url = get_keyos_login_url().replace("/login", "/addPlace/add")
            add_payload = {"name": place_id_name}
            add_headers = {
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest"
            }
            body = json.dumps(add_payload)
            r_add = client.session.post(add_place_url, data=body, headers=add_headers, timeout=30, verify=False)
            
            # Eklenen mahalin ID'sini bulmak için düzenleme sayfasını tekrar sorgula
            r_edit2 = client.session.get(edit_page_url, timeout=30, verify=False)
            if r_edit2.status_code == 200:
                soup = BeautifulSoup(r_edit2.text, 'html.parser')
                place_select = soup.find('select', attrs={'name': 'placeId'})
                if place_select:
                    for opt in place_select.find_all('option'):
                        val = opt.get('value')
                        text = opt.get_text(strip=True)
                        if text.strip().upper() == place_id_name.strip().upper():
                            place_id_val = val
                            break
                            
            if not place_id_val:
                return jsonify({"success": False, "error": f"'{place_id_name}' mahali KeyOS'ta bulunamadı ve otomatik oluşturulamadı."}), 500

        # 6. Bilgisayar güncellemesini yap
        update_computer_url = get_keyos_login_url().replace("/login", "/updateComputer/update")
        update_payload = {
            "id": str(computer_id),
            "serialNumber": serial,
            "placeId": str(place_id_val),
            "hostName": hostname
        }
        update_headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest"
        }
        body_update = json.dumps(update_payload)
        r_update = client.session.post(update_computer_url, data=body_update, headers=update_headers, timeout=30, verify=False)
        
        if r_update.status_code == 200 and "success" in r_update.text:
            return jsonify({"success": True, "message": "KeyOS başarıyla güncellendi!"})
        else:
            return jsonify({"success": False, "error": f"KeyOS Güncelleme Sunucu Hatası: {r_update.text}"}), 500

    except Exception as e:
        import traceback
        print(f"[KEYOS UPDATE API ERROR] {traceback.format_exc()}")
        return jsonify({"success": False, "error": f"Güncelleme hatası: {str(e)}"}), 500


def push_hostname_to_keyos(user_id, serial, hostname, location_code):
    """
    Dahili fonksiyon: Envanter güncellemesi sırasında mahal değiştiğinde
    otomatik olarak KeyOS MGT üzerinde hostname ve mahal güncellemesi yapar.
    
    Bu fonksiyon bir HTTP endpoint değildir; inventory_core.py tarafından
    doğrudan import edilerek çağrılır.
    
    Returns: (success: bool, message: str)
    """
    import threading
    
    def _do_keyos_push(uid, ser, host, loc):
        try:
            # 1. Kullanıcının kayıtlı KeyOS bilgilerini çek
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT keyos_user, keyos_pass FROM users WHERE id = ?", (uid,))
            row = cursor.fetchone()
            conn.close()
            
            if not row or not row[0] or not row[1]:
                print(f"[KeyOS Auto-Sync] Kullanıcı #{uid} için kayıtlı KeyOS yetkisi bulunamadı. Atlanıyor.")
                return
                
            keyos_u = row[0]
            keyos_p = decrypt_password(row[1])
            
            # 2. KeyOS'a giriş yap
            client = KeyOSClient(keyos_u, keyos_p)
            if not client.login():
                print(f"[KeyOS Auto-Sync] KeyOS girişi başarısız! Kullanıcı: {keyos_u}")
                return
                
            # 3. Cihazı seri numarasıyla bul
            api_url = get_keyos_login_url().replace("/login", "/computers/getDataTable")
            ajax_payload = {
                'draw': 1, 'start': 0, 'length': 10000,
                'search[value]': '', 'search[regex]': 'false'
            }
            resp = client.session.post(api_url, data=ajax_payload, timeout=30, verify=False)
            if resp.status_code != 200:
                print(f"[KeyOS Auto-Sync] KeyOS cihaz listesi çekilemedi. HTTP {resp.status_code}")
                return
                
            data_list = resp.json().get('data', [])
            computer_id = None
            target_serial = ser.strip().upper()
            for row_c in data_list:
                if str(row_c.get('serialNumber', '')).strip().upper() == target_serial:
                    computer_id = row_c.get('id')
                    break
                    
            if not computer_id:
                print(f"[KeyOS Auto-Sync] '{ser}' seri numaralı cihaz KeyOS'ta bulunamadı.")
                return
                
            # 4. Mahal adını KeyOS formatına çevir (nokta -> tire)
            place_id_name = str(loc).replace('.', '-').strip().upper()
            
            # 5. Düzenleme sayfasından mahal ID'sini bul
            edit_url = get_keyos_login_url().replace("/login", f"/updateComputer?{computer_id}")
            place_id_val = None
            
            import time
            for attempt in range(1, 4):
                r_edit = client.session.get(edit_url, timeout=30, verify=False)
                if r_edit.status_code == 200:
                    soup = BeautifulSoup(r_edit.text, 'html.parser')
                    place_select = soup.find('select', attrs={'name': 'placeId'})
                    if place_select:
                        for opt in place_select.find_all('option'):
                            if opt.get_text(strip=True).strip().upper() == place_id_name:
                                place_id_val = opt.get('value')
                                break
                if place_id_val:
                    break
                if attempt < 3:
                    time.sleep(2.0)
                    
            # 6. Mahal yoksa oluştur
            if not place_id_val:
                add_url = get_keyos_login_url().replace("/login", "/addPlace/add")
                add_headers = {
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "X-Requested-With": "XMLHttpRequest"
                }
                client.session.post(add_url, data=json.dumps({"name": place_id_name}), headers=add_headers, timeout=30, verify=False)
                
                # Yeni mahalin ID'sini al
                r_edit2 = client.session.get(edit_url, timeout=30, verify=False)
                if r_edit2.status_code == 200:
                    soup2 = BeautifulSoup(r_edit2.text, 'html.parser')
                    ps2 = soup2.find('select', attrs={'name': 'placeId'})
                    if ps2:
                        for opt in ps2.find_all('option'):
                            if opt.get_text(strip=True).strip().upper() == place_id_name:
                                place_id_val = opt.get('value')
                                break
                                
            if not place_id_val:
                print(f"[KeyOS Auto-Sync] '{place_id_name}' mahali KeyOS'ta bulunamadı/oluşturulamadı.")
                return
                
            # 7. Güncellemeyi gönder
            update_url = get_keyos_login_url().replace("/login", "/updateComputer/update")
            update_payload = {
                "id": str(computer_id),
                "serialNumber": ser,
                "placeId": str(place_id_val),
                "hostName": host
            }
            update_headers = {
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest"
            }
            r_update = client.session.post(update_url, data=json.dumps(update_payload), headers=update_headers, timeout=30, verify=False)
            
            if r_update.status_code == 200 and "success" in r_update.text:
                print(f"[KeyOS Auto-Sync] BAŞARILI: {ser} -> Hostname: {host}, Mahal: {place_id_name}")
            else:
                print(f"[KeyOS Auto-Sync] BAŞARISIZ: {ser} -> {r_update.text}")
                
        except Exception as ex:
            print(f"[KeyOS Auto-Sync] HATA: {ex}")
    
    # Arka planda çalıştır - kullanıcıyı bekletme
    t = threading.Thread(target=_do_keyos_push, args=(user_id, serial, hostname, location_code), daemon=True)
    t.start()
    print(f"[KeyOS Auto-Sync] Arka plan görevi başlatıldı: {serial} -> {hostname}")
    return True, "KeyOS güncelleme görevi arka planda başlatıldı."


@keyos_service_bp.route('/bulk_update', methods=['POST'])
@require_auth
def bulk_update_keyos():
    """Toplu hostname güncelleme: KeyOS'a 1 kez bağlanır, listeyi 1 kez çeker, tüm güncellemeleri sırayla yapar."""
    try:
        data = request.json
        items = data.get('items', [])  # [{serial, hostname, placeId}, ...]
        
        if not items:
            return jsonify({"success": False, "error": "Güncellenecek cihaz listesi boş."}), 400
        
        user_id = request.current_user.get('user_id')
        
        # 1. DB'den aktif kullanıcının KeyOS yetkilendirme bilgilerini çek
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT keyos_user, keyos_pass FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row or not row[0] or not row[1]:
            return jsonify({"success": False, "error": "Profil ayarlarınızdan KeyOS MGT kullanıcı adı ve şifrenizi kaydetmelisiniz."}), 400
        
        keyos_u = row[0]
        keyos_p = decrypt_password(row[1])
        
        # 2. KeyOS'a giriş yap
        client = KeyOSClient(keyos_u, keyos_p)
        if not client.login():
            return jsonify({"success": False, "error": "KeyOS Girişi Başarısız!"}), 401
        
        # 3. Tüm bilgisayar listesini BİR KEZ çek
        api_url = get_keyos_login_url().replace("/login", "/computers/getDataTable")
        resp_all = client.session.post(api_url, data={
            'draw': 1, 'start': 0, 'length': 10000,
            'search[value]': '', 'search[regex]': 'false'
        }, timeout=60, verify=False)
        
        if resp_all.status_code != 200:
            return jsonify({"success": False, "error": "KeyOS bilgisayar tablosu çekilemedi."}), 500
        
        all_computers = resp_all.json().get('data', [])
        
        # Seri no → ID sözlüğü oluştur
        serial_to_id = {}
        for comp in all_computers:
            s = str(comp.get('serialNumber', '')).strip().upper()
            if s and len(s) > 2:
                serial_to_id[s] = comp.get('id')
        
        # 4. Mahal cache'i (aynı mahali tekrar tekrar aramayı engellemek için)
        place_cache = {}
        
        results = []
        import time
        
        for item in items:
            serial = item.get('serial', '').strip()
            hostname = item.get('hostname', '').strip()
            place_id_name = item.get('placeId', '').strip()
            print(f"[KeyOS Bulk Update] İşleniyor: {serial} -> Hostname: {hostname}, Mahal: {place_id_name}")
            
            if not serial or not hostname:
                results.append({"serial": serial, "success": False, "error": "Eksik veri"})
                continue
            
            computer_id = serial_to_id.get(serial.upper())
            if not computer_id:
                results.append({"serial": serial, "success": False, "error": "KeyOS'ta bulunamadı"})
                continue
            
            try:
                # Mahal ID'sini bul veya oluştur
                place_id_val = place_cache.get(place_id_name.upper()) if place_id_name else None
                
                if place_id_name and not place_id_val:
                    edit_page_url = get_keyos_login_url().replace("/login", f"/updateComputer?{computer_id}")
                    r_edit = client.session.get(edit_page_url, timeout=30, verify=False)
                    if r_edit.status_code == 200:
                        soup = BeautifulSoup(r_edit.text, 'html.parser')
                        place_select = soup.find('select', attrs={'name': 'placeId'})
                        if place_select:
                            for opt in place_select.find_all('option'):
                                val = opt.get('value')
                                text = opt.get_text(strip=True)
                                if text.strip().upper() == place_id_name.strip().upper():
                                    place_id_val = val
                                    place_cache[place_id_name.upper()] = val
                                    break
                
                # Güncelleme yap
                update_url = get_keyos_login_url().replace("/login", "/updateComputer/update")
                update_payload = {
                    "id": str(computer_id),
                    "serialNumber": serial,
                    "hostName": hostname
                }
                if place_id_val:
                    update_payload["placeId"] = str(place_id_val)
                
                update_headers = {
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "X-Requested-With": "XMLHttpRequest"
                }
                r_update = client.session.post(update_url, data=json.dumps(update_payload), headers=update_headers, timeout=30, verify=False)
                
                if r_update.status_code == 200 and "success" in r_update.text:
                    results.append({"serial": serial, "success": True})
                    print(f"  [+] BAŞARILI: {serial}")
                else:
                    results.append({"serial": serial, "success": False, "error": f"Sunucu yanıtı: {r_update.status_code}"})
                    print(f"  [-] HATA ({serial}): Sunucu yanıtı {r_update.status_code}")
                    
            except Exception as item_err:
                results.append({"serial": serial, "success": False, "error": str(item_err)})
                print(f"  [!] EXCEPTION ({serial}): {str(item_err)}")
            
            time.sleep(0.5)  # KeyOS'u boğmamak için kısa bekleme
        
        success_count = sum(1 for r in results if r['success'])
        fail_count = len(results) - success_count
        
        return jsonify({
            "success": True,
            "message": f"{success_count} cihaz güncellendi, {fail_count} başarısız.",
            "results": results,
            "updated": success_count,
            "failed": fail_count
        })
        
    except Exception as e:
        import traceback
        print(f"[KEYOS BULK UPDATE ERROR] {traceback.format_exc()}")
        return jsonify({"success": False, "error": f"Toplu güncelleme hatası: {str(e)}"}), 500

import datetime
import pandas as pd
from flask import send_file
from io import BytesIO

WEEKLY_STATUS_FILE = os.path.join(BASE_DIR, "database", "data", "keyos_weekly_status.json")

def fetch_keyos_weekly_status():
    """Arka planda çalışacak: KeyOS'tan tüm cihazları çekip JSON'a kaydeder."""
    print(f"[{datetime.datetime.now()}] [APScheduler] KeyOS haftalık durumu güncelleniyor...")
    try:
        username = os.getenv("KEYOS_USER", "dashboard")
        password = os.getenv("KEYOS_PASS", "DashBoard2025*!")
        
        client = KeyOSClient(username, password)
        if not client.login():
            print("[APScheduler] KeyOS Giriş Başarısız!")
            return False
            
        api_url = get_keyos_login_url().replace("/login", "/computers/getDataTable")
        payload = {
            'draw': 1, 'start': 0, 'length': 10000,
            'search[value]': '', 'search[regex]': 'false'
        }
        
        resp = client.session.post(api_url, data=payload, timeout=60, verify=False)
        if resp.status_code != 200:
            print("[APScheduler] KeyOS cihaz listesi çekilemedi!")
            return False
            
        keyos_data = resp.json().get('data', [])
        
        parsed_data = []
        for row in keyos_data:
            serial = str(row.get('serialNumber', '')).strip().upper()
            if serial and len(serial) > 2:
                parsed_data.append({
                    "Seri_No": serial,
                    "Hostname": str(row.get('hostName', '-')).strip(),
                    "IP_Adresi": _first_value(row, ['ethernetIPAddress', 'wifiIPAddress', 'ipAddress', 'ip', 'IPv4']),
                    "MAC_Adresi": str(row.get('ethernetMACAddress', '-')).strip(),
                    "Bagli_Yazicilar": str(row.get('printers', '-')).strip(),
                    "KeyOS_Versiyon": str(row.get('keyOSVersion', '-')).strip(),
                    "Son_Guncelleme": str(row.get('lastUpdatedDateTime', '-')).strip(),
                    "Aktif": "Evet" if str(row.get('active', '0')) == "1" else "Hayır"
                })
                
        os.makedirs(os.path.join(BASE_DIR, "database", "data"), exist_ok=True)
        with open(WEEKLY_STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "last_fetch": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_devices": len(parsed_data),
                "devices": parsed_data
            }, f, ensure_ascii=False, indent=2)
            
        print(f"[{datetime.datetime.now()}] [APScheduler] KeyOS haftalık durumu başarıyla {len(parsed_data)} cihaz için kaydedildi.")
        return True
    except Exception as e:
        print(f"[{datetime.datetime.now()}] [APScheduler] KeyOS fetch hatası: {e}")
        return False

@keyos_service_bp.route('/force_weekly_sync', methods=['POST'])
@require_admin
def force_weekly_sync():
    """Kullanıcının butona basarak anında senkronizasyonu tetiklemesini sağlar."""
    success = fetch_keyos_weekly_status()
    if success:
        return jsonify({"success": True, "message": "KeyOS durumu başarıyla güncellendi."})
    else:
        return jsonify({"success": False, "error": "KeyOS durumu güncellenirken bir hata oluştu."}), 500

@keyos_service_bp.route('/weekly_excel', methods=['GET'])
@require_admin
def get_weekly_excel():
    """Kaydedilmiş JSON'u okuyup Excel olarak döndürür."""
    try:
        if not os.path.exists(WEEKLY_STATUS_FILE):
            return jsonify({"success": False, "error": "Henüz oluşturulmuş bir rapor yok. Lütfen 'Şimdi Çek' butonuna tıklayın."}), 404
            
        with open(WEEKLY_STATUS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        devices = data.get("devices", [])
        
        dc_data = {}
        try:
            from modules.desktop_central_service import scrape_desktop_central_computers
            dc_data = scrape_desktop_central_computers() or {}
            print(f"[EXCEL] DC'den {len(dc_data)} cihaz cekildi.")
        except Exception as dc_err:
            print(f"[EXCEL DC ERROR] {dc_err}")
        
        try:
            from core.database_sql import query_db
            db_pcs = query_db("""
                SELECT p.pc_no, p.hostname, p.ip, p.mac, p.pc_serial, p.last_active, 
                       p.windows, p.keyos, p.connected_printers, m.location_name 
                FROM pcs p 
                LEFT JOIN mahal_list m ON p.location_code = m.location_code 
                WHERE p.is_deleted = 0 OR p.is_deleted IS NULL
            """) or []
            
            # KeyOS cihazlarını DB verileriyle zenginleştir
            for d in devices:
                serial = str(d.get("Seri_No", "")).strip().upper()
                mac = str(d.get("MAC_Adresi", "")).strip().upper()
                
                db_pc = None
                if serial and serial != "-":
                    db_pc = next((pc for pc in db_pcs if str(pc.get("pc_serial", "")).strip().upper() == serial), None)
                if not db_pc and mac and mac != "-":
                    db_pc = next((pc for pc in db_pcs if str(pc.get("mac", "")).strip().upper() == mac), None)
                
                pc_no_str = ""
                mahal_str = ""
                hostname_str = str(d.get("Hostname", "-")).strip()
                
                if db_pc:
                    raw_pc_no = str(db_pc.get("pc_no") or "").strip()
                    if raw_pc_no.isdigit():
                        pc_no_str = f"PC-{raw_pc_no.zfill(3)}"
                    elif raw_pc_no:
                        pc_no_str = raw_pc_no.upper()
                        
                    mahal_str = str(db_pc.get("location_name") or "-").strip()
                    if hostname_str == "-" and db_pc.get("hostname"):
                        hostname_str = str(db_pc.get("hostname")).strip()
                        
                    db_pc["_processed"] = True
                
                d["PC NO"] = pc_no_str
                d["MAHAL"] = mahal_str
                d["Hostname"] = hostname_str
                d["KEYOS Son_Guncelleme"] = d.get("Son_Guncelleme", "-")
                
                # Desktop Central aktiflik bilgisini JSON'dan al
                ip_adresi = str(d.get("IP_Adresi", "")).strip()
                if ip_adresi in dc_data:
                    d["Desktop_Central_Aktiflik"] = dc_data[ip_adresi].get("last_contact", "-")
                else:
                    d["Desktop_Central_Aktiflik"] = "-"
                
            # İşlenmemiş Windows makinelerini (DC) ekle
            for pc in db_pcs:
                if not pc.get("_processed") and pc.get("windows") == 1:
                    raw_pc_no = str(pc.get("pc_no") or "").strip()
                    pc_no_str = ""
                    if raw_pc_no.isdigit():
                        pc_no_str = f"PC-{raw_pc_no.zfill(3)}"
                    elif raw_pc_no:
                        pc_no_str = raw_pc_no.upper()
                        
                    devices.append({
                        "PC NO": pc_no_str,
                        "MAHAL": str(pc.get("location_name") or "-").strip(),
                        "Hostname": str(pc.get("hostname") or "-").strip(),
                        "Seri_No": str(pc.get("pc_serial") or "-").strip(),
                        "IP_Adresi": str(pc.get("ip") or "-").strip(),
                        "MAC_Adresi": str(pc.get("mac") or "-").strip(),
                        "KEYOS Son_Guncelleme": "-",
                        "Desktop_Central_Aktiflik": dc_data.get(str(pc.get("ip") or "").strip(), {}).get("last_contact", str(pc.get("last_active") or "-")).strip(),
                        "Aktif": "-",
                        "KeyOS_Versiyon": "-",
                        "Bagli_Yazicilar": str(pc.get("connected_printers") or "-").strip()
                    })
                    
        except Exception as db_err:
            print(f"[EXCEL DB ERROR] {db_err}")

        if not devices:
            return jsonify({"success": False, "error": "Raporda cihaz bulunamadı."}), 404
            
        df = pd.DataFrame(devices)
        
        # Excel sütun sıralamasını ayarla
        columns_order = [
            "PC NO", "MAHAL", "Hostname", "Seri_No", "IP_Adresi", "MAC_Adresi", 
            "KEYOS Son_Guncelleme", "Desktop_Central_Aktiflik", "Aktif", "KeyOS_Versiyon", "Bagli_Yazicilar"
        ]
        
        # Eksik sütun varsa tamamla (hata vermemesi için)
        for col in columns_order:
            if col not in df.columns:
                df[col] = "-"
                
        df = df[columns_order]
        
        # Excel'i hafızada oluştur
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='KeyOS ve DC Cihazlar', index=False)
            
            # Sütun genişliklerini ayarla (opsiyonel)
            worksheet = writer.sheets['KeyOS ve DC Cihazlar']
            worksheet.set_column('A:A', 15)  # PC NO
            worksheet.set_column('B:B', 30)  # MAHAL
            worksheet.set_column('C:C', 20)  # Hostname
            worksheet.set_column('D:D', 15)  # Seri No
            worksheet.set_column('E:F', 18)  # IP / MAC
            worksheet.set_column('G:G', 22)  # KEYOS Son Guncelleme
            worksheet.set_column('H:H', 25)  # DC Aktiflik
            worksheet.set_column('I:I', 10)  # Aktif
            worksheet.set_column('J:K', 20)  # Versiyon / Yazıcılar
            
        output.seek(0)
        
        date_str = data.get('last_fetch', '').replace(':', '').replace(' ', '_')
        filename = f"KeyOS_Durum_Raporu_{date_str}.xlsx"
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        print(f"[EXCEL GENERATION ERROR] {e}")
        return jsonify({"success": False, "error": f"Excel oluşturulurken hata oluştu: {str(e)}"}), 500
