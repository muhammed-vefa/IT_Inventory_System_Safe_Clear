from core.integrations import get_integration_config
from flask import Blueprint, jsonify, request
import requests
import os
from core.auth import require_editor

bim_service_bp = Blueprint('bim_service', __name__)

@bim_service_bp.route('/client_ip', methods=['GET'])
def get_client_ip():
    # Proxy varsa X-Forwarded-For kontrol et
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ',' in ip: ip = ip.split(',')[0].strip()
    return jsonify({"ip": ip})

@bim_service_bp.route('/run_command', methods=['POST'])
@require_editor
def run_command():
    try:
        data = request.json or {}
        target_ip = data.get('ip')
        command = data.get('command')
        username = data.get('username')
        password = data.get('password')

        # Eger username veya password bos gelirse DB'den kullanicinin kayitli bilgilerini cek
        if not username or not password or password == '********':
            user_id = request.current_user.get('user_id')
            if user_id:
                from core.database_sql import get_db_connection
                from core.encryption import decrypt_password
                conn = get_db_connection()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT bim_user, bim_pass FROM users WHERE id = ?", (user_id,))
                    row = cursor.fetchone()
                    conn.close()
                    if row:
                        if not username:
                            username = row[0]
                        if not password or password == '********':
                            if row[1]:
                                password = decrypt_password(row[1])

        if not target_ip or not command:
            return jsonify({"error": "IP ve Komut zorunludur."}), 400

        if not username or not password:
            return jsonify({"error": "BİM kullanıcı adı ve şifresi bulunamadı. Lütfen profilinizden kaydedin."}), 400

        bim_config = get_integration_config('BIM') or {}
        bim_base_url = bim_config.get('base_url', 'http://bim.kocaelish.com').rstrip('/')
        
        # 1. Login (Web arayüzünü taklit et)
        login_data = {
            "Functions": "Login",
            "UserName": username,
            "Password": password
        }
        
        base_url = os.getenv("BIM_API_URL", f"{bim_base_url}/Handler.ashx")
        
        # Tarayıcı gibi davranması için header ekleyelim (Bot korumasını aşmak için)
        browser_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            "Referer": os.getenv("BIM_REFERER", f"{bim_base_url}/"),
            "Origin": os.getenv("BIM_ORIGIN", bim_base_url),
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Forwarded-For": target_ip,
            "Client-IP": target_ip
        }
        
        import urllib.parse
        encoded_login_data = urllib.parse.urlencode(login_data)
        
        session = requests.Session()
        login_resp = session.post(base_url, data=encoded_login_data, headers=browser_headers, timeout=10, verify=False)
        
        if login_resp.status_code != 200 or login_resp.text.strip() == "Error" or not login_resp.text.strip():
            # Kullanıcıya daha net bir hata verelim
            return jsonify({"error": f"BIM sitesi giriş bilgilerinizi reddetti. Lütfen Kullanıcı Adı veya Şifrenizi kontrol edin. (Sunucu Yanıtı: {login_resp.text.strip()})"}), 401
            
        ipa_session = login_resp.text.strip()
        
        # 2. Komutu eşleştir ve gönder
        func = data.get('function')  # AddPrinter, RemovePrinter vb.
        cmd_lower = str(command).lower()
        
        post_data = {}
        # Browser headers to bypass any new WAF or basic protections
        headers = {
            "User-Agent": browser_headers["User-Agent"],
            "Referer": browser_headers["Referer"],
            "Origin": browser_headers["Origin"],
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Forwarded-For": target_ip,
            "Client-IP": target_ip
        }
        
        if func in ["AddPrinter", "RemovePrinter"]:
            # JS frontend doesn't send UserName or IPASession for these functions
            post_data["Functions"] = func
            post_data["IPAddress"] = target_ip
            post_data["PrinterName"] = command
        elif "shutdown /r" in cmd_lower:
            post_data["Functions"] = "Reboot"
            post_data["IPAddress"] = target_ip
            post_data["UserName"] = username
            headers["IPASession"] = ipa_session
        elif "shutdown /s" in cmd_lower:
            post_data["Functions"] = "Shutdown" 
            post_data["IPAddress"] = target_ip
            post_data["UserName"] = username
            headers["IPASession"] = ipa_session
        else:
            # Genel komut
            post_data["Functions"] = "RunCommand"
            post_data["IPAddress"] = target_ip
            post_data["UserName"] = username
            post_data["Commands"] = command
            headers["IPASession"] = ipa_session
            
        encoded_post_data = urllib.parse.urlencode(post_data)
            
        try:
            cmd_resp = session.post(base_url, data=encoded_post_data, headers=headers, timeout=45, verify=False)
            
            if cmd_resp.status_code == 200:
                return jsonify({"success": True, "result": cmd_resp.text.strip()})
            else:
                return jsonify({"error": f"BIM Servis Hatası: {cmd_resp.status_code} - {cmd_resp.text.strip()}"}), 500
        except requests.exceptions.Timeout:
            return jsonify({"success": True, "result": "BIM sunucusuna komut iletildi ancak yanıt süresi aşıldı (45 sn). Uzun süren komutlar arka planda tamamlanabilir."})

    except Exception as e:
        print(f"[BIM ERROR] {e}")
        return jsonify({"error": str(e)}), 500

