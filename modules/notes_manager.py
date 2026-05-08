from flask import Blueprint, request, jsonify, send_from_directory
import os
from werkzeug.utils import secure_filename
from core.database_sql import get_db_connection, query_db
from core.auth import require_auth, require_admin

notes_manager_bp = Blueprint('notes_manager', __name__)

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads", "notes"))
BAT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "bat_uygulama"))

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)
if not os.path.exists(BAT_DIR):
    os.makedirs(BAT_DIR)

@notes_manager_bp.route('/get_counts', methods=['GET'])
@require_auth
def get_kb_counts():
    """Tüm cihazlar için not sayılarını ve son not başlığını döner."""
    try:
        counts = query_db('''
            SELECT target_id, COUNT(*) as count, 
            MAX(title) as last_title, MAX(content) as last_content
            FROM knowledge_base 
            WHERE type = 'pc'
            GROUP BY target_id
        ''')
        res = {str(c['target_id']): {"count": c['count'], "last_title": c['last_title'], "last_content": c['last_content']} for c in counts}
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@notes_manager_bp.route('/get_by_target/<type>/<int:target_id>', methods=['GET'])
@require_auth
def get_kb_by_target(type, target_id):
    """Belirli bir cihaz (pc/printer) için notları getirir."""
    try:
        notes = query_db("SELECT * FROM knowledge_base WHERE type=? AND target_id=? ORDER BY created_at DESC", (type, target_id))
        return jsonify([dict(n) for n in notes])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@notes_manager_bp.route('/add', methods=['POST'])
