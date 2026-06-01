from flask import Blueprint, jsonify, request
from core.database_sql import get_db_connection, query_db
from core.auth import require_auth, require_editor, require_admin

depot_manager_bp = Blueprint('depot_manager', __name__)

def get_target_table(category):
    """Kategoriye gore tablo adini doner."""
    cat_norm = str(category or "").upper().strip()
    # Onemli: 'OFİS / GİDA' ve 'OFIS / GIDA' gibi varyasyonlari destekle
    if cat_norm in ['SARF MALZEME', 'OFIS / GIDA', 'OFİS / GİDA', 'OFİS / GIDA']:
        return "consumable_items", "consumable"
    return "depot_items", "depot"

@depot_manager_bp.route('/get_all', methods=['GET'])
@require_auth
def get_all():
    try:
        query = """
            SELECT id, name, category, current_stock, critical_stock, unit, description, 
            field_stock, faulty_stock, lost_stock, total_stock, 'depot' as table_origin
            FROM depot_items
            UNION ALL
            SELECT id, name, category, current_stock, critical_stock, unit, description, 
            field_stock, 0 as faulty_stock, 0 as lost_stock, total_stock, 'consumable' as table_origin
            FROM consumable_items
            ORDER BY name ASC
        """
        results = query_db(query)
        return jsonify(results or [])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@depot_manager_bp.route('/update_stock', methods=['POST'])
@require_editor
def update_stock():
    try:
        data = request.json
        item_id = data.get('id')
        category = data.get('category')
        action = data.get('action')
        amount = int(data.get('amount', 0))
        
        table_name, _ = get_target_table(category)
        
        if not item_id or not action or amount <= 0:
            return jsonify({"success": False, "error": "Geçersiz veri"}), 400
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(f"SELECT current_stock FROM {table_name} WHERE id=?", (item_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({"success": False, "error": "Ürün bulunamadı"}), 404
            
        current_qty = row[0] or 0
        new_qty = current_qty + (amount if action == 'IN' else -amount)
        
        if action == 'OUT' and current_qty < amount:
            conn.close()
            return jsonify({"success": False, "error": "Yetersiz stok!"}), 400
            
        cursor.execute(f"UPDATE {table_name} SET current_stock=? WHERE id=?", (new_qty, item_id))
        conn.commit()
        conn.close()
        
        return jsonify({"success": True, "message": "Stok güncellendi", "new_quantity": new_qty})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@depot_manager_bp.route('/add', methods=['POST'])
@require_editor
def add_item():
    try:
        data = request.json
        name = data.get('name')
        category = data.get('category')
        qty = int(data.get('current_stock', 0))
        crit = int(data.get('critical_stock', 0))
        unit = data.get('unit', 'Adet')
        desc = data.get('description', '')
        saha = int(data.get('field_stock', 0))
        is_faulty = int(data.get('faulty_stock', 0))
        kayip = int(data.get('lost_stock', 0))
        total = int(data.get('total_stock', 0))
        
        table_name, table_type = get_target_table(category)
        
        if table_type == 'consumable':
            query_db(f"""
                INSERT INTO {table_name} 
                (name, category, current_stock, critical_stock, unit, description, field_stock, total_stock) 
                VALUES (?,?,?,?,?,?,?,?)
            """, (name, category, qty, crit, unit, desc, saha, total))
        else:
            query_db(f"""
                INSERT INTO {table_name} 
                (name, category, current_stock, critical_stock, unit, description, field_stock, faulty_stock, lost_stock, total_stock) 
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (name, category, qty, crit, unit, desc, saha, is_faulty, kayip, total))
        
        return jsonify({"success": True, "message": "Ürün eklendi."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@depot_manager_bp.route('/update/<int:item_id>', methods=['PUT'])
@require_editor
def update_item(item_id):
    try:
        data = request.json
        name = data.get('name')
        category = data.get('category')
        qty = int(data.get('current_stock', 0))
        crit = int(data.get('critical_stock', 0))
        unit = data.get('unit', 'Adet')
        desc = data.get('description', '')
        saha = int(data.get('field_stock', 0))
        is_faulty = int(data.get('faulty_stock', 0))
        kayip = int(data.get('lost_stock', 0))
        total = int(data.get('total_stock', 0))
        
        table_name, table_type = get_target_table(category)
        
        if table_type == 'consumable':
            query_db(f"""
                UPDATE {table_name} SET 
                name=?, category=?, current_stock=?, critical_stock=?, unit=?, 
                description=?, field_stock=?, total_stock=? 
                WHERE id=?
            """, (name, category, qty, crit, unit, desc, saha, total, item_id))
        else:
            query_db(f"""
                UPDATE {table_name} SET 
                name=?, category=?, current_stock=?, critical_stock=?, unit=?, 
                description=?, field_stock=?, faulty_stock=?, lost_stock=?, total_stock=? 
                WHERE id=?
            """, (name, category, qty, crit, unit, desc, saha, is_faulty, kayip, total, item_id))
        
        return jsonify({"success": True, "message": "Ürün güncellendi."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@depot_manager_bp.route('/delete/<int:item_id>', methods=['DELETE'])
@require_admin
def delete_item(item_id):
    try:
        category = request.args.get('category')
        table_name, _ = get_target_table(category)
        query_db(f"DELETE FROM {table_name} WHERE id=?", (item_id,))
        return jsonify({"success": True, "message": "Ürün silindi."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@depot_manager_bp.route('/transaction', methods=['POST'])
@require_editor
def transaction():
    try:
        data = request.json
        item_id = data.get('depot_item_id')
        category = data.get('category')
        trans_type = data.get('type')  # 'in' or 'out'
        qty = int(data.get('quantity', 0))
        
        table_name, _ = get_target_table(category)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(f"SELECT current_stock FROM {table_name} WHERE id=?", (item_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({"error": "Ürün bulunamadı"}), 404
            
        current_qty = row[0] or 0
        new_qty = current_qty + (qty if trans_type == 'in' else -qty)
        
        if trans_type == 'out' and current_qty < qty:
            conn.close()
            return jsonify({"error": "Yetersiz stok!"}), 400
            
        cursor.execute(f"UPDATE {table_name} SET current_stock=? WHERE id=?", (new_qty, item_id))
        conn.commit()
        conn.close()
        
        return jsonify({"success": True, "new_stock": new_qty})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@depot_manager_bp.route('/weekly_report', methods=['GET'])
@require_auth
def weekly_report():
    try:
        query = """
            SELECT id, name, category, current_stock, critical_stock, unit
            FROM depot_items WHERE is_deleted = 0
            UNION ALL
            SELECT id, name, category, current_stock, critical_stock, unit
            FROM consumable_items WHERE is_deleted = 0
            ORDER BY name ASC
        """
        items = query_db(query) or []
        
        return jsonify({
            "items": items,
            "transactions": [] # Henüz stok hareketleri tablosu olmadığı için boş döndürüyoruz.
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

