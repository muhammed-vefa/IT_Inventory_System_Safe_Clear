from flask import Blueprint, jsonify, request, send_from_directory, current_app
from core.database_sql import get_db_connection, query_db
from core.auth import require_auth, require_admin
import datetime
import os
import re
from werkzeug.utils import secure_filename

vpn_manager_bp = Blueprint("vpn_manager", __name__)

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads", "vpn_petitions")
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def ensure_vpn_schema(conn):
    try:
        cursor = conn.cursor()
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('vpn_users') AND name = 'sicil_no')
            BEGIN
                ALTER TABLE vpn_users ADD sicil_no NVARCHAR(50)
            END
            
            IF EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('vpn_users') AND name = 'username')
            BEGIN
                ALTER TABLE vpn_users ALTER COLUMN username NVARCHAR(255)
            END

            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name='mym_personnel')
            BEGIN
                CREATE TABLE mym_personnel (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    username NVARCHAR(255),
                    sicil_no NVARCHAR(50),
                    full_name NVARCHAR(255),
                    tc_no NVARCHAR(50),
                    phone NVARCHAR(100),
                    email NVARCHAR(255),
                    department NVARCHAR(255),
                    title NVARCHAR(255),
                    institution NVARCHAR(255),
                    work_status NVARCHAR(50) DEFAULT N'Çalışıyor',
                    created_at DATETIME DEFAULT GETDATE(),
                    last_edit_date DATETIME,
                    last_edit_user NVARCHAR(255),
                    is_deleted BIT DEFAULT 0,
                    archive_date DATETIME,
                    deleted_at DATETIME
                )
            END
        """)
        conn.commit()
    except Exception as e:
        print(f"[VPN SCHEMA MIGRATION WARNING] {e}")

@vpn_manager_bp.route("/get_all", methods=["GET"])
@require_auth
def get_all():
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify([]), 500
        ensure_vpn_schema(conn)
        cursor = conn.cursor()
        
        query = """
            SELECT id, username, full_name, tc_no, phone, email, department, 
                   title, institution, user_type, vpn_status, has_petition, 
                   petition_date, expiry_date, petition_file, work_status, 
                   is_risk_detected, sicil_no, notes, created_at, last_edit_date, last_edit_user
            FROM vpn_users 
            WHERE is_deleted = 0 OR is_deleted IS NULL
            ORDER BY 
                CASE WHEN sicil_no IS NULL OR sicil_no = '' THEN 1 ELSE 0 END,
                TRY_CAST(sicil_no AS INT) ASC,
                sicil_no ASC,
                full_name ASC
        """
        cursor.execute(query)
        columns = [column[0] for column in cursor.description]
        rows = cursor.fetchall()
        
        today = datetime.date.today()
        results = []
        
        for row in rows:
            item = dict(zip(columns, row))
            
            # Tarih dönüşümleri ve Kalan Gün Hesabı
            exp_date = item.get("expiry_date")
            pet_date = item.get("petition_date")
            
            if isinstance(exp_date, datetime.datetime):
                exp_date_obj = exp_date.date()
                item["expiry_date_str"] = exp_date.strftime("%d.%m.%Y")
            elif isinstance(exp_date, datetime.date):
                exp_date_obj = exp_date
                item["expiry_date_str"] = exp_date.strftime("%d.%m.%Y")
            else:
                exp_date_obj = None
                item["expiry_date_str"] = "-"
                
            if isinstance(pet_date, (datetime.datetime, datetime.date)):
                item["petition_date_str"] = pet_date.strftime("%d.%m.%Y")
            else:
                item["petition_date_str"] = "-"
                
            # Kalan gün ve durum rozeti
            if exp_date_obj:
                days_left = (exp_date_obj - today).days
                item["days_left"] = days_left
                
                # Yıllık döngü doluluk oranı (%100'den 0'a)
                total_cycle_days = 365
                percent = max(0, min(100, int((days_left / total_cycle_days) * 100)))
                item["percent_left"] = percent
            else:
                item["days_left"] = 999
                item["percent_left"] = 100
                days_left = 999
                
            # Hesaplanan durum
            is_kapatildi = (item.get("vpn_status") or "").strip().lower() in ["kapatıldı", "kapatildi", "kapalı", "kapali", "pasif"]
            w_status = (item.get("work_status") or "").lower()
            is_ayrildi = "ayrıl" in w_status or "ayril" in w_status

            if is_kapatildi:
                item["calculated_status"] = "KAPATILDI"
                item["status_label"] = "AYRILDI (KAPALI)" if is_ayrildi else "VPN KAPATILDI"
                item["status_badge_class"] = "secondary"
            elif is_ayrildi or item.get("is_risk_detected") == 1:
                item["calculated_status"] = "AYRILDI"
                item["status_label"] = "İŞTEN AYRILDI"
                item["status_badge_class"] = "danger-blink"
            elif days_left < 0:
                item["calculated_status"] = "SURESI_BITTI"
                item["status_label"] = f"SÜRESİ DOLDU ({abs(days_left)} gün önce)"
                item["status_badge_class"] = "danger"
            elif days_left <= 30:
                item["calculated_status"] = "SURESI_YAKLASTI"
                item["status_label"] = f"SON {days_left} GÜN"
                item["status_badge_class"] = "warning"
            else:
                item["calculated_status"] = "GUNCEL"
                item["status_label"] = f"GÜNCEL ({days_left} GÜN)"
                item["status_badge_class"] = "success"
                
            results.append(item)
            
        conn.close()
        return jsonify(results)
    except Exception as e:
        print(f"[VPN API ERROR] get_all: {e}")
        return jsonify({"error": str(e)}), 500

@vpn_manager_bp.route("/extend/<int:item_id>", methods=["POST"])
@require_admin
def extend_validity(item_id):
    try:
        user_name = request.current_user.get("display_name") or request.current_user.get("username") or "Bilinmiyor"
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Mevcut bitiş tarihini al
        cursor.execute("SELECT expiry_date FROM vpn_users WHERE id = ? AND (is_deleted = 0 OR is_deleted IS NULL)", (item_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({"success": False, "error": "Kullanıcı bulunamadı"}), 404
            
        current_exp = row[0]
        today = datetime.datetime.now()
        
        if current_exp and current_exp > today:
            new_exp = current_exp + datetime.timedelta(days=365)
        else:
            new_exp = today + datetime.timedelta(days=365)
            
        cursor.execute("""
            UPDATE vpn_users 
            SET expiry_date = ?, 
                petition_date = GETDATE(),
                has_petition = 'VAR',
                vpn_status = 'Aktif',
                last_edit_user = ?, 
                last_edit_date = GETDATE()
            WHERE id = ?
        """, (new_exp, user_name, item_id))
        
        conn.commit()
        conn.close()
        return jsonify({"success": True, "new_expiry_date": new_exp.strftime("%d.%m.%Y")})
    except Exception as e:
        print(f"[VPN API ERROR] extend: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@vpn_manager_bp.route("/update/<int:item_id>", methods=["POST", "PUT"])
@require_admin
def update_vpn_user(item_id):
    try:
        data = request.json or {}
        user_name = request.current_user.get("display_name") or request.current_user.get("username") or "Bilinmiyor"
        
        phone = data.get("phone")
        notes = data.get("notes")
        vpn_status = data.get("vpn_status")
        department = data.get("department")
        title = data.get("title")
        user_type = data.get("user_type")
        has_petition = data.get("has_petition")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE vpn_users 
            SET phone = COALESCE(?, phone),
                notes = COALESCE(?, notes),
                vpn_status = COALESCE(?, vpn_status),
                department = COALESCE(?, department),
                title = COALESCE(?, title),
                user_type = COALESCE(?, user_type),
                has_petition = COALESCE(?, has_petition),
                last_edit_user = ?,
                last_edit_date = GETDATE()
            WHERE id = ?
        """, (phone, notes, vpn_status, department, title, user_type, has_petition, user_name, item_id))
        
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        print(f"[VPN API ERROR] update: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@vpn_manager_bp.route("/close_vpn/<int:item_id>", methods=["POST"])
@require_admin
def close_vpn(item_id):
    try:
        user_name = request.current_user.get("display_name") or request.current_user.get("username") or "Bilinmiyor"
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE vpn_users 
            SET vpn_status = 'Kapatıldı',
                is_risk_detected = 0,
                last_edit_user = ?,
                last_edit_date = GETDATE()
            WHERE id = ?
        """, (user_name, item_id))
        
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        print(f"[VPN API ERROR] close_vpn: {e}")
        return jsonify({"success": False, "error": str(e)}), 500



@vpn_manager_bp.route("/activate_vpn/<int:item_id>", methods=["POST"])
@require_admin
def activate_vpn(item_id):
    try:
        user_name = request.current_user.get("display_name") or request.current_user.get("username") or "Bilinmiyor"
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE vpn_users 
            SET vpn_status = 'Aktif',
                last_edit_user = ?,
                last_edit_date = GETDATE()
            WHERE id = ?
        """, (user_name, item_id))
        
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        print(f"[VPN API ERROR] activate_vpn: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@vpn_manager_bp.route("/upload_petition/<int:item_id>", methods=["POST"])
@require_admin
def upload_petition(item_id):
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "Lütfen bir dilekçe belgesi seçin!"}), 400
            
        file = request.files['file']
        if file.filename == '' or not allowed_file(file.filename):
            return jsonify({"success": False, "error": "Geçersiz dosya türü (PDF, PNG, JPG olmalı)"}), 400
            
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            
        ext = file.filename.rsplit('.', 1)[1].lower()
        safe_name = f"dilekce_{item_id}_{int(datetime.datetime.now().timestamp())}.{ext}"
        save_path = os.path.join(UPLOAD_FOLDER, safe_name)
        file.save(save_path)
        
        extend_year = request.form.get("extend_one_year") == "1"
        user_name = request.current_user.get("display_name") or request.current_user.get("username") or "Bilinmiyor"
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        new_exp_str = None
        if extend_year:
            cursor.execute("SELECT expiry_date FROM vpn_users WHERE id = ?", (item_id,))
            r = cursor.fetchone()
            current_exp = r[0] if r else None
            today = datetime.datetime.now()
            if current_exp and current_exp > today:
                new_exp = current_exp + datetime.timedelta(days=365)
            else:
                new_exp = today + datetime.timedelta(days=365)
            new_exp_str = new_exp.strftime("%d.%m.%Y")
            
            cursor.execute("""
                UPDATE vpn_users 
                SET petition_file = ?,
                    has_petition = 'VAR',
                    petition_date = GETDATE(),
                    expiry_date = ?,
                    vpn_status = 'Aktif',
                    last_edit_user = ?,
                    last_edit_date = GETDATE()
                WHERE id = ?
            """, (safe_name, new_exp, user_name, item_id))
        else:
            cursor.execute("""
                UPDATE vpn_users 
                SET petition_file = ?,
                    has_petition = 'VAR',
                    last_edit_user = ?,
                    last_edit_date = GETDATE()
                WHERE id = ?
            """, (safe_name, user_name, item_id))
            
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True, 
            "filename": safe_name, 
            "extended": extend_year,
            "new_expiry_date": new_exp_str
        })
    except Exception as e:
        print(f"[VPN API ERROR] upload_petition: {e}")
        return jsonify({"success": False, "error": str(e)}), 500



