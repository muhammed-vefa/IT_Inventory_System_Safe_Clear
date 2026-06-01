from flask import Blueprint, jsonify, request
import requests
import xml.etree.ElementTree as ET

bim_service_bp = Blueprint('bim_service', __name__)

@bim_service_bp.route('/client_ip', methods=['GET'])
def get_client_ip():
    # Proxy varsa X-Forwarded-For kontrol et
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ',' in ip: ip = ip.split(',')[0].strip()
    return jsonify({"ip": ip})

@bim_service_bp.route('/run_command', methods=['POST'])
def run_command():
    try:
        data = request.json
        target_ip = data.get('ip')
        command = data.get('command')
        username = data.get('username')
        password = data.get('password')

        if not target_ip or not command:
            return jsonify({"error": "IP ve Komut zorunludur."}), 400

        base_url = "http://bim.kocaelish.com/Handler.ashx"
        
        # 1. Login (Web arayüzünü taklit et)
        login_data = {
            "Functions": "Login",
            "UserName": username,
            "Password": password
        }
        
        # Tarayıcı gibi davranması için header ekleyelim (Bot korumasını aşmak için)
        browser_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            "Referer": "http://bim.kocaelish.com/",
            "Origin": "http://bim.kocaelish.com"
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
            post_data["Command"] = command
            
        headers = {
            "IPASession": ipa_session
        }
        
        cmd_resp = requests.post(base_url, data=post_data, headers=headers, timeout=15)
        
        if cmd_resp.status_code == 200:
            return jsonify({"success": True, "result": cmd_resp.text.strip()})
        else:
            return jsonify({"error": f"BIM Servis Hatası: {cmd_resp.status_code}"}), 500

    except Exception as e:
        print(f"[BIM ERROR] {e}")
        return jsonify({"error": str(e)}), 500