@bim_service_bp.route('/printers/local_windows/info', methods=['GET'])
def local_windows_info():
    import subprocess
    import json
    from flask import jsonify
    
    try:
        cmd_printers = 'powershell -NoProfile -Command "Get-Printer | Select-Object Name, PortName, DriverName, PrinterStatus | ConvertTo-Json -Compress"'
        res_pr = subprocess.run(cmd_printers, capture_output=True, text=True, shell=True)
        printers = []
        if res_pr.returncode == 0 and res_pr.stdout.strip():
            try:
                data = json.loads(res_pr.stdout.strip())
                if isinstance(data, dict): data = [data]
                printers = data
            except: pass
            
        cmd_drivers = 'powershell -NoProfile -Command "Get-PrinterDriver | Select-Object Name | ConvertTo-Json -Compress"'
        res_dr = subprocess.run(cmd_drivers, capture_output=True, text=True, shell=True)
        drivers = []
        if res_dr.returncode == 0 and res_dr.stdout.strip():
            try:
                data = json.loads(res_dr.stdout.strip())
                if isinstance(data, dict): data = [data]
                drivers = [d.get("Name") for d in data if d.get("Name")]
            except: pass
            
        return jsonify({"success": True, "printers": printers, "drivers": drivers})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@bim_service_bp.route('/printers/local_windows/install', methods=['POST'])
def local_windows_install():
    import subprocess
    import json
    from flask import jsonify, request
    data = request.json or {}
    
    ip = data.get("ip")
    name = data.get("name")
    driver = data.get("driver", "Generic / Text Only")
    remove_list = data.get("remove_list", [])
    
    if not ip or not name:
        return jsonify({"success": False, "error": "IP ve isim zorunludur."})
        
    try:
        logs = []
        for rm_printer in remove_list:
            cmd_rm = f'powershell -NoProfile -Command "Remove-Printer -Name \'{rm_printer}\'"'
            subprocess.run(cmd_rm, capture_output=True, text=True, shell=True)
            logs.append(f"{rm_printer} silindi.")
            
        port_name = f"IP_{ip}"
        cmd_port = f'powershell -NoProfile -Command "Add-PrinterPort -Name \'{port_name}\' -PrinterHostAddress \'{ip}\'"'
        r1 = subprocess.run(cmd_port, capture_output=True, text=True, shell=True)
        
        cmd_add = f'powershell -NoProfile -Command "Add-Printer -Name \'{name}\' -DriverName \'{driver}\' -PortName \'{port_name}\'"'
        r2 = subprocess.run(cmd_add, capture_output=True, text=True, shell=True)
        
        if r2.returncode != 0:
            return jsonify({"success": False, "error": f"Yazıcı eklenemedi: {r2.stderr}"})
            
        return jsonify({"success": True, "message": f"{name} ({ip}) başarıyla kuruldu! \n" + chr(10).join(logs)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
