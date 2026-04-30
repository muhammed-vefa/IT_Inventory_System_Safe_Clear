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

def get_keyos_session(username, password):
    """KeyOS sistemine giriş yapıp bir session döndürür."""
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    if not username or username == 'dashboard_placeholder': 
        return None

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    
    try:
        # 1. Giriş sayfasını aç
        resp = session.get(LOGIN_URL, timeout=15, verify=False)
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        csrf_token = ""
        token_meta = soup.find('meta', {'name': 'csrf-token'})
        if token_meta: csrf_token = token_meta['content']
        token_input = soup.find('input', {'name': '_token'})
        if token_input: csrf_token = token_input.get('value', '')
        
        # 2. Login form'u POST et
        data = { "userName": username, "password": password }
        if csrf_token: data["_token"] = csrf_token
        
        login_post_url = BASE_URL + "/"
        login_resp = session.post(login_post_url, data=data, timeout=15, verify=False, allow_redirects=True)
        
        final_url = login_resp.url.lower()
        response_text = login_resp.text.lower()
        
        # Login başarı kontrolü
        login_failed = (
            '/login' in final_url or
            ('kullanıcı adı' in response_text and 'şifre' in response_text)
        )
        
        if login_resp.status_code in [200, 302] and not login_failed:
            return session
        else:
            print(f"KeyOS Login failed for {username}. Status: {login_resp.status_code}")
    except Exception as e:
        pass # Sessiz hata
    return None

@keyos_service_bp.route('/check/<serial>', methods=['GET'])
@require_auth
@limiter.limit("10 per minute")
def check_device(serial):
    """Seri no ile KeyOS'tan cihaz bilgilerini çeker."""
    session = get_keyos_session(os.getenv('KEYOS_USER'), os.getenv('KEYOS_PASS'))
    if not session:
        return jsonify({"error": "KeyOS sistemine giriş yapılamadı."}), 401
    
    try:
        # Search for device
        # The site might use a query param like ?search=... or we might need to scrape the table
        # Based on subagent, searching is usually dynamic. We'll try searching via query param first
        resp = session.get(f"{COMPUTERS_URL}?search={serial}", timeout=30, verify=False)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Find the row with the serial
        table = soup.find('table')
        if not table:
            return jsonify({"error": "Cihaz listesi tablosu bulunamadı."}), 404
            
        rows = table.find_all('tr')[1:] # Skip header
        target_row = None
        for row in rows:
            if serial.upper() in row.get_text().upper():
                target_row = row
                break
        
        if not target_row:
            return jsonify({"error": "Cihaz KeyOS sisteminde bulunamadı."}), 404
            
        cols = target_row.find_all('td')
        # Structure based on subagent:
        # Col 0: Index/Checkbox
        # Col 1: Hostname
        # Col 2: Brand/Model
        # Col 3: Serial
        # Col 4: Version
        # Col 5: Connected Printers
        # Col 6: IP Address
        
        hostname = cols[1].get_text(strip=True) if len(cols) > 1 else ""
        printers = cols[5].get_text(strip=True) if len(cols) > 5 else ""
        ip_address = cols[6].get_text(strip=True) if len(cols) > 6 else ""
        
        return jsonify({
            "success": True,
            "hostname": hostname,
            "ip": ip_address,
            "printers": printers,
            "serial": serial
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
        
    session = get_keyos_session(admin_user, admin_pass)
    if not session:
        return jsonify({"error": "Yetkili girişi başarısız (KeyOS)."}), 401
        
    try:
        # 1. Find internal ID for the device
        resp = session.get(f"{COMPUTERS_URL}?search={serial}", timeout=30, verify=False)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Look for update link
        edit_link = soup.find('a', href=re.compile(r'updateComputer\?ID='))
        if not edit_link:
            return jsonify({"error": "Düzenleme bağlantısı bulunamadı. Yetkiniz olmayabilir."}), 403
            
        id_match = re.search(r'ID=(\d+)', edit_link['href'])
        if not id_match:
            return jsonify({"error": "Cihaz ID'si ayrıştırılamadı."}), 500
            
        device_id = id_match.group(1)
        
        # 2. Submit update
        # We might need to get the edit page first for more fields or CSRF
        edit_page = session.get(f"{UPDATE_URL}?ID={device_id}", verify=False, timeout=15)
        edit_soup = BeautifulSoup(edit_page.text, 'html.parser')
        
        # Prepare payload - some fields might be hidden or required
        payload = {
            "ID": device_id,
            "hostname": new_hostname,
            "placeId": new_place_id
        }
        
        # Extract existing hidden fields if any
        for hidden in edit_soup.find_all('input', type='hidden'):
            if hidden.get('name') and hidden.get('name') not in payload:
                payload[hidden['name']] = hidden.get('value', '')
        
        # KeyOS uses placeId as a select. We need the ID, not just the name.
        # But if the user provides the tire format ID (e.g. 102), we use that.
        # If they provide the string, we might need to find it in the options.
        
        post_resp = session.post(UPDATE_URL, data=payload, verify=False, timeout=20)
        
        if post_resp.status_code == 200:
            return jsonify({"success": True, "message": "KeyOS güncellemesi başarılı."})
        else:
            return jsonify({"error": f"Güncelleme sırasında hata oluştu: {post_resp.status_code}"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
