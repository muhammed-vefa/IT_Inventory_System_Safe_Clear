from flask import Blueprint, request, jsonify
import requests
from bs4 import BeautifulSoup
import re
import os
from core.extensions import limiter

keyos_service_bp = Blueprint('keyos_service', __name__)
from core.auth import require_auth, require_admin

BASE_URL = os.getenv('KEYOS_URL', 'https://keyosmgt.kocaelish.com')
LOGIN_URL = f"{BASE_URL}/login"
COMPUTERS_URL = f"{BASE_URL}/computers"
UPDATE_URL = f"{BASE_URL}/updateComputer"

import time

# Global Session Cache
_active_sessions = {} # {username: {'session': session, 'last_activity': timestamp}}

def is_session_valid(session):
    """Oturumun hala geçerli olup olmadığını basit bir istek ile kontrol eder."""
    try:
        # Ana sayfayı veya basit bir sayfayı çekerek kontrol et
        resp = session.get(BASE_URL + "/", timeout=5, verify=False, allow_redirects=False)
        return resp.status_code == 200
    except Exception:
        return False

def get_keyos_session(username, password):
    """KeyOS sistemine giriş yapıp bir session döndürür. Varsa önbellekteki oturumu kullanır."""
    global _active_sessions
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    if not username or username == 'dashboard_placeholder': 
        return None

    # 1. Önbellekte geçerli bir oturum var mı kontrol et
    now = time.time()
    if username in _active_sessions:
        cached = _active_sessions[username]
        # Eğer son işlem 10 dakikadan yeniyse, oturumu doğrula ve kullan
        if now - cached['last_activity'] < 600: 
            if is_session_valid(cached['session']):
                cached['last_activity'] = now # Aktivite zamanını güncelle
                return cached['session']

    # 2. Yeni oturum oluştur ve giriş yap
    session = requests.Session()
    
    # Retry strategy for network resiliency
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    retry_strategy = Retry(
        total=3,
        status_forcelist=[429, 500, 502, 503, 504],
        backoff_factor=1,
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    
    try:
        # Giriş sayfasını aç
        try:
            resp = session.get(LOGIN_URL, timeout=45, verify=False)
        except requests.exceptions.RequestException as e:
            print(f"KeyOS Connection Error (GET Login): {str(e)}")
            return None
        soup = BeautifulSoup(resp.text, 'html.parser')
        csrf_token = ""
        token_meta = soup.find('meta', {'name': 'csrf-token'})
        if token_meta: csrf_token = token_meta['content']
        token_input = soup.find('input', {'name': '_token'})
        if token_input: csrf_token = token_input.get('value', '')
        
        # Login form'unu bul ve action'ı al
        form = soup.find('form')
        # Subagent bulgusu: Gerçek login endpoint'i /login/login
        login_post_url = f"{BASE_URL}/login/login"
            
        # Login form'u JSON POST et (Subagent bulgusu: AJAX/JSON kullanılıyor)
        json_data = { "userName": username, "password": password }
        
        headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/json',
            'Accept': 'application/json, text/javascript, */*; q=0.01'
        }
        
        try:
            login_resp = session.post(login_post_url, json=json_data, headers=headers, timeout=45, verify=False, allow_redirects=True)
        except requests.exceptions.RequestException as e:
            print(f"KeyOS Connection Error (POST Login): {str(e)}")
            return None
        
        final_url = login_resp.url.lower()
        # AJAX yanıtı genellikle JSON döner
        try:
            response_json = login_resp.json()
            is_success = response_json.get('type') == 'success'
        except:
            is_success = False
            response_text = login_resp.text.lower()
            
        login_failed = not is_success
        
        if login_resp.status_code in [200, 302] and not login_failed:
            # Oturumu önbelleğe al
            _active_sessions[username] = {'session': session, 'last_activity': time.time()}
            return session
        else:
            reason = "Bilinmeyen hata"
            if login_failed:
                reason = "Kullanıcı adı veya şifre hatalı (Giriş sayfası tekrar yüklendi)"
            elif login_resp.status_code != 200:
                reason = f"HTTP Hatası: {login_resp.status_code}"
            
            print(f"DEBUG: KeyOS Login failed for {username}. Reason: {reason}")
            # Hata bilgisini logs/keyos_error.log dosyasına yaz (Son yanıtın bir kısmını kaydet)
            try:
                with open('logs/keyos_error.log', 'w', encoding='utf-8') as f:
                    f.write(f"Time: {time.ctime()}\n")
                    f.write(f"User: {username}\n")
                    f.write(f"Status: {login_resp.status_code}\n")
                    f.write(f"URL: {login_resp.url}\n")
                    f.write(f"Reason: {reason}\n")
                    f.write("-" * 20 + " RESPONSE START " + "-" * 20 + "\n")
                    f.write(login_resp.text[:2000]) # İlk 2000 karakter
            except: pass
    except Exception as e:
        print(f"KeyOS Session Error: {str(e)}")
    
    return None

