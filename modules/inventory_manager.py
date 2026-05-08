from flask import Blueprint, jsonify, request
from core.database_sql import query_db, get_db_connection
from core.excel_utils import write_excel_data
from modules.logs_manager import log_change, get_mac_address
from core.auth import require_auth, require_editor, require_admin
import os

inventory_manager_bp = Blueprint('inventory_manager', __name__)

ENV_EXCEL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "database", "envanter.xlsx"))

FIELD_LABELS = {
    'kule': 'Kule', 'kat': 'Kat', 'mahal_kodu': 'Mahal Kodu', 'mahal_adi': 'Mahal Adı',
    'telefon': 'Telefon', 'ip': 'IP Adresi', 'aciklama': 'Açıklama',
    'sahada': 'Sahada', 'depo': 'Depoda', 'arizali': 'Arızalı', 'mahalsiz': 'Kayıp',
    'windows': 'Windows', 'keyos': 'KeyOS', 'pc_seri': 'PC Seri No', 
    'monitor_seri': 'Monitör Seri No', 'monitor_model': 'Monitör Model',
    'monitor2_seri': '2. Monitör Seri No', 'monitor2_model': '2. Monitör Model',
    'bagli_yazicilar': 'Bağlı Yazıcılar', 'by_seri': 'Barkod Yazıcı Seri',
    'bo_seri': 'Barkod Okuyucu Seri', 'tarayici_seri': 'Tarayıcı Seri No',
    'assigned_to': 'Zimmetlenen Kişi', 'phone': 'Cep Telefon', 'title': 'Unvan', 'unit': 'Birim'
}

@inventory_manager_bp.route('/get_all', methods=['GET'])
@require_auth
def get_inventory():
    try:
        items = query_db("SELECT * FROM inventory")
        return jsonify([dict(row) for row in items])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@inventory_manager_bp.route('/update', methods=['POST'])
