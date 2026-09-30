from flask import Blueprint, jsonify, request
from core.database_sql import get_db_connection, query_db
from core.auth import require_admin
import datetime

network_manager_bp = Blueprint("network_manager", __name__)

@network_manager_bp.route("/get_all", methods=["GET"])
def get_all():
    conn = get_db_connection()
    if not conn: return jsonify([])
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM network_devices WHERE is_deleted = 0 OR is_deleted IS NULL ORDER BY location_code ASC")
    columns = [column[0] for column in cursor.description]
    results = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    return jsonify(results)

@network_manager_bp.route("/add", methods=["POST"])
@require_admin
def add_device():
    data = request.json
    dev_cat = data.get("device_category")
    sub_cat = data.get("sub_category", "")
    dev_name = data.get("device_name", "")
    tower = data.get("tower", "")
    loc_code = data.get("location_code", "")
    proj_mahal = data.get("proje_mahali", "")
    isl_mahal = data.get("isletme_mahali", "")
    ip_addr = data.get("ip_address", "")
    sw_serial = data.get("sw_serial_numbers", "")
    mac_address = data.get("mac_address", "")
    warranty = data.get("warranty_info", "")
    
    if not dev_cat:
        return jsonify({"success": False, "error": "Kategori gerekli!"}), 400
        
    user_name = request.current_user.get("display_name") or request.current_user.get("username") or "Bilinmiyor"
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO network_devices 
        (device_category, sub_category, device_name, tower, location_code, proje_mahali, isletme_mahali, ip_address, sw_serial_numbers, mac_address, warranty_info, last_edit_user, last_edit_date) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE())
    """, (dev_cat, sub_cat, dev_name, tower, loc_code, proj_mahal, isl_mahal, ip_addr, sw_serial, mac_address, warranty, user_name))
    conn.commit()
    conn.close()
    
    return jsonify({"success": True})

@network_manager_bp.route("/update/<int:item_id>", methods=["PUT"])
@require_admin
def update_device(item_id):
    data = request.json
    dev_cat = data.get("device_category")
    sub_cat = data.get("sub_category", "")
    dev_name = data.get("device_name", "")
    tower = data.get("tower", "")
    loc_code = data.get("location_code", "")
    proj_mahal = data.get("proje_mahali", "")
    isl_mahal = data.get("isletme_mahali", "")
    ip_addr = data.get("ip_address", "")
    sw_serial = data.get("sw_serial_numbers", "")
    mac_address = data.get("mac_address", "")
    warranty = data.get("warranty_info", "")
    
    if not dev_cat:
        return jsonify({"success": False, "error": "Kategori gerekli!"}), 400
        
    user_name = request.current_user.get("display_name") or request.current_user.get("username") or "Bilinmiyor"
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE network_devices SET 
        device_category=?, sub_category=?, device_name=?, tower=?, location_code=?, proje_mahali=?, isletme_mahali=?, ip_address=?, sw_serial_numbers=?, mac_address=?, warranty_info=?,
        last_edit_user=?, last_edit_date=GETDATE()
        WHERE id=?
    """, (dev_cat, sub_cat, dev_name, tower, loc_code, proj_mahal, isl_mahal, ip_addr, sw_serial, mac_address, warranty, user_name, item_id))
    conn.commit()
    conn.close()
    
    return jsonify({"success": True})

@network_manager_bp.route("/delete/<int:item_id>", methods=["DELETE"])
@require_admin
def delete_device(item_id):
    user_name = request.current_user.get("display_name") or request.current_user.get("username") or "Bilinmiyor"
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE network_devices SET is_deleted=1, deleted_at=GETDATE(), last_edit_user=? WHERE id=?", (user_name, item_id))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

