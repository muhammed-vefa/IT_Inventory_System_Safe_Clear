from flask import Blueprint, jsonify, request
from core.database_sql import get_db_connection, query_db
from core.auth import require_auth, require_editor, require_admin, require_depot_editor

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
        """
        results = query_db(query) or []
        
        def sort_key(item):
            cat = str(item.get('category', '') or '').upper().strip()
            cat_order = {
                'AĞ VE ALTYAPI': 1,
                'DONANIM': 2,
                'AKSESUAR': 3,
                'SARF MALZEME': 4,
                'OFİS / GIDA': 5,
                'OFIS / GIDA': 5
            }
            return (cat_order.get(cat, 6), str(item.get('name', '') or '').lower())
            
        results.sort(key=sort_key)
        
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@depot_manager_bp.route('/update_stock', methods=['POST'])
@require_depot_editor
def update_stock():
    try:
        data = request.json
        item_id = data.get('id')
        category = data.get('category')
        action = data.get('action')
        amount = int(data.get('amount', 0))
        
        table_name, table_type = get_target_table(category)
        
        if not item_id or not action or amount <= 0:
            return jsonify({"success": False, "error": "Gecersiz veri"}), 400
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(f"SELECT current_stock FROM {table_name} WHERE id=?", (item_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({"success": False, "error": "Urun bulunamadi"}), 404
            
        current_qty = row[0] or 0
        new_qty = current_qty + (amount if action == 'IN' else -amount)
        
        if action == 'OUT' and current_qty < amount:
            conn.close()
            return jsonify({"success": False, "error": "Yetersiz stok!"}), 400
            
        cursor.execute(f"UPDATE {table_name} SET current_stock=? WHERE id=?", (new_qty, item_id))
        
        user_name = request.current_user.get('display_name') or request.current_user.get('username') or 'Bilinmiyor'
        
        try:
            cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name='depot_transactions')
            BEGIN
                CREATE TABLE [depot_transactions] (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    item_id INT NOT NULL,
                    item_type NVARCHAR(50) DEFAULT 'depot',
                    transaction_type NVARCHAR(50),
                    quantity INT NOT NULL,
                    previous_stock INT NOT NULL,
                    new_stock INT NOT NULL,
                    username NVARCHAR(100),
                    created_at DATETIME DEFAULT GETDATE(),
                    description NVARCHAR(MAX)
                )
            END
            """)
        except Exception as e:
            pass

        cursor.execute("""
            INSERT INTO depot_transactions (item_id, item_type, transaction_type, quantity, previous_stock, new_stock, username, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (item_id, table_type, 'in' if action == 'IN' else 'out', amount, current_qty, new_qty, user_name, 'Stok Guncelleme'))
        
        conn.commit()
        conn.close()
        
        return jsonify({"success": True, "message": "Stok guncellendi", "new_quantity": new_qty})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@depot_manager_bp.route('/add', methods=['POST'])
@require_depot_editor
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
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if table_type == 'consumable':
            cursor.execute(f"""
                INSERT INTO {table_name} 
                (name, category, current_stock, critical_stock, unit, description, field_stock, total_stock) 
                VALUES (?,?,?,?,?,?,?,?)
            """, (name, category, qty, crit, unit, desc, saha, total))
        else:
            cursor.execute(f"""
                INSERT INTO {table_name} 
                (name, category, current_stock, critical_stock, unit, description, field_stock, faulty_stock, lost_stock, total_stock) 
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (name, category, qty, crit, unit, desc, saha, is_faulty, kayip, total))
        
        cursor.execute("SELECT @@IDENTITY")
        row = cursor.fetchone()
        new_id = row[0] if row else None

        user_name = request.current_user.get('display_name') or request.current_user.get('username') or 'Bilinmiyor'
        if new_id:
            cursor.execute("""
                INSERT INTO depot_transactions (item_id, item_type, transaction_type, quantity, previous_stock, new_stock, username, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (new_id, table_type, 'in', qty, 0, qty, user_name, 'Yeni Urun Eklendi'))
            
        conn.commit()
        conn.close()
        
        return jsonify({"success": True, "message": "Urun eklendi."})
    except Exception as e:
        if 'conn' in locals() and conn:
            conn.close()
        return jsonify({"success": False, "error": str(e)}), 500


@depot_manager_bp.route('/update/<int:item_id>', methods=['PUT'])
@require_depot_editor
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
        table_type_param = data.get('table_type')
        
        if table_type_param == 'consumable':
            table_name, table_type = 'consumable_items', 'consumable'
        elif table_type_param == 'depot':
            table_name, table_type = 'depot_items', 'depot'
        else:
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
        table_type_param = request.args.get('table_type')
        if table_type_param == 'consumable':
            table_name = 'consumable_items'
        elif table_type_param == 'depot':
            table_name = 'depot_items'
        else:
            table_name, _ = get_target_table(category)
        query_db(f"DELETE FROM {table_name} WHERE id=?", (item_id,))
        return jsonify({"success": True, "message": "Ürün silindi."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@depot_manager_bp.route('/transaction', methods=['POST'])
@require_depot_editor
def transaction():
    try:
        data = request.json
        item_id = data.get('depot_item_id')
        category = data.get('category')
        table_type_param = data.get('table_type')
        trans_type = data.get('type')  # 'in' or 'out'
        qty = int(data.get('quantity', 0))
        description = data.get('description', 'Stok Hareketi')
        
        if table_type_param == 'consumable':
            table_name = 'consumable_items'
            table_type = 'consumable'
        elif table_type_param == 'depot':
            table_name = 'depot_items'
            table_type = 'depot'
        else:
            table_name, table_type = get_target_table(category)
        
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
        
        user_name = request.current_user.get('display_name') or request.current_user.get('username') or 'Bilinmiyor'
        
        # Tablo yoksa otomatik olustur (Sistem onarim)
        try:
            cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name='depot_transactions')
            BEGIN
                CREATE TABLE [depot_transactions] (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    item_id INT NOT NULL,
                    item_type NVARCHAR(50) DEFAULT 'depot',
                    transaction_type NVARCHAR(50),
                    quantity INT NOT NULL,
                    previous_stock INT NOT NULL,
                    new_stock INT NOT NULL,
                    username NVARCHAR(100),
                    created_at DATETIME DEFAULT GETDATE(),
                    description NVARCHAR(MAX)
                )
            END
            """)
        except Exception as e:
            pass

        cursor.execute("""
            INSERT INTO depot_transactions (item_id, item_type, transaction_type, quantity, previous_stock, new_stock, username, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (item_id, table_type, trans_type, qty, current_qty, new_qty, user_name, description))
        
        conn.commit()
        conn.close()
        
        return jsonify({"success": True, "new_stock": new_qty})
    except Exception as e:
        if 'conn' in locals() and conn:
            conn.close()
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
        
        # Son 7 gunun hareketlerini cek
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name='depot_transactions')
            BEGIN
                CREATE TABLE [depot_transactions] (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    item_id INT NOT NULL,
                    item_type NVARCHAR(50) DEFAULT 'depot',
                    transaction_type NVARCHAR(50),
                    quantity INT NOT NULL,
                    previous_stock INT NOT NULL,
                    new_stock INT NOT NULL,
                    username NVARCHAR(100),
                    created_at DATETIME DEFAULT GETDATE(),
                    description NVARCHAR(MAX)
                )
            END
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            pass

        trans_query = """
            SELECT t.created_at as transaction_time, 
                   COALESCE(d.category, c.category, 'Belirsiz') as category,
                   COALESCE(d.name, c.name, 'Bilinmeyen Urun') as name, 
                   t.transaction_type, t.quantity, t.username
            FROM depot_transactions t
            LEFT JOIN depot_items d ON t.item_id = d.id AND (t.item_type != 'consumable' AND UPPER(LTRIM(RTRIM(t.item_type))) NOT IN ('SARF MALZEME', 'OFIS / GIDA', 'OFİS / GİDA', 'OFİS / GIDA'))
            LEFT JOIN consumable_items c ON t.item_id = c.id AND (t.item_type = 'consumable' OR UPPER(LTRIM(RTRIM(t.item_type))) IN ('SARF MALZEME', 'OFIS / GIDA', 'OFİS / GİDA', 'OFİS / GIDA'))
            WHERE t.created_at >= DATEADD(day, -7, GETDATE())
            ORDER BY t.created_at DESC
        """
        transactions_raw = query_db(trans_query) or []
        
        transactions = []
        for row in transactions_raw:
            created_at_val = row.get('transaction_time')
            # transaction_time is not affected by normalize_row stripping time, so it's a raw datetime object
            if created_at_val:
                try:
                    created_at_str = created_at_val.isoformat()
                except AttributeError:
                    created_at_str = str(created_at_val).replace(" ", "T")
            else:
                created_at_str = ""

            transactions.append({
                "created_at": created_at_str,
                "item_category": row.get('category', ''),
                "item_name": row.get('name', ''),
                "transaction_type": row.get('transaction_type', ''),
                "quantity": row.get('quantity', 0),
                "user_name": row.get('username', '')
            })
        
        return jsonify({
            "items": items,
            "transactions": transactions
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

