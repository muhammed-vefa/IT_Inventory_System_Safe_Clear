import os
from flask import Blueprint, jsonify, request
from core.database_sql import query_db, get_db_connection
from core.auth import require_auth, require_editor, require_admin
from werkzeug.utils import secure_filename

notes_manager_bp = Blueprint('notes_manager', __name__)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads", "notes")


@notes_manager_bp.route('/counts/<device_type>', methods=['GET'])
@require_auth
def get_note_counts(device_type):
    """Her cihaz için not sayılarını ve son notu getirir."""
    try:
        # get counts and the most recent note for each device
        query = '''
            SELECT device_id, COUNT(*) as count, 
                   (SELECT TOP 1 title FROM technical_notes tn2 WHERE tn2.device_id = tn1.device_id ORDER BY created_at DESC) as last_title,
                   (SELECT TOP 1 content FROM technical_notes tn2 WHERE tn2.device_id = tn1.device_id ORDER BY created_at DESC) as last_content
            FROM technical_notes tn1
            WHERE device_type = ?
            GROUP BY device_id
        '''
        results = query_db(query, (device_type,))
        
        counts = {}
        for row in results:
            counts[str(row['device_id'])] = {
                'count': row['count'],
                'last_title': row['last_title'],
                'last_content': row['last_content']
            }
        return jsonify(counts)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@notes_manager_bp.route('/get/<device_type>/<int:device_id>', methods=['GET'])
def get_notes(device_type, device_id):
    """Belirli bir cihaza ait tüm teknik notları ve görsellerini getirir."""
    try:
        notes = query_db(
            "SELECT * FROM technical_notes WHERE device_id=? AND device_type=? ORDER BY created_at DESC",
            (device_id, device_type)
        )
        result = []
        for note in notes:
            n = dict(note)
            images = query_db("SELECT * FROM note_images WHERE note_id=?", (n['id'],))
            n['images'] = [dict(img) for img in images]
            result.append(n)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@notes_manager_bp.route('/add', methods=['POST'])
