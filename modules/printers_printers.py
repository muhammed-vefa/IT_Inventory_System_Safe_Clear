import os
from core.utils import normalize_row
from flask import Blueprint, jsonify, request
from core.database_sql import get_db_connection
from core.auth import require_auth, require_admin, require_editor

printers_printers_bp = Blueprint('printers_printers', __name__)

@printers_printers_bp.route('/get_all', methods=['GET'])
@require_auth
def get_all():
    conn = get_db_connection()
    if not conn: return jsonify([])
    cursor = conn.cursor()
    
    all_devices = []
    try:
        query = "SELECT * FROM printers WHERE is_deleted = 0"
        cursor.execute(query)
        columns = [column[0] for column in cursor.description]
        for row in cursor.fetchall():
            d = normalize_row(dict(zip(columns, row)))
            d['device_class'] = 'PRINTER'
            raw_no = str(d.get('pr_no') or '')
            if raw_no.isdigit():
                d['pr_no'] = f"PR-{raw_no.zfill(3)}"
            elif '-' not in raw_no and len(raw_no) > 0:
                 digits = "".join(filter(str.isdigit, raw_no))
                 if digits: d['pr_no'] = f"PR-{digits.zfill(3)}"
            
            d['seri'] = d.get('serial_no')
            d['mahal'] = d.get('location') or d.get('location_code') or d.get('mahal') or ''
            
            if d.get('is_faulty') == 1 or d.get('is_faulty') == True:
                d['status'] = 'Arızalı'
            elif d.get('warehouse') == 1 or d.get('warehouse') == 1:
                d['status'] = 'Depoda'
            elif d.get('in_service') == 1 or d.get('serviste') == 1:
                d['status'] = 'Serviste'
            elif d.get('without_location') == 1 or d.get('without_location') == 1:
                d['status'] = 'Kayıp'
            else:
                d['status'] = d.get('status') or 'Kurulu'
            
            all_devices.append(d)
    except Exception as e:
        print("PRINTER GET_ALL ERR:", e)
    finally:
        conn.close()

    return jsonify(all_devices)

@printers_printers_bp.route('/update', methods=['POST'])
@require_editor
def update_printer():
    try:
        data = request.json
        if not data or 'id' not in data:
            return jsonify({"error": "ID belirtilmedi."}), 400
        
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

        update_fields = []
        params = []
        allowed_fields = ['pr_no', 'model', 'ip', 'seri', 'mac', 'mahal', 'location_code', 'status', 'cups_location', 'on_field', 'warehouse', 'is_faulty', 'without_location', 'serviste']
        
        for field in allowed_fields:
            if field in data:
                sql_col = column_map.get(field, field).lower()
                if sql_col not in columns_lower: continue 
                
                # Get actual column name for query
                actual_col = original_columns[columns_lower.index(sql_col)]
                
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
            conn.close()
            return jsonify({"success": True, "message": "Degisiklik yok."})

        params.append(record_id)
        query = f"UPDATE printers SET {', '.join(update_fields)} WHERE id = ?"
        cursor.execute(query, params)
        conn.commit()
        conn.close()
        
        return jsonify({"success": True, "message": "Cihaz guncellendi."})
    except Exception as e:
        print(f"[PRINTER UPDATE ERROR] {e}")
        return jsonify({"error": str(e)}), 500

