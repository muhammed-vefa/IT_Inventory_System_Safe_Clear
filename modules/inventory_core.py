from flask import Blueprint, jsonify, request
from core.database_sql import query_db, get_db_connection
from core.auth import require_auth, require_admin, require_editor
from core.permissions import require_operation
from datetime import datetime
import json
import os

inventory_core_bp = Blueprint('inventory_core', __name__)

_KEYOS_STATS_CACHE = None
_KEYOS_STATS_TIME = 0

def get_keyos_live_stats_cached():
    global _KEYOS_STATS_CACHE, _KEYOS_STATS_TIME
    import time
    if time.time() - _KEYOS_STATS_TIME < 60 and _KEYOS_STATS_CACHE:
        return _KEYOS_STATS_CACHE
        
    try:
        from modules.keyos_service import KeyOSClient
        import os
        username = os.getenv("KEYOS_USER", "dashboard")
        password = os.getenv("KEYOS_PASS", "")
        client = KeyOSClient(username, password)
        stats = client.get_live_dashboard_stats()
        if stats:
            _KEYOS_STATS_CACHE = stats
            _KEYOS_STATS_TIME = time.time()
            return stats
    except Exception as e:
        print(f"[KeyOS] Cached Stats Error: {e}")
        
    return _KEYOS_STATS_CACHE or {"k5": 0, "k5_10": 0, "k11_29": 0, "k30p": 0}

# =====================================================
#  TABLO ESLEME: Kategori -> SQL Tablo Adi
# =====================================================
# =====================================================
#  TABLO ESLEME: Kategori -> SQL Tablo Adi
# =====================================================
TABLE_MAP = {
    'PC': 'pcs',
    'SK': 'queing_machines',
    'SIRAMATIK': 'queing_machines',
    'KIOSK': 'queing_machines',
    'TABLET': 'tablets',
    'PRINTER': 'printers',
    'MONITOR': 'monitors',
    'BARKOD YAZICI': 'barcode_printers',
    'BARKOD OKUYUCU': 'barcode_readers',
    'TARAYICI': 'scanners',
    'BARCODE_PRINTER': 'barcode_printers',
    'BARCODE_READER': 'barcode_readers',
    'SCANNER': 'scanners'
}

def get_table_for_type(device_type):
    """Cihaz turune gore SQL tablo adini doner."""
    return TABLE_MAP.get((device_type or 'PC').upper(), 'pcs')

def map_db_to_frontend(row, table):
    if not row: return row
    row = dict(row)
    
    # Common mappings
    if 'location_code' in row:
        row['location_code'] = row['location_code']
    if 'on_field' in row:
        row['on_field'] = row['on_field']
    if 'warehouse' in row:
        row['warehouse'] = row['warehouse']
    if 'is_faulty' in row:
        row['is_faulty'] = row['is_faulty']
    if 'without_location' in row:
        row['without_location'] = row['without_location']
    if 'pending_installation' in row:
        row['pending_installation'] = row['pending_installation']
        
    if table == 'pcs':
        if 'pc_serial' in row:
            row['pc_serial'] = row['pc_serial']
        if 'by_serial' in row:
            row['by_seri'] = row['by_serial']
        if 'bo_serial' in row:
            row['bo_seri'] = row['bo_serial']
        if 'scanner_serial' in row:
            row['tarayici_seri'] = row['scanner_serial']
        if 'monitor_serial' in row:
            row['monitor_seri'] = row['monitor_serial']
        if 'monitor2_serial' in row:
            row['monitor2_seri'] = row['monitor2_serial']
        if 'connected_printers' in row:
            row['bagli_yazicilar'] = row['connected_printers']
            
    elif table in ['queing_machines', 'tablets']:
        if 'serial_no' in row:
            row['serial_no'] = row['serial_no']
            
    # Clean "0" and "0.0" serial values
    serial_fields = [
        'pc_serial', 'by_serial', 'bo_serial', 'scanner_serial', 'monitor_serial', 'monitor2_serial',
        'serial_no', 'seri', 'by_seri', 'bo_seri', 'tarayici_seri', 'monitor_seri', 'monitor2_seri'
    ]
    for field in serial_fields:
        if field in row and row[field] is not None:
            s = str(row[field]).strip()
            if s in ('0', '0.0', '0,0'):
                row[field] = ''
            
    return row

_SCHEMA_CACHE = {}

def get_table_schema(table_name):
    if table_name in _SCHEMA_CACHE:
        return _SCHEMA_CACHE[table_name]
    try:
        from core.database_sql import query_db
        query = "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = ?"
        cols = query_db(query, (table_name,))
        if cols:
            _SCHEMA_CACHE[table_name] = set(c['column_name'].lower() for c in cols)
            return _SCHEMA_CACHE[table_name]
    except Exception as e:
        print(f"[SCHEMA CACHE ERROR] {table_name}: {e}")
    return set()

def get_safe_columns(table_name, requested_cols):
    """Checks INFORMATION_SCHEMA.COLUMNS to return only existing columns for the table."""
    existing_set = get_table_schema(table_name)
    if not existing_set: return "*"
    safe_cols = [c for c in requested_cols if c.lower() in existing_set]
    return ", ".join(safe_cols) if safe_cols else "*"

def check_column_exists(table_name, col_name):
    """Checks if a specific column exists in a table."""
    existing_set = get_table_schema(table_name)
    if not existing_set: return False
    return col_name.lower() in existing_set


