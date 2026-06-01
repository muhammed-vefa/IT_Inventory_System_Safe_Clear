import os
import sys
# Path patch for sub-folder execution
project_root = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(project_root) == 'tools':
    project_root = os.path.dirname(project_root)
if project_root not in sys.path:
    sys.path.append(project_root)
os.chdir(project_root)

import os
import sys
import subprocess
from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

# --- Uygulama Yapilandirmasi ---
BASE_DIR = project_root
PARENT_DIR = os.path.dirname(BASE_DIR)

DATA_DIR = BASE_DIR

# .env yukleme
env_path = os.path.join(DATA_DIR, ".env")
if not os.path.exists(env_path):
    env_path = os.path.join(DATA_DIR, "tools", ".env")
load_dotenv(env_path, override=True)

# --- Cumartesi Otomatik Yedekleme ---
def check_saturday_backup():
    import datetime
    from core.database_sql import backup_sql_db
    
    today = datetime.datetime.now()
    if today.weekday() == 5: # 5 = Cumartesi
        yedek_klasor = os.path.join(BASE_DIR, "database", "yedek")
        bugun_str = today.strftime("%Y-%m-%d")
        
        # Bugun yedek alinmis mi kontrol et
        alinmis = False
        if os.path.exists(yedek_klasor):
            for f in os.listdir(yedek_klasor):
                if bugun_str in f:
                    alinmis = True
                    break
        
        if not alinmis:
            print("[*] Bugün Cumartesi ve henüz yedek alınmamış. Otomatik yedekleme başlatılıyor...")
            backup_sql_db()
        else:
            print("[*] Bugün Cumartesi, ancak bugünün yedeği zaten mevcut.")

check_saturday_backup()

app = Flask(__name__, static_folder=BASE_DIR, static_url_path='')
app.url_map.strict_slashes = False
CORS(app)

# Veritabani ve Modulleri Yukle
from core.database_sql import init_db
from core.utils import error_response

# --- Rate Limiting (ZORUNLU) ---
from core.limiter import limiter
limiter.init_app(app)

app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16MB limit

# Blueprints (Eksiksiz Liste)
from modules.inventory_core import inventory_core_bp
from modules.inventory_pcs import inventory_pcs_bp
from modules.inventory_tablets import inventory_tablets_bp
from modules.inventory_queing import inventory_queing_bp
from modules.inventory_monitors import inventory_monitors_bp
from modules.inventory_mahal import inventory_mahal_bp

from modules.printers_printers import printers_printers_bp
from modules.printers_barcode_printers import printers_barcode_printers_bp
from modules.printers_barcode_readers import printers_barcode_readers_bp
from modules.printers_scanners import printers_scanners_bp
from modules.user_manager import user_manager_bp
from modules.areas_manager import areas_manager_bp
from modules.notes_manager import notes_manager_bp
from modules.depot_manager import depot_manager_bp
from modules.mahal_manager import mahal_manager_bp
from modules.service_manager import service_manager_bp
from modules.logs_manager import logs_manager_bp
from modules.document_service import document_service_bp
from modules.bim_service import bim_service_bp
from modules.keyos_service import keyos_service_bp
from modules.monitoring_manager import monitoring_manager_bp
from modules.bat_manager import bat_manager_bp
from modules.admin_reports import admin_reports_bp

# Blueprint Kayitlari
# Inventory Blueprints
app.register_blueprint(inventory_core_bp, url_prefix='/api/inventory')
app.register_blueprint(inventory_pcs_bp, url_prefix='/api/inventory')
app.register_blueprint(inventory_tablets_bp, url_prefix='/api/inventory')
app.register_blueprint(inventory_queing_bp, url_prefix='/api/inventory')
app.register_blueprint(inventory_monitors_bp, url_prefix='/api/inventory')
app.register_blueprint(inventory_mahal_bp, url_prefix='/api/inventory')

# Printers Blueprints (Separated by device type as per Constitution)
app.register_blueprint(printers_printers_bp, url_prefix='/api/printers/printers')
app.register_blueprint(printers_barcode_printers_bp, url_prefix='/api/printers/barcode_printers')
app.register_blueprint(printers_barcode_readers_bp, url_prefix='/api/printers/barcode_readers')
app.register_blueprint(printers_scanners_bp, url_prefix='/api/printers/scanners')
app.register_blueprint(user_manager_bp, url_prefix='/api/users')
app.register_blueprint(areas_manager_bp, url_prefix='/api/areas')
app.register_blueprint(notes_manager_bp, url_prefix='/api/notes')
app.register_blueprint(depot_manager_bp, url_prefix='/api/depot')
app.register_blueprint(mahal_manager_bp, url_prefix='/api/mahal')
app.register_blueprint(service_manager_bp, url_prefix='/api/service')
app.register_blueprint(logs_manager_bp, url_prefix='/api/logs')
app.register_blueprint(document_service_bp, url_prefix='/api/downloads')
app.register_blueprint(bim_service_bp, url_prefix='/api/bim')
app.register_blueprint(keyos_service_bp, url_prefix='/api/keyos')
app.register_blueprint(monitoring_manager_bp, url_prefix='/api/system')
app.register_blueprint(bat_manager_bp, url_prefix='/api/bat_apps')
app.register_blueprint(admin_reports_bp, url_prefix='/api/admin/reports')