@printers_printers_bp.route('/delete/<int:id>', methods=['DELETE'])
@require_editor
def delete_device(id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE printers SET is_deleted = 1, deleted_at = GETDATE() WHERE id = ?", (id,))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Cihaz silindi."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@printers_printers_bp.route('/query_cups', methods=['POST'])
@require_editor
def query_cups():
    try:
        import requests
        from bs4 import BeautifulSoup
        import re
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Fetch all active printers from DB, selecting ip as well
        cursor.execute("SELECT id, pr_no, cups_location, location, ip FROM printers WHERE is_deleted = 0")
        db_printers = cursor.fetchall()
        
        def extract_printer_number(name):
            if not name:
                return None
            digits = "".join(filter(str.isdigit, str(name)))
            if digits:
                return int(digits)
            return None

        # Build lookup maps
        db_printers_ip_map = {}
        db_printers_num_map = {}
        for db_id, pr_no, db_cups, db_loc, db_ip in db_printers:
            # Clean IP address
            clean_ip = str(db_ip).strip() if db_ip else None
            if clean_ip:
                db_printers_ip_map[clean_ip] = (db_id, pr_no, db_cups, db_loc, db_ip)
            
            num = extract_printer_number(pr_no)
            if num is not None:
                db_printers_num_map[num] = (db_id, pr_no, db_cups, db_loc, db_ip)

        updated_count = 0
        first = 0
        last_page_first_printer = None
        cups_host = "10.241.1.21"
        
        while True:
            cups_url = f"http://10.241.1.21:49631/printers/?FIRST={first}"
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
                    cups_location = cols[2].get_text(strip=True)
                    
                    if not cups_name: continue
                    
                    if current_page_first_printer is None:
                        current_page_first_printer = cups_name
                        
                    parsed_on_this_page += 1
                    
                    # Fetch printer details to extract IP from Connection URI
                    printer_ip = None
                    try:
                        detail_url = f"http://10.241.1.21:49631/printers/{cups_name}"
                        detail_resp = requests.get(detail_url, timeout=5, verify=False)
                        if detail_resp.status_code == 200:
                            # 1. Try to extract IP from connection URI
                            uri_match = re.search(r'(?:socket|ipp|lpd|http|https|dnssd|hp)://([^:/\'"\s]+)', detail_resp.text)
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
                        print(f"[MATRIX_CUPS] MATCH BY IP: {cups_name} -> DB IP: {printer_ip}")
                    
                    if not matched_printer:
                        cups_num = extract_printer_number(cups_name)
                        if cups_num is not None and cups_num in db_printers_num_map:
                            matched_printer = db_printers_num_map[cups_num]
                            print(f"[MATRIX_CUPS] MATCH BY NUM FALLBACK: {cups_name} -> Num: {cups_num}")
                        else:
                            for db_id, pr_no, db_cups, db_loc, db_ip in db_printers:
                                if pr_no and (cups_name.lower() in pr_no.lower() or pr_no.lower() in cups_name.lower()):
                                    matched_printer = (db_id, pr_no, db_cups, db_loc, db_ip)
                                    print(f"[MATRIX_CUPS] MATCH BY SUBSTRING FALLBACK: {cups_name} -> PR No: {pr_no}")
                                    break
                                
                    if matched_printer:
                        db_id, db_pr_no, db_cups, db_loc, db_ip = matched_printer
                        hedef_arayuz_adresi = f"http://10.241.1.21:49631/printers/{cups_name}"
                        hedef_mahal = cups_location
                        
                        if str(hedef_arayuz_adresi) != str(db_cups) or str(hedef_mahal) != str(db_loc):
                            cursor.execute("UPDATE printers SET cups_location = ?, location = ? WHERE id = ?", (hedef_arayuz_adresi, hedef_mahal, db_id))
                            updated_count += 1
                            print(f"[MATRIX_CUPS] YAZICI GUNCEL: {cups_name} -> Mahal: {hedef_mahal} | Arayuz: {hedef_arayuz_adresi}")
            
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

@printers_printers_bp.route('/cups/update_mahal', methods=['POST'])
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

        cursor.execute("SELECT cups_location FROM printers WHERE pr_no = ? AND is_deleted = 0", (pr_no,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Yazıcı bulunamadı."}), 404
        old_location = row[0]

        cursor.execute("UPDATE printers SET cups_location = ? WHERE pr_no = ?", (mahal, pr_no))
        
        import requests
        cups_admin_url = f"http://10.241.1.21:49631/admin/"
        post_data = {
            "OP": "modify-printer",
            "PRINTER_NAME": pr_no,
            "PRINTER_LOCATION": mahal,
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
            log_change("printers", pr_no, pr_no, "cups_location", old_location, mahal, "system", "Admin")
            return jsonify({"success": True, "message": "SQL ve CUPS başarıyla güncellendi."})
        else:
            conn.rollback()
            cursor.execute("INSERT INTO sync_status (operation, status, details) VALUES (?, ?, ?)", 
                           ("CUPS_SYNC", "FAILED_COMPENSATED", f"Printer: {pr_no}, Error: {error_detail}"))
            conn.commit()
            return jsonify({"error": "CUPS senkronizasyonu başarısız, veritabanı işlemi geri alındı.", "details": error_detail}), 500

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@printers_printers_bp.route('/cups/modify_location', methods=['POST'])
@require_editor
def modify_cups_location():
    try:
        data = request.json
        pr_no = data.get('pr_no')
        new_location = data.get('location')
        
        if not pr_no or not new_location:
            return jsonify({"error": "PR No ve Yeni Mahal bilgisi gereklidir."}), 400
            
        import requests
        import base64
        from bs4 import BeautifulSoup
        
        session = requests.Session()
        cups_user = os.getenv("CUPS_USER", "root")
        cups_pass = os.getenv("CUPS_PASS", "change_me_immediately")
        
        auth_str = f"{cups_user}:{cups_pass}"
        b64_auth = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')
        session.headers.update({'Authorization': f'Basic {b64_auth}'})
        
        # Step 0: Get printer page to find the modify form (which has org.cups.sid)
        printer_url = f"http://10.241.1.21:49631/printers/{pr_no}"
        r0 = session.get(printer_url, verify=False, timeout=10)
        if r0.status_code != 200:
            return jsonify({"error": f"Yazıcı sayfası açılamadı (HTTP {r0.status_code})"}), 500
            
        soup0 = BeautifulSoup(r0.text, 'html.parser')
        modify_form = soup0.find(lambda tag: tag.name == 'form' and 'modify-printer' in str(tag))
        if not modify_form:
            return jsonify({"error": "Modify Printer formu bulunamadı. Yazıcı adı yanlış olabilir."}), 500
            
        post_url = "http://10.241.1.21:49631" + modify_form.get('action', '/admin/')
        data0 = {}
        for inp in modify_form.find_all('input'):
            if inp.get('name') and inp.get('value') is not None:
                data0[inp.get('name')] = inp.get('value')
        
        data0['OP'] = 'modify-printer'
                
        # Step 1: Submit to start modify wizard (Returns Connection page)
        r1 = session.post(post_url, data=data0, verify=False, timeout=10)
        soup1 = BeautifulSoup(r1.text, 'html.parser')
        form1 = soup1.find(lambda tag: tag.name == 'form' and tag.get('action') and '/admin' in tag.get('action'))
        if not form1:
            return jsonify({"error": "Sihirbaz Adım 1'e (Bağlantı) geçilemedi."}), 500
            
        data1 = {}
        for inp in form1.find_all('input'):
            if inp.get('type', '').lower() in ['radio', 'checkbox'] and not inp.has_attr('checked'):
                continue
            if inp.get('name') and inp.get('value') is not None and inp.get('type', '').lower() != 'submit':
                data1[inp.get('name')] = inp.get('value')
        for sel in form1.find_all('select'):
            name = sel.get('name')
            selected = sel.find('option', selected=True)
            if selected:
                data1[name] = selected.get('value')
            else:
                opts = sel.find_all('option')
                if opts: data1[name] = opts[0].get('value')
        submit_btn1 = form1.find('input', type='submit')
        if submit_btn1 and submit_btn1.get('name'):
            data1[submit_btn1.get('name')] = submit_btn1.get('value')
            
        data1['printer_name'] = pr_no
        data1['OP'] = 'modify-printer'
                
        # Step 2: Submit Connection (Returns Details/Location page)
        r2 = session.post(post_url, data=data1, verify=False, timeout=10)
        soup2 = BeautifulSoup(r2.text, 'html.parser')
        form2 = soup2.find(lambda tag: tag.name == 'form' and tag.get('action') and '/admin' in tag.get('action'))
        if not form2:
            return jsonify({"error": "Sihirbaz Adım 2'ye (Mahal Detay) geçilemedi."}), 500
            
        data2 = {}
        for inp in form2.find_all('input'):
            if inp.get('type', '').lower() in ['radio', 'checkbox'] and not inp.has_attr('checked'):
                continue
            if inp.get('name') and inp.get('value') is not None and inp.get('type', '').lower() != 'submit':
                data2[inp.get('name')] = inp.get('value')
        
        for sel in form2.find_all('select'):
            name = sel.get('name')
            selected = sel.find('option', selected=True)
            if selected:
                data2[name] = selected.get('value')
            else:
                opts = sel.find_all('option')
                if opts: data2[name] = opts[0].get('value')
        submit_btn2 = form2.find('input', type='submit')
        if submit_btn2 and submit_btn2.get('name'):
            data2[submit_btn2.get('name')] = submit_btn2.get('value')
                
        # Ensure location is set
        data2['PRINTER_LOCATION'] = new_location
        data2['printer_name'] = pr_no
        data2['OP'] = 'modify-printer'
                
        # Step 3: Submit Details (Returns Driver/PPD page)
        r3 = session.post(post_url, data=data2, verify=False, timeout=10)
        soup3 = BeautifulSoup(r3.text, 'html.parser')
        
        # In step 3, there might be multiple forms (e.g. PPD upload). We need the one with action=/admin
        form3 = soup3.find(lambda tag: tag.name == 'form' and tag.get('action') and '/admin' in tag.get('action') and not ('enctype' in tag.attrs and 'multipart' in tag.attrs['enctype']))
        if not form3:
            form3 = soup3.find(lambda tag: tag.name == 'form' and tag.get('action') and '/admin' in tag.get('action'))
            
        if not form3:
            return jsonify({"error": "Sihirbaz Adım 3'e (Sürücü) geçilemedi."}), 500
            
        data3 = {}
        for inp in form3.find_all('input'):
            if inp.get('type', '').lower() in ['radio', 'checkbox'] and not inp.has_attr('checked'):
                continue
            if inp.get('name') and inp.get('value') is not None and inp.get('type', '').lower() != 'submit':
                data3[inp.get('name')] = inp.get('value')
        for sel in form3.find_all('select'):
            name = sel.get('name')
            selected = sel.find('option', selected=True)
            if selected:
                data3[name] = selected.get('value')
            else:
                opts = sel.find_all('option')
                if opts: data3[name] = opts[0].get('value')
        submit_btn3 = form3.find('input', type='submit')
        if submit_btn3 and submit_btn3.get('name'):
            data3[submit_btn3.get('name')] = submit_btn3.get('value')
            
        data3['printer_name'] = pr_no
        data3['OP'] = 'modify-printer'
                
        # Step 4: Submit Driver (Finalizes)
        r4 = session.post(post_url, data=data3, verify=False, timeout=10)
        soup4 = BeautifulSoup(r4.text, 'html.parser')
        
        # Check for error blockquote
        error_title = soup4.find(lambda tag: tag.name in ['h2', 'h1'] and 'Error' in tag.text)
        blockquote = soup4.find('blockquote')
        
        is_success = False
        if "successfully" in r4.text.lower() or "successful" in r4.text.lower() or "has been modified" in r4.text.lower():
            is_success = True
        elif r4.status_code == 200 and not blockquote:
            # No error blockquote means success in CUPS usually
            is_success = True
            
        if is_success:
            return jsonify({"success": True, "message": f"{pr_no} CUPS lokasyonu '{new_location}' olarak güncellendi."})
        else:
            err_msg = blockquote.text.strip() if blockquote else "Bilinmeyen CUPS Hatası (Hata mesajı alınamadı)"
            return jsonify({"error": f"CUPS İşlemi başarısız: {err_msg}"}), 500
            
    except Exception as e:
        print(f"[CUPS MODIFY ERROR] {e}")
        return jsonify({"error": str(e)}), 500

@printers_printers_bp.route('/device/<int:device_id>', methods=['GET'])
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
             
        if d.get('is_faulty') == 1 or d.get('is_faulty') == True: d['status'] = 'Arızalı'
        elif d.get('warehouse') == 1 or d.get('warehouse') == 1: d['status'] = 'Depoda'
        elif d.get('in_service') == 1 or d.get('serviste') == 1: d['status'] = 'Serviste'
        elif d.get('without_location') == 1 or d.get('without_location') == 1: d['status'] = 'Kayıp'
        else: d['status'] = 'Kurulu'
        
        d['seri'] = d.get('serial_no')
        d['mahal'] = d.get('location') or d.get('location_code') or d.get('mahal') or ''
            
        conn.close()
        return jsonify({"success": True, "data": d})
        
    except Exception as e:
        print(f"[API ERROR] printer get_device_detail: {e}")
        return jsonify({"error": str(e)}), 500
@printers_printers_bp.route('/check_serial', methods=['POST'])
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

@printers_printers_bp.route('/auto_register', methods=['POST'])
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
        
        query = f"INSERT INTO {table_name} (name, serial_no, status, recorded_device_no) VALUES (?, ?, ?, ?)"
        cursor.execute(query, (new_name, serial, 'Kurulu', pc_no))
        
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": f"{new_name} olarak kaydedildi."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@printers_printers_bp.route('/cups/pause', methods=['POST'])
@require_editor
def pause_reject_cups():
    try:
        data = request.json
        pr_no = data.get('pr_no')
        if not pr_no:
            return jsonify({'error': 'PR No gereklidir.'}), 400
            
        import requests
        cups_admin_url = 'http://10.241.1.21:49631/admin/'
        
        # 1. Pause Printer
        post_pause = {
            'OP': 'pause-printer',
            'printer_name': pr_no,
            'confirm': 'Yes'
        }
        requests.post(cups_admin_url, data=post_pause, timeout=10, verify=False)
        
        # 2. Reject Jobs
        post_reject = {
            'OP': 'reject-jobs',
            'printer_name': pr_no,
            'confirm': 'Yes'
        }
        requests.post(cups_admin_url, data=post_reject, timeout=10, verify=False)
        
        return jsonify({'success': True, 'message': f'{pr_no} CUPS üzerinde duraklatıldı ve reddedildi.'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


import requests
from flask import request, jsonify

@printers_printers_bp.route('/batch_action', methods=['POST'])
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

            base_url = "http://bim.kocaelish.com/Handler.ashx"
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
                send_data["Command"] = command

            headers = {
                "IPASession": ipa_session,
                "User-Agent": browser_headers["User-Agent"],
                "Referer": "http://bim.kocaelish.com/",
                "Origin": "http://bim.kocaelish.com"
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
        with open('batch_action_error.log', 'w') as f:
            f.write(traceback.format_exc())
        return jsonify({'error': str(e)}), 500
