from flask import Blueprint, jsonify, request
import requests
from bs4 import BeautifulSoup
from core.database_sql import query_db, get_db_connection
import os
import json
from dotenv import load_dotenv
import urllib3
import socket

# DNS Rate-Limit Koruması: Sürekli istek atıldığında Windows/DNS sunucusu 
# 'getaddrinfo failed' hatası vermesin diye IP'yi manuel çözümlüyoruz.
_orig_getaddrinfo = socket.getaddrinfo
def _patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if host == 'keyosmgt.kocaelish.com':
        host = '10.241.1.45'
    return _orig_getaddrinfo(host, port, family, type, proto, flags)
socket.getaddrinfo = _patched_getaddrinfo

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

keyos_service_bp = Blueprint('keyos_service', __name__)

# Config
KEYOS_LOGIN_URL = "https://keyosmgt.kocaelish.com/login"
KEYOS_COMPUTERS_URL = "https://keyosmgt.kocaelish.com/computers"

class KeyOSClient:
    def __init__(self, username, password):
        self.session = requests.Session()
        self.username = username
        self.password = password
        self.is_logged_in = False

    def login(self):
        try:
            # Get CSRF if any
            r = self.session.get(KEYOS_LOGIN_URL, timeout=10, verify=False)
            
            # The login API is /login/login and accepts JSON
            login_api = KEYOS_LOGIN_URL + "/login"
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
            
            dash_url = KEYOS_LOGIN_URL.replace("/login", "/dashboard")
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
                api_url = KEYOS_LOGIN_URL.replace("/login", "/computers/getDataTable")
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
                    "ip": record.get('ethernetIPAddress', '-').strip()
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

@keyos_service_bp.route('/manual_sync', methods=['POST'])
def sync_all():
    """Tüm envanteri KeyOS ile (Toplu Veri Çekerek) senkronize eder."""
    try:
        username = os.getenv("KEYOS_USER", "dashboard")
        password = os.getenv("KEYOS_PASS", "DashBoard2025*!")
        
        client = KeyOSClient(username, password)
        if not client.login():
            return jsonify({"success": False, "error": "KeyOS Giriş Başarısız! (Hedef sunucuya bağlanılamadı veya şifre yanlış)"})
            
        # Toplu veri çekme işlemi (Excel mantığına benzer, ancak daha hızlı JSON API)
        api_url = KEYOS_LOGIN_URL.replace("/login", "/computers/getDataTable")
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
        
        # KeyOS verilerini Seri No'ya göre bir sözlüğe (dictionary) aktaralım, arama anında O(1) olsun.
        keyos_dict = {}
        for row in keyos_data:
            serial = str(row.get('serialNumber', '')).strip().upper()
            if serial:
                keyos_dict[serial] = {
                    "hostname": str(row.get('hostName', '-')).strip(),
                    "mac": str(row.get('ethernetMACAddress', '-')).strip(),
                    "printers": str(row.get('printers', '-')).strip(),
                    "ip": str(row.get('ethernetIPAddress', '-')).strip()
                }

        # Kendi veritabanımızdaki cihazları al
        inventory = query_db("SELECT id, pc_no, pc_serial, hostname FROM pcs WHERE pc_serial IS NOT NULL AND pc_serial != '-'")
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
                # Update DB
                query_db("""
                    UPDATE pcs SET 
                    ip = ?, mac = ?, keyos = 1, 
                    connected_printers = ?
                    WHERE id = ?
                """, (details['ip'], details['mac'], details['printers'], pc['id']))
                
                # Check Hostname mismatch
                if details['hostname'].upper() != (pc['hostname'] or '').upper():
                    mismatches.append({
                        "pc_no": pc['pc_no'],
                        "local_hostname": pc['hostname'],
                        "keyos_hostname": details['hostname']
                    })
                
                successful_list.append({
                    "pc_no": pc['pc_no'],
                    "serial": pc['pc_serial'],
                    "ip": details['ip'],
                    "mac": details['mac'],
                    "printers": details['printers']
                })
                updated_count += 1
            else:
                failed_list.append({
                    "pc_no": pc['pc_no'],
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
        
        os.makedirs("data", exist_ok=True)
        reports_file = "data/keyos_reports.json"
        
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
        report_path = "data/keyos_reports.json"
        if not os.path.exists(report_path):
            # Geriye dönük uyumluluk için eski dosyayı da kontrol edelim
            old_report_path = "data/last_keyos_report.json"
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

@keyos_service_bp.route('/update_mahal', methods=['POST'])
def update_mahal():
    """Kullanıcının kendi yetkili hesabı ile KeyOS'ta mahal günceller."""
    data = request.json
    # Bu kısım KeyOS MGT'nin mahal güncelleme form yapısına göre doldurulmalı.
    # Şimdilik sadece yetkili girişi deneyip başarılı ise "ok" dönecek bir yapı.
    return jsonify({"status": "pending", "message": "KeyOS Mahal Güncelleme Modülü Hazırlanıyor..."})