@require_editor
def update_inventory():
    """Günceller, değişiklikleri loglar, çevre birimlerini yazıcılara aktarır, Excel'e yazar."""
    data = request.json
    id = data.get('id')
    changed_by = data.get('changed_by', 'system')
    display_name = data.get('display_name', 'Sistem')
    
    if not id: return jsonify({"error": "ID missing"}), 400
    
    try:
        conn = get_db_connection()

        # 1. Mevcut kaydı al (log karşılaştırması için)
        old_record = conn.execute("SELECT * FROM inventory WHERE id=?", (id,)).fetchone()
        if not old_record:
            conn.close()
            return jsonify({"error": "Kayıt bulunamadı"}), 404

        pc_label = f"PC-{old_record['pc_no'] or id}"

        # 2. Güncelleme yap
        conn.execute('''UPDATE inventory SET 
            kule=?, kat=?, mahal_kodu=?, mahal_adi=?, telefon=?, ip=?, 
            aciklama=?, sahada=?, depo=?, arizali=?, mahalsiz=?, windows=?, keyos=?,
            pc_seri=?, monitor_seri=?, monitor_model=?, monitor2_seri=?, monitor2_model=?, bagli_yazicilar=?, 
            by_seri=?, bo_seri=?, tarayici_seri=?, assigned_to=?, phone=?, title=?, unit=?
            WHERE id=?''', (
            data.get('kule'), data.get('kat'), data.get('mahal_kodu'), data.get('mahal_adi'),
            data.get('telefon'), data.get('ip'), data.get('aciklama'), 
            data.get('sahada'), data.get('depo'), data.get('arizali'), data.get('mahalsiz'),
            data.get('windows'), data.get('keyos'),
            data.get('pc_seri'), data.get('monitor_seri'), data.get('monitor_model'),
            data.get('monitor2_seri'), data.get('monitor2_model'),
            data.get('bagli_yazicilar'), data.get('by_seri'), data.get('bo_seri'), 
            data.get('tarayici_seri'), data.get('assigned_to'), data.get('phone'),
            data.get('title'), data.get('unit'), id
        ))

        # 2.5 Hostname Güncelleme (Eski ve Yeni Mahal için)
        new_mahal = data.get('mahal_kodu')
        new_hostname = data.get('hostname')
        old_mahal = old_record['mahal_kodu']
        old_hostname = old_record['hostname']
        
        _sync_hostnames(conn, new_mahal)
        if old_mahal and old_mahal != new_mahal:
            _sync_hostnames(conn, old_mahal)

        # 2.6 KeyOS Otomatik Güncelleme
        # Eğer mahal veya hostname değiştiyse ve kullanıcının KeyOS şifresi varsa KeyOS'u güncelle
        if (new_mahal != old_mahal or new_hostname != old_hostname):
            try:
                user_id = request.current_user.get('user_id')
                user_info = conn.execute("SELECT keyos_user, keyos_pass FROM users WHERE id=?", (user_id,)).fetchone()
                if user_info and user_info['keyos_user'] and user_info['keyos_pass']:
                    from modules.keyos_service import update_device_internal
                    # KeyOS'ta mahaller tireli tutulduğu için çeviriyoruz
                    keyos_mahal = (new_mahal or '').replace('.', '-').upper()
                    serial = old_record['pc_seri']
                    if serial:
                        success, error = update_device_internal(
                            serial, new_hostname, keyos_mahal, 
                            user_info['keyos_user'], user_info['keyos_pass']
                        )
                        if not success:
                            # Admin uyarısı oluştur (Gelecekte bildirim tablosuna yazılabilir)
                            print(f"KeyOS Otomatik Güncelleme Başarısız: {error}")
                            # Değişiklik loguna özel not düş
                            log_change(id, pc_label, "KeyOS Durumu", "Başarısız", f"Kullanıcı değişiklik yaptı ancak KeyOS güncellenemedi: {error}", changed_by, display_name)
                else:
                    log_change(id, pc_label, "KeyOS Durumu", "Atlandı", "KeyOS şifresi kayıtlı olmadığı için sadece envanter güncellendi.", changed_by, display_name)
            except Exception as e:
                print(f"KeyOS Sync Error in update_inventory: {e}")

        # 3. Değişiklikleri logla
        tracked_fields = ['kule', 'kat', 'mahal_kodu', 'mahal_adi', 'telefon', 'ip', 
                         'aciklama', 'sahada', 'depo', 'arizali', 'mahalsiz', 'windows', 'keyos',
                         'pc_seri', 'monitor_seri', 'monitor_model', 'monitor2_seri', 'monitor2_model',
                         'bagli_yazicilar', 'by_seri', 'bo_seri', 'tarayici_seri', 'assigned_to', 'phone', 'title', 'unit']
        for field in tracked_fields:
            old_val = old_record.get(field, '')
            new_val = data.get(field, '')
            # checkbox alanlarını normalize et
            old_str = str(old_val) if old_val else '0'
            new_str = str(new_val) if new_val else '0'
            # '1' / 'True' / 'VAR' gibi durumları '1' yap
            if old_str.upper() in ('TRUE', 'VAR', 'EVET'): old_str = '1'
            if new_str.upper() in ('TRUE', 'VAR', 'EVET'): new_str = '1'
            if old_str in ('None', ''): old_str = '0'
            if new_str in ('None', ''): new_str = '0'
            
            label = FIELD_LABELS.get(field, field)
            # IP ve MAC bilgisini loglamaya dahil et
            client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            if ',' in client_ip: client_ip = client_ip.split(',')[0]
            client_mac = get_mac_address(client_ip)
            
            log_change(conn, 'inventory', id, pc_label, label, old_str, new_str, changed_by, display_name, client_ip=client_ip, client_mac=client_mac)

        # 4. Çevre birimlerini (BY, BO, Tarayıcı) yazıcılar tablosuna aktar
        _sync_peripherals(conn, old_record)

        conn.commit()
        
        # 5. Excel'e yedekle
        _backup_to_excel(conn)
        
        conn.close()
        return jsonify({"message": "Başarıyla kaydedildi."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def _sync_hostnames(conn, mahal_kodu):
    """Mahal koduna göre hostname oluşturur ve sıralar (Örn: AB2T5298x01)."""
    if not mahal_kodu or str(mahal_kodu).strip() == "" or str(mahal_kodu) == 'None':
        return
    
    # Bu mahalde bulunan tüm cihazları al (ID'ye göre sıralı)
    devices = conn.execute(
        "SELECT id FROM inventory WHERE mahal_kodu = ? ORDER BY id ASC",
        (mahal_kodu,)
    ).fetchall()
    
    if not devices:
        return

    # Noktaları temizle
    mahal_clean = str(mahal_kodu).replace('.', '').replace(' ', '').strip()
    
    for idx, dev in enumerate(devices):
        new_hostname = f"{mahal_clean}x{(idx + 1):02d}"
        conn.execute("UPDATE inventory SET hostname = ? WHERE id = ?", (new_hostname, dev['id']))


def _sync_peripherals(conn, record):
    """PC kaydındaki BY, BO, Tarayıcı seri numaralarını printers tablosuna aktarır."""
    mahal = record.get('mahal_adi', '') or ''
    pc_no = record.get('pc_no', '') or ''
    
    peripherals = [
        {'seri_field': 'by_seri', 'model': 'Barkod Yazıcı', 'pr_prefix': 'BY'},
        {'seri_field': 'bo_seri', 'model': 'Barkod Okuyucu', 'pr_prefix': 'BO'},
        {'seri_field': 'tarayici_seri', 'model': 'Tarayıcı', 'pr_prefix': 'TR'},
    ]
    
    for p in peripherals:
        seri = record.get(p['seri_field'], '')
        if not seri or seri.strip() == '':
            continue
        
        # Bu seri numarası ile printers tablosunda kayıt var mı kontrol et
        existing = conn.execute(
            "SELECT id FROM printers WHERE seri = ?", (seri,)
        ).fetchone()
        
        if existing:
            # Varsa mahal bilgisini güncelle
            conn.execute(
                "UPDATE printers SET mahal=? WHERE id=?",
                (mahal, existing['id'])
            )
        else:
            # Yoksa yeni kayıt ekle
            pr_no = f"{p['pr_prefix']}-{pc_no}" if pc_no else f"{p['pr_prefix']}-{seri[:6]}"
            conn.execute(
                "INSERT INTO printers (pr_no, model, seri, mac, ip, mahal) VALUES (?,?,?,?,?,?)",
                (pr_no, p['model'], seri, '', '', mahal)
            )


def _backup_to_excel(conn):
    """Envanter verisini Excel dosyasına yedekler."""
    try:
        all_items = conn.execute("SELECT * FROM inventory").fetchall()
        headers = ['PC', 'KULE', 'KAT', 'MAHAL KODU', 'MAHAL ADI', 'KEYOS MAHALİ', 'SAHADA', 'DEPO', 
                   'ARIZALI', 'MAHALSİZ', 'TELEFON', 'İP', 'BAĞLI OLAN YAZICILAR', 'PC SERİ NO', 
                   'MONİTÖR SERİ NO', 'MONİTÖR MODEL', '2. MONİTÖR SERİ NO', '2. MONİTÖR MODEL',
                   'WINDOWS', 'KEYOS', 'RDP', 
                   '6900 PR-NO', '5200 PR-NO', '8690 PR-NO', 'BARKOD YAZICI SERİ NO', 
                   'BARKOD OKUYUCU SERİ NO', 'TARAYICI SERİ NO', 'AÇIKLAMA']
        
        excel_data = []
        for row in all_items:
            excel_data.append({
                'PC': row['pc_no'], 'KULE': row['kule'], 'KAT': row['kat'], 'MAHAL KODU': row['mahal_kodu'],
                'MAHAL ADI': row['mahal_adi'], 'KEYOS MAHALİ': row['keyos_mahal'], 'SAHADA': row['sahada'],
                'DEPO': row['depo'], 'ARIZALI': row['arizali'], 'MAHALSİZ': row['mahalsiz'],
                'TELEFON': row['telefon'], 'İP': row['ip'], 'BAĞLI OLAN YAZICILAR': row['bagli_yazicilar'],
                'PC SERİ NO': row['pc_seri'], 'MONİTÖR SERİ NO': row['monitor_seri'], 
                'MONİTÖR MODEL': row['monitor_model'],
                '2. MONİTÖR SERİ NO': row['monitor2_seri'],
                '2. MONİTÖR MODEL': row['monitor2_model'],
                'WINDOWS': row['windows'], 'KEYOS': row['keyos'],
                'RDP': row['rdp'], '6900 PR-NO': row['pr6900'], '5200 PR-NO': row['pr5200'],
                '8690 PR-NO': row['pr8690'], 'BARKOD YAZICI SERİ NO': row['by_seri'], 
                'BARKOD OKUYUCU SERİ NO': row['bo_seri'], 'TARAYICI SERİ NO': row['tarayici_seri'], 
                'AÇIKLAMA': row['aciklama']
            })
            
        write_excel_data(ENV_EXCEL_PATH, excel_data, headers)
    except Exception as e:
        print(f"Excel yedekleme hatası: {e}")


@inventory_manager_bp.route('/add', methods=['POST'])
@require_admin
def add_inventory():
    """Yeni cihazı veritabanına sadece manuel olarak ekler."""
    data = request.json
    try:
        conn = get_db_connection()
        conn.execute('''INSERT INTO inventory (
            pc_no, ip, kule, mahal_kodu, mahal_adi, pc_seri, windows, keyos, sahada, device_type,
            assigned_to, phone, title, unit
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (
            data.get('pc_no'), data.get('ip'), data.get('kule'), data.get('mahal_kodu'),
            data.get('mahal_adi'), data.get('pc_seri'), data.get('windows'), data.get('keyos'),
            data.get('sahada'), data.get('device_type'), data.get('assigned_to'),
            data.get('phone'), data.get('title'), data.get('unit')
        ))
        
        # New: Sync hostnames for the new mahal
        _sync_hostnames(conn, data.get('mahal_kodu'))

        conn.commit()
        return jsonify({"message": "Yeni cihaz eklendi"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@inventory_manager_bp.route('/count', methods=['POST'])
def mark_counted():
    """Envanter sayım modunda bir cihazı 'sayıldı' olarak işaretler."""
    data = request.json
    device_id = data.get('id')
    counted_by = data.get('counted_by', 'Bilinmiyor')
    
    if not device_id:
        return jsonify({"error": "ID gerekli"}), 400
    
    try:
        conn = get_db_connection()
        conn.execute(
            "UPDATE inventory SET last_counted_at = GETDATE(), counted_by = ? WHERE id = ?",
            (counted_by, device_id)
        )
        conn.commit()
        conn.close()
        return jsonify({"message": "Cihaz sayıldı olarak işaretlendi"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@inventory_manager_bp.route('/count/undo', methods=['POST'])
def undo_mark_counted():
    """Bir cihazın sayım işaretini geri alır."""
    data = request.json
    device_id = data.get('id')
    
    if not device_id:
        return jsonify({"error": "ID gerekli"}), 400
    
    try:
        conn = get_db_connection()
        conn.execute(
            "UPDATE inventory SET last_counted_at = NULL, counted_by = NULL WHERE id = ?",
            (device_id,)
        )
        conn.commit()
        conn.close()
        return jsonify({"message": "Sayım geri alındı"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@inventory_manager_bp.route('/count/reset', methods=['POST'])
def reset_count():
    """Tüm sayım işaretlerini sıfırlar (yeni sayım başlatmak için)."""
    try:
        conn = get_db_connection()
        conn.execute("UPDATE inventory SET last_counted_at = NULL, counted_by = NULL")
        conn.commit()
        conn.close()
        return jsonify({"message": "Sayım sıfırlandı"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@inventory_manager_bp.route('/mahal_list', methods=['GET'])
def get_mahal_list():
    """mahal_telefon.xlsx dosyasından mahal ve telefon listesini getirir."""
    try:
        mahal_path = os.path.join(os.path.dirname(__file__), "..", "database", "mahal_telefon.xlsx")
        from core.excel_utils import read_excel_data
        
        # Mahal ve Mahal Adı listesini oku (Sayfa 0)
        mahal_data = read_excel_data(mahal_path, sheet_name=0)
        
        # Telefon bilgilerini oku (Sayfa 1 - Telefon sekmesi)
        phone_data = read_excel_data(mahal_path, sheet_name=1)
        
        # Telefonları bir haritaya koy (Mahal Adı -> Telefon)
        phone_map = {}
        for p in phone_data:
            m_name = (p.get('MAHAL ADI') or p.get('MÂHÂL ADI') or '').strip().upper()
            if m_name:
                phone_map[m_name] = p.get('TELEFON') or p.get('TEL') or ''

        # Sonucu oluştur
        result = []
        for m in mahal_data:
            m_code = (m.get('MAHAL') or '').strip()
            # MÂHÂL ADI (circumflex ile) veya MAHAL ADI
            m_name = (m.get('MÂHÂL ADI') or m.get('MAHAL ADI') or '').strip()
            
            if m_name:
                phone = phone_map.get(m_name.upper(), '')
                result.append({
                    'mahal': m_code,
                    'mahal_adi': m_name,
                    'telefon': phone
                })
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
