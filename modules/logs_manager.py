from flask import Blueprint, jsonify, request
from core.database_sql import query_db, get_db_connection
from core.auth import require_auth, require_admin
import subprocess
import re
import platform

logs_manager_bp = Blueprint('logs_manager', __name__)

def get_mac_address(ip):
    """Verilen IP adresi için ARP tablosundan MAC adresini çözümler. Daha dirençli olması için önce ping atar."""
    if not ip or ip in ['127.0.0.1', '::1', '0.0.0.0']:
        try:
            import uuid
            return ':'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff) for i in range(0,8*6,8)][::-1]).upper()
        except:
            return None
            
    try:
        # Önce ping atarak ARP tablosuna düşmesini sağla (Sessizce)
        param = '-n' if platform.system().lower() == 'windows' else '-c'
        subprocess.run(['ping', param, '1', '-w', '200', ip], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Windows için arp -a [ip] komutu
        output = subprocess.check_output(["arp", "-a", ip], shell=True, stderr=subprocess.DEVNULL).decode('cp854', errors='ignore')
        
        # Regex ile MAC adresini bul
        match = re.search(r'([0-9a-fA-F]{2}[:-]){5}([0-9a-fA-F]{2})', output)
        if match:
            return match.group(0).replace('-', ':').upper()
    except Exception:
        pass
    return None


@logs_manager_bp.route('/get_all', methods=['GET'])
@require_auth
def get_logs():
    """Tüm değişiklik günlüğünü getirir. Opsiyonel filtreler: limit, user, table."""
    try:
        limit = request.args.get('limit', 200, type=int)
        user_filter = request.args.get('user', '')
        table_filter = request.args.get('table', '')

        query = "SELECT TOP " + str(min(limit, 1000)) + " * FROM audit_logs WHERE 1=1"
        params = []

        if user_filter:
            query += " AND changed_by = ?"
            params.append(user_filter)
        if table_filter:
            query += " AND table_name = ?"
            params.append(table_filter)

        query += " ORDER BY created_at DESC"

        conn = get_db_connection()
        rows = conn.execute(query, tuple(params)).fetchall()
        conn.close()

        result = []
        for r in rows:
            d = dict(r)
            # datetime serialization
            if d.get('created_at'):
                d['created_at'] = str(d['created_at'])
            result.append(d)

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@logs_manager_bp.route('/get_record_history/<table_name>/<int:record_id>', methods=['GET'])
@require_auth
def get_record_history(table_name, record_id):
    """Belirli bir kaydın (ürünün) tüm geçmişini (sınırsız) getirir."""
    try:
        query = "SELECT * FROM audit_logs WHERE table_name = ? AND record_id = ? ORDER BY created_at DESC"
        
        conn = get_db_connection()
        rows = conn.execute(query, (table_name, record_id)).fetchall()
        conn.close()

        result = []
        for r in rows:
            d = dict(r)
            if d.get('created_at'):
                d['created_at'] = str(d['created_at'])
            result.append(d)

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def log_change(conn, table_name, record_id, record_label, field_name, old_value, new_value, changed_by, display_name, client_ip=None, client_mac=None):
    """Bir değişikliği audit_logs tablosuna kaydeder."""
    old_str = str(old_value) if old_value is not None else ''
    new_str = str(new_value) if new_value is not None else ''

    # Eğer değer değişmediyse kaydetme
    if old_str.strip() == new_str.strip():
        return

    conn.execute('''INSERT INTO audit_logs 
        (table_name, record_id, record_label, field_name, old_value, new_value, changed_by, display_name, client_ip, client_mac)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (table_name, record_id, record_label, field_name, old_str, new_str, changed_by, display_name, client_ip, client_mac))


@logs_manager_bp.route('/clear_all', methods=['DELETE'])
@require_admin
def clear_all_logs():
    """Tüm işlem geçmişini (audit_logs) temizler."""
    try:
        conn = get_db_connection()
        result = conn.execute("DELETE FROM audit_logs")
        deleted = result.rowcount
        conn.commit()
        conn.close()
        return jsonify({"message": f"{deleted} adet kayıt silindi.", "deleted": deleted})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

