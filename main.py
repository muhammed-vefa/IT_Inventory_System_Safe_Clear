import os
import sys
import subprocess
from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

# --- Otomatik Bagimlilik Kontrolu ---
def bootstrap():
    required = [
        ('flask', 'flask'), ('flask_cors', 'flask-cors'), ('pyodbc', 'pyodbc'),
        ('openpyxl', 'openpyxl'), ('pandas', 'pandas'), ('waitress', 'waitress'),
        ('jwt', 'pyjwt'), ('flask_limiter', 'flask-limiter')
    ]
    for mod, pkg in required:
        try: __import__(mod)
        except ImportError: subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

bootstrap()

# --- Uygulama Yapilandirmasi ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# Tum dizini statik olarak aciyoruz (Kullanicinin istedigi restorasyon)
app = Flask(__name__, static_folder=BASE_DIR, static_url_path='')
CORS(app)
load_dotenv()

# Veritabani ve Modul Importlari
from core.database_sql import init_db
from core.extensions import limiter

# Blueprints
from modules.inventory_manager import inventory_manager_bp
from modules.user_manager import user_manager_bp
# Diger modulleri placeholder'lar uzerinden bagliyoruz (Hata vermemesi icin)
from modules.placeholders import (
    printer_manager_bp, areas_manager_bp, notes_manager_bp, 
    depot_manager_bp, document_service_bp, logs_manager_bp,
    mahal_manager_bp, service_manager_bp, bim_service_bp, keyos_service_bp
)

app.register_blueprint(inventory_manager_bp, url_prefix='/api/inventory')
app.register_blueprint(user_manager_bp, url_prefix='/api/users')
app.register_blueprint(printer_manager_bp, url_prefix='/api/printers')
app.register_blueprint(areas_manager_bp, url_prefix='/api/areas')
app.register_blueprint(notes_manager_bp, url_prefix='/api/notes')
app.register_blueprint(depot_manager_bp, url_prefix='/api/depot')
app.register_blueprint(document_service_bp, url_prefix='/api/documents')
app.register_blueprint(logs_manager_bp, url_prefix='/api/logs')
app.register_blueprint(mahal_manager_bp, url_prefix='/api/mahal')
app.register_blueprint(service_manager_bp, url_prefix='/api/service')
app.register_blueprint(bim_service_bp, url_prefix='/api/bim')
app.register_blueprint(keyos_service_bp, url_prefix='/api/keyos')

# --- Ana Yonlendirme (SPA Destekli) ---
@app.route('/')
def index():
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    # Eger istenen dosya fiziksel olarak varsa onu gonder (CSS, JS, Logo vb.)
    file_path = os.path.join(BASE_DIR, path)
    if os.path.isfile(file_path):
        return send_from_directory(BASE_DIR, path)
    # Yoksa index.html gonder (Frontend router devralir)
    return send_from_directory(BASE_DIR, 'index.html')

if __name__ == '__main__':
    if not os.path.exists('logs'): os.makedirs('logs')
    init_db()
    print("RESTORE EDILDI: Sunucu http://localhost:5000 adresinde aktif.")
    try:
        from waitress import serve
        serve(app, host='0.0.0.0', port=5000)
    except:
        app.run(host='0.0.0.0', port=5000)
