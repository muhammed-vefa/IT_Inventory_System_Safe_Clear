import os
import re
import time
import subprocess
import requests
import urllib3
from flask import Blueprint, request, jsonify
from core.auth import require_auth, require_editor, require_admin
# from main import get_db_connection, query_db, log_change  <-- Circular import riski nedeniyle kaldırıldı
from bs4 import BeautifulSoup

# Disable insecure request warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

printer_manager_bp = Blueprint('printer_manager', __name__)

PRINTER_STATUS_PORTAL = "https://10.241.1.21:49631/printers/"

CUPS_LATEST_STATUS = "Bekleniyor..."

class CUPSHelper:
    BASE_URL = "https://10.241.1.21:49631"
    AUTH_USER = 'root'
    AUTH_PASS = '1234qqqQ'

    @classmethod
    def _run_curl(cls, url, data=None, referer=None, multipart=False):
        cookie_file = "cups_cookies.txt"
        # Modern User-Agent ve Expect başlığı CUPS'ın takılmasını engeller
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        cmd = ['curl.exe', '-k', '-L', '-s', '--anyauth', '--user', f"{cls.AUTH_USER}:{cls.AUTH_PASS}", 
               '-c', cookie_file, '-b', cookie_file, '-H', 'Expect:', '-A', user_agent]
        
        if not multipart: cmd.extend(['-H', 'Content-Type: application/x-www-form-urlencoded'])
        if referer: cmd.extend(['-H', f'Referer: {referer}'])
        
        if data:
            if not isinstance(data, dict):
                data = {}
            for k, v in data.items():
                if multipart:
                    if k == 'PPD_FILE' and not v:
                        # Boş dosya girişi için Windows'ta @nul kullanmak daha güvenlidir
                        cmd.extend(['-F', 'PPD_FILE=@nul'])
                    else:
                        cmd.extend(['-F', f"{k}={v}"])
                else:
                    cmd.extend(['--data-urlencode', f"{k}={v}"])
        cmd.append(url)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=20, encoding='utf-8', errors='ignore')
            return result.stdout or ""
        except: return ""

    @classmethod
    def get_printer_name_by_ip(cls, target_ip):
        """CUPS sunucusunda IP adresine (Device URI) göre yazıcı adını bulur."""
        try:
            url = f"{cls.BASE_URL}/printers/"
            output = cls._run_curl(url)
            soup = BeautifulSoup(output, 'html.parser')
            for link in soup.find_all('a', href=re.compile(r'/printers/')):
                row = link.find_parent('tr')
                if row and target_ip in row.get_text():
                    return link.get_text().strip()
            return None
        except: return None

    @classmethod
    def update_location(cls, printer_name, new_location, target_ip=None):
        """Dinamik Rota Algoritması: Başarı mesajı görene kadar formu takip eder."""
        global CUPS_LATEST_STATUS
        try:
            # 1. SID Çek
            printer_url = f"{cls.BASE_URL}/printers/{printer_name}"
            res = cls._run_curl(printer_url, referer=f"{cls.BASE_URL}/printers/")
            sid = cls._extract_sid(res)
            
            # 2. Sihirbazı Başlat
            CUPS_LATEST_STATUS = "Sihirbaz başlatılıyor..."
            curr_url = f"{cls.BASE_URL}/admin/"
            payload = {"org.cups.sid": sid, "OP": "modify-printer", "printer_name": printer_name, "administration": "modify-printer"}
            curr_res = cls._run_curl(curr_url, data=payload, referer=printer_url)
            
            # 3. Dinamik Döngü (Max 10 Adım)
            for i in range(4, 12):
                if any(word in curr_res.lower() for word in ["successfully", "başarıyla", "updated"]):
                    CUPS_LATEST_STATUS = "Tamamlandı: Başarıyla güncellendi."
                    return True, "CUPS Mahal başarıyla güncellendi."

                step_name = f"Adım {i}"
                # Formda PRINTER_LOCATION varsa ve bizimkine eşit değilse override et
                overrides = {}
                if 'name="PRINTER_LOCATION"' in curr_res:
                    overrides["PRINTER_LOCATION"] = new_location
                    CUPS_LATEST_STATUS = f"{step_name}: Mahal bilgisi yazılıyor..."
                else:
                    CUPS_LATEST_STATUS = f"{step_name}: İlerleniyor..."

                # Buton tespiti: Önce 'Modify Printer' ara, yoksa 'Continue'
                btn_target = "continue"
                if 'value="Modify Printer"' in curr_res: btn_target = "Modify Printer"
                
                res_obj, err = cls._process_wizard_step(curr_res, curr_url, step_name, overrides, btn_target)
                if err: return False, err
                
                curr_res = res_obj["html"]
                curr_url = res_obj["url"]

            return False, "HATA: Maksimum adım sayısına ulaşıldı ama başarı mesajı alınamadı."
            
        except Exception as e:
            CUPS_LATEST_STATUS = f"HATA: {str(e)}"
            return False, str(e)

    @classmethod
    def update_location(cls, printer_name, new_location, target_ip=None):
        """Dinamik Rota Algoritması: Başarı mesajı görene kadar formu takip eder."""
        global CUPS_LATEST_STATUS
        try:
            # 1. SID Çek
            printer_url = f"{cls.BASE_URL}/printers/{printer_name}"
            res = cls._run_curl(printer_url, referer=f"{cls.BASE_URL}/printers/")
            sid = cls._extract_sid(res)
            
            # 2. Sihirbazı Başlat
            CUPS_LATEST_STATUS = "Sihirbaz başlatılıyor..."
            curr_url = f"{cls.BASE_URL}/admin/"
            payload = {"org.cups.sid": sid, "OP": "modify-printer", "printer_name": printer_name, "administration": "modify-printer"}
            curr_res = cls._run_curl(curr_url, data=payload, referer=printer_url)

            # 3. Dinamik Döngü (İçerik Odaklı)
            last_title = ""
            title_repeat_count = 0
            for i in range(1, 15):
                # Başarı Kontrolü
                if any(word in curr_res.lower() for word in ["successfully", "başarıyla", "updated", "changed"]):
                    CUPS_LATEST_STATUS = "Tamamlandı: Başarıyla güncellendi."
                    return True, "CUPS Mahal başarıyla güncellendi."

                # Sayfa Tespiti
                title_match = re.search(r'<title>(.*?)<\/title>', curr_res, re.I)
                title = (title_match.group(1) if title_match else "Bilinmeyen Sayfa").strip()
                
                if title == last_title: title_repeat_count += 1
                else: title_repeat_count = 0
                last_title = title
                
                if title_repeat_count >= 4:
                    return False, f"HATA: {title} sayfasında takılı kalındı (Döngü)."

                step_name = f"Aşama {i}"
                btn_target = "Continue"
                overrides = {}

                # İÇERİK ODAKLI KARAR MEKANİZMASI (Canlı İnceleme Sonuçları)
                if "Current Connection:" in curr_res:
                    print(f"DEBUG: {step_name} - Bağlantı aşaması onaylanıyor...")
                    btn_target = "Continue"
                elif "Location:" in curr_res:
                    print(f"DEBUG: {step_name} - Mahal girişi yapılıyor...")
                    overrides["PRINTER_LOCATION"] = new_location
                    btn_target = "Continue"
                elif "Model:" in curr_res or "Make:" in curr_res:
                    print(f"DEBUG: {step_name} - Model/Sürücü aşaması, kaydediliyor...")
                    btn_target = "Modify Printer"
                elif "modified successfully" in curr_res.lower():
                    CUPS_LATEST_STATUS = "Tamamlandı: Başarıyla güncellendi."
                    print(f"DEBUG SUCCESS: İşlem başarıyla bitti.")
                    return True, "CUPS Mahal başarıyla güncellendi."
                else:
                    # Tanınamayan sayfa durumunda güvenli ilerleme
                    print(f"DEBUG: {step_name} - Sayfa içeriği analiz edilemedi, varsayılan 'Continue' denenecek.")
                    btn_target = "Continue"

                res_obj, err = cls._process_wizard_step(curr_res, curr_url, step_name, overrides, btn_target)
                if err: return False, err
                
                curr_res = res_obj["html"]
                curr_url = res_obj["url"]

            return False, "HATA: Maksimum adım sayısına ulaşıldı."
            
        except Exception as e:
            CUPS_LATEST_STATUS = f"HATA: {str(e)}"
            return False, str(e)

    @classmethod
    def _process_wizard_step(cls, html, referer, step_name, overrides=None, btn_target="Continue"):
        """Form verilerini koruyarak sihirbaz adımlarını geçer."""
        soup = BeautifulSoup(html, 'html.parser')
        form = soup.find('form')
        if not form: 
            return None, f"HATA: {step_name} sayfasında FORM bulunamadı."
        
        payload = cls._extract_form_data(form)
        if overrides and isinstance(overrides, dict):
            payload.update(overrides)
        
        payload['org.cups.sid'] = cls._extract_sid(html)
        
        # Butonu Bul ve Bas
        btn = form.find(['input', 'button'], value=re.compile(btn_target, re.I))
        if btn: 
            payload[btn.get('name', 'submit')] = btn.get('value', btn_target)
        else:
            any_btn = form.find(['input', 'button'], type='submit')
            if any_btn: payload[any_btn.get('name', 'submit')] = any_btn.get('value', 'Continue')
        
        print(f"DEBUG: {step_name} Gönderilen Veri (Keys): {list(payload.keys())}")
        
        action = form.get('action', '/admin/')
        # URL'nin sonuna slaj ekle (Yönlendirme hatasını önlemek için)
        if not action.endswith('/'): action += '/'
        target_url = f"{cls.BASE_URL}{action}" if action.startswith('/') else f"{cls.BASE_URL}/admin/{action}"
        
        time.sleep(1.5)
        is_multipart = (form.get('enctype') == 'multipart/form-data')
        next_html = cls._run_curl(target_url, data=payload, referer=referer, multipart=is_multipart)
        
        return {"html": next_html, "url": target_url}, None

    @classmethod
    def _extract_form_data(cls, form):
        """Mevcut formdaki tüm inputları (gizli dahil) yakalar."""
        data = {}
        for inp in form.find_all(['input', 'select', 'textarea']):
            name = inp.get('name')
            if not name or (inp.get('type') == 'radio' and not inp.has_attr('checked')): continue
            if inp.name == 'select':
                opt = inp.find('option', selected=True) or inp.find('option')
                data[name] = opt.get('value', '') if opt else ''
            else: data[name] = inp.get('value', '')
        return data

    @classmethod
    def _extract_sid(cls, html):
        match = re.search(r'name=["\']org\.cups\.sid["\'][^>]*value=["\']?([a-f0-9]+)["\']?', html, re.I)
        return match.group(1) if match else ""

