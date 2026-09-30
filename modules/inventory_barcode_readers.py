from core.utils import normalize_row
from flask import Blueprint, jsonify, request
from core.database_sql import get_db_connection
from core.auth import require_auth, require_admin, require_editor

inventory_barcode_readers_bp = Blueprint('inventory_barcode_readers', __name__)

@inventory_barcode_readers_bp.route('/get_all', methods=['GET'])
@require_auth
def get_all():
    conn = get_db_connection()
    if not conn: return jsonify([])
    cursor = conn.cursor()
    
    all_devices = []
    try:
        include_archived = request.args.get('include_archived') == 'true'
        if include_archived:
            query = "SELECT * FROM barcode_readers"
        else:
            query = "SELECT * FROM barcode_readers WHERE is_deleted = 0"
        cursor.execute(query)
        columns = [column[0] for column in cursor.description]
        for row in cursor.fetchall():
            d = normalize_row(dict(zip(columns, row)))
            d['device_class'] = 'BARCODE_READER'
            raw_no = str(d.get('name') or '')
            if raw_no.isdigit(): d['pr_no'] = f"BO-{raw_no.zfill(3)}"
            else: d['pr_no'] = raw_no
            
            d['seri'] = d.get('serial_no')
            d['recorded_device_no'] = d.get('recorded_device_no') or d.get('pc_no')
            d['pc_no'] = d['recorded_device_no']
            d['mahal'] = d.get('recorded_device_no') or d.get('pc_no')
            
            if not d.get('status'):
                d['status'] = 'Kurulu'
                
            all_devices.append(d)
    except Exception as e:
        print("PRINTER GET_ALL ERR (barcode_readers):", e)
    finally:
        conn.close()

    return jsonify(all_devices)

@inventory_barcode_readers_bp.route('/update', methods=['POST'])
@require_editor
def update_device():
    try:
        data = request.json
        if not data or 'id' not in data:
            return jsonify({"error": "ID belirtilmedi."}), 400
        
        record_id = data['id']
        changed_by = data.get('changed_by', 'system')
        display_name = data.get('display_name', 'Sistem')

        column_map = {
            'ip': 'pc_no',
            'seri': 'serial_no',
            'serial_no': 'serial_no',
            'pr_no': 'name',
            'name': 'name'
        }

        from modules.logs_manager import log_change
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM barcode_readers WHERE id = ? AND is_deleted = 0", (record_id,))
        columns = [column[0] for column in cursor.description]
        old_row = cursor.fetchone()
        if not old_row:
            conn.close()
            return jsonify({"error": "Cihaz bulunamadi."}), 404
        
        old_data = dict(zip(columns, old_row))
        record_label = old_data.get('name') or str(record_id)

        update_fields = []
        params = []
        allowed_fields = ['pr_no', 'ip', 'seri', 'status', 'name', 'serial_no']
        
        for field in allowed_fields:
            if field in data:
                sql_col = column_map.get(field, field)
                if sql_col not in columns: continue 
                
                new_val = data[field]
                old_val = old_data.get(sql_col)
                
                if str(new_val) != str(old_val if old_val is not None else ''):
                    log_change('barcode_readers', record_id, record_label, field, old_val, new_val, changed_by, display_name)
                    update_fields.append(f"[{sql_col}] = ?")
                    params.append(new_val)

        if not update_fields:
            # Sadece arşivden çıkarma durumu olabilir, en azından is_deleted=0 yapalım
            update_fields.append("is_deleted = 0")
        else:
            update_fields.append("is_deleted = 0")

        params.append(record_id)
        query = f"UPDATE barcode_readers SET {', '.join(update_fields)} WHERE id = ?"
        cursor.execute(query, params)
        
        # Reverse sync to PCs
        new_pc = str(data.get('mahal', '')).strip()
        old_pc = str(old_data.get('pc_no', '')).strip()
        serial = str(data.get('seri') or old_data.get('serial_no', '')).strip()
        
        if 'mahal' in data and new_pc != old_pc:
            if old_pc:
                cursor.execute("UPDATE pcs SET bo_serial = NULL WHERE pc_no = ?", (old_pc.replace('PC-',''),))
            if new_pc:
                cursor.execute("UPDATE pcs SET bo_serial = ? WHERE pc_no = ?", (serial, new_pc.replace('PC-','')))

        conn.commit()
        conn.close()
        
        return jsonify({"success": True, "message": "Cihaz guncellendi."})
    except Exception as e:
        print(f"[BARCODE READER UPDATE ERROR] {e}")
        return jsonify({"error": str(e)}), 500

@inventory_barcode_readers_bp.route('/delete/<int:id>', methods=['DELETE'])
@require_editor
def delete_device(id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE barcode_readers SET is_deleted = 1, deleted_at = GETDATE() WHERE id = ?", (id,))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Cihaz silindi."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@inventory_barcode_readers_bp.route('/device/<int:device_id>', methods=['GET'])
@require_auth
def get_device_detail(device_id):
    try:
        conn = get_db_connection()
        if not conn: return jsonify({"error": "Veritabanı bağlantısı yok"}), 500
        
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM barcode_readers WHERE id = ?", (device_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return jsonify({"error": "Cihaz bulunamadı"}), 404
            
        columns = [column[0] for column in cursor.description]
        d = normalize_row(dict(zip(columns, row)))
        d['device_class'] = 'BARCODE_READER'
        
        raw_no = str(d.get('name') or '')
        if raw_no.isdigit(): d['pr_no'] = f"BO-{raw_no.zfill(3)}"
        else: d['pr_no'] = raw_no
        d['seri'] = d.get('serial_no')
        d['recorded_device_no'] = d.get('recorded_device_no') or d.get('pc_no')
        d['mahal'] = d.get('recorded_device_no') or d.get('pc_no')
        if not d.get('status'):
            d['status'] = 'Kurulu'
            
        conn.close()
        return jsonify({"success": True, "data": d})
        
    except Exception as e:
        print(f"[API ERROR] barcode_reader get_device_detail: {e}")
        return jsonify({"error": str(e)}), 500

@inventory_barcode_readers_bp.route('/check_serial', methods=['POST'])
@require_auth
def check_serial():
    try:
        data = request.json
        serial = data.get('serial')
        if not serial:
            return jsonify({"error": "Seri no gereklidir."}), 400
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM barcode_readers WHERE serial_no = ? AND is_deleted = 0", (serial,))
        found = cursor.fetchone() is not None
                
        conn.close()
        return jsonify({"success": True, "exists": found, "table": 'barcode_readers'})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@inventory_barcode_readers_bp.route('/auto_register', methods=['POST'])
@require_editor
def auto_register():
    try:
        data = request.json
        serial = data.get('serial')
        pc_no = data.get('pc_no')
        
        if not serial:
            return jsonify({"error": "Eksik bilgi."}), 400
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM barcode_readers WHERE serial_no = ? AND is_deleted = 0", (serial,))
        if cursor.fetchone():
            conn.close()
            return jsonify({"success": True, "message": "Cihaz zaten kayıtlı."})
            
        cursor.execute("SELECT MAX(id) FROM barcode_readers")
        max_id = cursor.fetchone()[0] or 0
        new_name = f"BO-{(max_id + 1):03d}"
        
        query = "INSERT INTO barcode_readers (name, serial_no, status, pc_no) VALUES (?, ?, ?, ?)"
        cursor.execute(query, (new_name, serial, 'Kurulu', pc_no))
        
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": f"{new_name} olarak kaydedildi."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