@require_auth
def add_note():
    """Yeni teknik not ekler (opsiyonel görsel ile)."""
    try:
        device_id = request.form.get('device_id')
        device_type = request.form.get('device_type', 'pc')
        title = request.form.get('title', '')
        content = request.form.get('content', '')
        user_id = request.form.get('user_id', 'unknown')
        user_name = request.form.get('user_name', 'Bilinmiyor')

        if not device_id:
            return jsonify({"error": "device_id gerekli"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO technical_notes (device_id, device_type, title, content, user_id, user_name) VALUES (?,?,?,?,?,?)",
            (device_id, device_type, title, content, user_id, user_name)
        )
        note_id = cursor.lastrowid

        # Görsel yükleme
        if 'image' in request.files:
            file = request.files['image']
            if file.filename:
                device_dir = os.path.join(UPLOAD_DIR, f"{device_type}_{device_id}")
                os.makedirs(device_dir, exist_ok=True)
                filename = secure_filename(f"{note_id}_{file.filename}")
                filepath = os.path.join(device_dir, filename)
                file.save(filepath)
                cursor.execute(
                    "INSERT INTO note_images (note_id, filename) VALUES (?,?)",
                    (note_id, f"{device_type}_{device_id}/{filename}")
                )

        conn.commit()
        conn.close()
        return jsonify({"message": "Not başarıyla eklendi", "id": note_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@notes_manager_bp.route('/delete/<int:note_id>', methods=['DELETE'])
@require_auth
def delete_note(note_id):
    """Notu siler (sadece not sahibi veya Admin)."""
    try:
        user_id = request.args.get('user_id', '')
        user_role = request.args.get('role', '')

        note = query_db("SELECT * FROM technical_notes WHERE id=?", (note_id,), one=True)
        if not note:
            return jsonify({"error": "Not bulunamadı"}), 404

        note_data = dict(note)
        # Sahipsiz notları ("sadece admin" kuralı) veya sahibi olmayanı kontrol et
        can_delete = False
        if user_role == 'ADMIN':
            can_delete = True
        elif note_data['user_id'] and note_data['user_id'] == user_id:
            can_delete = True
        
        if not can_delete:
            return jsonify({"error": "Bu notu silme yetkiniz yok (Sadece Admin veya Ekleyen)"}), 403

        # İlişkili görselleri sil
        images = query_db("SELECT * FROM note_images WHERE note_id=?", (note_id,))
        for img in images:
            img_path = os.path.join(UPLOAD_DIR, dict(img)['filename'])
            if os.path.exists(img_path):
                os.remove(img_path)

        conn = get_db_connection()
        conn.execute("DELETE FROM note_images WHERE note_id=?", (note_id,))
        conn.execute("DELETE FROM technical_notes WHERE id=?", (note_id,))
        conn.commit()
        conn.close()
        return jsonify({"message": "Not silindi"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@notes_manager_bp.route('/update/<int:note_id>', methods=['PUT'])
def update_note(note_id):
    """Notu günceller (sadece not sahibi veya Admin)."""
    try:
        data = request.json
        user_id = data.get('user_id', '')
        user_role = data.get('role', '')
        title = data.get('title', '')
        content = data.get('content', '')

        note = query_db("SELECT * FROM technical_notes WHERE id=?", (note_id,), one=True)
        if not note:
            return jsonify({"error": "Not bulunamadı"}), 404

        note_data = dict(note)
        can_edit = False
        if user_role == 'ADMIN':
            can_edit = True
        elif note_data['user_id'] and note_data['user_id'] == user_id:
            can_edit = True
            
        if not can_edit:
            return jsonify({"error": "Bu notu düzenleme yetkiniz yok"}), 403

        conn = get_db_connection()
        conn.execute(
            "UPDATE technical_notes SET title=?, content=? WHERE id=?",
            (title, content, note_id)
        )
        conn.commit()
        conn.close()
        return jsonify({"message": "Not güncellendi"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@notes_manager_bp.route('/kb/add', methods=['POST'])
@require_auth
def add_kb_entry():
    """Bilgi bankasına yeni kayıt ekler."""
    try:
        # FormData veya JSON desteği
        if request.is_json:
            data = request.json
        else:
            data = request.form

        title = data.get('title', '')
        content = data.get('content', '')
        kb_type = data.get('device_type', 'kodlar') # Varsayılan kodlar
        user_id = data.get('user_id', 'unknown')
        user_name = data.get('user_name', 'Bilinmiyor')
        requires_user = int(data.get('requires_user', 0))

        if not title or not content:
            return jsonify({"error": "Başlık ve içerik gerekli"}), 400

        # Resim yükleme
        image_filename = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                # Klasör yoksa oluştur
                if not os.path.exists(UPLOAD_DIR):
                    os.makedirs(UPLOAD_DIR)
                
                image_filename = secure_filename(f"kb_{title[:10]}_{file.filename}")
                file.save(os.path.join(UPLOAD_DIR, image_filename))

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO knowledge_base (type, title, content, user_id, user_name, requires_user, image_path) VALUES (?,?,?,?,?,?,?)",
            (kb_type, title, content, user_id, user_name, requires_user, image_filename)
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
    """Bilgi bankası verilerini getirir (kodlar veya kapanis)."""
    try:
        results = query_db("SELECT * FROM knowledge_base WHERE type=? ORDER BY title ASC", (kb_type,))
        return jsonify([dict(row) for row in results])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@notes_manager_bp.route('/kb/update/<int:id>', methods=['PUT', 'POST']) # POST multipart form için
def update_kb_entry(id):
    """Bilgi bankası kaydını günceller (Sadece Admin)."""
    try:
        user_role = request.form.get('role') if 'role' in request.form else request.json.get('role') if request.is_json else None
        
        if user_role != 'ADMIN':
            return jsonify({"error": "Sadece Admin düzenleme yapabilir"}), 403

        if request.is_json:
            data = request.json
        else:
            data = request.form

        title = data.get('title')
        content = data.get('content')
        kb_type = data.get('type') # Kategori değişimi
        requires_user = int(data.get('requires_user', 0))

        # Resim yükleme
        image_filename = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                if not os.path.exists(UPLOAD_DIR):
                    os.makedirs(UPLOAD_DIR)
                image_filename = secure_filename(f"kb_upd_{id}_{file.filename}")
                file.save(os.path.join(UPLOAD_DIR, image_filename))

        conn = get_db_connection()
        if image_filename:
            conn.execute(
                "UPDATE knowledge_base SET title=?, content=?, type=?, requires_user=?, image_path=? WHERE id=?",
                (title, content, kb_type, requires_user, image_filename, id)
            )
        else:
            conn.execute(
                "UPDATE knowledge_base SET title=?, content=?, type=?, requires_user=? WHERE id=?",
                (title, content, kb_type, requires_user, id)
            )
        conn.commit()
        conn.close()
        return jsonify({"message": "Kayıt güncellendi"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@notes_manager_bp.route('/kb/delete/<int:id>', methods=['DELETE'])
@require_admin
def delete_kb_entry(id):
    """Bilgi bankası kaydını siler (Sadece sahibi veya Admin)."""
    try:
        user_id = request.args.get('user_id')
        user_role = request.args.get('role')

        entry = query_db("SELECT * FROM knowledge_base WHERE id=?", (id,), one=True)
        if not entry: return jsonify({"error": "Kayıt bulunamadı"}), 404

        if user_role != 'ADMIN':
            return jsonify({"error": "Sadece Admin silebilir"}), 403

        conn = get_db_connection()
        conn.execute("DELETE FROM knowledge_base WHERE id=?", (id,))
        conn.commit()
        conn.close()
        return jsonify({"message": "Kayıt silindi"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@notes_manager_bp.route('/kb/sync_from_excel', methods=['POST'])
def sync_kb_from_excel():
    """bilgi_bankasi.xlsx dosyasındaki verileri Bilgi Bankası'na senkronize eder."""
    import os
    import openpyxl
    from core.excel_utils import read_excel_data
    try:
        excel_path = os.path.join(BASE_DIR, "database", "bilgi_bankasi.xlsx")
        if not os.path.exists(excel_path):
            return jsonify({"error": "bilgi_bankasi.xlsx bulunamadı."}), 404

        conn = get_db_connection()
        wb = openpyxl.load_workbook(excel_path, data_only=True)
        
        # Sheet -> KB Type mapping
        sheet_mapping = {
            'kodlar': 'kodlar',
            'kapanis_açıklaması': 'kapanis',
            'sorun giderme notları': 'bilgiler'
        }

        added = 0
        updated = 0

        for sheet_name, kb_type in sheet_mapping.items():
            if sheet_name not in wb.sheetnames:
                continue
            
            data = read_excel_data(excel_path, sheet_name=sheet_name)
            if not data: continue

            for item in data:
                # Başlık ve İçerik kolonlarını esnek ara
                title = str(item.get('KONU BAŞLIĞI') or item.get('BASLIK') or item.get('KOMUT') or '').strip()
                content = str(item.get('NOT') or item.get('ACIKLAMA') or item.get('ICERIK') or '').strip()

                if not title or not content:
                    continue

                # Mevcut kaydı kontrol et (Başlığa göre)
                exists = conn.execute(
                    "SELECT id FROM knowledge_base WHERE title=? AND type=?", 
                    (title, kb_type)
                ).fetchone()

                if exists:
                    conn.execute(
                        "UPDATE knowledge_base SET content=? WHERE id=?",
                        (content, exists['id'])
                    )
                    updated += 1
                else:
                    conn.execute(
                        "INSERT INTO knowledge_base (type, title, content, user_name) VALUES (?,?,?,?)",
                        (kb_type, title, content, 'EXCEL_SYNC')
                    )
                    added += 1

        conn.commit()
        conn.close()
        return jsonify({"message": f"Bilgi Bankası senkronize edildi: {added} yeni, {updated} güncellendi."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