@printer_manager_bp.route('/cups_status', methods=['GET'])
def get_cups_status():
    global CUPS_LATEST_STATUS
    return jsonify({"status": CUPS_LATEST_STATUS})

@printer_manager_bp.route('/get_all', methods=['GET'])
@require_auth
def get_printers():
    """Tüm yazıcıları yazıcılar tablosundan getirir."""
    from core.database_sql import query_db
    try:
        items = query_db("SELECT * FROM printers")
        return jsonify([dict(row) for row in items])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def ping_host(host):
    """Pings a host and returns True if it's online, False otherwise."""
    import platform
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    command = ['ping', param, '1', '-w', '2000', host]
    try:
        return subprocess.call(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0
    except Exception:
        return False

@printer_manager_bp.route('/status/<ip>', methods=['GET'])
def get_status(ip):
    """Canlı yazıcı durumunu Brother web arayüzünden çeker."""
    from modules.printer_service import get_brother_printer_status
    return jsonify(get_brother_printer_status(ip))

@printer_manager_bp.route('/update', methods=['POST'])
@require_editor
def update_printer():
    from core.database_sql import get_db_connection
    data = request.json
    id = data.get('id')
    if not id: return jsonify({"error": "ID missing"}), 400
    try:
        conn = get_db_connection()
        conn.execute('''UPDATE printers SET pr_no=?, model=?, ip=?, seri=?, mac=?, status=?, mahal=? WHERE id=?''', (
            data.get('pr_no'), data.get('model'), data.get('ip'), 
            data.get('seri'), data.get('mac'), data.get('status'), data.get('mahal'), id
        ))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@printer_manager_bp.route('/cups/update_mahal', methods=['POST'])
@require_editor
def cups_update_mahal():
    data = request.json
    ip = data.get('ip')
    mahal = data.get('mahal')
    if not ip or not mahal: return jsonify({"error": "Parametreler eksik."}), 400
    try:
        printer_name = CUPSHelper.get_printer_name_by_ip(ip)
        if not printer_name: return jsonify({"error": f"CUPS üzerinde {ip} bulunamadı."}), 200
        success, msg = CUPSHelper.update_location(printer_name, mahal, target_ip=ip)
        return jsonify({"success": success, "message": msg})
    except Exception as e:
        return jsonify({"error": str(e)}), 200