@vpn_manager_bp.route("/search_personnel", methods=["GET"])
@require_auth
def search_personnel():
    """MYM personel havuzundan TC veya Sicil No ile arama yapar."""
    try:
        q = (request.args.get("q") or "").strip()
        if not q or len(q) < 3:
            return jsonify({"results": [], "error": "En az 3 karakter girin"}), 200
        
        conn = get_db_connection()
        if not conn:
            return jsonify({"results": [], "error": "DB bağlantı hatası"}), 500
        cursor = conn.cursor()
        
        # Önce mym_personnel tablosunda ara (TC, Sicil No, Ad Soyad, Username)
        cursor.execute("""
            SELECT TOP 10 id, username, sicil_no, full_name, tc_no, phone, email, 
                   department, title, institution, work_status
            FROM mym_personnel
            WHERE (is_deleted = 0 OR is_deleted IS NULL)
              AND (
                  tc_no LIKE ? OR
                  sicil_no LIKE ? OR
                  full_name LIKE ? OR
                  username LIKE ?
              )
            ORDER BY full_name ASC
        """, (f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%"))
        
        columns = [col[0] for col in cursor.description]
        results = []
        for row in cursor.fetchall():
            item = dict(zip(columns, row))
            # Bu kişi zaten VPN listesinde mi?
            cursor.execute(
                "SELECT id FROM vpn_users WHERE username = ? AND (is_deleted = 0 OR is_deleted IS NULL)",
                (item["username"],)
            )
            item["already_vpn"] = cursor.fetchone() is not None
            results.append(item)
        
        conn.close()
        return jsonify({"results": results})
    except Exception as e:
        print(f"[VPN API ERROR] search_personnel: {e}")
        return jsonify({"results": [], "error": str(e)}), 500


@vpn_manager_bp.route("/add_new", methods=["POST"])
@require_admin
def add_new_vpn_user():
    """MYM personelinden seçilen kişiyi VPN kullanıcısı olarak ekler."""
    try:
        data = request.json or {}
        username = (data.get("username") or "").strip()
        if not username:
            return jsonify({"success": False, "error": "Kullanıcı adı gerekli!"}), 400
        
        user_name = request.current_user.get("display_name") or request.current_user.get("username") or "Bilinmiyor"
        
        conn = get_db_connection()
        if not conn:
            return jsonify({"success": False, "error": "DB bağlantı hatası"}), 500
        cursor = conn.cursor()
        
        # Zaten VPN listesinde mi kontrol et
        cursor.execute(
            "SELECT id FROM vpn_users WHERE username = ? AND (is_deleted = 0 OR is_deleted IS NULL)",
            (username,)
        )
        if cursor.fetchone():
            conn.close()
            return jsonify({"success": False, "error": "Bu kullanıcı zaten VPN listesinde!"}), 409
        
        # MYM personel bilgilerini çek
        cursor.execute("""
            SELECT username, sicil_no, full_name, tc_no, phone, email,
                   department, title, institution, work_status
            FROM mym_personnel
            WHERE username = ? AND (is_deleted = 0 OR is_deleted IS NULL)
        """, (username,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return jsonify({"success": False, "error": "MYM personel havuzunda bulunamadı!"}), 404
        
        cols = [c[0] for c in cursor.description]
        person = dict(zip(cols, row))
        
        today = datetime.datetime.now()
        expiry = today + datetime.timedelta(days=365)
        
        # Kullanıcı tipi belirle
        combined = f"{person.get('title', '')} {person.get('department', '')}".lower()
        if any(x in combined for x in ['tabip', 'hekim', 'asistan', 'uzman doktor', 'doçent', 'prof']):
            user_type = 'HEKİM'
        elif any(x in combined for x in ['şirket', 'iss', 'firma', 'teknik', 'destek']):
            user_type = 'DIŞ DESTEK'
        else:
            user_type = 'İDARİ'
        
        cursor.execute("""
            INSERT INTO vpn_users (
                username, full_name, tc_no, phone, email,
                department, title, institution, user_type,
                vpn_status, has_petition, petition_date, expiry_date,
                work_status, is_risk_detected, sicil_no,
                created_at, last_edit_user, is_deleted
            ) VALUES (
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?,
                'Aktif', 'YOK', GETDATE(), ?,
                ?, 0, ?,
                GETDATE(), ?, 0
            )
        """, (
            person['username'], person['full_name'], person.get('tc_no', ''),
            person.get('phone', ''), person.get('email', ''),
            person.get('department', ''), person.get('title', ''),
            person.get('institution', 'KOCAELİ ENTEGRE SAĞLIK KAMPÜSÜ'), user_type,
            expiry,
            person.get('work_status', 'Çalışıyor'), person.get('sicil_no', ''),
            user_name
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True, 
            "message": f"{person['full_name']} VPN listesine eklendi!",
            "expiry_date": expiry.strftime("%d.%m.%Y")
        })
    except Exception as e:
        print(f"[VPN API ERROR] add_new: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@vpn_manager_bp.route("/petition/<filename>", methods=["GET"])
@require_auth
def get_petition_file(filename):
    safe_name = secure_filename(filename)
    return send_from_directory(UPLOAD_FOLDER, safe_name)