@keyos_service_bp.route('/check/<serial>', methods=['GET'])
@require_auth
@limiter.limit("10 per minute")
def check_device(serial):
    """Flask rotası: Seri no ile KeyOS'tan cihaz bilgilerini çeker."""
    success, data = check_device_internal(serial)
    if success:
        return jsonify(data)
    else:
        status_code = 404 if "bulunamadı" in data.get("error", "").lower() else 500
        return jsonify(data), status_code

def check_device_internal(serial):
    """Dahili Fonksiyon: Seri no ile KeyOS'tan cihaz bilgilerini çeker (Session destekli)."""
    session = get_keyos_session(os.getenv('KEYOS_USER'), os.getenv('KEYOS_PASS'))
    if not session:
        return False, {"error": "KeyOS sistemine giriş yapılamadı."}
    
    try:
        # Cihaz arama
        resp = session.get(f"{COMPUTERS_URL}?search={serial}", timeout=30, verify=False)
        if resp.status_code != 200:
            return False, {"error": f"KeyOS HTTP Hatası: {resp.status_code}"}
            
        soup = BeautifulSoup(resp.text, 'html.parser')
        table = soup.find('table')
        if not table:
            return False, {"error": "Cihaz listesi tablosu bulunamadı."}
            
        rows = table.find_all('tr')[1:]
        target_row = None
        for row in rows:
            if serial.upper() in row.get_text().upper():
                target_row = row
                break
        
        if not target_row:
            return False, {"error": "Cihaz KeyOS sisteminde bulunamadı."}
            
        cols = target_row.find_all('td')
        hostname = cols[1].get_text(strip=True) if len(cols) > 1 else ""
        printers = cols[5].get_text(strip=True) if len(cols) > 5 else ""
        ip_address = cols[6].get_text(strip=True) if len(cols) > 6 else ""
        
        return True, {
            "success": True,
            "hostname": hostname,
            "ip": ip_address,
            "printers": printers,
            "serial": serial
        }
        
    except Exception as e:
        return False, {"error": str(e)}

@keyos_service_bp.route('/update', methods=['POST'])
@require_admin
def update_device():
    """KeyOS üzerindeki cihaz bilgilerini günceller."""
    data = request.json
    serial = data.get('serial')
    new_hostname = data.get('hostname')
    new_place_id = data.get('placeId') # Format: B-02-C1-229
    
    # Auth for update
    admin_user = data.get('keyos_user')
    admin_pass = data.get('keyos_pass')
    
    if not all([serial, admin_user, admin_pass]):
        return jsonify({"error": "Seri no, kullanıcı adı ve şifre zorunludur."}), 400
        
    success, result = update_device_internal(serial, new_hostname, new_place_id, admin_user, admin_pass)
    if success:
        return jsonify({"success": True, "message": result})
    else:
        return jsonify({"error": result}), 500

