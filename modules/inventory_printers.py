import os
import re
import requests
from core.utils import normalize_row
from core.integrations import get_integration_config
from flask import Blueprint, jsonify, request
from core.database_sql import get_db_connection
from core.auth import require_auth, require_admin, require_editor
from core.limiter import limiter

_digits_re = re.compile(r'\d+')
def extract_printer_number(name):
    if not name:
        return None
    match = _digits_re.search(str(name))
    return int(match.group()) if match else None

inventory_printers_bp = Blueprint('inventory_printers', __name__)

@inventory_printers_bp.route('/get_all', methods=['GET'])
@require_auth
def get_all():
    conn = get_db_connection()
    if not conn: return jsonify([])
    cursor = conn.cursor()
    
    all_devices = []
    try:
        # Fetch active service status to override printer status dynamically
        cursor.execute("SELECT pr_no, status FROM printer_service WHERE is_deleted = 0 AND return_date IS NULL")
        active_services = {}
        for row in cursor.fetchall():
            s_pr_no, s_status = row
            if s_pr_no:
                num = extract_printer_number(s_pr_no)
                if num is not None:
                    active_services[num] = s_status

        include_archived = request.args.get('include_archived') == 'true'
        if include_archived:
            query = "SELECT * FROM printers"
        else:
            query = "SELECT * FROM printers WHERE is_deleted = 0"
        cursor.execute(query)
        columns = [column[0] for column in cursor.description]

        # Load live status cache for list/card compatibility.
        # If live status module fails, do not break printer listing.
        try:
            from modules.printer_live_status import get_live_status_cache
            live_cache = get_live_status_cache()
        except Exception as live_err:
            print("PRINTER LIVE CACHE ERR:", live_err)
            live_cache = {}

        for row in cursor.fetchall():
            d = normalize_row(dict(zip(columns, row)))
            d['device_class'] = 'PRINTER'
            raw_no = str(d.get('pr_no') or '')
            if raw_no.isdigit():
                d['pr_no'] = f"PR-{raw_no.zfill(3)}"
            elif '-' not in raw_no and len(raw_no) > 0:
                 m = _digits_re.search(raw_no)
                 if m: d['pr_no'] = f"PR-{m.group().zfill(3)}"
            
            d['seri'] = d.get('serial_no')
            raw_mahal = str(d.get('location_code') or d.get('mahal') or '')
            if raw_mahal.startswith('DEPO-'):
                d['mahal'] = 'DEPO-' + raw_mahal[5:].replace('-', '.')
            elif raw_mahal.startswith('SERVİSTE-'):
                d['mahal'] = 'SERVİSTE-' + raw_mahal[9:].replace('-', '.')
            else:
                d['mahal'] = raw_mahal.replace('-', '.')
            
            # Dynamic override if there's an active incomplete service record
            pr_num = extract_printer_number(d.get('pr_no'))
            service_status = active_services.get(pr_num) if pr_num is not None else None
            
            if service_status:
                d['status'] = service_status
                if service_status == 'Arızalı':
                    d['is_faulty'] = 1
                    d['in_service'] = 0
                elif service_status == 'Serviste':
                    d['is_faulty'] = 0
                    d['in_service'] = 1
            elif d.get('is_faulty') == 1 or d.get('is_faulty') == True:
                d['status'] = 'Arızalı'
            elif d.get('warehouse') == 1:
                d['status'] = 'Depoda'
            elif d.get('in_service') == 1 or d.get('serviste') == 1:
                d['status'] = 'Serviste'
            elif d.get('without_location') == 1:
                d['status'] = 'Kayıp'
            else:
                d['status'] = d.get('status') or 'Kurulu'

            # Keep frontend-compatible live status fields on list/card payloads.
            pr_key = d.get('pr_no')
            if pr_key and pr_key in live_cache:
                live_info = live_cache[pr_key]
                d['live_status'] = live_info.get('status', 'Bilinmiyor')
                d['live_toner'] = live_info.get('toner', 'Bilinmiyor')
                d['live_is_online'] = live_info.get('is_online', False)
            else:
                d['live_status'] = 'Bilinmiyor'
                d['live_toner'] = 'Bilinmiyor'
                d['live_is_online'] = False
            
            all_devices.append(d)
    except Exception as e:
        print("PRINTER GET_ALL ERR:", e)
    finally:
        conn.close()

    return jsonify(all_devices)

@inventory_printers_bp.route('/update', methods=['POST'])
@require_editor
def update_printer():
    try:
        data = request.json
        if not data or 'id' not in data:
            return jsonify({"error": "ID belirtilmedi."}), 400

        # Synchronize location_code if location changes
        new_loc = data.get('mahal') or data.get('location_code')
        if new_loc is not None:
            data['location_code'] = new_loc

        # Clean "0" and empty serial values to None for SQL NULL mapping
        serial_keys = ['seri', 'serial_no']
        for k in serial_keys:
            if k in data and data[k] is not None:
                s = str(data[k]).strip()
                if s in ('0', '0.0', '0,0', ''):
                    data[k] = None
        
        record_id = data['id']
        changed_by = data.get('changed_by', 'system')
        display_name = data.get('display_name', 'Sistem')

        column_map = {
            'seri': 'serial_no',
            'serial_no': 'serial_no',
            'location_code': 'location_code',
            'mahal': 'location_code',
            'on_field': 'on_field',
            'warehouse': 'warehouse',
            'without_location': 'without_location',
            'serviste': 'in_service',
            'in_service': 'in_service'
        }

        from modules.logs_manager import log_change
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM printers WHERE id = ? AND is_deleted = 0", (record_id,))
        original_columns = [column[0] for column in cursor.description]
        columns_lower = [c.lower() for c in original_columns]
        old_row = cursor.fetchone()
        if not old_row:
            conn.close()
            return jsonify({"error": "Cihaz bulunamadi."}), 404
        
        old_data = dict(zip(columns_lower, old_row))
        record_label = old_data.get('pr_no') or str(record_id)

        # PRINTER STATUS UPDATE BLOCK WITH UNCLOSED SERVICE RECORD
        is_setting_to_kurulu = False
        if 'status' in data and data['status'] == 'Kurulu':
            is_setting_to_kurulu = True
        elif data.get('on_field') == 1 or data.get('on_field') == 1:
            is_setting_to_kurulu = True

        if is_setting_to_kurulu:
            pr_no = data.get('pr_no') or old_data.get('pr_no')
            if pr_no:
                cursor.execute("""
                    SELECT id FROM printer_service 
                    WHERE pr_no = ? AND return_date IS NULL AND is_deleted = 0
                """, (pr_no,))
                if cursor.fetchone():
                    conn.close()
                    return jsonify({"error": "yazıcının kapanmamış servis işlem kaydı var depocunuz ile iletişime geçin"}), 400

        if 'status' in data:
            status_val = data['status']
            data['on_field'] = 1 if status_val == 'Kurulu' else 0
            data['warehouse'] = 1 if status_val == 'Depoda' else 0
            data['is_faulty'] = 1 if status_val == 'Arızalı' else 0
            data['without_location'] = 1 if status_val == 'Kayıp' else 0
            data['serviste'] = 1 if status_val == 'Serviste' else 0
            
            if status_val == 'Kurulu':
                loc = data.get('location_code') or old_data.get('location_code')
                if loc:
                    data['location_code'] = str(loc).replace('SERVİSTE-', '').replace('DEPO-', '').strip()
                mahal = data.get('mahal') or old_data.get('mahal')
                if mahal:
                    data['mahal'] = str(mahal).replace('SERVİSTE-', '').replace('DEPO-', '').strip()

        update_fields = []
        params = []
        allowed_fields = ['pr_no', 'model', 'ip', 'seri', 'mac', 'mahal', 'location_code', 'status', 'on_field', 'warehouse', 'is_faulty', 'without_location', 'serviste']
        
        seen_sql_cols = set()
        for field in allowed_fields:
            if field in data:
                sql_col = column_map.get(field, field).lower()
                if sql_col not in columns_lower: continue 
                
                # Get actual column name for query
                actual_col = original_columns[columns_lower.index(sql_col)]
                if actual_col.lower() in seen_sql_cols: continue
                seen_sql_cols.add(actual_col.lower())
                
                new_val = data[field]
                old_val = old_data.get(sql_col)
                
                # Handle boolean vs integer comparison properly
                new_s = str(new_val).strip().lower() if new_val is not None else ''
                old_s = str(old_val).strip().lower() if old_val is not None else ''
                
                # Normalize bools for comparison
                if new_s in ['1', 'true', 'yes']: new_s = '1'
                elif new_s in ['0', 'false', 'no']: new_s = '0'
                
                if old_s in ['1', 'true', 'yes']: old_s = '1'
                elif old_s in ['0', 'false', 'no']: old_s = '0'
                
                if new_s != old_s:
                    log_change('printers', record_id, record_label, field, old_val, new_val, changed_by, display_name)
                    update_fields.append(f"[{actual_col}] = ?")
                    params.append(new_val)

        if not update_fields:
            # Sadece arşivden çıkarma durumu olabilir, en azından is_deleted=0 yapalım
            update_fields.append("[is_deleted] = 0")
        else:
            update_fields.append("[is_deleted] = 0")

        params.append(record_id)
        query = f"UPDATE printers SET {', '.join(update_fields)} WHERE id = ?"
        cursor.execute(query, params)
        conn.commit()
        conn.close()
        
        return jsonify({"success": True, "message": "Cihaz guncellendi."})
    except Exception as e:
        print(f"[PRINTER UPDATE ERROR] {e}")
        return jsonify({"error": str(e)}), 500

