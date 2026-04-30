from flask import Blueprint, request, jsonify
import requests
from core.auth import require_auth, require_admin

bim_service_bp = Blueprint('bim_service', __name__)

BIM_URL = "http://bim.kocaelish.com/Handler.ashx"

def get_bim_session(username, password):
    """BIM sistemine giriş yapıp IPASession token'ını alır."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        # 1. Deneme: 'Functions' parametresi ile
        data = {
            "Functions": "Login",
            "UserName": username,
            "Password": password
        }
        resp = requests.post(BIM_URL, data=data, headers=headers, timeout=15)
        print(f"BIM Login Attempt 1 (Functions) - Status: {resp.status_code}, Response: {resp.text[:50]}")
        
        if resp.status_code == 200 and resp.text.strip() != "Error" and len(resp.text.strip()) > 5:
            return resp.text.strip()
            
        # 2. Deneme: 'Function' (tekil) parametresi ile (Bazı versiyonlar bunu bekler)
        data["Function"] = "Login"
        del data["Functions"]
        resp = requests.post(BIM_URL, data=data, headers=headers, timeout=15)
        print(f"BIM Login Attempt 2 (Function) - Status: {resp.status_code}, Response: {resp.text[:50]}")
        
        if resp.status_code == 200 and resp.text.strip() != "Error" and len(resp.text.strip()) > 5:
            return resp.text.strip()

    except Exception as e:
        print(f"BIM Login Exception: {e}")
    return None

@bim_service_bp.route('/client_ip', methods=['GET'])
@require_auth
def get_client_ip():
    """İsteği yapan istemcinin IP adresini döndürür."""
    if request.headers.getlist("X-Forwarded-For"):
        ip = request.headers.getlist("X-Forwarded-For")[0]
    else:
        ip = request.remote_addr
    
    # Yerel geliştirmede IPv6 localhost (::1) dönebilir, bunu düzeltelim
    if ip == "::1":
        ip = "127.0.0.1"
        
    return jsonify({"ip": ip})

@bim_service_bp.route('/run_command', methods=['POST'])
@require_admin
def run_command():
    """BIM sistemi üzerinden belirtilen IP'ye komut gönderir."""
    try:
        data = request.json
        ip_address = data.get('ip')
        command = data.get('command')
        username = data.get('username')
        password = data.get('password')
        
        if not ip_address or not command or not username or not password:
            return jsonify({"error": "IP adresi, komut, kullanıcı adı ve şifre zorunludur."}), 400
            
        # 1. IPASession al
        session_token = get_bim_session(username, password)
        if not session_token:
            return jsonify({"error": "BIM sistemine giriş yapılamadı. Kullanıcı adı veya şifreniz hatalı olabilir (kocaelish.com)."}), 401
            
        # 2. Komutu çalıştır
        bim_func = data.get('function', 'RunCommand')
        payload = {
            "Functions": bim_func,
            "UserName": username,
            "IPAddress": ip_address
        }
        
        # BİM Yazıcı Ekle/Kaldır servisi 'PrinterName' parametresini bekler
        if bim_func in ['AddPrinter', 'RemovePrinter']:
            payload["PrinterName"] = command
        else:
            payload["Commands"] = command
        headers = {
            "IPASession": session_token,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        resp = requests.post(BIM_URL, data=payload, headers=headers, timeout=30)
        result_text = resp.text.strip()
        
        if resp.status_code == 200:
            if result_text == "Error":
                 return jsonify({"error": "BIM sistemi komutu kabul etmedi (Error döndü). Yetkiniz olmayabilir."}), 403
            return jsonify({"message": "Komut BIM sistemine iletildi.", "result": result_text})
        else:
            return jsonify({"error": f"BIM sunucusu hata döndürdü: {resp.status_code}. Yanıt: {result_text[:100]}"}), 500
            
    except Exception as e:
        import traceback
        print(f"BIM Run Command Error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": f"Sistem Hatası: {str(e)}"}), 500