def update_device_internal(serial, new_hostname, new_place_id, admin_user, admin_pass):
    """KeyOS üzerindeki cihaz bilgilerini günceller (Internal use)."""
    session = get_keyos_session(admin_user, admin_pass)
    if not session:
        return False, "Yetkili girişi başarısız (KeyOS)."
        
    try:
        # 1. Find internal ID for the device
        resp = session.get(f"{COMPUTERS_URL}?search={serial}", timeout=30, verify=False)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Look for update link
        edit_link = soup.find('a', href=re.compile(r'updateComputer\?ID='))
        if not edit_link:
            return False, "Düzenleme bağlantısı bulunamadı. Yetkiniz olmayabilir."
            
        id_match = re.search(r'ID=(\d+)', edit_link['href'])
        if not id_match:
            return False, "Cihaz ID'si ayrıştırılamadı."
            
        device_id = id_match.group(1)
        
        # 2. Submit update
        edit_page = session.get(f"{UPDATE_URL}?ID={device_id}", verify=False, timeout=30)
        edit_soup = BeautifulSoup(edit_page.text, 'html.parser')
        
        payload = {
            "ID": device_id,
            "hostname": new_hostname,
            "placeId": new_place_id
        }
        
        for hidden in edit_soup.find_all('input', type='hidden'):
            if hidden.get('name') and hidden.get('name') not in payload:
                payload[hidden['name']] = hidden.get('value', '')
        
        post_resp = session.post(UPDATE_URL, data=payload, verify=False, timeout=20)
        
        if post_resp.status_code == 200:
            return True, "KeyOS güncellemesi başarılı."
        else:
            return False, f"Güncelleme hatası: {post_resp.status_code}"
            
    except Exception as e:
        return False, str(e)

def get_all_mismatches_internal():
    """Envanterdeki cihazlar ile KeyOS'u karşılaştırır ve listeyi döner."""
    from core.database_sql import query_db
    
    try:
        pcs = query_db("SELECT id, pc_no, hostname, pc_seri FROM inventory WHERE sahada=1")
        session = get_keyos_session(os.getenv('KEYOS_USER'), os.getenv('KEYOS_PASS'))
        if not session:
            return None, "KeyOS Login failed"
            
        mismatches = []
        resp = session.get(f"{COMPUTERS_URL}?limit=5000", timeout=60, verify=False)
        soup = BeautifulSoup(resp.text, 'html.parser')
        table = soup.find('table')
        if not table:
            return None, "KeyOS table not found"
            
        keyos_data = {}
        rows = table.find_all('tr')[1:]
        for row in rows:
            cols = row.find_all('td')
            if len(cols) > 6:
                k_hostname = cols[1].get_text(strip=True)
                k_serial = cols[3].get_text(strip=True).upper()
                k_ip = cols[6].get_text(strip=True)
                keyos_data[k_serial] = {"hostname": k_hostname, "ip": k_ip}
        
        for pc in pcs:
            serial = (pc['pc_seri'] or '').strip().upper()
            if not serial: continue
            
            if serial in keyos_data:
                k_info = keyos_data[serial]
                if k_info['hostname'].upper() != (pc['hostname'] or '').strip().upper():
                    mismatches.append({
                        "id": pc['id'],
                        "pc_no": pc['pc_no'],
                        "inv_hostname": pc['hostname'],
                        "keyos_hostname": k_info['hostname'],
                        "ip": k_info['ip']
                    })
        
        return mismatches, None
    except Exception as e:
        return None, str(e)

@keyos_service_bp.route('/check_all_mismatches', methods=['GET'])
@require_admin
def check_all_mismatches():
    """Envanterdeki cihazlar ile KeyOS'u karşılaştırır."""
    mismatches, error = get_all_mismatches_internal()
    if error:
        return jsonify({"error": error}), 500
    return jsonify({"success": True, "mismatches": mismatches})

@keyos_service_bp.route('/manual_sync', methods=['POST'])
@require_admin
def manual_sync():
    """Admin tarafından tetiklenen manuel KeyOS senkronizasyonu."""
    print("Manual KeyOS Sync Started...")
    try:
        mismatches, error = get_all_mismatches_internal()
        if error:
            print(f"Manual Sync Error: {error}")
            return jsonify({"error": error}), 400 # Return 400 instead of 500 for expected errors
        
        print(f"Manual Sync Completed: Found {len(mismatches)} mismatches")
        return jsonify({"success": True, "count": len(mismatches), "mismatches": mismatches})
    except Exception as e:
        import traceback
        print(f"CRITICAL ERROR in manual_sync: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": f"Sistem Hatası: {str(e)}"}), 500
