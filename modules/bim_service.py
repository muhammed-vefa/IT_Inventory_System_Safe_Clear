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
        bim_base_url = bim_config.get('base_url', 'http://bim.ornek-kurum.com').rstrip('/')
        
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
            "Origin": os.getenv("BIM_ORIGIN", bim_base_url)
        }
        
        login_resp = requests.post(base_url, data=login_data, headers=browser_headers, timeout=10)
        
        if login_resp.status_code != 200 or login_resp.text.strip() == "Error" or not login_resp.text.strip():
            # Kullanıcıya daha net bir hata verelim
            return jsonify({"error": f"BIM sitesi giriş bilgilerinizi reddetti. Lütfen Kullanıcı Adı veya Şifrenizi kontrol edin. (Sunucu Yanıtı: {login_resp.text.strip()})"}), 401
            
        ipa_session = login_resp.text.strip()
        
        # 2. Komutu eşleştir ve gönder
        func = data.get('function')  # AddPrinter, RemovePrinter vb.
        cmd_lower = str(command).lower()
        
        post_data = {
            "UserName": username,
            "IPAddress": target_ip
        }
        
        if func in ["AddPrinter", "RemovePrinter"]:
            post_data["Functions"] = func
            post_data["PrinterName"] = command
        elif "shutdown /r" in cmd_lower:
            post_data["Functions"] = "Reboot"
        elif "shutdown /s" in cmd_lower:
            post_data["Functions"] = "Shutdown" 
        else:
            # Genel komut (Eğer arka uç destekliyorsa)
            post_data["Functions"] = "RunCommand"
            post_data["Commands"] = command
            
        headers = {
            "IPASession": ipa_session,
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        import urllib.parse
        encoded_data = urllib.parse.urlencode(post_data, quote_via=urllib.parse.quote)
        
        try:
            cmd_resp = requests.post(base_url, data=encoded_data, headers=headers, timeout=45)
            
            if cmd_resp.status_code == 200:
                return jsonify({"success": True, "result": cmd_resp.text.strip()})
            else:
                return jsonify({"error": f"BIM Servis Hatası: {cmd_resp.status_code}"}), 500
        except requests.exceptions.Timeout:
            return jsonify({"success": True, "result": "BIM sunucusuna komut iletildi ancak yanıt süresi aşıldı (45 sn). Uzun süren komutlar (wget vb.) arka planda başarıyla tamamlanmış olabilir."})

    except Exception as e:
        print(f"[BIM ERROR] {e}")
        return jsonify({"error": str(e)}), 500