# --- Alias for Cached Frontends ---
# Bazen tarayıcılar eski JS dosyasını (printers/batch_action) önbellekte tutabiliyor.
# 404 hatasını bypass etmek için doğrudan alias oluşturuyoruz.
@app.route('/api/printers/batch_action', methods=['POST'])
def batch_action_alias():
    from modules.printers_printers import batch_action
    return batch_action()

# --- Global Exception Handler (PRODUCTION HARDENING) ---
@app.errorhandler(Exception)
def handle_exception(e):
    # Log the error
    print(f"[UNHANDLED EXCEPTION] {str(e)}")
    import traceback
    traceback.print_exc()
    
    # Return standard error format
    return error_response(
        message="Beklenmeyen bir hata oluştu.",
        details=str(e) if app.debug else "Lütfen sistem yöneticisi ile iletişime geçin.",
        code=500
    )

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/api/'):
        return error_response(message="Endpoint bulunamadı", code=404)
    return send_from_directory(BASE_DIR, 'index.html')

@app.after_request
def audit_logger(response):
    """Tüm API isteklerini loglar (Production Hardening)."""
    # Statik dosyaları atla
    if request.path.startswith('/api/'):
        user_id = "Guest"
        if hasattr(request, 'current_user') and request.current_user:
            user_id = request.current_user.get('display_name') or request.current_user.get('username') or request.current_user.get('id', 'Unknown')
        else:
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
                from core.auth import decode_token
                payload = decode_token(token)
                if payload:
                    user_id = payload.get('display_name') or payload.get('username') or 'Unknown'
            
        client_ip = request.remote_addr
        method = request.method
        path = request.path
        
        import datetime
        print(f"[MATRIX] [{datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]}] HTTP {method} {path} | Cihaz: {client_ip} | Kullanici: {user_id}")
        
    return response

@app.errorhandler(429)
def ratelimit_handler(e):
    return error_response(message="Çok fazla istek gönderildi, lütfen biraz bekleyin.", code=429)

from core.auth import require_auth

@app.route('/api/dashboard/stats')
@require_auth
def dashboard_stats():
    from modules.inventory_core import get_stats
    return get_stats()

@app.route('/')
def index():
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/api/logs/click', methods=['POST'])
def log_click():
    data = request.json or {}
    element = data.get('element', 'Bilinmeyen Element')
    user = data.get('user', 'Guest')
    if user == 'undefined': user = 'Guest'
    print(f"[MATRIX_CLICK] Kullanici '{user}' sunu tikladi: {element}")
    return jsonify({"status": "ok"})

@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE']) # SPA ve Statik Destek
def serve_static(path):
    if path.startswith('api/'):
        return error_response(message="Endpoint bulunamadı", code=404)
        
    # GUVENLIK KONTROLU (Production Hardening): Hassas dosya uzantilarini ve klasorleri engelle
    yasakli_uzantilar = ['.py', '.env', '.db', '.bak', '.log', '.bat', '.md', '.sql']
    yasakli_klasorler = ['core/', 'modules/', 'tools/', 'database/', 'logs/']
    
    path_lower = path.lower()
    if any(path_lower.endswith(ext) for ext in yasakli_uzantilar) or any(path_lower.startswith(f) for f in yasakli_klasorler):
        return error_response(message="Bu dosyaya erisim yetkiniz yok (Security Policy).", code=403)
        
    file_path = os.path.join(BASE_DIR, path)
    if os.path.isfile(file_path):
        return send_from_directory(BASE_DIR, path)
    
    for folder in ['img', 'logo', 'assets', 'frontend']:
        alt_path = os.path.join(BASE_DIR, folder, path)
        if os.path.isfile(alt_path):
            return send_from_directory(os.path.join(BASE_DIR, folder), path)
            
    return send_from_directory(BASE_DIR, 'index.html')

# --- STARTUP SEQUENCE (Runs on both direct execution and WSGI import) ---
_SYSTEM_INITIALIZED = False

def initialize_system():
    global _SYSTEM_INITIALIZED
    if _SYSTEM_INITIALIZED:
        return
        
    print("\n" + "="*60)
    print("   KEYDATA IT ENVANTER SISTEMI - STARTUP SEQUENCE")
    print("="*60)
    print(f"[*] KOD DIZINI (BASE):  {BASE_DIR}")
    print(f"[*] VERI DIZINI (DATA):  {DATA_DIR}")
    
    try:
        print("[*] Veritabanı onarımı ve migrasyonlar başlatılıyor (init_db)...")
        init_db()
        print("[*] Veritabanı şeması güncel.")
    except Exception as e:
        print(f"[!] Veritabanı Migrasyon Hatası: {e}")


        
    _SYSTEM_INITIALIZED = True

# Initialize immediately upon import
initialize_system()

if __name__ == '__main__':

    # Waitress yerine Flask'ın kendi detaylı log veren sunucusunu kullanıyoruz (Hata ayıklama için)
    print("[*] Sunucu 5000 portunda (Detaylı Log Modu) yayında...")
    app.run(host='0.0.0.0', port=5000, debug=False)

