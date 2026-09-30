from flask import Blueprint, jsonify, request
from core.database_sql import query_db, get_db_connection
from core.auth import require_auth, require_admin, require_editor
from core.permissions import require_operation
from datetime import datetime
from modules.inventory_core import get_table_for_type, map_db_to_frontend, get_safe_columns, check_column_exists

inventory_monitors_bp = Blueprint('inventory_monitors', __name__)

@inventory_monitors_bp.route('/monitors', methods=['GET'])
def get_monitors():
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Database connection error"}), 500
            
        cursor = conn.cursor()
        include_archived = request.args.get('include_archived') == 'true'
        if include_archived:
            query = "SELECT * FROM monitors"
        else:
            query = "SELECT * FROM monitors WHERE is_deleted = 0"
        cursor.execute(query)
        columns = [column[0] for column in cursor.description]
        data = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        # Format the data exactly like barcode printers for the frontend
        formatted_data = []
        for d in data:
            item = {k: v for k, v in d.items()}
            item['device_class'] = 'MONITOR'
            item['device_type'] = 'MONITOR'
            raw_no = str(item.get('name') or '')
            if raw_no.isdigit(): item['pr_no'] = f"MN-{raw_no.zfill(3)}"
            else: item['pr_no'] = raw_no
            item['id'] = d.get('id')
            item['name'] = d.get('name')
            item['location_code'] = d.get('location_code')
            item['mahal'] = d.get('location_code')
            item['on_field'] = d.get('on_field')
            item['is_faulty'] = d.get('is_faulty')
            item['model'] = d.get('model')
            item['serial_no'] = d.get('serial_no')
            item['seri'] = d.get('serial_no')
            item['mac'] = d.get('mac')
            item['assigned_to'] = d.get('assigned_to')
            item['notes'] = d.get('notes')
            item['monitor_type'] = d.get('monitor_type')
            
            # Anayasaya göre Monitörlerin bağlı olduğu PC 'status' kolonunda tutulur.
            # Frontend'de IP inputuna ve UI'a yansıması için:
            item['ip'] = d.get('status')
            item['recorded_device_no'] = d.get('status')
            item['pc_no'] = d.get('status')
            
            # Durum (Status) hesaplama
            if d.get('is_faulty'):
                item['status'] = 'ARIZALI'
            elif d.get('on_field'):
                item['status'] = 'KURULU'
            elif d.get('warehouse'):
                item['status'] = 'DEPODA'
            elif d.get('without_location'):
                item['status'] = 'KAYIP'
            elif d.get('in_service'):
                item['status'] = 'SERVİSTE'
            else:
                item['status'] = 'KURULU'
            
            formatted_data.append(item)

        def monitor_sort_key(item):
            pr_no = str(item.get('pr_no') or '').upper()
            if pr_no.startswith('MN-'):
                try:
                    num = int(pr_no.replace('MN-', ''))
                    return (0, num, pr_no)
                except ValueError:
                    return (0, float('inf'), pr_no)
            else:
                return (1, float('inf'), pr_no)

        formatted_data.sort(key=monitor_sort_key)
            
        return jsonify(formatted_data)
    except Exception as e:
        print(f"Error fetching monitors: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if 'conn' in locals() and conn:
            try:
                conn.close()
            except Exception as conn_close_e:
                print(f"[Monitors DB Close Error] {conn_close_e}")