@inventory_printers_bp.route('/delete/<int:id>', methods=['DELETE'])
@require_editor
def delete_device(id):
    try:
        from flask import request
        device_class = request.args.get('class', 'PRINTER').upper()
        
        table_map = {
            'PRINTER': 'printers',
            'BARCODE_PRINTER': 'barcode_printers',
            'BARCODE_READER': 'barcode_readers',
            'SCANNER': 'scanners'
        }
        table_name = table_map.get(device_class, 'printers')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"UPDATE {table_name} SET is_deleted = 1, deleted_at = GETDATE() WHERE id = ?", (id,))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Cihaz silindi."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@inventory_printers_bp.route('/query_cups', methods=['POST'])
@require_editor
def query_cups():
    try:
        import requests
        from bs4 import BeautifulSoup
        import re
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Fetch all active printers from DB, selecting ip as well
        cursor.execute("SELECT id, pr_no, location_code, ip FROM printers WHERE is_deleted = 0")
        db_printers = cursor.fetchall()
        
        # Using global extract_printer_number

        # Build lookup maps
        db_printers_ip_map = {}
        db_printers_num_map = {}
        for db_id, pr_no, db_loc, db_ip in db_printers:
            # Clean IP address
            clean_ip = str(db_ip).strip() if db_ip else None
            if clean_ip:
                db_printers_ip_map[clean_ip] = (db_id, pr_no, db_loc, db_ip)
            
            num = extract_printer_number(pr_no)
            if num is not None:
                db_printers_num_map[num] = (db_id, pr_no, db_loc, db_ip)

        updated_count = 0
        first = 0
        last_page_first_printer = None
        cups_config = get_integration_config('CUPS') or {}; cups_base_url = cups_config.get('base_url', 'http://192.168.X.X:49631').rstrip('/'); from urllib.parse import urlparse; cups_host = urlparse(cups_base_url).hostname or '192.168.X.X'
        
        while True:
            cups_url = f"{cups_base_url}/printers/?FIRST={first}"
            response = requests.get(cups_url, timeout=10, verify=False)
            
            if response.status_code != 200:
                if first == 0:
                    conn.close()
                    return jsonify({"error": f"CUPS Sunucusu Hatasi: {response.status_code}"}), 500
                break
                
            soup = BeautifulSoup(response.text, 'html.parser')
            rows = soup.find_all('tr')
            
            parsed_on_this_page = 0
            current_page_first_printer = None
            
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 3:
                    cups_name = cols[0].get_text(strip=True)
                    hedef_mahal = cols[2].get_text(strip=True).replace("-", ".")
                    
                    if not cups_name: continue
                    
                    if current_page_first_printer is None:
                        current_page_first_printer = cups_name
                        
                    parsed_on_this_page += 1
                    
                    # Fetch printer details to extract IP from Connection URI
                    printer_ip = None
                    try:
                        detail_url = f"{cups_base_url}/printers/{cups_name}"
                        detail_resp = requests.get(detail_url, timeout=5, verify=False)
                        if detail_resp.status_code == 200:
                            # 1. Try to extract IP from connection URI
                            uri_match = re.search(r"(?:socket|ipp|lpd|http|https|dnssd|hp)://([^:/'\"\s]+)", detail_resp.text)
                            if uri_match:
                                potential_ip = uri_match.group(1)
                                if re.match(r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$', potential_ip):
                                    if potential_ip not in (cups_host, '127.0.0.1', '0.0.0.0'):
                                        printer_ip = potential_ip
                            
                            # 2. Fallback: Find all IPs and filter out server IP & loopback
                            if not printer_ip:
                                all_ips = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', detail_resp.text)
                                for ip_candidate in all_ips:
                                    if ip_candidate not in (cups_host, '127.0.0.1', '0.0.0.0'):
                                        printer_ip = ip_candidate
                                        break
                    except Exception as detail_err:
                        print(f"[CUPS DETAIL ERROR] Failed to fetch details for {cups_name}: {detail_err}")

                    # Match printer using IP as primary, then robust fallbacks
                    matched_printer = None
                    
                    if printer_ip and printer_ip in db_printers_ip_map:
                        matched_printer = db_printers_ip_map[printer_ip]
                        print(f"[MATRIX_CUPS] MATCH BY IP: {cups_name} -> DB IP: {printer_ip}", flush=True)
                    
                    if not matched_printer:
                        cups_num = extract_printer_number(cups_name)
                        if cups_num is not None and cups_num in db_printers_num_map:
                            matched_printer = db_printers_num_map[cups_num]
                            print(f"[MATRIX_CUPS] MATCH BY NUM FALLBACK: {cups_name} -> Num: {cups_num}", flush=True)
                        else:
                            for db_id, pr_no, db_loc, db_ip in db_printers:
                                if pr_no and (cups_name.lower() in pr_no.lower() or pr_no.lower() in cups_name.lower()):
                                    matched_printer = (db_id, pr_no, db_loc, db_ip)
                                    print(f"[MATRIX_CUPS] MATCH BY SUBSTRING FALLBACK: {cups_name} -> PR No: {pr_no}", flush=True)
                                    break
                                
                    if matched_printer:
                        db_id, db_pr_no, db_loc, db_ip = matched_printer
                        
                        cursor.execute("UPDATE printers SET cups_queue_name = ? WHERE id = ?", (cups_name, db_id))
                        
                        if str(hedef_mahal) != str(db_loc):
                            cursor.execute("UPDATE printers SET location_code = ? WHERE id = ?", (hedef_mahal, db_id))
                            updated_count += 1
                            print(f"[MATRIX_CUPS] YAZICI GUNCEL: {cups_name} -> Mahal: {hedef_mahal}", flush=True)
                        else:
                            updated_count += 1
                            print(f"[MATRIX_CUPS] YAZICI EŞLEŞTİ: {cups_name} -> DB ID: {db_id}", flush=True)
            
            if parsed_on_this_page == 0 or current_page_first_printer == last_page_first_printer:
                break
                
            last_page_first_printer = current_page_first_printer
            first += 100
        
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": f"CUPS sorgusu tamamlandi. Toplam {updated_count} yazici guncellendi."})
        
    except Exception as e:
        print(f"[CUPS ERROR] {e}")
        return jsonify({"error": str(e)}), 500

@inventory_printers_bp.route('/cups/update_mahal', methods=['POST'])
@require_editor
def update_cups_mahal():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        data = request.json
        pr_no = data.get('pr_no')
        mahal = data.get('mahal')
        
        if not pr_no or not mahal:
            return jsonify({"error": "PR No ve Mahal bilgisi gereklidir."}), 400
            
        cursor.execute("INSERT INTO sync_status (operation, status, details) VALUES (?, ?, ?)", 
                       ("CUPS_SYNC", "STARTED", f"Printer: {pr_no}, New Mahal: {mahal}"))
        conn.commit()

        cursor.execute("SELECT location_code FROM printers WHERE pr_no = ? AND is_deleted = 0", (pr_no,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Yazıcı bulunamadı."}), 404
        old_location = row[0]

        cursor.execute("UPDATE printers SET location_code = ? WHERE pr_no = ?", (mahal, pr_no))
        
        cups_mahal = mahal.replace(".", "-")
        
        import requests
        cups_config = get_integration_config('CUPS') or {}; cups_base_url = cups_config.get('base_url', 'http://192.168.X.X:49631').rstrip('/'); cups_admin_url = f"{cups_base_url}/admin/"
        post_data = {
            "OP": "modify-printer",
            "PRINTER_NAME": pr_no,
            "PRINTER_LOCATION": cups_mahal,
            "printer_is_shared": "1",
            "confirm": "Yes"
        }
        
        cups_success = False
        error_detail = ""
        for attempt in range(3):
            try:
                resp = requests.post(cups_admin_url, data=post_data, timeout=5, verify=False)
                if resp.status_code == 200:
                    cups_success = True
                    break
                else:
                    error_detail = f"Status: {resp.status_code}"
            except Exception as e:
                error_detail = str(e)
                continue
        
        if cups_success:
            conn.commit()
            cursor.execute("INSERT INTO sync_status (operation, status, details) VALUES (?, ?, ?)", 
                           ("CUPS_SYNC", "SUCCESS", f"Printer: {pr_no} synced successfully"))
            conn.commit()
            from modules.logs_manager import log_change
            log_change("printers", pr_no, pr_no, "location_code", old_location, mahal, "system", "Admin")
            return jsonify({"success": True, "message": "SQL ve CUPS başarıyla güncellendi."})
        else:
            conn.rollback()
            cursor.execute("INSERT INTO sync_status (operation, status, details) VALUES (?, ?, ?)", 
                           ("CUPS_SYNC", "FAILED_COMPENSATED", f"Printer: {pr_no}, Error: {error_detail}"))
            conn.commit()
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

def update_cups_printer_location_wizard(pr_no, new_location):
    """CUPS Wizard ile yazıcı lokasyonunu değiştirir.
    CUPS 2.2.6 modify-printer işlemi wizard tabanlı çalışır:
    Step 1: Connection (DEVICE_URI)
    Step 2: Connection Details (BAUDRATE, PRINTER_LOCATION görünür)
    Step 3: Name/Location/Make (PRINTER_LOCATION override edilir)
    Step 4: Tamamlandı
    NOT: BeautifulSoup kullanmaz, sadece re (regex) ile parse eder.
    """
    import requests
    import re
    import base64

    # Normalize pr_no to PR-XXX format
    clean_digits = "".join(filter(str.isdigit, str(pr_no)))
    if clean_digits:
        pr_no = f"PR-{clean_digits.zfill(3)}"

    cups_config = get_integration_config('CUPS') or {}; CUPS_URL = cups_config.get('base_url', 'http://192.168.X.X:49631').rstrip('/')
    CUPS_USER = cups_config.get('auth_username') or 'root'
    CUPS_PASS = cups_config.get('auth_password') or '1234qqqQ'
    TIMEOUT = 30

    def parse_form(html):
        """CUPS wizard HTML'ini regex ile parse eder (bs4 gerektirmez)."""
        # İlk <FORM> etiketini bul
        form_match = re.search(r'<FORM\s[^>]*METHOD="POST"[^>]*>(.*?)</FORM>', html, re.DOTALL | re.IGNORECASE)
        if not form_match:
            return None, {}
        
        form_html = form_match.group(0)
        form_body = form_match.group(1)
        
        # Action
        action_m = re.search(r'ACTION="([^"]+)"', form_html, re.IGNORECASE)
        action = action_m.group(1) if action_m else '/admin'
        
        data = {}
        
        # Hidden inputs: <INPUT TYPE="HIDDEN" NAME="x" VALUE="y">
        for m in re.finditer(r'<INPUT\s+[^>]*TYPE="HIDDEN"[^>]*NAME="([^"]+)"[^>]*VALUE="([^"]*)"', form_body, re.IGNORECASE):
            data[m.group(1)] = m.group(2)
        # Also match reverse order: NAME before TYPE
        for m in re.finditer(r'<INPUT\s+[^>]*NAME="([^"]+)"[^>]*TYPE="HIDDEN"[^>]*VALUE="([^"]*)"', form_body, re.IGNORECASE):
            data[m.group(1)] = m.group(2)
        
        # Text inputs: <INPUT TYPE="TEXT" NAME="x" VALUE="y">
        for m in re.finditer(r'<INPUT\s+[^>]*TYPE="TEXT"[^>]*NAME="([^"]+)"[^>]*VALUE="([^"]*)"', form_body, re.IGNORECASE):
            data[m.group(1)] = m.group(2)
        for m in re.finditer(r'<INPUT\s+[^>]*NAME="([^"]+)"[^>]*TYPE="TEXT"[^>]*VALUE="([^"]*)"', form_body, re.IGNORECASE):
            if m.group(1) not in data:
                data[m.group(1)] = m.group(2)
        
        # Radio inputs with CHECKED: <INPUT TYPE="RADIO" NAME="x" VALUE="y" CHECKED>
        for m in re.finditer(r'<INPUT\s+[^>]*TYPE="RADIO"[^>]*NAME="([^"]+)"[^>]*VALUE="([^"]*)"[^>]*CHECKED', form_body, re.IGNORECASE):
            data[m.group(1)] = m.group(2)
        
        # Checkbox inputs with CHECKED: <INPUT TYPE="CHECKBOX" NAME="x" VALUE="y" CHECKED>
        for m in re.finditer(r'<INPUT\s+[^>]*TYPE="CHECKBOX"[^>]*NAME="([^"]+)"[^>]*VALUE="([^"]*)"[^>]*CHECKED', form_body, re.IGNORECASE):
            data[m.group(1)] = m.group(2)
        for m in re.finditer(r'<INPUT\s+[^>]*NAME="([^"]+)"[^>]*TYPE="CHECKBOX"[^>]*VALUE="([^"]*)"[^>]*CHECKED', form_body, re.IGNORECASE):
            data[m.group(1)] = m.group(2)
        
        # Select elements with SELECTED option
        for sel_m in re.finditer(r'<SELECT\s+[^>]*NAME="([^"]+)"[^>]*>(.*?)</SELECT>', form_body, re.DOTALL | re.IGNORECASE):
            name = sel_m.group(1)
            options_html = sel_m.group(2)
            selected = re.search(r'<OPTION\s+[^>]*VALUE="([^"]+)"[^>]*SELECTED', options_html, re.IGNORECASE)
            if selected:
                data[name] = selected.group(1)
            else:
                first = re.search(r'<OPTION\s+[^>]*VALUE="([^"]+)"', options_html, re.IGNORECASE)
                if first:
                    data[name] = first.group(1)
        
        # Textarea
        for ta_m in re.finditer(r'<TEXTAREA\s+[^>]*NAME="([^"]+)"[^>]*>(.*?)</TEXTAREA>', form_body, re.DOTALL | re.IGNORECASE):
            data[ta_m.group(1)] = ta_m.group(2)
        
        return action, data

    try:
        session = requests.Session()
        b64_auth = base64.b64encode(f"{CUPS_USER}:{CUPS_PASS}".encode()).decode()
        session.headers.update({'Authorization': f'Basic {b64_auth}'})

        # Get SID from printer page
        r = session.get(f"{CUPS_URL}/printers/{pr_no}", verify=False, timeout=TIMEOUT)
        sid_m = re.search(r'org\.cups\.sid.*?VALUE="([^"]+)"', r.text, re.I)
        if not sid_m:
            return False, f"{pr_no} için CUPS SID bulunamadı"
        sid = sid_m.group(1)

        # Start modify wizard
        html = session.post(f"{CUPS_URL}/admin/", data={
            'org.cups.sid': sid, 'OP': 'modify-printer', 'printer_name': pr_no
        }, verify=False, timeout=TIMEOUT).text

        if 'unauthorized' in html.lower():
            return False, "CUPS yetkilendirme hatası (401)"

        # Navigate wizard steps (max 6)
        for step in range(6):
            action, data = parse_form(html)
            if not action or not data:
                return True, f"{pr_no} CUPS lokasyonu '{new_location}' olarak güncellendi."

            # Override PRINTER_LOCATION at every step where it appears
            if 'PRINTER_LOCATION' in data:
                data['PRINTER_LOCATION'] = new_location.replace(".", "-")
                data['printer_is_shared'] = '1'

            html = session.post(f"{CUPS_URL}{action}", data=data, verify=False, timeout=TIMEOUT).text

        return True, f"{pr_no} CUPS wizard tamamlandı."

    except Exception as e:
        import traceback
        traceback.print_exc()
        return False, f"CUPS Wizard Hatası: {str(e)}"

@inventory_printers_bp.route('/cups/modify_location', methods=['POST'])
@require_auth
def modify_cups_location():
    try:
        data = request.json
        pr_no = data.get('pr_no')
        new_location = data.get('location')
        
        if not pr_no or not new_location:
            return jsonify({"error": "PR No ve Yeni Mahal bilgisi gereklidir."}), 400
        
        success, message = update_cups_printer_location_wizard(pr_no, new_location)
        
        if success:
            return jsonify({"success": True, "message": message})
        else:
            return jsonify({"error": f"CUPS İşlemi başarısız: {message}"}), 500
            
    except Exception as e:
        print(f"[CUPS MODIFY ERROR] {e}")
        return jsonify({"error": str(e)}), 500

@inventory_printers_bp.route('/device/<int:device_id>', methods=['GET'])
@require_auth
def get_device_detail(device_id):
    try:
        conn = get_db_connection()
        if not conn: return jsonify({"error": "Veritabanı bağlantısı yok"}), 500
        
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM printers WHERE id = ?", (device_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return jsonify({"error": "Cihaz bulunamadı"}), 404
            
        columns = [column[0] for column in cursor.description]
        d = normalize_row(dict(zip(columns, row)))
        d['device_class'] = 'PRINTER'
        
        raw_no = str(d.get('pr_no') or '')
        if raw_no.isdigit(): d['pr_no'] = f"PR-{raw_no.zfill(3)}"
        elif '-' not in raw_no and len(raw_no) > 0:
             digits = "".join(filter(str.isdigit, raw_no))
             if digits: d['pr_no'] = f"PR-{digits.zfill(3)}"
             
        pr_num = extract_printer_number(d.get('pr_no'))
        service_status = None
        if pr_num is not None:
            cursor.execute("SELECT pr_no, status FROM printer_service WHERE is_deleted = 0 AND return_date IS NULL")
            for s_row in cursor.fetchall():
                if extract_printer_number(s_row[0]) == pr_num:
                    service_status = s_row[1]
                    break
        
        if service_status:
            d['status'] = service_status
            if service_status == 'Arızalı':
                d['is_faulty'] = 1
                d['in_service'] = 0
            elif service_status == 'Serviste':
                d['is_faulty'] = 0
                d['in_service'] = 1
        else:
            if d.get('is_faulty') == 1 or d.get('is_faulty') == True: d['status'] = 'Arızalı'
            elif d.get('warehouse') == 1: d['status'] = 'Depoda'
            elif d.get('in_service') == 1 or d.get('serviste') == 1: d['status'] = 'Serviste'
            elif d.get('without_location') == 1: d['status'] = 'Kayıp'
            else: d['status'] = 'Kurulu'
        
        d['seri'] = d.get('serial_no')
        d['mahal'] = d.get('location_code') or d.get('mahal') or ''
            
        conn.close()
        return jsonify({"success": True, "data": d})
        
    except Exception as e:
        print(f"[API ERROR] printer get_device_detail: {e}")
        return jsonify({"error": str(e)}), 500
@inventory_printers_bp.route('/check_serial', methods=['POST'])
def check_serial():
    """Seri numarasâ”€â–’nâ”€â–’n veritabanâ”€â–’nda olup olmadâ”€â–’â”€şâ”€â–’nâ”€â–’ kontrol eder."""
    try:
        data = request.json
        serial = data.get('serial')
        if not serial:
            return jsonify({"error": "Seri no gereklidir."}), 400
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Tâ”œâ•m cihaz tablolarâ”€â–’nda ara
        tables = ['barcode_readers', 'barcode_printers', 'scanners']
        found = False
        table_found = ""
        
        for table in tables:
            cursor.execute(f"SELECT id FROM {table} WHERE serial_no = ? AND is_deleted = 0", (serial,))
            if cursor.fetchone():
                found = True
                table_found = table
                break
                
        conn.close()
        return jsonify({"success": True, "exists": found, "table": table_found})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@inventory_printers_bp.route('/auto_register', methods=['POST'])
@require_editor
def auto_register():
    """Yeni cihazâ”€â–’ otomatik olarak ilgili tabloya kaydeder."""
    try:
        data = request.json
        serial = data.get('serial')
        device_type = data.get('device_type') # 'BARCODE_READER', 'BARCODE_PRINTER', 'SCANNER'
        pc_no = data.get('pc_no')
        
        if not serial or not device_type:
            return jsonify({"error": "Eksik bilgi."}), 400
            
        table_map = {
            'BARCODE_READER': 'barcode_readers',
            'BARCODE_PRINTER': 'barcode_printers',
            'SCANNER': 'scanners'
        }
        table_name = table_map.get(device_type)
        if not table_name:
            return jsonify({"error": "Geâ”œğersiz cihaz tâ”œâ•râ”œâ•."}), 400
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Zaten var mâ”€â–’ kontrol et (Duplicate â”œÃ‚nleme, is_deleted=0)
        cursor.execute(f"SELECT id FROM {table_name} WHERE serial_no = ? AND is_deleted = 0", (serial,))
        if cursor.fetchone():
            conn.close()
            return jsonify({"success": True, "message": "Cihaz zaten kayâ”€â–’tlâ”€â–’."})
            
        # Yeni isim â”œâ•ret (BO-001, BY-001, TR-001)
        prefix_map = {'barcode_readers': 'BO', 'barcode_printers': 'BY', 'scanners': 'TR'}
        prefix = prefix_map[table_name]
        
        cursor.execute(f"SELECT MAX(id) FROM {table_name}")
        max_id = cursor.fetchone()[0] or 0
        new_name = f"{prefix}-{(max_id + 1):03d}"
        
        query = f"INSERT INTO {table_name} (name, serial_no, status, pc_no) VALUES (?, ?, ?, ?)"
        cursor.execute(query, (new_name, serial, 'Kurulu', pc_no))
        
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": f"{new_name} olarak kaydedildi."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
# ═══════════════ MOBİL CUPS YAZDIRMA ═══════════════
@inventory_printers_bp.route('/cups/list_printers', methods=['GET'])
@require_auth
def list_cups_printers():
    """CUPS web arayüzünden tüm yazıcı sayfalarını gezerek listesini çeker ve JSON olarak döner."""
    try:
        import requests as http_req
        from bs4 import BeautifulSoup

        printers = []
        first = 0
        last_page_first_printer = None
        show_all = request.args.get('show_all', 'false') == 'true'
        cups_config = get_integration_config('CUPS') or {}
        cups_base_url = cups_config.get('base_url', 'http://192.168.X.X:49631').rstrip('/')

        while True:
            cups_url = f"{cups_base_url}/printers/?FIRST={first}"
            response = http_req.get(cups_url, timeout=10, verify=False)

            if response.status_code != 200:
                if first == 0:
                    return jsonify({"error": f"CUPS sunucusu yanıt vermedi: {response.status_code}"}), 502
                break

            soup = BeautifulSoup(response.text, 'html.parser')
            rows = soup.find_all('tr')

            parsed_on_this_page = 0
            current_page_first_printer = None

            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 4:
                    name = cols[0].get_text(strip=True)
                    if not name:
                        continue
                        
                    if current_page_first_printer is None:
                        current_page_first_printer = name
                        
                    parsed_on_this_page += 1

                    status_text = cols[1].get_text(strip=True) if len(cols) > 1 else ''
                    location = cols[2].get_text(strip=True).replace("-", ".") if len(cols) > 2 else ''
                    
                    # Status classification
                    status_lower = status_text.lower()
                    if 'idle' in status_lower or 'boşta' in status_lower:
                        status = 'idle'
                    elif 'processing' in status_lower or 'yazdır' in status_lower:
                        status = 'processing'
                    elif 'paused' in status_lower or 'duraklat' in status_lower:
                        status = 'paused'
                    elif 'stopped' in status_lower:
                        status = 'stopped'
                    else:
                        status = 'unknown'
                    
                    # Skip paused/stopped printers by default
                    if not show_all and status in ('paused', 'stopped'):
                        continue

                    # Çift (duplicate) yazıcıları önlemek için kontrol et
                    if not any(p['name'] == name for p in printers):
                        printers.append({
                            "name": name,
                            "status": status,
                            "status_text": status_text,
                            "location": location
                        })

            # Eğer bir sayfada 100'den az yazıcı geldiyse, bu son sayfadır.
            # CUPS pagination bug'ını (400. indekste başa sarması) önlemek için burada çıkıyoruz.
            if parsed_on_this_page < 100 or current_page_first_printer == last_page_first_printer:
                break
                
            last_page_first_printer = current_page_first_printer
            first += 100

        return jsonify({"success": True, "printers": printers, "total": len(printers)})

    except Exception as e:
        print(f"[CUPS LIST ERROR] {e}")
        return jsonify({"error": f"CUPS yazıcı listesi alınamadı: {str(e)}"}), 500


@inventory_printers_bp.route('/cups/print_job', methods=['POST'])
@require_auth
def cups_print_job():
    """Mobil cihazdan gelen dosyayı IPP protokolü ile CUPS yazıcısına gönderir."""
    import struct
    import requests as http_req

    cups_config = get_integration_config('CUPS') or {}; CUPS_URL = cups_config.get('base_url', 'http://192.168.X.X:49631').rstrip('/')
    ALLOWED_TYPES = {
        'application/pdf': 'application/pdf',
        'image/png': 'image/png',
        'image/jpeg': 'image/jpeg',
        'image/jpg': 'image/jpeg'
    }
    MAX_SIZE = 10 * 1024 * 1024  # 10 MB

    try:
        printer_name_raw = request.form.get('printer_name')
        copies = int(request.form.get('copies', 1))

        if not printer_name_raw:
            return jsonify({"error": "Yazıcı adı belirtilmedi."}), 400
            
        printer_name = printer_name_raw
        
        # Mobil UI'dan veritabanı formatında (ip veya pr_no) gelen ismi, CUPS tam adına çevirme
        import re
        if '.' in printer_name_raw:
            cups_search = printer_name_raw.replace('.', '_')
            try:
                resp = http_req.get(CUPS_URL + "/printers/", verify=False, timeout=4)
                if resp.status_code == 200:
                    html = resp.text
                    # CUPS kuyruk isimlerini sayfadan regex ile bulalım (örn: 10_241_23_3_Lexmark)
                    match = re.search(rf'href="/printers/([^"]*{cups_search}[^"]*)"', html)
                    if match:
                        printer_name = match.group(1)
                        print(f"[CUPS MATCH] {printer_name_raw} -> resolved to -> {printer_name}")
            except Exception as e:
                print(f"[CUPS MATCH ERROR] Could not resolve {printer_name_raw}: {e}")

        if copies < 1 or copies > 99:
            return jsonify({"error": "Kopya sayısı 1-99 arasında olmalıdır."}), 400

        if 'file' not in request.files:
            return jsonify({"error": "Dosya yüklenmedi."}), 400

        file = request.files['file']
        if not file.filename:
            return jsonify({"error": "Dosya adı boş."}), 400

        # MIME type kontrolü
        content_type = file.content_type or ''
        if content_type not in ALLOWED_TYPES:
            return jsonify({"error": f"Desteklenmeyen dosya türü: {content_type}. Sadece PDF, PNG ve JPG kabul edilir."}), 400

        doc_format = ALLOWED_TYPES[content_type]

        # Dosya boyutu kontrolü
        file_data = file.read()
        if len(file_data) > MAX_SIZE:
            return jsonify({"error": f"Dosya boyutu çok büyük ({len(file_data) // (1024*1024)} MB). Maksimum 10 MB."}), 400

        if len(file_data) == 0:
            return jsonify({"error": "Dosya boş."}), 400

        from urllib.parse import urlparse
        cups_host = urlparse(CUPS_URL).hostname or '192.168.X.X'
        printer_uri = f"ipp://{cups_host}:49631/printers/{printer_name}"
        job_name = file.filename or "mobile-print-job"
        username = "it-envanter"

        def ipp_str_attr(tag, name, value):
            n = name.encode('utf-8')
            v = value.encode('utf-8')
            return struct.pack('>bH', tag, len(n)) + n + struct.pack('>H', len(v)) + v

        def ipp_int_attr(tag, name, value):
            n = name.encode('utf-8')
            return struct.pack('>bH', tag, len(n)) + n + struct.pack('>Hi', 4, value)

        # IPP header: version 1.1, Print-Job (0x0002), request-id 1
        ipp_header = struct.pack('>bbHI', 1, 1, 0x0002, 1)

        # Operation attributes group (tag 0x01)
        ipp_body = b'\x01'
        ipp_body += ipp_str_attr(0x47, 'attributes-charset', 'utf-8')
        ipp_body += ipp_str_attr(0x48, 'attributes-natural-language', 'en')
        ipp_body += ipp_str_attr(0x45, 'printer-uri', printer_uri)
        ipp_body += ipp_str_attr(0x42, 'requesting-user-name', username)
        ipp_body += ipp_str_attr(0x42, 'job-name', job_name)
        ipp_body += ipp_str_attr(0x49, 'document-format', doc_format)

        # Job attributes group (tag 0x02)
        ipp_body += b'\x02'
        ipp_body += ipp_int_attr(0x21, 'copies', copies)

        # End of attributes (tag 0x03)
        ipp_body += b'\x03'

        # IPP isteğini gönder
        ipp_data = ipp_header + ipp_body + file_data

        ipp_response = http_req.post(
            f"{CUPS_URL}/printers/{printer_name}",
            data=ipp_data,
            headers={'Content-Type': 'application/ipp'},
            timeout=30,
            verify=False
        )

        # IPP yanıtını parse et
        if len(ipp_response.content) >= 8:
            resp_version_major, resp_version_minor, status_code, request_id = struct.unpack('>bbHI', ipp_response.content[:8])

            if status_code <= 0x00FF:
                # Başarılı
                # Job-ID'yi bul (opsiyonel)
                job_id = None
                resp_data = ipp_response.content[8:]
                # Basit job-id arama (integer attribute tag 0x21, name "job-id")
                job_id_marker = b'\x21' + struct.pack('>H', 6) + b'job-id' + struct.pack('>H', 4)
                idx = resp_data.find(job_id_marker)
                if idx >= 0:
                    val_start = idx + len(job_id_marker)
                    if val_start + 4 <= len(resp_data):
                        job_id = struct.unpack('>i', resp_data[val_start:val_start+4])[0]

                msg = f"Yazdırma işi başarıyla gönderildi → {printer_name}"
                if job_id:
                    msg += f" (İş No: {job_id})"

                print(f"[CUPS PRINT] {msg} | Dosya: {file.filename} | Kopya: {copies}")
                return jsonify({"success": True, "message": msg, "job_id": job_id})
            else:
                error_msg = f"CUPS yazdırma hatası (IPP Durum: 0x{status_code:04X})"
                print(f"[CUPS PRINT ERROR] {error_msg}")
                return jsonify({"error": error_msg}), 500
        else:
            return jsonify({"error": "CUPS sunucusundan geçersiz yanıt alındı."}), 502

    except Exception as e:
        print(f"[CUPS PRINT ERROR] {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Yazdırma işi gönderilemedi: {str(e)}"}), 500


@inventory_printers_bp.route('/cups/pause', methods=['POST'])
@require_editor
def pause_reject_cups():
    try:
        data = request.json
        pr_no = data.get('pr_no')
        if not pr_no:
            return jsonify({'error': 'PR No gereklidir.'}), 400
            
        import requests as http_req
        import re
        import urllib3
        urllib3.disable_warnings()
        
        from core.integrations import get_integration_config
        cups_config = get_integration_config('CUPS') or {}
        cups_base_url = cups_config.get('base_url', 'http://192.168.X.X:49631').rstrip('/')
        username = cups_config.get('auth_username') or cups_config.get('username', 'admin')
        password = cups_config.get('auth_password') or cups_config.get('password', '')
        
        printer_url = f"{cups_base_url}/printers/{pr_no}"
        
        session = http_req.Session()
        if username and password:
            session.auth = (username, password)
        
        # SID token'ı al
        get_resp = session.get(printer_url, verify=False, timeout=10)
        if get_resp.status_code == 404:
            return jsonify({'error': f"CUPS'ta {pr_no} adında bir yazıcı bulunamadı."}), 404
        if get_resp.status_code == 401:
            return jsonify({'error': "CUPS yetkilendirme hatası. Entegrasyon Ayarlarından CUPS şifresini kontrol edin."}), 401
            
        sid_match = re.search(r'NAME="org\.cups\.sid"\s+VALUE="([^"]+)"', get_resp.text, re.IGNORECASE)
        sid = sid_match.group(1) if sid_match else ""
        
        # 1. Pause Printer
        resp1 = session.post(printer_url, data={'org.cups.sid': sid, 'OP': 'stop-printer'}, timeout=10, verify=False)
        
        # SID yeniden al (CUPS her işlemde SID değiştirebilir)
        get_resp2 = session.get(printer_url, verify=False, timeout=10)
        sid_match2 = re.search(r'NAME="org\.cups\.sid"\s+VALUE="([^"]+)"', get_resp2.text, re.IGNORECASE)
        sid2 = sid_match2.group(1) if sid_match2 else sid
        
        # 2. Reject Jobs
        resp2 = session.post(printer_url, data={'org.cups.sid': sid2, 'OP': 'reject-jobs'}, timeout=10, verify=False)
        
        if resp1.status_code == 401 or resp2.status_code == 401:
            return jsonify({'error': 'CUPS yetkilendirme hatası (401). CUPS ayarlarına geçerli bir yetkili şifresi girmelisiniz.'}), 401
        
        return jsonify({'success': True, 'message': f'{pr_no} CUPS üzerinde duraklatıldı ve reddedildi.'})
    except http_req.exceptions.RequestException as e:
        return jsonify({'success': False, 'error': f"CUPS bağlantı hatası: {str(e)}"}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@inventory_printers_bp.route('/cups/resume', methods=['POST'])
@require_editor
def resume_accept_cups():
    try:
        data = request.json
        pr_no = data.get('pr_no')
        if not pr_no:
            return jsonify({'error': 'PR No gereklidir.'}), 400
            
        import requests as http_req
        import re
        import urllib3
        urllib3.disable_warnings()
        
        from core.integrations import get_integration_config
        cups_config = get_integration_config('CUPS') or {}
        cups_base_url = cups_config.get('base_url', 'http://192.168.X.X:49631').rstrip('/')
        username = cups_config.get('auth_username') or cups_config.get('username', 'admin')
        password = cups_config.get('auth_password') or cups_config.get('password', '')
        
        printer_url = f"{cups_base_url}/printers/{pr_no}"
        
        session = http_req.Session()
        if username and password:
            session.auth = (username, password)
        
        # SID token'ı al
        get_resp = session.get(printer_url, verify=False, timeout=10)
        if get_resp.status_code == 404:
            return jsonify({'error': f"CUPS'ta {pr_no} adında bir yazıcı bulunamadı."}), 404
        if get_resp.status_code == 401:
            return jsonify({'error': "CUPS yetkilendirme hatası. Entegrasyon Ayarlarından CUPS şifresini kontrol edin."}), 401
            
        sid_match = re.search(r'NAME="org\.cups\.sid"\s+VALUE="([^"]+)"', get_resp.text, re.IGNORECASE)
        sid = sid_match.group(1) if sid_match else ""
        
        # 1. Resume Printer
        resp1 = session.post(printer_url, data={'org.cups.sid': sid, 'OP': 'start-printer'}, timeout=10, verify=False)
        
        # SID yeniden al
        get_resp2 = session.get(printer_url, verify=False, timeout=10)
        sid_match2 = re.search(r'NAME="org\.cups\.sid"\s+VALUE="([^"]+)"', get_resp2.text, re.IGNORECASE)
        sid2 = sid_match2.group(1) if sid_match2 else sid
        
        # 2. Accept Jobs
        resp2 = session.post(printer_url, data={'org.cups.sid': sid2, 'OP': 'accept-jobs'}, timeout=10, verify=False)
        
        if resp1.status_code == 401 or resp2.status_code == 401:
            return jsonify({'error': 'CUPS yetkilendirme hatası (401). CUPS ayarlarına geçerli bir yetkili şifresi girmelisiniz.'}), 401
        
        return jsonify({'success': True, 'message': f'{pr_no} CUPS üzerinde uyandırıldı ve iş kabulüne açıldı.'})
    except http_req.exceptions.RequestException as e:
        return jsonify({'success': False, 'error': f"CUPS bağlantı hatası: {str(e)}"}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


import requests
from flask import request, jsonify

@inventory_printers_bp.route('/batch_action', methods=['POST'])
@require_editor
def batch_action():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        data = request.json
        action = data.get('action') # 'add' or 'remove'
        bim_function = data.get('bim_function')
        command = data.get('command')
        targets = data.get('targets', [])
        bim_user = data.get('bim_user')
        bim_pass = data.get('bim_pass')
        user = data.get('user', 'system')
        
        if bim_pass == '********':
            user_id = request.current_user.get('user_id')
            if user_id:
                from core.encryption import decrypt_password
                cursor.execute("SELECT bim_pass FROM users WHERE id = ?", (user_id,))
                user_row = cursor.fetchone()
                if user_row and user_row[0]:
                    bim_pass = decrypt_password(user_row[0])

        success_count = 0
        failed_targets = []

        for target in targets:
            pc_id = target.get('value')
            cursor.execute("SELECT id, ip, pc_no FROM pcs WHERE id = ?", (pc_id,))
            pc_row = cursor.fetchone()
            if not pc_row:
                failed_targets.append(f"PC ID {pc_id} bulunamadi.")
                continue
            
            p_id, p_ip, p_name = pc_row
            if not p_ip:
                failed_targets.append(f"{p_name} (IP yok)")
                continue

            bim_config = get_integration_config('BIM') or {}
            bim_base_url = bim_config.get('base_url', 'http://bim.ornek-kurum.com').rstrip('/')
            base_url = f"{bim_base_url}/Handler.ashx"
            login_data = {
                "Functions": "Login",
                "UserName": bim_user,
                "Password": bim_pass
            }
            browser_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            }
            
            try:
                login_resp = requests.post(base_url, data=login_data, headers=browser_headers, timeout=10)
                if login_resp.status_code != 200 or login_resp.text.strip() == "Error" or not login_resp.text.strip():
                    failed_targets.append(f"{p_name} (BIM Giris Basarisiz)")
                    continue
                ipa_session = login_resp.text.strip()
            except Exception as e:
                failed_targets.append(f"{p_name} (BIM Login Hatasi)")
                continue

            send_data = {
                "UserName": bim_user,
                "IPAddress": p_ip
            }
            if bim_function in ["AddPrinter", "RemovePrinter"]:
                send_data["Functions"] = bim_function
                send_data["PrinterName"] = command
            else:
                send_data["Functions"] = "RunCommand"
                send_data["Commands"] = command

            headers = {
                "IPASession": ipa_session,
                "User-Agent": browser_headers["User-Agent"],
                "Referer": f"{bim_base_url}/",
                "Origin": bim_base_url
            }

            try:
                cmd_resp = requests.post(base_url, data=send_data, headers=headers, timeout=15)
                if cmd_resp.status_code != 200 or "Error" in cmd_resp.text:
                    failed_targets.append(f"{p_name} (BIM Hatasi: {cmd_resp.text.strip()})")
                    continue
            except Exception as e:
                failed_targets.append(f"{p_name} (BIM Cmd Hatasi)")
                continue

            success_count += 1
        
        return jsonify({
            "success": True,
            "success_count": success_count,
            "failed": failed_targets
        })

    except Exception as e:
        import traceback
        with open('batch_action_error.log', 'w', encoding='utf-8') as f:
            f.write(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@inventory_printers_bp.route('/add', methods=['POST'])
@require_admin
def add_device():
    try:
        data = request.json
        device_type = data.get('device_type') # PRINTER, BARCODE_PRINTER, BARCODE_READER, SCANNER
        
        if not device_type:
            return jsonify({"error": "Cihaz türü belirtilmedi."}), 400
            
        table_map = {
            'PRINTER': 'printers',
            'BARCODE_PRINTER': 'barcode_printers',
            'BARCODE_READER': 'barcode_readers',
            'SCANNER': 'scanners'
        }
        
        table_name = table_map.get(device_type)
        if not table_name:
            return jsonify({"error": "Geçersiz cihaz türü."}), 400
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Name automatic generation if empty
        name = data.get('name')
        if not name or name.strip() == '':
            prefix_map = {
                'printers': 'PR',
                'barcode_printers': 'BY',
                'barcode_readers': 'BO',
                'scanners': 'TR'
            }
            prefix = prefix_map.get(table_name)
            cursor.execute(f"SELECT MAX(id) FROM {table_name}")
            max_id_row = cursor.fetchone()
            max_id = max_id_row[0] if (max_id_row and max_id_row[0]) else 0
            name = f"{prefix}-{(max_id + 1):03d}"
            
        if table_name == 'printers':
            pr_no = data.get('pr_no') or name
            model = data.get('model')
            serial_no = data.get('serial_no')
            mac = data.get('mac')
            ip = data.get('ip')
            location_code = data.get('location_code')
            status = data.get('status') or 'Kurulu'
            on_field = 1 if status == 'Kurulu' else 0
            warehouse = 1 if status == 'Depoda' else 0
            is_faulty = 1 if status == 'Arızalı' else 0
            in_service = 1 if status == 'Serviste' else 0
            
            query = """INSERT INTO printers 
                       (pr_no, model, serial_no, mac, ip, location_code, status, on_field, warehouse, is_faulty, serviste, is_deleted)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)"""
            cursor.execute(query, (pr_no, model, serial_no, mac, ip, location_code, status, on_field, warehouse, is_faulty, in_service))
        else:
            model = data.get('model')
            serial_no = data.get('serial_no')
            pc_no = data.get('pc_no')
            status = data.get('status') or 'Kurulu'
            
            query = f"""INSERT INTO {table_name} 
                       (name, model, serial_no, pc_no, status, is_deleted)
                       VALUES (?, ?, ?, ?, ?, 0)"""
            cursor.execute(query, (name, model, serial_no, pc_no, status))

        conn.commit()
        conn.close()
        
        from modules.logs_manager import log_change
        log_change(table_name, name, name, 'creation', None, 'New Device Added', 'system', 'Admin')

        return jsonify({"success": True, "message": f"{name} başarıyla eklendi."})
    except Exception as e:
        print(f"[ADD DEVICE ERROR] {e}")
        return jsonify({"error": str(e)}), 500

@inventory_printers_bp.route('/live_status/<int:printer_id>', methods=['GET'])
@limiter.exempt
@require_auth
def get_live_status_by_id(printer_id):
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"success": False, "error": "Veritabanı bağlantısı yok"}), 500

        cursor = conn.cursor()
        cursor.execute(
            "SELECT ip, cups_queue_name, pr_no FROM printers WHERE id = ? AND is_deleted = 0",
            (printer_id,)
        )
        row = cursor.fetchone()
        if not row:
            status = {
                "status": "Bilinmiyor",
                "toner": "Bilinmiyor",
                "is_online": False,
                "cups_state": "Bilinmiyor",
                "cups_is_paused": False,
                "cups_is_rejecting": False
            }
            payload = {"success": True, "data": status}
            payload.update(status)
            return jsonify(payload), 404

        ip = row[0]
        cups_queue_name = row[1]
        pr_no = row[2]

        from modules.printer_live_status import fetch_printer_status
        status = fetch_printer_status(ip) if ip else {
            "status": "Bilinmiyor",
            "toner": "Bilinmiyor",
            "is_online": False
        }

        # CUPS status fetch. Keep both the old wrapped response and top-level fields
        # so older and newer frontend callers remain compatible.
        q_name = cups_queue_name or pr_no
        status['cups_state'] = "Bilinmiyor"
        status['cups_is_paused'] = False
        status['cups_is_rejecting'] = False

        if q_name:
            try:
                cups_config = get_integration_config('CUPS') or {}
                cups_base_url = cups_config.get('base_url', 'http://192.168.X.X:49631').rstrip('/')
                resp = requests.get(f"{cups_base_url}/printers/{q_name}", timeout=3, verify=False)
                html = resp.text.lower()

                is_paused = 'value="start-printer"' in html or "paused" in html or "durduruldu" in html
                is_active = 'value="stop-printer"' in html or "idle" in html or "active" in html or "aktif" in html
                is_rejecting = "rejecting" in html or "reddediyor" in html or "iş kabul edilmiyor" in html

                state_match = re.search(
                    r'\(\s*(Idle|Paused|Processing)[^,]*,?\s*(Accepting[^,]*|Rejecting[^,]*),',
                    resp.text,
                    re.IGNORECASE
                )
                if state_match:
                    st = state_match.group(1).strip()
                    if st.lower() == 'idle':
                        st = 'Boşta'
                    elif st.lower() == 'paused':
                        st = 'Durduruldu'
                    elif st.lower() == 'processing':
                        st = 'İşleniyor'

                    status_str = f"{st}"
                    if "accepting" in state_match.group(2).lower():
                        status_str += " (Kabul Ediyor)"
                        is_rejecting = False
                    elif "rejecting" in state_match.group(2).lower():
                        status_str += " (Reddediyor)"
                        is_rejecting = True
                    status['cups_state'] = status_str
                else:
                    if is_paused:
                        status['cups_state'] = "Durduruldu"
                    elif is_active:
                        status['cups_state'] = "Aktif"

                status['cups_is_paused'] = is_paused
                status['cups_is_rejecting'] = is_rejecting
            except Exception:
                status['cups_state'] = "Erişim Yok"
                status['cups_is_rejecting'] = False

        payload = {"success": True, "data": status}
        payload.update(status)
        return jsonify(payload)
    except Exception as e:
        print(f"LIVE STATUS ERROR: {e}")
        status = {
            "status": "Bilinmiyor",
            "toner": "Bilinmiyor",
            "is_online": False,
            "cups_state": "Bilinmiyor",
            "cups_is_paused": False,
            "cups_is_rejecting": False
        }
        payload = {"success": False, "error": str(e), "data": status}
        payload.update(status)
        return jsonify(payload), 500
    finally:
        if conn:
            conn.close()

@inventory_printers_bp.route('/cups/toggle_pause', methods=['POST'])
@require_editor
def toggle_cups_pause():
    try:
        data = request.json
        printer_id = data.get('id')
        action_type = data.get('action') # 'pause' or 'resume'
        
        if not printer_id or action_type not in ['pause', 'resume']:
            return jsonify({"error": "Geçersiz parametreler."}), 400
            
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT cups_queue_name, pr_no FROM printers WHERE id = ? AND is_deleted = 0", (printer_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return jsonify({"error": "Yazıcı bulunamadı"}), 404
            
        q_name = row[0] or row[1]
        if not q_name:
            return jsonify({"error": "Yazıcı CUPS kuyruk adı bulunamadı"}), 400
            
        import requests
        import base64
        import re
        from core.integrations import get_integration_config
        cups_config = get_integration_config('CUPS') or {}
        cups_base_url = cups_config.get('base_url', 'http://192.168.X.X:49631').rstrip('/')
        cups_user = cups_config.get('auth_username') or 'root'
        cups_pass = cups_config.get('auth_password') or '1234qqqQ'
        
        session = requests.Session()
        b64_auth = base64.b64encode(f"{cups_user}:{cups_pass}".encode()).decode()
        session.headers.update({'Authorization': f'Basic {b64_auth}'})
        
        r = session.get(f"{cups_base_url}/printers/{q_name}", verify=False, timeout=5)
        sid_m = re.search(r'org\.cups\.sid.*?VALUE="([^"]+)"', r.text, re.I)
        if not sid_m:
            return jsonify({"error": "CUPS oturumu alınamadı (SID bulunamadı)"}), 500
        sid = sid_m.group(1)
        
        op = "stop-printer" if action_type == 'pause' else "start-printer"
        
        resp = session.post(f"{cups_base_url}/printers/{q_name}", data={
            'org.cups.sid': sid,
            'OP': op,
            'printer_name': q_name
        }, verify=False, timeout=5)
        
        if resp.status_code == 200 and 'unauthorized' not in resp.text.lower():
            return jsonify({"success": True, "message": "İşlem başarıyla uygulandı."})
        else:
            return jsonify({"error": "CUPS sunucusu isteği reddetti veya yetki hatası."}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@inventory_printers_bp.route('/cups/toggle_reject', methods=['POST'])
@require_editor
def toggle_cups_reject():
    try:
        data = request.json
        printer_id = data.get('id')
        action_type = data.get('action') # 'reject' or 'accept'
        
        if not printer_id or action_type not in ['reject', 'accept']:
            return jsonify({"error": "Geçersiz parametreler."}), 400
            
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT cups_queue_name, pr_no FROM printers WHERE id = ? AND is_deleted = 0", (printer_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return jsonify({"error": "Yazıcı bulunamadı"}), 404
            
        q_name = row[0] or row[1]
        if not q_name:
            return jsonify({"error": "Yazıcı CUPS kuyruk adı bulunamadı"}), 400
            
        import requests
        import base64
        import re
        from core.integrations import get_integration_config
        cups_config = get_integration_config('CUPS') or {}
        cups_base_url = cups_config.get('base_url', 'http://192.168.X.X:49631').rstrip('/')
        cups_user = cups_config.get('auth_username') or 'root'
        cups_pass = cups_config.get('auth_password') or '1234qqqQ'
        
        session = requests.Session()
        b64_auth = base64.b64encode(f"{cups_user}:{cups_pass}".encode()).decode()
        session.headers.update({'Authorization': f'Basic {b64_auth}'})
        
        r = session.get(f"{cups_base_url}/printers/{q_name}", verify=False, timeout=5)
        sid_m = re.search(r'org\.cups\.sid.*?VALUE="([^"]+)"', r.text, re.I)
        if not sid_m:
            return jsonify({"error": "CUPS oturumu alınamadı (SID bulunamadı)"}), 500
        sid = sid_m.group(1)
        
        op = "reject-jobs" if action_type == 'reject' else "accept-jobs"
        
        resp = session.post(f"{cups_base_url}/printers/{q_name}", data={
            'org.cups.sid': sid,
            'OP': op,
            'printer_name': q_name
        }, verify=False, timeout=5)
        
        if resp.status_code == 200 and 'unauthorized' not in resp.text.lower():
            return jsonify({"success": True, "message": "İşlem başarıyla uygulandı."})
        else:
            return jsonify({"error": "CUPS sunucusu isteği reddetti veya yetki hatası."}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

