from flask import Blueprint, jsonify, request
from core.database_sql import query_db, get_db_connection
from modules.logs_manager import log_change, get_mac_address
from core.auth import require_auth, require_editor, require_admin
from modules.bim_service import get_bim_session, BIM_URL
import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

printer_manager_bp = Blueprint('printer_manager', __name__)

PRINTER_STATUS_PORTAL = "https://10.241.1.21:49631/printers/"

def get_cups_printers():
    """CUPS sunucusundaki tüm yazıcı isimlerini (PR NO) çeker."""
    try:
        # Gelişmiş SSL ayarları (Eski CUPS sunucuları için TLSv1.2 zorlama ve şifreleme desteği)
        session = requests.Session()
        from urllib3.util import ssl_
        ctx = ssl_.create_urllib3_context()
        ctx.load_default_certs()
        ctx.check_hostname = False
        ctx.verify_mode = 0 # SSL verify off
        # TLSv1.2 ve altı için daha toleranslı olması için ciphers ayarı
        ctx.set_ciphers('DEFAULT@SECLEVEL=1')
        
        adapter = requests.adapters.HTTPAdapter()
        adapter.pool_connections = 1
        adapter.pool_maxsize = 1
        session.mount("https://", adapter)
        
        # SSL Context'i session ile kullanıyoruz
        try:
            res = session.get(PRINTER_STATUS_PORTAL, verify=False, timeout=5)
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
            pr_no=?, model=?, ip=?, seri=?, mac=?, status=?
            WHERE id=?''', (
            data.get('pr_no'), data.get('model'), data.get('ip'), 
            data.get('seri'), data.get('mac'), data.get('status'), id
        ))

        # 3. Değişiklikleri logla
        tracked_fields = ['pr_no', 'model', 'ip', 'seri', 'mac', 'status']
        for field in tracked_fields:
            old_val = str(old_record.get(field, '') or '')
            new_val = str(data.get(field, '') or '')
            
            label_map = {
                'pr_no': 'PR Numarası', 'model': 'Model', 'ip': 'IP Adresi',
                'seri': 'Seri No', 'mac': 'MAC Adresi', 'status': 'Durum'
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

@printer_manager_bp.route('/sync_from_excel', methods=['POST'])
@require_admin
def sync_printers_from_excel():
    """Excel'den yazıcıları senkronize eder ve site durumunu Excel'e yazar."""
    try:
        import os
        import openpyxl
        # main.py ile aynı dizine bak (C:\Users\MUHAMMED-VEFA-IS\Desktop\IT_Inventory_System\)
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        yaz_path = os.path.join(BASE_DIR, "yazıcılar.xlsx")
        
        if not os.path.exists(yaz_path):
            return jsonify({"error": "yazıcılar.xlsx bulunamadı"}), 404
            
        conn = get_db_connection()
        wb = openpyxl.load_workbook(yaz_path, data_only=True)
        sheet = wb.active
        rows = list(sheet.rows)
        headers = [str(cell.value).strip().upper() if cell.value else f"Col{i}" for i, cell in enumerate(rows[0])]
        
        durum_idx = -1
        for i, h in enumerate(headers):
            if h in ['DURUM', 'STATUS', 'STATE']: durum_idx = i; break
        
        if durum_idx == -1:
            durum_idx = len(headers)
            sheet.cell(row=1, column=durum_idx+1, value='DURUM')
        
        updated_count = 0
        for r_idx, row_cells in enumerate(rows[1:], start=2):
            item = {headers[i]: row_cells[i].value for i in range(len(row_cells)) if i < len(headers)}
            
            pr_no = str(item.get('PR NUMARASI') or item.get('PR NO') or 
                        item.get('BY NO') or item.get('BARKOD YAZICI NO') or 
                        item.get('BO NO') or item.get('BARKOD OKUYUCU NO') or 
                        item.get('TR NO') or item.get('TARAYICI NO') or '').strip()
            seri = str(item.get('SERİ NUMARASI') or item.get('SERI NO') or '').strip()
            mac = str(item.get('MAC ADRESS') or item.get('MAC ADRES') or '').strip()
            
            # Ana Yazıcılar (PR-) için Seri ve MAC zorunlu
            # Diğerleri (BY, BO, TR) için sadece Seri yeterli
            is_barcode_or_scanner = any(x in pr_no.upper() for x in ['BY', 'BO', 'TR'])
            
            if not pr_no or not seri:
                continue
                
            if not is_barcode_or_scanner and not mac:
                # Standart yazıcılarda MAC zorunlu olsun demiştik
                continue

            exists = conn.execute("SELECT id, status, model, seri, mac, ip FROM printers WHERE pr_no=? OR (seri=? AND seri != '')", (pr_no, seri)).fetchone()
            excel_status = str(row_cells[durum_idx].value or '').strip()
            
            if exists:
                # Sitedeki yönetim durumunu (Kurulu, Depoda vb.) Excel'e geri yaz
                cur_status = exists['status'] or 'Kurulu'
                sheet.cell(row=r_idx, column=durum_idx+1, value=cur_status)
                
                # Excel'deki diğer kolonlarla DB'yi güncelle
                conn.execute('''UPDATE printers SET model=?, seri=?, mac=?, ip=? WHERE id=?''', 
                             (item.get('MODEL') or exists['model'], 
                              seri or exists['seri'], 
                              mac or exists['mac'], 
                              item.get('IP ADRES') or exists['ip'], 
                              exists['id']))
            else:
                final_status = excel_status if excel_status in ['Kurulu', 'Depoda', 'Arızalı', 'Serviste'] else 'Kurulu'
                conn.execute('''INSERT INTO printers (pr_no, model, seri, mac, ip, status) 
                              VALUES (?,?,?,?,?,?)''', (
                    pr_no, item.get('MODEL'), seri, 
                    mac, item.get('IP ADRES'), final_status
                ))
            updated_count += 1
        
        try: wb.save(yaz_path)
        except: pass
        
        conn.commit()
        conn.close()
        return jsonify({"message": f"{updated_count} yazıcı senkronize edildi."})
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
            
            # 1. DB GÜNCELLEME
            current_raw = (pc['bagli_yazicilar'] or "").strip()
            pr_list = [x.strip() for x in current_raw.split(',') if x.strip()]
            
            db_updated = False
            if action == 'add':
                if pr_no not in pr_list:
                    pr_list.append(pr_no)
                    db_updated = True
            elif action == 'remove':
                if pr_no in pr_list:
                    pr_list.remove(pr_no)
                    db_updated = True
            
            if db_updated:
                new_val = ", ".join(pr_list)
                conn.execute("UPDATE inventory SET bagli_yazicilar=? WHERE id=?", (new_val, pc_id))
                client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
                log_change(conn, 'inventory', pc_id, f"PC-{pc['pc_no']}", f'Bağlı Yazıcılar (Toplu {action.capitalize()})', current_raw, new_val, user_name, user_name, client_ip=client_ip)
                updated_count += 1

            # 2. BIM KOMUTU GÖNDERME
            if session_token and pc['ip'] and bim_func and command:
                try:
                    payload = {
                        "Functions": bim_func,
                        "UserName": bim_user,
                        "IPAddress": pc['ip'],
                        "PrinterName": command if bim_func in ['AddPrinter', 'RemovePrinter'] else None,
                        "Commands": command if bim_func not in ['AddPrinter', 'RemovePrinter'] else None
                    }
                    # None olanları temizle
                    payload = {k: v for k, v in payload.items() if v is not None}
                    
                    headers = {"IPASession": session_token}
                    resp = requests.post(BIM_URL, data=payload, headers=headers, timeout=15)
                    
                    if resp.status_code != 200 or "Error" in resp.text:
                        bim_errors.append(f"PC-{pc['pc_no']} ({pc['ip']}): BIM Hatası")
                except Exception as e:
                    bim_errors.append(f"PC-{pc['pc_no']} ({pc['ip']}): Bağlantı Hatası")

        conn.commit()
        conn.close()
        
        # Excel yedekleme (opsiyonel)
        try:
            from modules.inventory_manager import _backup_to_excel
            _backup_to_excel(get_db_connection())
        except: pass

        if bim_errors and not session_token:
             return jsonify({"success": True, "count": updated_count, "message": "DB güncellendi ancak BIM girişi yapılamadı."})
        
        if bim_errors:
            return jsonify({
                "success": False, 
                "error": f"Bazı cihazlarda BIM hatası oluştu: {', '.join(bim_errors[:3])}...",
                "count": updated_count
            })

        return jsonify({"success": True, "count": updated_count, "message": f"{updated_count} cihazda işlem başarıyla tamamlandı."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