@notes_manager_bp.route('/kb/add', methods=['POST'])
@require_auth
def save_kb_entry():
    """Yeni bir bilgi bankası veya cihaz notu kaydeder."""
    try:
        if request.is_json:
            data = request.json
        else:
            data = request.form

        title = data.get('title', '')
        content = data.get('content', '')
        kb_type = data.get('device_type') or data.get('type') or 'kodlar'
        target_id = data.get('device_id') # Frontend device_id gönderiyor (Cihaz notları için)
        user_id = data.get('user_id', 'unknown')
        user_name = data.get('user_name', 'Bilinmiyor')
        requires_user = int(data.get('requires_user', 0))

        if not title:
            return jsonify({"error": "Başlık gerekli"}), 400
        if kb_type != 'indir' and not content:
            return jsonify({"error": "İçerik gerekli"}), 400

        # Resim yükleme
        image_filename = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                target_dir = BAT_DIR if kb_type == 'indir' else UPLOAD_DIR
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir)
                
                image_filename = secure_filename(f"{file.filename}") if kb_type == 'indir' else secure_filename(f"kb_{title[:10]}_{file.filename}")
                file.save(os.path.join(target_dir, image_filename))

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO knowledge_base (type, target_id, title, content, user_id, user_name, requires_user, image_path) VALUES (?,?,?,?,?,?,?,?)",
            (kb_type, target_id, title, content, user_id, user_name, requires_user, image_filename)
        )
        entry_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return jsonify({"message": "Kayıt başarıyla eklendi", "id": entry_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@notes_manager_bp.route('/kb/<kb_type>', methods=['GET'])
@require_auth
def get_knowledge_base(kb_type):
    """Kategoriye göre genel bilgi bankası öğelerini getirir."""
    try:
        notes = query_db("SELECT * FROM knowledge_base WHERE type=? ORDER BY created_at DESC", (kb_type,))
        return jsonify([dict(n) for n in notes])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@notes_manager_bp.route('/update/<int:id>', methods=['POST', 'PUT'])
@notes_manager_bp.route('/kb/update/<int:id>', methods=['POST', 'PUT'])
@require_auth
def update_kb_entry(id):
    """Bilgi bankası veya cihaz notu kaydeder."""
    try:
        if request.is_json:
            data = request.json
        else:
            data = request.form

        title = data.get('title')
        content = data.get('content')
        kb_type = data.get('type') or data.get('device_type')
        requires_user = data.get('requires_user')

        # Resim yükleme
        image_filename = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                target_dir = BAT_DIR if kb_type == 'indir' else UPLOAD_DIR
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir)
                image_filename = secure_filename(f"{file.filename}") if kb_type == 'indir' else secure_filename(f"kb_upd_{id}_{file.filename}")
                file.save(os.path.join(target_dir, image_filename))

        conn = get_db_connection()
        updates = []
        params = []
        if title:
            updates.append("title=?")
            params.append(title)
        if content is not None:
            updates.append("content=?")
            params.append(content)
        if kb_type:
            updates.append("type=?")
            params.append(kb_type)
        if requires_user is not None:
            updates.append("requires_user=?")
            params.append(int(requires_user))
        if image_filename:
            updates.append("image_path=?")
            params.append(image_filename)
        
        if not updates:
            return jsonify({"message": "Güncellenecek alan yok"})

        query = f"UPDATE knowledge_base SET {', '.join(updates)} WHERE id=?"
        params.append(id)
        
        conn.execute(query, params)
        conn.commit()
        conn.close()
        return jsonify({"message": "Kayıt güncellendi"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@notes_manager_bp.route('/delete/<int:id>', methods=['DELETE'])
@notes_manager_bp.route('/kb/delete/<int:id>', methods=['DELETE', 'GET']) # GET fallback for some UI actions
@require_admin
def delete_kb_entry(id):
    """Bilgi bankası kaydını siler (Sadece Admin)."""
    try:
        conn = get_db_connection()
        conn.execute("DELETE FROM knowledge_base WHERE id=?", (id,))
        conn.commit()
        conn.close()
        return jsonify({"message": "Kayıt silindi"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@notes_manager_bp.route('/search', methods=['GET'])
@require_auth
def search_kb():
    """Bilgi bankasında başlık veya içeriğe göre arama yapar."""
    query = request.args.get('q', '').upper()
    try:
        results = query_db("""
            SELECT * FROM knowledge_base 
            WHERE (UPPER(title) LIKE ? OR UPPER(content) LIKE ?)
            ORDER BY created_at DESC
        """, (f'%{query}%', f'%{query}%'))
        return jsonify([dict(r) for r in results])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@notes_manager_bp.route('/get_file/<path:filename>', methods=['GET'])
@require_auth
def get_kb_file(filename):
    """Yüklenen resimleri veya dosyaları servis eder."""
    return send_from_directory(UPLOAD_DIR, filename)
@notes_manager_bp.route('/kb/sync_from_excel', methods=['POST'])
@require_admin
def sync_kb_from_excel_route():
    """bilgi_bankası.xlsx dosyasındaki verileri knowledge_base tablosuna aktarır."""
    try:
        bilgi_path = os.path.join(os.path.dirname(__file__), "..", "database", "bilgi_bankası.xlsx")
        if not os.path.exists(bilgi_path):
            return jsonify({"error": "bilgi_bankası.xlsx bulunamadı"}), 404
            
        from core.excel_utils import read_excel_data
        conn = get_db_connection()
        
        # 1. Kodlar (Sekme 0)
        kodlar = read_excel_data(bilgi_path, sheet_name=0)
        if kodlar:
            for item in kodlar:
                title = (item.get('KONU BAŞLIĞI') or item.get('KONU BALII') or '-').strip()
                content = item.get('NOT') or '-'
                if not title or title == '-': continue
                
                exists = conn.execute("SELECT id FROM knowledge_base WHERE title=?", (title,)).fetchone()
                if exists:
                    conn.execute("UPDATE knowledge_base SET content=?, type='kodlar' WHERE id=?", (content, exists['id']))
                else:
                    conn.execute("INSERT INTO knowledge_base (type, title, content) VALUES (?,?,?)", ('kodlar', title, content))

        # 2. Kapanış Açıklamaları (Sekme 1)
        try:
            kapanis = read_excel_data(bilgi_path, sheet_name=1)
            if kapanis:
                for item in kapanis:
                    title = (item.get('BAŞLIK') or item.get('BALIK') or '-').strip()
                    content = item.get('KAPANIŞ AÇIKLAMASI') or item.get('KAPANI AIKLAMASI') or '-'
                    if not title or title == '-': continue
                    
                    exists = conn.execute("SELECT id FROM knowledge_base WHERE title=?", (title,)).fetchone()
                    if exists:
                        conn.execute("UPDATE knowledge_base SET content=?, type='kapanis' WHERE id=?", (content, exists['id']))
                    else:
                        conn.execute("INSERT INTO knowledge_base (type, title, content) VALUES (?,?,?)", ('kapanis', title, content))
        except Exception: pass

        # 3. Sorun Giderme (Sekme 2)
        try:
            sorun = read_excel_data(bilgi_path, sheet_name=2)
            if sorun:
                for item in sorun:
                    title = (item.get('BAŞLIK') or item.get('BALIK') or '-').strip()
                    content = (item.get('İÇERİK') or item.get('ICERIK') or item.get('NOT') or '-').strip()
                    if not title or title == '-': continue
                    
                    exists = conn.execute("SELECT id FROM knowledge_base WHERE title=?", (title,)).fetchone()
                    if exists:
                        conn.execute("UPDATE knowledge_base SET content=?, type='sorun-giderme' WHERE id=?", (content, exists['id']))
                    else:
                        conn.execute("INSERT INTO knowledge_base (type, title, content) VALUES (?,?,?)", ('sorun-giderme', title, content))
        except Exception: pass

        conn.commit()
        conn.close()
        return jsonify({"message": "Bilgi bankası Excel ile senkronize edildi."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
