from flask import Blueprint, jsonify, request
from core.database_sql import query_db, get_db_connection
from core.auth import require_auth, require_editor, require_admin
import pandas as pd
import os

magicinfo_manager_bp = Blueprint('magicinfo_manager', __name__)

EXCEL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'database', 'magicinfo.xls'))

@magicinfo_manager_bp.route('/get_all', methods=['GET'])
@require_auth
def get_magicinfo_devices():
    """Veritabanındaki MagicInfo cihazlarını listeler. Boşsa Excel'den aktarır."""
    try:
        devices = query_db("SELECT * FROM magicinfo_devices")
        
        if not devices:
            # Excel'den aktar
            if os.path.exists(EXCEL_PATH):
                # Excel dosyasındaki tüm sekmeleri oku
                xls = pd.ExcelFile(EXCEL_PATH)
                for sheet_name in xls.sheet_names:
                    df = pd.read_excel(xls, sheet_name=sheet_name)
                    df.columns = [str(c).strip() for c in df.columns]
                    df = df.fillna('')
                    
                    for _, row in df.iterrows():
                        name = str(row.get('Aygıt Adı') or row.get('Device Name') or row.get('Name', 'Bilinmiyor'))
                        if name.lower() in ('bilinmiyor', '', 'none'): continue
                        
                        mac = str(row.get('MAC Adresi') or row.get('MAC Address') or row.get('MAC', '-'))
                        ip = str(row.get('IP') or row.get('IP Address') or '-')
                        location = str(row.get('Konum') or row.get('Location') or '')
                        
                        # Eğer satırda sunucu bilgisi yoksa sekme adını kullan
                        server = str(row.get('Sunucu') or row.get('Server') or sheet_name)
                        
                        query_db("INSERT INTO magicinfo_devices (name, mac, ip, location, server) VALUES (?, ?, ?, ?, ?)",
                                 (name, mac, ip, location, server))
                
                devices = query_db("SELECT * FROM magicinfo_devices")
        
        return jsonify([dict(d) for d in devices])
    except Exception as e:
        print(f"MagicInfo Get Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@magicinfo_manager_bp.route('/update', methods=['POST'])
@require_editor
def update_device():
    """Cihaz bilgilerini günceller."""
    data = request.json
    device_id = data.get('id')
    name = data.get('name')
    location = data.get('location')
    server = data.get('server')
    
    if not device_id:
        return jsonify({"success": False, "error": "ID gerekli"}), 400
        
    try:
        query_db("UPDATE magicinfo_devices SET name=?, location=?, server=? WHERE id=?",
                 (name, location, server, device_id))
        return jsonify({"success": True, "message": "Cihaz güncellendi."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@magicinfo_manager_bp.route('/action', methods=['POST'])
@require_editor
def device_action():
    """MagicInfo ekranlarına komut gönderir (Power, Reboot, Source, vs)"""
    data = request.json
    action = data.get('action') # POWER_ON, POWER_OFF, REBOOT, SOURCE
    ip = data.get('ip')
    
    # Burada MagicInfo API entegrasyonu yapılmalı
    # Şimdilik sadece başarılı yanıt dönüyoruz.
    return jsonify({
        "success": True, 
        "message": f"{ip} cihazı için {action} komutu API'ye iletildi. (API Entegrasyonu Bekleniyor)"
    })

@magicinfo_manager_bp.route('/screenshot', methods=['GET'])
def get_screenshot():
    """Canlı ekran resmini çeker."""
    from flask import send_file
    ip = request.args.get('ip')
    
    # Gerçek API entegre edilene kadar dummy/placeholder döneriz
    # Varsayılan logo dosyasını gönderelim ki img tag'i kırılmasın
    try:
        return send_file('../logo/keydata.png', mimetype='image/png')
    except:
        return jsonify({"success": False, "error": "Logo bulunamadı."})
