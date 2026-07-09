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
import mimetypes

# Windows Registry kaynaklı tarayıcı sorunlarını (Özellikle Opera) çözmek için MIME tipi zorlaması
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('image/svg+xml', '.svg')

from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv

app = Flask(__name__, static_folder=None)
# Reverse Proxy (Apache/Nginx vs) arkasında çalışırken gerçek IP'yi almak için:
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
app.url_map.strict_slashes = False
CORS(app)

# --- Uygulama Yapilandirmasi ---
BASE_DIR = project_root
PARENT_DIR = os.path.dirname(BASE_DIR)

DATA_DIR = BASE_DIR

# .env yukleme
env_path = os.path.join(DATA_DIR, ".env")
if not os.path.exists(env_path):
    env_path = os.path.join(DATA_DIR, "tools", ".env")
load_dotenv(env_path, override=True)

# --- Otomatik Arka Plan Görevleri (APScheduler) ---
# Görevler core.scheduler_logic içerisinde tanımlıdır.

app = Flask(__name__, static_folder=BASE_DIR, static_url_path='')
app.url_map.strict_slashes = False
CORS(app)

# Veritabani ve Modulleri Yukle
from core.database_sql import init_db
from core.utils import error_response

# --- Rate Limiting (ZORUNLU) ---
from core.limiter import limiter
limiter.init_app(app)

# Dosya yukleme limitini sinirsiz (veya cok yuksek) yapiyoruz ki ISO dosyalari falan yuklenebilsin
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0 # Statik dosyaların önbelleklenmesini devre dışı bırak
# app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16MB limit (IPTAL EDILDI)

# Blueprints (Eksiksiz Liste)
from modules.inventory_core import inventory_core_bp
from modules.inventory_pcs import inventory_pcs_bp
from modules.inventory_tablets import inventory_tablets_bp
from modules.inventory_queing import inventory_queing_bp
from modules.inventory_monitors import inventory_monitors_bp
from modules.inventory_mahal import inventory_mahal_bp

from modules.inventory_printers import inventory_printers_bp
from modules.inventory_barcode_printers import inventory_barcode_printers_bp
from modules.inventory_barcode_readers import inventory_barcode_readers_bp
from modules.inventory_scanners import inventory_scanners_bp
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
from modules.admin_reports import admin_reports_bp
from modules.installations_manager import installations_manager_bp
from modules.printer_pages_api import printer_pages_bp
from modules.integrations_manager import integrations_bp
from modules.desktop_central_service import desktop_central_service_bp

# Blueprint Kayitlari
# Inventory Blueprints
app.register_blueprint(inventory_core_bp, url_prefix='/api/inventory')
app.register_blueprint(inventory_core_bp, url_prefix='/api/dashboard', name='inventory_core_dashboard') # Alias for cached frontend
app.register_blueprint(inventory_pcs_bp, url_prefix='/api/inventory')
app.register_blueprint(inventory_tablets_bp, url_prefix='/api/inventory')
app.register_blueprint(inventory_queing_bp, url_prefix='/api/inventory')
app.register_blueprint(inventory_monitors_bp, url_prefix='/api/inventory')
app.register_blueprint(inventory_mahal_bp, url_prefix='/api/inventory')

# Printers Blueprints (Separated by device type as per Constitution)
app.register_blueprint(inventory_printers_bp, url_prefix='/api/inventory/printers')
app.register_blueprint(inventory_barcode_printers_bp, url_prefix='/api/inventory/barcode_printers')
app.register_blueprint(printer_pages_bp, url_prefix='/api/inventory/printer_pages')
app.register_blueprint(inventory_barcode_readers_bp, url_prefix='/api/inventory/barcode_readers')
app.register_blueprint(inventory_scanners_bp, url_prefix='/api/inventory/scanners')
app.register_blueprint(user_manager_bp, url_prefix='/api/users')
app.register_blueprint(areas_manager_bp, url_prefix='/api/areas')
app.register_blueprint(notes_manager_bp, url_prefix='/api/notes')
app.register_blueprint(depot_manager_bp, url_prefix='/api/depot')
app.register_blueprint(mahal_manager_bp, url_prefix='/api/mahal')
app.register_blueprint(service_manager_bp, url_prefix='/api/service')
app.register_blueprint(logs_manager_bp, url_prefix='/api/logs')
app.register_blueprint(document_service_bp, url_prefix='/api/downloads')
app.register_blueprint(document_service_bp, url_prefix='/api/documents', name='document_service_docs') # Added for backward compatibility with frontend
app.register_blueprint(bim_service_bp, url_prefix='/api/bim')
app.register_blueprint(keyos_service_bp, url_prefix='/api/keyos')
app.register_blueprint(desktop_central_service_bp, url_prefix='/api/desktop_central')
app.register_blueprint(monitoring_manager_bp, url_prefix='/api/system')
app.register_blueprint(admin_reports_bp, url_prefix='/api/admin/reports')
app.register_blueprint(installations_manager_bp, url_prefix='/api/installations')
app.register_blueprint(installations_manager_bp, url_prefix='/api/isvec', name='installations_manager_isvec')