@inventory_core_bp.route('/stats', methods=['GET'])
@require_auth
def get_stats():
    try:
        # Dynamically build stats query based on existing columns
        pc_cols = {
            "on_field": "SUM(CASE WHEN on_field=1 THEN 1 ELSE 0 END)",
            "is_faulty": "SUM(CASE WHEN is_faulty=1 THEN 1 ELSE 0 END)",
            "warehouse": "SUM(CASE WHEN warehouse=1 THEN 1 ELSE 0 END)",
            "without_location": "SUM(CASE WHEN without_location=1 THEN 1 ELSE 0 END)",
            "windows": "SUM(CASE WHEN windows=1 THEN 1 ELSE 0 END)",
            "keyos": "SUM(CASE WHEN keyos=1 THEN 1 ELSE 0 END)"
        }
        safe_pc = []
        for key, sql in pc_cols.items():
            safe_pc.append(f"{sql} as pc_{key}")
        
        pr_cols = {
            "on_field": "SUM(CASE WHEN on_field=1 THEN 1 ELSE 0 END)",
            "is_faulty": "SUM(CASE WHEN is_faulty=1 THEN 1 ELSE 0 END)",
            "warehouse": "SUM(CASE WHEN warehouse=1 THEN 1 ELSE 0 END)",
            "without_location": "SUM(CASE WHEN without_location=1 THEN 1 ELSE 0 END)"
        }
        safe_pr = []
        for key, sql in pr_cols.items():
            safe_pr.append(f"{sql} as pr_{key}")

        query = f"SELECT {', '.join(safe_pc)} FROM pcs WHERE (is_deleted = 0 OR is_deleted IS NULL)"
        pr_query = f"SELECT {', '.join(safe_pr)} FROM printers WHERE (is_deleted = 0 OR is_deleted IS NULL)"

        pc_stats = query_db(query, one=True) or {}
        pr_stats = query_db(pr_query, one=True) or {}

        # Handle is_faulty vs is_faulty alias for printers
        pr_ariza_count = pr_stats.get('pr_arizali', 0) or pr_stats.get('pr_is_faulty', 0)

        # BARKOD & TARAYICI EK İSTATİSTİKLER (PCS tablosundaki on_field sayıları)
        pc_extra = query_db("""
            SELECT 
                SUM(CASE WHEN p.bo_serial IS NOT NULL AND TRIM(p.bo_serial) NOT IN ('', '-', 'Yok', '0') THEN 1 ELSE 0 END) as bo_sahada,
                SUM(CASE WHEN p.by_serial IS NOT NULL AND TRIM(p.by_serial) NOT IN ('', '-', 'Yok', '0') THEN 1 ELSE 0 END) as by_sahada,
                SUM(CASE WHEN p.scanner_serial IS NOT NULL AND TRIM(p.scanner_serial) NOT IN ('', '-', 'Yok', '0') THEN 1 ELSE 0 END) as tr_all_sahada,
                SUM(CASE WHEN p.scanner_serial IS NOT NULL AND TRIM(p.scanner_serial) NOT IN ('', '-', 'Yok', '0') AND (s.name LIKE '%C230%' OR s.model LIKE '%C230%') THEN 1 ELSE 0 END) as tr_c230_sahada,
                SUM(CASE WHEN p.scanner_serial IS NOT NULL AND TRIM(p.scanner_serial) NOT IN ('', '-', 'Yok', '0') AND (s.name LIKE '%G2090%' OR s.model LIKE '%G2090%') THEN 1 ELSE 0 END) as tr_g2090_sahada
            FROM pcs p 
            LEFT JOIN scanners s ON p.scanner_serial = s.serial_no
            WHERE (p.is_deleted = 0 OR p.is_deleted IS NULL)
        """, one=True) or {}

        # DEPO İSTATİSTİKLERİ (Barkod, Tarayıcı vb. için)
        depo_extra = query_db("""
            SELECT 
                SUM(CASE WHEN name LIKE '%Barkod Okuyucu%' THEN current_stock ELSE 0 END) as bo_depo,
                SUM(CASE WHEN name LIKE '%Barkod Yazıcı%' OR name LIKE '%Barkod Yazici%' THEN current_stock ELSE 0 END) as by_depo,
                SUM(CASE WHEN name LIKE '%Tarayıcı%' OR name LIKE '%Tarayici%' THEN current_stock ELSE 0 END) as tr_all_depo,
                SUM(CASE WHEN (name LIKE '%Tarayıcı%' OR name LIKE '%Tarayici%') AND name LIKE '%C230%' THEN current_stock ELSE 0 END) as tr_c230_depo,
                SUM(CASE WHEN (name LIKE '%Tarayıcı%' OR name LIKE '%Tarayici%') AND name LIKE '%G2090%' THEN current_stock ELSE 0 END) as tr_g2090_depo
            FROM depot_items WHERE (is_deleted = 0 OR is_deleted IS NULL)
        """, one=True) or {}

        keyos_live = get_keyos_live_stats_cached()

        # En son KeyOS uyumsuzluk kontrolü logunu oku
        keyos_sync_log = None
        try:
            import json, os
            log_path = os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(__file__))), 'database', 'scheduler_logs.json')
            if os.path.exists(log_path):
                with open(log_path, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
                    # En sondan başa doğru KeyOS Sync ara
                    for log in reversed(logs):
                        if log.get("task_name") == "KeyOS Sync":
                            keyos_sync_log = log
                            break
        except Exception as e:
            print(f"[API ERROR] reading scheduler_logs: {e}")

        # Yazıcı çıktı sayısı uyarısı (son 30 gün çıktı sayısı < 30 olan aktif yazıcılar)
        low_print_count = 0
        try:
            from datetime import timedelta
            thirty_days_ago = datetime.now() - timedelta(days=30)
            low_print_printers_query = """
                SELECT COUNT(*) as cnt FROM printers p
                WHERE (p.is_deleted = 0 OR p.is_deleted IS NULL) AND p.on_field = 1
                AND p.ip IS NOT NULL AND p.ip != '' AND p.ip != '0'
                AND (
                    (
                        SELECT MAX(page_count) FROM printer_page_logs 
                        WHERE pr_no = p.pr_no AND timestamp >= ?
                    ) - (
                        SELECT MIN(page_count) FROM printer_page_logs 
                        WHERE pr_no = p.pr_no AND timestamp >= ?
                    ) < 30
                    OR NOT EXISTS (
                        SELECT 1 FROM printer_page_logs 
                        WHERE pr_no = p.pr_no AND timestamp >= ?
                    )
                )
            """
            res_low = query_db(low_print_printers_query, (thirty_days_ago, thirty_days_ago, thirty_days_ago), one=True)
            if res_low:
                low_print_count = res_low.get('cnt', 0)
        except Exception as ex:
            print(f"[API ERROR] low_print_printers: {ex}")

        return jsonify({
            "pc": {
                "on_field": pc_stats.get('pc_on_field', 0),
                "ariza": pc_stats.get('pc_is_faulty', 0),
                "warehouse": pc_stats.get('pc_warehouse', 0),
                "kayip": pc_stats.get('pc_without_location', 0)
            },
            "pr": {
                "on_field": pr_stats.get('pr_on_field', 0),
                "ariza": pr_ariza_count,
                "warehouse": pr_stats.get('pr_warehouse', 0),
                "kayip": pr_stats.get('pr_without_location', 0)
            },
            "os": {
                "win": pc_stats.get('pc_windows', 0),
                "keyos": pc_stats.get('pc_keyos', 0)
            },
            "bo": {
                "on_field": pc_extra.get('bo_sahada', 0),
                "warehouse": depo_extra.get('bo_depo', 0)
            },
            "by": {
                "on_field": pc_extra.get('by_sahada', 0),
                "warehouse": depo_extra.get('by_depo', 0)
            },
            "tr_c230": {
                "on_field": pc_extra.get('tr_c230_sahada', 0),
                "warehouse": depo_extra.get('tr_c230_depo', 0)
            },
            "tr_g2090": {
                "on_field": pc_extra.get('tr_g2090_sahada', 0),
                "warehouse": depo_extra.get('tr_g2090_depo', 0)
            },
            "keyos_uptime": keyos_live,
            "keyos_sync_log": keyos_sync_log,
            "low_print_printers": low_print_count
        })
    except Exception as e:
        print(f"[API ERROR] stats: {e}")
        return jsonify({"error": str(e)}), 500


# =====================================================
#  YENI KAYIT EKLEME (Tum cihaz turleri icin)
# =====================================================

@inventory_core_bp.route('/add', methods=['POST'])
@require_editor
def add_inventory():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Veri yok"}), 400

        # Clean "0" and empty serial values to None for SQL NULL mapping
        serial_keys = [
            'pc_serial', 'serial_no', 'seri', 'by_serial', 'bo_serial', 'scanner_serial', 'monitor_serial', 'monitor2_serial',
            'by_seri', 'bo_seri', 'tarayici_seri', 'monitor_seri', 'monitor2_seri'
        ]
        for k in serial_keys:
            if k in data and data[k] is not None:
                s = str(data[k]).strip()
                if s in ('0', '0.0', '0,0', ''):
                    data[k] = None
        
        device_type = data.get('device_type', 'PC')
        table_name = get_table_for_type(device_type)
        changed_by = request.current_user.get('username', 'system')
        display_name = request.current_user.get('display_name', 'Sistem')

        conn = get_db_connection()
        cursor = conn.cursor()

        if table_name == 'pcs':
            cursor.execute("INSERT INTO pcs (pc_no, pc_serial, ip, location_code, on_field, warehouse, windows, keyos, rdp_address, rdp_reason) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                           (data.get('pc_no'), data.get('pc_serial'), data.get('ip'), data.get('location_code'), data.get('on_field', 1), 0, data.get('windows', 0), data.get('keyos', 0), data.get('rdp_address'), data.get('rdp_reason')))

        elif table_name == 'tablets':
            cursor.execute("INSERT INTO tablets (device_name, serial_no, location_code, on_field, assigned_to, phone, title, unit) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                           (data.get('pc_no') or 'Tablet', data.get('pc_serial'), data.get('location_code'), data.get('on_field', 1), data.get('assigned_to'), data.get('phone'), data.get('title'), data.get('unit')))
        elif table_name == 'queing_machines':
            cursor.execute("INSERT INTO queing_machines (device_name, serial_no, location_code, on_field) VALUES (?, ?, ?, ?)",
                           (data.get('pc_no') or 'Sıramatik', data.get('pc_serial'), data.get('location_code'), data.get('on_field', 1)))
        elif table_name == 'monitors':
            cursor.execute("INSERT INTO monitors (name, model, serial_no, status, location_code, on_field, is_faulty, warehouse) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                           (data.get('name') or 'Monitör', data.get('model'), data.get('serial_no'), data.get('pc_no'), data.get('location_code'), data.get('on_field', 1), data.get('is_faulty', data.get('is_faulty', 0)), data.get('warehouse', data.get('warehouse', 0))))
        elif table_name == 'printers':
            cursor.execute("""
                INSERT INTO printers (pr_no, model, ip, mac, serial_no, location_code, on_field, is_faulty, warehouse, without_location)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get('pr_no', ''),
                data.get('model', ''),
                data.get('ip', ''),
                data.get('mac', ''),
                data.get('serial_no') or data.get('seri') or None,
                data.get('location_code') or data.get('mahal', ''),
                data.get('on_field', 1),
                data.get('is_faulty', 0),
                data.get('warehouse', 0),
                data.get('without_location', 0)
            ))

        conn.commit()
        conn.close()
        
        from modules.logs_manager import log_activity
        log_activity(request.current_user.get('id', 0), "ADD_DEVICE", f"{device_type} cihazi eklendi")
        
        return jsonify({"success": True, "message": "Cihaz basariyla eklendi."})
    except Exception as e:
        print(f"[API ERROR] add_inventory: {e}")
        return jsonify({"error": str(e)}), 500

# =====================================================
#  GUNCELLEME (Tum cihaz turleri icin)
# =====================================================

@inventory_core_bp.route('/update', methods=['POST'])
@require_editor
def update_inventory():
    """Cihaz bilgilerini gunceller ve audit_logs tablosuna kaydeder."""
    try:
        data = request.json
        if not data or 'id' not in data:
            return jsonify({"error": "ID belirtilmedi."}), 400

        # Clean "0" and empty serial values to None for SQL NULL mapping
        serial_keys = [
            'pc_serial', 'serial_no', 'seri', 'by_serial', 'bo_serial', 'scanner_serial', 'monitor_serial', 'monitor2_serial',
            'by_seri', 'bo_seri', 'tarayici_seri', 'monitor_seri', 'monitor2_seri'
        ]
        for k in serial_keys:
            if k in data and data[k] is not None:
                s = str(data[k]).strip()
                if s in ('0', '0.0', '0,0', ''):
                    data[k] = None
        
        record_id = data['id']
        device_type = data.get('device_type', 'PC')
        table_name = get_table_for_type(device_type)
        changed_by = request.current_user.get('username', 'system')
        display_name = request.current_user.get('display_name', 'Sistem')
        
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if client_ip and ',' in client_ip:
            client_ip = client_ip.split(',')[0].strip()

        # Translate Turkish frontend keys to English database columns
        translation_map = {
            'pcs': {
                'location_code': 'location_code',
                'pc_serial': 'pc_serial',
                'on_field': 'on_field',
                'warehouse': 'warehouse',
                'is_faulty': 'is_faulty',
                'without_location': 'without_location',
                'pending_installation': 'pending_installation',
                'by_seri': 'by_serial',
                'bo_seri': 'bo_serial',
                'tarayici_seri': 'scanner_serial',
                'monitor_seri': 'monitor_serial',
                'monitor2_seri': 'monitor2_serial',
                'bagli_yazicilar': 'connected_printers'
            },
            'queing_machines': {
                'location_code': 'location_code',
                'serial_no': 'serial_no',
                'on_field': 'on_field',
                'warehouse': 'warehouse',
                'is_faulty': 'is_faulty',
                'without_location': 'without_location',
                'pending_installation': 'pending_installation'
            },
            'tablets': {
                'location_code': 'location_code',
                'serial_no': 'serial_no',
                'on_field': 'on_field',
                'warehouse': 'warehouse',
                'is_faulty': 'is_faulty',
                'without_location': 'without_location',
                'pending_installation': 'pending_installation'
            }
        }
        
        table_map = translation_map.get(table_name, {})
        translated_data = {}
        for k, v in data.items():
            db_key = table_map.get(k, k)
            translated_data[db_key] = v
        data = translated_data

        from modules.logs_manager import log_change
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. ESKI VERIYI CEK (is_deleted=0 kontroluyle)
        cursor.execute(f"SELECT * FROM {table_name} WHERE id = ? AND is_deleted = 0", (record_id,))
        columns_raw = [column[0] for column in cursor.description]
        columns_lower = [c.lower() for c in columns_raw]
        old_row = cursor.fetchone()
        if not old_row:
            conn.close()
            return jsonify({"error": "Cihaz bulunamadi veya silinmis."}), 404
        
        old_data = dict(zip(columns_lower, old_row))
        if table_name == 'pcs':
            pc_num = str(old_data.get('pc_no', '')).strip()
            pc_pad = pc_num.zfill(3) if pc_num.isdigit() else pc_num
            pc_name = f"PC-{pc_pad}" if pc_pad else "PC"
            record_label = f"{pc_name} ({old_data.get('pc_serial', '')})".strip(' ()')
        elif table_name in ['printers', 'barcode_printers', 'barcode_readers', 'scanners']:
            record_label = f"{old_data.get('pr_no', '')} ({old_data.get('serial_no', '')})".strip(' ()')
        elif table_name in ['tablets', 'queing_machines']:
            record_label = f"{old_data.get('device_name', '')} ({old_data.get('serial_no', '')})".strip(' ()')
        else:
            record_label = str(record_id)
        if not record_label: record_label = str(record_id)

        # Automatic Hostname generation on location_code change
        _keyos_auto_sync_data = None  # Mahal değişirse KeyOS otomatik senkronizasyon bilgisi
        if table_name == 'pcs':
            new_loc = data.get('location_code')
            old_loc = old_data.get('location_code')
            current_host = old_data.get('hostname')
            
            # If location_code changes or if current hostname is empty/None
            if (new_loc and new_loc != old_loc) or not current_host or str(current_host).strip() in ('', 'None', 'NULL', '-'):
                target_loc = new_loc if new_loc else old_loc
                if target_loc:
                    clean_loc = str(target_loc).replace('.', '').strip().upper()
                    if clean_loc:
                        # Find existing hostnames in this location to find first unused suffix
                        cursor.execute("SELECT hostname FROM pcs WHERE location_code = ? AND is_deleted = 0 AND id != ?", (target_loc, record_id))
                        existing_rows = cursor.fetchall()
                        existing_suffixes = set()
                        for r_item in existing_rows:
                            host_val = r_item[0]
                            if host_val and 'x' in host_val.lower():
                                suffix_str = host_val.lower().split('x')[-1]
                                try:
                                    existing_suffixes.add(int(suffix_str))
                                except ValueError as val_e:
                                    print(f"[Inventory Core Suffix Conversion Error] {val_e}")
                        seq = 1
                        while seq in existing_suffixes:
                            seq += 1
                        generated_host = f"{clean_loc}x{seq:02d}"
                        
                        # Add to data to be updated
                        data['hostname'] = generated_host
                        
                        # Mahal değişikliği varsa KeyOS Auto-Sync verisi hazırla
                        if new_loc and new_loc != old_loc:
                            pc_serial = old_data.get('pc_serial', '')
                            user_id = request.current_user.get('user_id')
                            if pc_serial and str(pc_serial).strip() not in ('', '-', 'None', 'NULL') and user_id:
                                _keyos_auto_sync_data = {
                                    'user_id': user_id,
                                    'serial': str(pc_serial).strip(),
                                    'hostname': generated_host,
                                    'location_code': target_loc
                                }

        # 2. GUNCELLENEBILIR ALANLAR (tablo bazli - English DB Column names)
        allowed_fields_map = {
            'pcs': [
                'location_code', 'keyos_location', 'ip', 'mac', 'hostname', 'description',
                'pc_serial', 'monitor_serial', 'monitor2_serial', 'connected_printers',
                'by_serial', 'bo_serial', 'scanner_serial', 'pr6900', 'pr5200', 'pr8690',
                'on_field', 'warehouse', 'is_faulty', 'without_location', 'windows', 'keyos', 'rdp',
                'rdp_address', 'rdp_reason', 'pending_installation', 'hostname_mismatch', 'device_type'
            ],
            'queing_machines': [
                'pc_no', 'location_code', 'ip', 'mac', 'serial_no',
                'on_field', 'warehouse', 'is_faulty', 'without_location', 'pending_installation'
            ],
            'tablets': [
                'pc_no', 'location_code', 'ip', 'mac', 'serial_no', 'assigned_to', 'phone', 'title', 'unit',
                'on_field', 'warehouse', 'is_faulty', 'without_location', 'pending_installation'
            ],
            'barcode_printers': ['serial_no', 'pc_no', 'name', 'status', 'ip', 'mac', 'location_code', 'on_field', 'warehouse', 'is_faulty', 'without_location', 'pending_installation', 'recorded_device_no'],
            'barcode_readers': ['serial_no', 'pc_no', 'name', 'status', 'ip', 'mac', 'location_code', 'on_field', 'warehouse', 'is_faulty', 'without_location', 'pending_installation', 'recorded_device_no'],
            'scanners': ['serial_no', 'pc_no', 'name', 'status', 'ip', 'mac', 'location_code', 'on_field', 'warehouse', 'is_faulty', 'without_location', 'pending_installation', 'recorded_device_no', 'model'],
            'monitors': ['serial_no', 'pc_no', 'name', 'status', 'ip', 'mac', 'location_code', 'on_field', 'warehouse', 'is_faulty', 'without_location', 'pending_installation', 'recorded_device_no', 'model', 'monitor_type']
        }
        allowed_fields = allowed_fields_map.get(table_name, allowed_fields_map['pcs'])

        # Dynamic location_code / location_code fallback based on actual table schema
        if 'location_code' in allowed_fields and not check_column_exists(table_name, 'location_code'):
            if check_column_exists(table_name, 'location_code'):
                allowed_fields = [f if f != 'location_code' else 'location_code' for f in allowed_fields]
                if 'location_code' in data:
                    data['location_code'] = data.pop('location_code')

        # 3. DEGISIKLIKLERI TOPLA
        update_fields = []
        params = []
        
        for field in allowed_fields:
            if field in data:
                if not check_column_exists(table_name, field):
                    continue
                new_val = data[field]
                old_val = old_data.get(field.lower())
                
                old_s = str(old_val).strip().lower() if old_val is not None else ''
                new_s = str(new_val).strip().lower() if new_val is not None else ''
                
                # Normalize bools for comparison
                if new_s in ['1', 'true', 'yes']: new_s = '1'
                elif new_s in ['0', 'false', 'no']: new_s = '0'
                
                if old_s in ['1', 'true', 'yes']: old_s = '1'
                elif old_s in ['0', 'false', 'no']: old_s = '0'
                
                if new_s != old_s:
                    if field in ['location_code', 'keyos_location'] and not old_s and not new_s:
                        continue
                    if field == 'device_type' and new_s == old_s:
                        continue
                    log_change(table_name, record_id, record_label, field, old_val, new_val, changed_by, display_name, client_ip)
                    update_fields.append(f"[{field}] = ?")
                    params.append(new_val)

        # Son duzenleme bilgisini kaydet (sadece pcs icin)
        if table_name == 'pcs' and update_fields:
            update_fields.append("last_edit_date = GETDATE()")
            update_fields.append("last_edit_user = ?")
            params.append(display_name)

        if not update_fields:
            # Sadece arşivden çıkarma durumu olabilir, en azından is_deleted=0 yapalım
            update_fields.append("[is_deleted] = 0")
        else:
            update_fields.append("[is_deleted] = 0")

        # CONFLICT DETECTION & BIDIRECTIONAL SYNC FOR PERIPHERALS (When updating PC)
        force_update = data.get('force_update', False)
        peripheral_sync_tasks = [] # (table, serial, old_serial)
        
        
        reverse_sync_tasks = []
        if table_name in ['barcode_printers', 'barcode_readers', 'scanners', 'monitors']:
            new_pc = str(data.get('pc_no', '')).strip()
            old_pc = str(old_data.get('pc_no') or old_data.get('recorded_device_no') or '').strip()
            serial = str(data.get('serial_no') or old_data.get('serial_no', '')).strip()
            
            pc_changed = 'pc_no' in data and new_pc != old_pc
            monitor_type_changed = table_name == 'monitors' and 'monitor_type' in data and str(data['monitor_type']) != str(old_data.get('monitor_type'))
            
            if pc_changed:
                if not force_update and new_pc:
                    confirm_msg = f"Bu cihazı {old_pc} bilgisayarından alıp {new_pc} bilgisayarına kaydetmek istediğinize emin misiniz?" if old_pc else f"Bu cihazı {new_pc} bilgisayarına kaydetmek istediğinize emin misiniz?"
                    conn.close()
                    return jsonify({
                        "success": True, 
                        "requires_confirmation": True, 
                        "confirm_message": confirm_msg
                    })
                if serial:
                    reverse_sync_tasks.append((table_name, serial, new_pc, old_pc))
            elif monitor_type_changed and serial and new_pc:
                reverse_sync_tasks.append((table_name, serial, new_pc, old_pc))
                    
        if table_name == 'pcs':
            pc_num = str(old_data.get('pc_no', '')).strip()
            pc_pad = pc_num.zfill(3) if pc_num.isdigit() else pc_num
            pc_name = f"PC-{pc_pad}" if pc_pad else "PC"
            
            peripherals_to_check = {
                'by_serial': ('barcode_printers', 'Barkod Yazıcı'),
                'bo_serial': ('barcode_readers', 'Barkod Okuyucu'),
                'scanner_serial': ('scanners', 'Tarayıcı'),
                'monitor_serial': ('monitors', '1. Monitör'),
                'monitor2_serial': ('monitors', '2. Monitör')
            }
            
            for field, (p_table, p_label) in peripherals_to_check.items():
                if field in data:
                    new_serial = str(data[field]).strip()
                    old_serial = str(old_data.get(field) or '').strip()
                    
                    if new_serial and new_serial not in ['---', 'None', ''] and new_serial != old_serial:
                        # Bu seri numarası başka bir PC'de kayıtlı mı?
                        cursor.execute(f"SELECT pc_no FROM {table_name} WHERE {field} = ? AND id != ?", (new_serial, record_id))
                        conflict_pc = cursor.fetchone()
                        
                        confirm_msgs = []
                        
                        if old_serial and old_serial not in ['---', 'None', '']:
                            confirm_msgs.append(f"• Bilgisayar üzerindeki mevcut {p_label} (Seri: {old_serial}) kaydı silinecek.")
                            
                        if conflict_pc:
                            conflict_pc_name = str(conflict_pc[0] or '')
                            clean_conflict_pc_name = f"PC-{conflict_pc_name.zfill(3) if conflict_pc_name.isdigit() else conflict_pc_name}"
                            confirm_msgs.append(f"• Girdiğiniz {p_label} seri numarası ({new_serial}) zaten başka bir bilgisayara ({clean_conflict_pc_name}) kayıtlı.")
                        
                        if confirm_msgs and not force_update:
                            conn.close()
                            return jsonify({
                                "success": True, 
                                "requires_confirmation": True, 
                                "confirm_message": "Dikkat, aşağıdaki değişiklikler/çakışmalar tespit edildi:\n\n" + "\n".join(confirm_msgs) + "\n\nEski kayıtları silip bu işlemi gerçekleştirmek istediğinize emin misiniz?"
                            })
                        
                        peripheral_sync_tasks.append((p_table, new_serial, old_serial, p_label))
                    elif not new_serial and old_serial and old_serial not in ['---', 'None', '']:
                        # Bağlantı kaldırıldı
                        if not force_update:
                            conn.close()
                            return jsonify({
                                "success": True, 
                                "requires_confirmation": True, 
                                "confirm_message": f"Bilgisayar üzerindeki {p_label} (Seri: {old_serial}) bağlantısını tamamen kaldırmak istediğinize emin misiniz?"
                            })
                        peripheral_sync_tasks.append((p_table, None, old_serial, p_label))

        # 4. VERITABANINI GUNCELLE
        params.append(record_id)
        query = f"UPDATE {table_name} SET {', '.join(update_fields)} WHERE id = ?"
        cursor.execute(query, params)
        
        # REVERSE SYNC (From Peripheral -> PC)
        for task in reverse_sync_tasks:
            p_table, serial, new_pc, old_pc = task
            pc_field = None
            if p_table == 'barcode_printers': pc_field = 'by_serial'
            elif p_table == 'barcode_readers': pc_field = 'bo_serial'
            elif p_table == 'scanners': pc_field = 'scanner_serial'
            elif p_table == 'monitors': pc_field = 'monitor_serial'
            if pc_field:
                if old_pc:
                    import re
                    clean_str = re.sub(r'^PC-?', '', old_pc.upper().strip())
                    if clean_str.isdigit():
                        num_val = str(int(clean_str))
                        pad_val = num_val.zfill(3)
                        pc_val = f"PC-{pad_val}"
                        old_candidates = (num_val, pad_val, pc_val)
                    else:
                        old_candidates = (clean_str, clean_str, clean_str)

                    if p_table == 'monitors':
                        cursor.execute("UPDATE pcs SET monitor_serial = NULL WHERE pc_no IN (?, ?, ?) AND monitor_serial = ?", (*old_candidates, serial))
                        cursor.execute("UPDATE pcs SET monitor2_serial = NULL WHERE pc_no IN (?, ?, ?) AND monitor2_serial = ?", (*old_candidates, serial))
                    else:
                        cursor.execute(f"UPDATE pcs SET {pc_field} = NULL WHERE pc_no IN (?, ?, ?) AND {pc_field} = ?", (*old_candidates, serial))
                
                if new_pc:
                    import re
                    clean_str = re.sub(r'^PC-?', '', new_pc.upper().strip())
                    if clean_str.isdigit():
                        num_val = str(int(clean_str))
                        pad_val = num_val.zfill(3)
                        pc_val = f"PC-{pad_val}"
                        new_candidates = (num_val, pad_val, pc_val)
                    else:
                        new_candidates = (clean_str, clean_str, clean_str)

                    if p_table == 'monitors':
                        mon_type = str(data.get('monitor_type') or old_data.get('monitor_type') or '1')
                        if '2' in mon_type:
                            cursor.execute("UPDATE pcs SET monitor2_serial = ? WHERE pc_no IN (?, ?, ?) AND (is_deleted = 0 OR is_deleted IS NULL)", (serial, *new_candidates))
                        else:
                            cursor.execute("UPDATE pcs SET monitor_serial = ? WHERE pc_no IN (?, ?, ?) AND (is_deleted = 0 OR is_deleted IS NULL)", (serial, *new_candidates))
                    else:
                        cursor.execute(f"UPDATE pcs SET {pc_field} = ? WHERE pc_no IN (?, ?, ?) AND (is_deleted = 0 OR is_deleted IS NULL)", (serial, *new_candidates))

        
        # PERIPHERAL SYNC (Update Peripheral Tables AND clean up old PCs)
        for task in peripheral_sync_tasks:
            p_table = task[0]
            new_serial = task[1]
            old_serial = task[2]
            
            # 1. Eski bağlı olduğu PC'nin üzerindeki seriali temizle (sadece başka bir bilgisayarda ise)
            if new_serial:
                for pc_f, (p_t, _) in peripherals_to_check.items():
                    if p_t == p_table:
                        cursor.execute(f"UPDATE pcs SET {pc_f} = NULL WHERE {pc_f} = ? AND id != ?", (new_serial, record_id))
                        break
        for task in peripheral_sync_tasks:
            p_table = task[0]
            new_serial = task[1]
            old_serial = task[2]
            p_label = task[3] if len(task) > 3 else None
            
            # 1. Eski bağlantıları kaldır
            if old_serial and old_serial not in ['---', 'None', '']:
                if p_table == 'monitors':
                    cursor.execute(f"UPDATE {p_table} SET recorded_device_no = NULL, monitor_type = NULL, pc_no = NULL, status = NULL WHERE serial_no = ?", (old_serial,))
                else:
                    cursor.execute(f"UPDATE {p_table} SET recorded_device_no = NULL, pc_no = NULL WHERE serial_no = ?", (old_serial,))
                
            # 2. Cihazın kendi tablosundaki pc_no'yu güncelle
            if new_serial:
                if p_table == 'monitors':
                    cursor.execute(f"UPDATE {p_table} SET recorded_device_no = ?, monitor_type = ?, pc_no = ?, status = ? WHERE serial_no = ?", (pc_name, p_label, pc_name, pc_name, new_serial))
                else:
                    cursor.execute(f"UPDATE {p_table} SET recorded_device_no = ?, pc_no = ? WHERE serial_no = ?", (pc_name, pc_name, new_serial))
                
        conn.commit()
        conn.close()
        
        # KeyOS Auto-Sync: Mahal değişikliği varsa arka planda KeyOS MGT'yi güncelle
        keyos_sync_msg = None
        if _keyos_auto_sync_data:
            try:
                from modules.keyos_service import push_hostname_to_keyos
                push_hostname_to_keyos(
                    _keyos_auto_sync_data['user_id'],
                    _keyos_auto_sync_data['serial'],
                    _keyos_auto_sync_data['hostname'],
                    _keyos_auto_sync_data['location_code']
                )
                keyos_sync_msg = f"KeyOS MGT üzerinde de güncelleme arka planda başlatıldı."
            except Exception as ks_e:
                print(f"[KeyOS Auto-Sync Trigger Error] {ks_e}")
                keyos_sync_msg = f"KeyOS otomatik güncelleme başlatılamadı: {str(ks_e)}"
        
        resp_msg = "Cihaz guncellendi."
        if keyos_sync_msg:
            resp_msg += f" {keyos_sync_msg}"
        
        return jsonify({"success": True, "message": resp_msg})
    except Exception as e:
        print(f"[UPDATE ERROR] {e}")
        return jsonify({"error": str(e)}), 500



@inventory_core_bp.route('/delete/<int:record_id>', methods=['DELETE'])
@require_editor
def delete_device(record_id):
    """Cihazi silinmis olarak isaretler (Soft Delete)."""
    try:
        device_type = request.args.get('type', 'PC')
        table_name = get_table_for_type(device_type)
        changed_by = request.current_user.get('username', 'system')
        display_name = request.current_user.get('display_name', 'Sistem')

        from modules.logs_manager import log_change
        conn = get_db_connection()
        cursor = conn.cursor()

        # Cihazi bul ve logla
        cursor.execute(f"SELECT pc_no FROM {table_name} WHERE id = ?", (record_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({"error": "Cihaz bulunamadı."}), 404
        
        pc_no = row[0]
        log_change(table_name, record_id, pc_no, 'is_deleted', 0, 1, changed_by, display_name)

        # Soft delete
        cursor.execute(f"UPDATE {table_name} SET is_deleted = 1 WHERE id = ?", (record_id,))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Cihaz silindi."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =====================================================
#  YEDEKLEME & TEMIZLEME
# =====================================================

@inventory_core_bp.route('/backup_db', methods=['POST'])
@require_admin
def manual_backup():
    try:
        from core.database_sql import backup_sql_db
        success, result = backup_sql_db()
        if success:
            return jsonify({"success": True, "message": f"Veritabani yedegi {result} klasorune basariyla kaydedildi."})
        else:
            return jsonify({"success": False, "error": result}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@inventory_core_bp.route('/clear_all_data', methods=['POST'])
@require_admin
def clear_all_data():
    """
    Tüm verileri ARŞİVLER (Soft Delete). 
    Gelecekte gerçekten silmek istenirse admin_confirmed_purge eklenebilir.
    """
    try:
        data = request.json or {}
        # Gelecekte ek güvenlik için: if not data.get('confirmed'): ...
        
        conn = get_db_connection()
        if not conn:
            return jsonify({"success": False, "error": "Veritabanı bağlantısı kurulamadı."}), 500
        cursor = conn.cursor()
        
        # Soft delete destekleyen tablolar
        soft_delete_tables = [
            "pcs", "queing_machines", "tablets",
            "printers", "barcode_printers", "barcode_readers", "scanners",
            "printer_service", "depot_items", "consumable_items", "users", "shared_areas"
        ]
        
        # Soft delete desteklemeyen ama temizlenmesi istenen tablolar (Hard Delete)
        hard_delete_tables = [
            "printer_service_history", "technical_notes", "closure_notes", 
            "troubleshooting_notes"
        ]

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        archived_count = 0
        for t in soft_delete_tables:
            try:
                # archive_date sütunu varsa set et
                cursor.execute(f"""
                    IF EXISTS (SELECT * FROM sysobjects WHERE name='{t}' AND xtype='U') 
                    UPDATE {t} SET is_deleted = 1, archive_date = '{now_str}' WHERE is_deleted = 0
                """)
                archived_count += cursor.rowcount
            except Exception as ex:
                # archive_date sütunu yoksa sadece is_deleted set et
                try:
                    cursor.execute(f"UPDATE {t} SET is_deleted = 1 WHERE is_deleted = 0")
                    archived_count += cursor.rowcount
                except Exception as inner_ex:
                    print(f"[ARCHIVE ERROR] {t} tablosunda is_deleted guncellenemedi: {inner_ex}")
                print(f"[ARCHIVE] {t} hatası: {ex}")

        for t in hard_delete_tables:
            try:
                cursor.execute(f"IF EXISTS (SELECT * FROM sysobjects WHERE name='{t}' AND xtype='U') DELETE FROM {t}")
            except Exception as ex:
                print(f"[PURGE] {t} hatası: {ex}")

        conn.commit()
        conn.close()
        
        from modules.logs_manager import log_activity
        log_activity(request.current_user.get('id'), "ARCHIVE_ALL", f"{archived_count} kayıt arşivlendi.")
        
        return jsonify({
            "success": True, 
            "message": f"Sistem genelindeki {archived_count} aktif kayıt arşivlendi ve temizlendi."
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@inventory_core_bp.route('/restore_archived', methods=['POST'])
@require_admin
def restore_archived():
    """Arşivlenmiş verileri geri yükler (Soft Restore)."""
    try:
        data = request.json
        table = data.get('table')
        record_id = data.get('id')
        
        if not table or not record_id:
            return jsonify({"error": "Tablo ve ID belirtilmelidir."}), 400

        # Sadece izin verilen tablolar
        allowed_tables = [
            "pcs", "queing_machines", "tablets", "printers", 
            "barcode_printers", "barcode_readers", "scanners"
        ]
        if table not in allowed_tables:
            return jsonify({"error": "Geçersiz tablo."}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(f"UPDATE {table} SET is_deleted = 0, archive_date = NULL WHERE id = ?", (record_id,))
        conn.commit()
        conn.close()
        
        from modules.logs_manager import log_activity
        log_activity(request.current_user.get('id', 0), f"RESTORE_{table.upper()}", f"ID: {record_id} geri yüklendi.")
        
        return jsonify({"success": True, "message": "Kayıt başarıyla geri yüklendi."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# =====================================================
#  TEKIL CIHAZ DETAYI (Lazy Loading Icin)
# =====================================================

@inventory_core_bp.route('/device/<int:device_id>', methods=['GET'])
@require_auth
def get_device_detail(device_id):
    try:
        from core.utils import success_response, error_response
        device_type = request.args.get('type', 'PC').upper()
        table = get_table_for_type(device_type)
        
        # Sadece izin verilen tablolardan veri çekildiğine emin ol
        if table not in ["pcs", "queing_machines", "tablets"]:
            return error_response("Geçersiz cihaz türü", code=400)
            
        # Tüm kolonları çek (* yerine güvenli get_safe_columns ile tümü)
        cols = get_safe_columns(table, ["*"]) 
        if cols == "*": cols = "*" # fallback
        
        query = f"SELECT d.*, d.location_code as location_code, m.location_name, m.tower as tower, m.floor as floor, m.phone_number FROM {table} d LEFT JOIN mahal_list m ON d.location_code = m.location_code WHERE d.id = ?"
        from core.database_sql import query_db
        items = query_db(query, (device_id,))
        if not items:
            return error_response("Cihaz bulunamadı", code=404)
            
        return success_response(map_db_to_frontend(items[0], table))
    except Exception as e:
        print(f"[API ERROR] get_device_detail: {e}")
        return error_response(f"Sistem Hatası: {str(e)}", code=500)

@inventory_core_bp.route('/device_by_code/<code>', methods=['GET'])
@require_auth
def get_device_by_code(code):
    try:
        code = str(code).strip()
        from core.database_sql import query_db
        from core.utils import success_response, error_response
        
        # 1. PC Tablosunda ara
        res = query_db("SELECT id, pc_serial as serial_no, location_code FROM pcs WHERE pc_no = ? AND (is_deleted = 0 OR is_deleted IS NULL)", (code,))
        if res:
            return success_response({"serial_no": res[0]['serial_no'], "location_code": res[0]['location_code']})
            
        # 2. Diğer Tablolarda ara
        tables = [
            ("printers", "serial_no", "recorded_device_no"),
            ("scanners", "serial_no", "recorded_device_no"),
            ("barcode_printers", "serial_no", "recorded_device_no"),
            ("barcode_readers", "serial_no", "recorded_device_no"),
            ("monitors", "serial_no", "recorded_device_no"),
            ("queing_machines", "pc_serial", "pc_no"),
            ("tablets", "pc_serial", "pc_no")
        ]
        
        for t, serial_col, pc_col in tables:
            try:
                # Query inside try-except to avoid table-not-exist or col-not-exist errors just in case
                res = query_db(f"SELECT id, {serial_col} as serial_no, location_code FROM {t} WHERE {pc_col} = ? AND (is_deleted = 0 OR is_deleted IS NULL)", (code,))
                if res:
                    return success_response({"serial_no": res[0]['serial_no'], "location_code": res[0]['location_code']})
            except Exception as e:
                print(f"[API ERROR] get_device_by_code loop error ({t}): {e}")
                pass
                
        return error_response("Cihaz bulunamadı", code=404)
    except Exception as e:
        print(f"[API ERROR] get_device_by_code: {e}")
        return error_response(f"Sistem Hatası: {str(e)}", code=500)

# =====================================================
#  SAYIM MODU
# =====================================================

@inventory_core_bp.route('/count', methods=['POST'])
@require_editor
def mark_counted():
    try:
        data = request.json
        record_id = data.get('id')
        counted_by = data.get('counted_by', request.current_user.get('display_name', 'Sistem'))
        
        if not record_id:
            return jsonify({"error": "ID belirtilmedi."}), 400
            
        from core.database_sql import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("UPDATE pcs SET last_counted_at = GETDATE(), counted_by = ? WHERE id = ?", (counted_by, record_id))
        conn.commit()
        conn.close()
        
        return jsonify({"success": True, "message": "Sayıldı olarak işaretlendi."})
    except Exception as e:
        print(f"[API ERROR] mark_counted: {e}")
        return jsonify({"error": str(e)}), 500


@inventory_core_bp.route('/count/undo', methods=['POST'])
@require_editor
def undo_mark_counted():
    try:
        data = request.json
        record_id = data.get('id')
        
        if not record_id:
            return jsonify({"error": "ID belirtilmedi."}), 400
            
        from core.database_sql import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("UPDATE pcs SET last_counted_at = NULL, counted_by = NULL WHERE id = ?", (record_id,))
        conn.commit()
        conn.close()
        
        return jsonify({"success": True, "message": "Sayım işlemi geri alındı."})
    except Exception as e:
        print(f"[API ERROR] undo_mark_counted: {e}")


@inventory_core_bp.route('/sync_peripherals', methods=['GET'])
@require_admin
def sync_peripherals():
    from core.database_sql import get_db_connection
    conn = get_db_connection()
    if not conn: return 'db error'
    try:
        c = conn.cursor()
        c.execute("UPDATE s SET s.recorded_device_no = 'PC-' + RIGHT('000' + CAST(p.pc_no AS VARCHAR), 3) FROM scanners s INNER JOIN pcs p ON s.serial_no = p.scanner_serial WHERE s.serial_no IS NOT NULL AND s.serial_no != '' AND s.serial_no != '---'")
        c.execute("UPDATE s SET s.recorded_device_no = 'PC-' + RIGHT('000' + CAST(p.pc_no AS VARCHAR), 3) FROM barcode_readers s INNER JOIN pcs p ON s.serial_no = p.bo_serial WHERE s.serial_no IS NOT NULL AND s.serial_no != '' AND s.serial_no != '---'")
        c.execute("UPDATE s SET s.recorded_device_no = 'PC-' + RIGHT('000' + CAST(p.pc_no AS VARCHAR), 3) FROM barcode_printers s INNER JOIN pcs p ON s.serial_no = p.by_serial WHERE s.serial_no IS NOT NULL AND s.serial_no != '' AND s.serial_no != '---'")
        conn.commit()
        return 'sync ok'
    except Exception as e:
        return str(e)


@inventory_core_bp.route('/weekly_location_report', methods=['GET'])
@require_auth
def get_weekly_location_report():
    """Son 7 günde mahal değişikliği yapılmış cihazların listesini getirir."""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"success": False, "error": "Veritabanı bağlantısı kurulamadı"}), 500
        
        cursor = conn.cursor()
        
        # 1. Mahal listesini çekip eşleme sözlüğü oluşturalım
        cursor.execute("SELECT location_code, location_name FROM mahal_list")
        mahal_map = {}
        for r in cursor.fetchall():
            mahal_map[str(r[0]).strip()] = r[1]
            
        # 2. Son 7 gündeki mahal değişikliklerini çekelim
        query = """
            SELECT table_name, record_id, record_label, field_name, 
                   old_value, new_value, changed_by, display_name, timestamp
            FROM audit_logs
            WHERE field_name IN ('location_code', 'keyos_location', 'warehouse', 'on_field', 'is_faulty', 'without_location')
              AND timestamp >= DATEADD(day, -7, GETDATE())
            ORDER BY timestamp DESC
        """
        cursor.execute(query)
        columns = [column[0] for column in cursor.description]
        
        results = []
        for row in cursor.fetchall():
            row_dict = dict(zip(columns, row))
            
            # Timestamp'ı string formatına çevir
            if row_dict.get('timestamp') and isinstance(row_dict['timestamp'], datetime):
                row_dict['timestamp'] = row_dict['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            
            field = row_dict.get('field_name', '')
            old_val_raw = str(row_dict.get('old_value', '')).strip()
            new_val_raw = str(row_dict.get('new_value', '')).strip()
            
            if field in ['location_code', 'keyos_location']:
                row_dict['old_location_name'] = mahal_map.get(old_val_raw, old_val_raw or '-')
                row_dict['new_location_name'] = mahal_map.get(new_val_raw, new_val_raw or '-')
            else:
                # Durum değişiklikleri
                row_dict['old_value'] = '-'
                row_dict['old_location_name'] = '-'
                row_dict['new_value'] = 'DURUM DEĞİŞTİ'
                
                new_bool = new_val_raw in ('1', 'true', 'True', 'yes', 'Yes')
                
                if field == 'warehouse' and new_bool:
                    row_dict['new_location_name'] = 'Depoya Taşındı'
                elif field == 'on_field' and new_bool:
                    row_dict['new_location_name'] = 'Sahada Kuruldu'
                elif field == 'is_faulty' and new_bool:
                    row_dict['new_location_name'] = 'Arızalı Olarak Ayrıldı'
                elif field == 'without_location' and new_bool:
                    row_dict['new_location_name'] = 'Kayıp/Mahalsiz İşaretlendi'
                else:
                    # If it was set to 0, it means it was removed from that state, which usually coincides with being put into another state.
                    # We can skip the '0' states to avoid duplicate rows, or just log them.
                    if not new_bool:
                        continue 
            
            # Cihaz tipi ismini daha okunabilir yapalım (Örn: pcs -> Bilgisayar)
            table_name = row_dict.get('table_name', '')
            device_type = "Bilinmeyen Cihaz"
            if table_name == 'pcs':
                device_type = "Bilgisayar"
            elif table_name == 'tablets':
                device_type = "Tablet"
            elif table_name == 'queing_machines':
                device_type = "Sıramatik"
            elif table_name == 'printers':
                device_type = "Yazıcı"
            elif table_name == 'barcode_printers':
                device_type = "Barkod Yazıcı"
            elif table_name == 'barcode_readers':
                device_type = "Barkod Okuyucu"
            elif table_name == 'scanners':
                device_type = "Tarayıcı"
            elif table_name == 'monitors':
                device_type = "Monitör"
            
            row_dict['device_type'] = device_type
            results.append(row_dict)
            
        conn.close()
        return jsonify({"success": True, "items": results})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@inventory_core_bp.route('/list_backups', methods=['GET'])
@require_admin
def list_backups():
    try:
        from config import BASE_DIR
        import os, datetime
        yedek_path = os.path.join(BASE_DIR, "database", "yedek")
        if not os.path.exists(yedek_path):
            return jsonify({"success": True, "backups": []})
            
        files = []
        for f in os.listdir(yedek_path):
            if f.endswith('.bak'):
                full_path = os.path.join(yedek_path, f)
                stat = os.stat(full_path)
                files.append({
                    "filename": f,
                    "size": stat.st_size,
                    "created_at": datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                })
        files.sort(key=lambda x: x['created_at'], reverse=True)
        return jsonify({"success": True, "backups": files})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@inventory_core_bp.route('/download_backup/<path:filename>', methods=['GET'])
@require_admin
def download_backup(filename):
    try:
        from config import BASE_DIR
        import os
        from flask import send_file
        from werkzeug.utils import secure_filename
        
        safe_filename = secure_filename(filename)
        yedek_path = os.path.join(BASE_DIR, "database", "yedek")
        file_path = os.path.join(yedek_path, safe_filename)
        
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({"success": False, "error": "Dosya bulunamadi"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@inventory_core_bp.route('/restore_db', methods=['POST'])
@require_admin
def restore_backup():
    try:
        from config import BASE_DIR
        import os
        from core.database_sql import restore_sql_db
        from werkzeug.utils import secure_filename
        
        backup_file = None
        
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename.endswith('.bak'):
                safe_name = secure_filename(file.filename)
                yedek_path = os.path.join(BASE_DIR, "database", "yedek")
                if not os.path.exists(yedek_path):
                    os.makedirs(yedek_path)
                backup_file = os.path.join(yedek_path, f"UPLOADED_{safe_name}")
                file.save(backup_file)
        elif request.json and 'filename' in request.json:
            safe_name = secure_filename(request.json['filename'])
            backup_file = os.path.join(BASE_DIR, "database", "yedek", safe_name)
            
        if not backup_file or not os.path.exists(backup_file):
            return jsonify({"success": False, "error": "Gecerli bir .bak dosyasi saglanamadi veya dosya bulunamadi."}), 400
            
        success, msg = restore_sql_db(backup_file)
        return jsonify({"success": success, "message" if success else "error": msg}), 200 if success else 500
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
