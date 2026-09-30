from core.utils import normalize_row
from flask import Blueprint, jsonify, request
from core.database_sql import get_db_connection
import socket
from functools import wraps

from core.auth import require_auth, require_admin

logs_manager_bp = Blueprint('logs_manager', __name__)



def log_change(table_name, record_id, record_label, field_name, old_value, new_value, changed_by, display_name="", client_ip="", client_mac=""):
    """Sistemdeki her türlü değişikliği audit_logs tablosuna kaydeder."""
    # Eğer IP adresi verilmemişse Flask request context'inden çekmeyi dene
    if not client_ip:
        try:
            from flask import request
            client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            if client_ip and ',' in client_ip:
                client_ip = client_ip.split(',')[0].strip()
        except Exception as e:
            print(f"[Log Change Context IP Fetch Error] {e}")
    if not client_ip:
        client_ip = "-"

    conn = get_db_connection()
    if not conn: return

    # Değerleri stringe çevir (NVARCHAR saklamak için)
    old_str = str(old_value) if old_value is not None else "-"
    new_str = str(new_value) if new_value is not None else "-"

    # Eğer değer değişmediyse kaydetme
    if old_str.strip() == new_str.strip():
        return

    try:
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO audit_logs 
            (table_name, record_id, record_label, field_name, old_value, new_value, changed_by, display_name, client_ip, client_mac)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (table_name, record_id, record_label, field_name, old_str, new_str, changed_by, display_name, client_ip, client_mac))
        conn.commit()
    except Exception as e:
        print(f"Log Kayıt Hatası: {e}")
    finally:
        conn.close()

def log_activity(user_id, action, details=""):
    """Kullanıcı aktivitelerini (login, deploy, archive vb.) kaydeder."""
    conn = get_db_connection()
    if not conn: return
    try:
        cursor = conn.cursor()
        # client_ip ve user_agent'i request context'inden çekmeye çalış
        client_ip = "-"
        user_agent = "-"
        username = "-"
        try:
            from flask import request
            client_ip = request.remote_addr
            user_agent = request.headers.get('User-Agent', '-')
            if hasattr(request, 'current_user'):
                username = request.current_user.get('username', '-')
        except Exception as e:
            print(f"[User Activity Log Context Error] {e}")

        cursor.execute('''INSERT INTO user_activity_log 
            (user_id, username, action, details, client_ip, user_agent)
            VALUES (?, ?, ?, ?, ?, ?)''',
            (user_id, username, action, details, client_ip, user_agent))
        conn.commit()
    except Exception as e:
        print(f"Aktivite Log Hatası: {e}")
    finally:
        conn.close()

@logs_manager_bp.route('/get_all', methods=['GET'])
@require_auth
def get_all_logs():
    """Tüm işlem geçmişini kronolojik olarak getirir."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC")
        columns = [column[0] for column in cursor.description]
        results = []
        for row in cursor.fetchall():
            results.append(normalize_row(dict(zip(columns, row))))
        conn.close()
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@logs_manager_bp.route('/clear_all', methods=['DELETE'])
@require_admin
def clear_all_logs():
    """Tüm işlem geçmişini (audit_logs) temizler."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM audit_logs")
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        return jsonify({"message": f"{deleted} adet kayıt silindi.", "deleted": deleted})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@logs_manager_bp.route('/get_record_history/<table_name>/<int:record_id>', methods=['GET'])
@require_auth
def get_record_history(table_name, record_id):
    """Belirli bir kayit icin gecmis duzenlemeleri getirir."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM audit_logs WHERE table_name = ? AND record_id = ? ORDER BY timestamp DESC", (table_name, record_id))
        columns = [column[0] for column in cursor.description]
        results = []
        for row in cursor.fetchall():
            results.append(normalize_row(dict(zip(columns, row))))
        conn.close()
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