# --- Alias for Cached Frontends ---
# Bazen tarayıcılar eski JS dosyasını (printers/batch_action) önbellekte tutabiliyor.
# 404 hatasını bypass etmek için doğrudan alias oluşturuyoruz.
@app.route('/api/printers/batch_action', methods=['POST'])
def batch_action_alias():
    from modules.inventory_printers import batch_action
    return batch_action()

@app.route('/api/system_info', methods=['GET'])
def get_system_info():
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        server_ip = s.getsockname()[0]
        s.close()
    except Exception:
        server_ip = request.host.split(':')[0]

    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if client_ip and ',' in client_ip:
        client_ip = client_ip.split(',')[0].strip()
        
    return jsonify({
        "server_ip": server_ip,
        "client_ip": client_ip,
        "version": "2.1.0"
    })

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
        
    # Prevent aggressive caching for the main HTML and static assets
    if not request.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'

    return response

@app.errorhandler(429)
def ratelimit_handler(e):
    return error_response(message="Çok fazla istek gönderildi, lütfen biraz bekleyin.", code=429)

from core.auth import require_auth

@app.route('/api/config')
def get_config():
    import os
    domain = os.getenv("HOSPITAL_DOMAIN", "kocaelish.com")
    return jsonify({
        "hospital_name": os.getenv("HOSPITAL_NAME", "Kocaeli Şehir Hastanesi"),
        "hospital_domain": domain,
        "links": {
            "bim": os.getenv("LINK_BIM", f"http://bim.{domain}/"),
            "mym": os.getenv("LINK_MYM", f"https://mym.{domain}/"),
            "hbys": os.getenv("LINK_HBYS", f"https://hbys.{domain}/hbys-web/desktop/desktop.html"),
            "cups": os.getenv("LINK_CUPS", f"http://print01.{domain}:49631/printers/"),
            "bulut": os.getenv("LINK_BULUT", f"https://bulut.{domain}/index.php/login"),
            "ortak_alan": os.getenv("LINK_ORTAK_ALAN", f"http://ortakalan.{domain}/WebClientNew/Login"),
            "speedtest": os.getenv("LINK_SPEEDTEST", f"http://speedtest.{domain}/"),
            "magicinfo_m1": os.getenv("LINK_MAGICINFO_M1", f"http://minfo-01.{domain}:7001/MagicInfo/login.htm?cmd=INIT#"),
            "magicinfo_m2": os.getenv("LINK_MAGICINFO_M2", f"http://minfo-02.{domain}:7001/MagicInfo/login.htm?cmd=INIT"),
            "magicinfo_m3": os.getenv("LINK_MAGICINFO_M3", f"http://minfo-03.{domain}:7001/MagicInfo/login.htm?cmd=INIT"),
            "desktop_central": os.getenv("LINK_DESKTOP_CENTRAL", f"https://desktopcentral.{domain}:8383/webclient#/uems/home/summary"),
            "lms": os.getenv("LINK_LMS", f"https://lms.{domain}/Login")
        }
    })

@app.route('/api/debug_db_state')
def debug_db_state():
    from core.database_sql import query_db
    try:
        rows = query_db("SELECT id, pc_no, ip, windows, keyos, last_active, keyos_last_active FROM pcs WHERE pc_no IN ('PC-005', 'PC-014', 'PC-006', 'PC-007')")
        return {"success": True, "data": rows}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.route('/api/debug_pc_14')
def debug_pc_14():
    from core.database_sql import query_db
    try:
        row = query_db("SELECT id, pc_no, ip, windows, keyos, last_active FROM pcs WHERE ip = '10.241.22.22'")
        from modules.inventory_core import _SCHEMA_CACHE
        return jsonify({
            "cache": list(_SCHEMA_CACHE.get('pcs', [])),
            "db_row": row
        })
    except Exception as e:
        return jsonify({"error": str(e)})

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
    
    for folder in ['static', 'img', 'assets', 'frontend']:
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

    try:
        from core.scheduler_logic import init_scheduler
        init_scheduler()
    except Exception as e:
        print(f"[!] APScheduler Başlatılamadı: {e}")

        
    _SYSTEM_INITIALIZED = True

# Initialize immediately upon import
initialize_system()

if __name__ == '__main__':

    # Waitress yerine Flask'ın kendi detaylı log veren sunucusunu kullanıyoruz (Hata ayıklama için)
    print("[*] Sunucu 5000 portunda (Detaylı Log Modu) yayında...")
    app.run(host='0.0.0.0', port=5000, debug=False)

