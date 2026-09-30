import re
from flask import Blueprint, jsonify, request
from core.database_sql import query_db, get_db_connection

inventory_call_screens_bp = Blueprint('inventory_call_screens', __name__)

@inventory_call_screens_bp.route('/call_screens', methods=['GET'])
def get_call_screens():
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Database connection error"}), 500
            
        cursor = conn.cursor()
        include_archived = request.args.get('include_archived') == 'true'
        if include_archived:
            query = "SELECT * FROM call_screens"
        else:
            query = "SELECT * FROM call_screens WHERE is_deleted = 0 OR is_deleted IS NULL"
            
        cursor.execute(query)
        columns = [column[0] for column in cursor.description]
        data = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        # Format the data for the frontend
        formatted_data = []
        for d in data:
            item = {k: v for k, v in d.items()}
            item['device_class'] = 'CALL_SCREEN'
            item['device_type'] = 'CALL_SCREEN'
            
            item['pr_no'] = d.get('device_name') or '-'
            item['pc_no'] = d.get('device_name') or '-'
            
            item['id'] = d.get('id')
            item['name'] = d.get('device_name')
            raw_loc = d.get('location_code')
            if raw_loc:
                raw_loc = re.sub(r'-\d+$', '', raw_loc)
            item['location_code'] = raw_loc
            item['mahal'] = raw_loc
            item['on_field'] = d.get('on_field')
            item['is_faulty'] = d.get('is_faulty')
            item['model'] = d.get('model')
            item['mac'] = d.get('mac')
            item['serial_no'] = d.get('serial_no') # Karttaki SERİ NO kısmında gerçek seri no görünsün
            item['firmware'] = d.get('firmware')
            item['ip'] = d.get('ip')
            item['notes'] = d.get('note')
            
            # Map organization and group_name into notes or assigned_to for display
            item['assigned_to'] = d.get('organization')
            
            # Status mapping
            if d.get('is_faulty'):
                item['status'] = 'ARIZALI'
            elif d.get('on_field'):
                item['status'] = 'KURULU'
            elif d.get('warehouse'):
                item['status'] = 'DEPODA'
            elif d.get('without_location'):
                item['status'] = 'KAYIP'
            elif d.get('in_service'):
                item['status'] = 'SERVISTE'
            else:
                item['status'] = 'KURULU'
            
            formatted_data.append(item)

        # Sort by device_name
        formatted_data.sort(key=lambda x: str(x.get('pr_no') or '').upper())
            
        return jsonify(formatted_data)
    except Exception as e:
        print(f"Error fetching call_screens: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if 'conn' in locals() and conn:
            try:
                conn.close()
            except Exception as conn_close_e:
                print(f"[Call Screens DB Close Error] {conn_close_e}")

@inventory_call_screens_bp.route('/call_screens/update', methods=['POST'])
def update_call_screen():
    data = request.json
    item_id = data.get('id')
    if not item_id:
        return jsonify({'success': False, 'error': 'ID eksik.'}), 400
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if 'pc_no' in data:
            updates.append("device_name = ?")
            params.append(data['pc_no'])
        if 'location_code' in data:
            updates.append("location_code = ?")
            params.append(data['location_code'])
        if 'ip' in data:
            updates.append("ip = ?")
            params.append(data['ip'])
        if 'mac' in data:
            updates.append("mac = ?")
            params.append(data['mac'])
        if 'serial_no' in data:
            updates.append("serial_no = ?")
            params.append(data['serial_no'])
        if 'notes' in data or 'note' in data:
            updates.append("note = ?")
            params.append(data.get('notes') or data.get('note'))
        if 'on_field' in data:
            updates.append("on_field = ?")
            params.append(1 if data['on_field'] else 0)
        if 'warehouse' in data:
            updates.append("warehouse = ?")
            params.append(1 if data['warehouse'] else 0)
        if 'is_faulty' in data:
            updates.append("is_faulty = ?")
            params.append(1 if data['is_faulty'] else 0)
            
        if not updates:
            return jsonify({'success': True})
            
        query = f"UPDATE call_screens SET {', '.join(updates)} WHERE id = ?"
        params.append(item_id)
        
        cursor.execute(query, params)
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if 'conn' in locals() and conn:
            conn.close()
